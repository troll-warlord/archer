from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pulumi
import pulumi_aws as aws

from archer.modules.aws.networking.security_groups import SecurityGroupBuildResult
from archer.modules.aws.networking.subnets import SubnetBuildResult
from archer.modules.aws.utils import make_tags, resolve_subnet_ids

if TYPE_CHECKING:
    from archer.models import AwsResources, InfrastructureConfig
    from archer.models.aws import EbsVolumeConfig, SecurityGroupRuleConfig


@dataclass
class Ec2BuildResult:
    instances: dict[str, aws.ec2.Instance] = field(default_factory=dict)
    security_groups: dict[str, aws.ec2.SecurityGroup] = field(default_factory=dict)
    outputs: dict[str, pulumi.Output[Any]] = field(default_factory=dict)


class Ec2Builder:
    def __init__(
        self,
        config: InfrastructureConfig,
        subnet_result: SubnetBuildResult,
        shared_sg_result: SecurityGroupBuildResult,
    ) -> None:
        self._config = config
        self._subnet_result = subnet_result
        self._shared_sg_result = shared_sg_result

    def build(self) -> Ec2BuildResult:
        resources: AwsResources = self._config.resources  # type: ignore[assignment]
        if not resources.ec2:
            return Ec2BuildResult()

        result = Ec2BuildResult()

        for ec2_cfg in resources.ec2:
            # Resolve subnet: prefer raw subnet_id (existing infra), else look up
            # the archer-declared subnet by name.
            subnet_id_inputs, subnet_deps = resolve_subnet_ids(
                [ec2_cfg.subnet_ref] if ec2_cfg.subnet_ref else [],
                [ec2_cfg.subnet_id] if ec2_cfg.subnet_id else [],
                self._subnet_result,
            )
            subnet_id = subnet_id_inputs[0] if subnet_id_inputs else None
            sg_ids = self._resolve_security_groups(ec2_cfg, result)

            kwargs: dict[str, Any] = {
                "instance_type": ec2_cfg.instance_type,
                "ami": ec2_cfg.ami,
                "subnet_id": subnet_id,
                "associate_public_ip_address": ec2_cfg.assign_public_ip,
                "vpc_security_group_ids": sg_ids,
                "tags": self._tags(ec2_cfg.name, ec2_cfg.tags),
            }
            if ec2_cfg.key_name:
                kwargs["key_name"] = ec2_cfg.key_name
            if ec2_cfg.root_volume:
                kwargs["root_block_device"] = aws.ec2.InstanceRootBlockDeviceArgs(
                    volume_type=ec2_cfg.root_volume.volume_type,
                    volume_size=ec2_cfg.root_volume.volume_size_gb,
                    encrypted=ec2_cfg.root_volume.encrypted,
                    kms_key_id=ec2_cfg.root_volume.kms_key_id,
                    delete_on_termination=ec2_cfg.root_volume.delete_on_termination,
                )
            if ec2_cfg.extra_volumes:
                kwargs["ebs_block_devices"] = [self._ebs_block_device(vol, i) for i, vol in enumerate(ec2_cfg.extra_volumes)]

            instance = aws.ec2.Instance(
                ec2_cfg.name,
                **kwargs,
                opts=pulumi.ResourceOptions(depends_on=subnet_deps) if subnet_deps else None,
            )

            result.instances[ec2_cfg.name] = instance
            result.outputs[f"ec2_{ec2_cfg.name}_instance_id"] = instance.id
            result.outputs[f"ec2_{ec2_cfg.name}_private_ip"] = instance.private_ip
            if ec2_cfg.assign_public_ip:
                result.outputs[f"ec2_{ec2_cfg.name}_public_ip"] = instance.public_ip

        return result

    def _resolve_security_groups(self, ec2_cfg: Any, result: Ec2BuildResult) -> list[pulumi.Output[str]]:
        sg_ids: list[pulumi.Output[str]] = []

        if ec2_cfg.security_group:
            sg_name = ec2_cfg.security_group.name or f"{ec2_cfg.name}-sg"
            sg = aws.ec2.SecurityGroup(
                sg_name,
                vpc_id=self._find_vpc_id(ec2_cfg),
                description=ec2_cfg.security_group.description or f"SG for {ec2_cfg.name}",
                ingress=[self._ingress_rule(rule) for rule in ec2_cfg.security_group.ingress],
                egress=[self._egress_rule(rule) for rule in ec2_cfg.security_group.egress]
                or [
                    aws.ec2.SecurityGroupEgressArgs(
                        protocol="-1",
                        from_port=0,
                        to_port=0,
                        cidr_blocks=["0.0.0.0/0"],
                    )
                ],
                tags=self._tags(sg_name),
            )
            result.security_groups[ec2_cfg.name] = sg
            result.outputs[f"ec2_{ec2_cfg.name}_security_group_id"] = sg.id
            sg_ids.append(sg.id)

        for sg_ref in ec2_cfg.security_group_refs:
            shared_sg = self._shared_sg_result.sg_map.get(sg_ref)
            if shared_sg:
                sg_ids.append(shared_sg.id)

        # Append any existing (external) security group IDs declared directly in config.
        for existing_sg_id in ec2_cfg.existing_security_group_ids:
            sg_ids.append(existing_sg_id)

        if not sg_ids and self._shared_sg_result.default_sg:
            sg_ids.append(self._shared_sg_result.default_sg.id)

        return sg_ids

    def _find_vpc_id(self, ec2_cfg: Any) -> pulumi.Input[str]:
        # 1. Explicit vpc_id on the EC2 config — for existing/external VPCs.
        if ec2_cfg.vpc_id:
            return ec2_cfg.vpc_id
        # 2. Archer-created VPC, surfaced through the shared security group result.
        if self._shared_sg_result.default_sg:
            return self._shared_sg_result.default_sg.vpc_id
        raise ValueError(f"EC2 instance '{ec2_cfg.name}': inline security_group requires a VPC. Set ec2.vpc_id (for existing VPCs) or declare a vpc block.")

    def _ingress_rule(self, rule: SecurityGroupRuleConfig) -> aws.ec2.SecurityGroupIngressArgs:
        return aws.ec2.SecurityGroupIngressArgs(
            protocol=rule.protocol,
            from_port=rule.from_port,
            to_port=rule.to_port,
            cidr_blocks=rule.cidr_blocks,
            description=rule.description,
        )

    def _egress_rule(self, rule: SecurityGroupRuleConfig) -> aws.ec2.SecurityGroupEgressArgs:
        return aws.ec2.SecurityGroupEgressArgs(
            protocol=rule.protocol,
            from_port=rule.from_port,
            to_port=rule.to_port,
            cidr_blocks=rule.cidr_blocks,
            description=rule.description,
        )

    def _ebs_block_device(self, volume: EbsVolumeConfig, index: int = 0) -> aws.ec2.InstanceEbsBlockDeviceArgs:
        # device_name is optional in config; fall back to /dev/xvdb, /dev/xvdc, …
        device = volume.device_name or f"/dev/xvd{chr(ord('b') + index)}"
        return aws.ec2.InstanceEbsBlockDeviceArgs(
            device_name=device,
            volume_type=volume.volume_type,
            volume_size=volume.volume_size_gb,
            encrypted=volume.encrypted,
            kms_key_id=volume.kms_key_id,
            delete_on_termination=volume.delete_on_termination,
        )

    def _tags(self, name: str, extra: dict[str, str] | None = None) -> dict[str, str]:
        return make_tags(self._config.project, self._config.stack, name, extra, global_tags=dict(self._config.tags))
