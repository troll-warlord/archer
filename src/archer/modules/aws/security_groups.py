from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pulumi
import pulumi_aws as aws

from archer.modules.aws.utils import make_tags
from archer.modules.aws.vpc import VpcBuildResult

if TYPE_CHECKING:
    from archer.models import InfrastructureConfig
    from archer.models.aws import AwsResources


@dataclass
class SecurityGroupBuildResult:
    default_sg: aws.ec2.SecurityGroup | None = None
    sg_map: dict[str, aws.ec2.SecurityGroup] = field(default_factory=dict)
    outputs: dict[str, pulumi.Output[Any]] = field(default_factory=dict)


class SecurityGroupBuilder:
    def __init__(self, config: InfrastructureConfig, vpc_result: VpcBuildResult) -> None:
        self._config = config
        self._vpc_result = vpc_result

    def build(self) -> SecurityGroupBuildResult:
        vpc = self._vpc_result.vpc
        if not vpc:
            return SecurityGroupBuildResult(default_sg=None)

        result = SecurityGroupBuildResult(default_sg=None)
        resources: AwsResources = self._config.resources  # type: ignore[assignment]

        # -----------------------------------------------------------------------
        # 1. Default project-wide SG (always created when a VPC exists)
        # -----------------------------------------------------------------------
        default_name = f"{self._config.project}-default-sg"
        default_sg = aws.ec2.SecurityGroup(
            default_name,
            vpc_id=vpc.id,
            description="archer-managed shared default security group",
            egress=[
                aws.ec2.SecurityGroupEgressArgs(
                    protocol="-1",
                    from_port=0,
                    to_port=0,
                    cidr_blocks=["0.0.0.0/0"],
                    description="Allow all outbound traffic",
                )
            ],
            tags=self._tags(default_name),
        )
        result.default_sg = default_sg
        result.sg_map["default"] = default_sg
        result.outputs["default_security_group_id"] = default_sg.id

        # -----------------------------------------------------------------------
        # 2. Named SGs declared in AwsResources.security_groups
        # -----------------------------------------------------------------------
        for sg_cfg in getattr(resources, "security_groups", []):
            ingress_args = [
                aws.ec2.SecurityGroupIngressArgs(
                    protocol=rule.protocol,
                    from_port=rule.from_port,
                    to_port=rule.to_port,
                    cidr_blocks=rule.cidr_blocks,
                    description=rule.description or "",
                )
                for rule in sg_cfg.ingress_rules
            ]
            egress_args = [
                aws.ec2.SecurityGroupEgressArgs(
                    protocol=rule.protocol,
                    from_port=rule.from_port,
                    to_port=rule.to_port,
                    cidr_blocks=rule.cidr_blocks,
                    description=rule.description or "",
                )
                for rule in sg_cfg.egress_rules
            ]
            # Default: allow all outbound when no explicit egress rules given
            if not egress_args:
                egress_args = [
                    aws.ec2.SecurityGroupEgressArgs(
                        protocol="-1",
                        from_port=0,
                        to_port=0,
                        cidr_blocks=["0.0.0.0/0"],
                        description="Allow all outbound traffic",
                    )
                ]

            sg = aws.ec2.SecurityGroup(
                sg_cfg.name,
                vpc_id=vpc.id,
                description=sg_cfg.description,
                ingress=ingress_args,
                egress=egress_args,
                tags=self._tags(sg_cfg.name, sg_cfg.tags),
            )
            result.sg_map[sg_cfg.name] = sg
            result.outputs[f"security_group_{sg_cfg.name}_id"] = sg.id

        return result

    def _tags(self, name: str, extra: dict[str, str] | None = None) -> dict[str, str]:
        return make_tags(self._config.project, self._config.stack, name, extra, global_tags=dict(self._config.tags))
