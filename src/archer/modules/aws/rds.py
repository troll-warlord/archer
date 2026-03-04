from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pulumi
import pulumi_aws as aws

from archer.modules.aws.subnets import SubnetBuildResult
from archer.modules.aws.utils import make_tags, resolve_subnet_ids, resolve_vpc_id
from archer.modules.aws.vpc import VpcBuildResult

if TYPE_CHECKING:
    from archer.models import AwsResources, InfrastructureConfig

_ENGINE_PORT: dict[str, int] = {
    "postgres": 5432,
    "mysql": 3306,
    "mariadb": 3306,
    "oracle-ee": 1521,
    "sqlserver-ex": 1433,
    "sqlserver-web": 1433,
}


@dataclass
class RdsBuildResult:
    instances: dict[str, aws.rds.Instance] = field(default_factory=dict)
    outputs: dict[str, pulumi.Output[Any]] = field(default_factory=dict)


class RdsBuilder:
    def __init__(self, config: InfrastructureConfig, vpc_result: VpcBuildResult, subnet_result: SubnetBuildResult) -> None:
        self._config = config
        self._vpc_result = vpc_result
        self._subnet_result = subnet_result

    def build(self) -> RdsBuildResult:
        resources: AwsResources = self._config.resources  # type: ignore[assignment]
        if not resources.rds:
            return RdsBuildResult()

        result = RdsBuildResult()

        for rds_cfg in resources.rds:
            db_sg = self._build_security_group(rds_cfg)
            subnet_group = self._build_subnet_group(rds_cfg)
            db_instance = self._build_instance(rds_cfg, db_sg, subnet_group)

            result.instances[rds_cfg.name] = db_instance
            result.outputs[f"rds_{rds_cfg.name}_id"] = db_instance.id
            result.outputs[f"rds_{rds_cfg.name}_endpoint"] = db_instance.endpoint
            result.outputs[f"rds_{rds_cfg.name}_address"] = db_instance.address

        return result

    def _build_security_group(self, rds_cfg: Any) -> aws.ec2.SecurityGroup | None:
        # Resolve VPC: prefer raw vpc_id on the config (existing VPC),
        # else use the archer-created VPC.
        vpc_id, vpc_deps = resolve_vpc_id(self._vpc_result, rds_cfg.vpc_id)
        if not vpc_id:
            return None

        port = _ENGINE_PORT.get(rds_cfg.engine, 5432)
        sg_name = f"{rds_cfg.name}-sg"
        # Use the archer VPC CIDR for ingress scope when available;
        # fall back to broad private-space CIDR when using an existing VPC.
        vpc_cidr: pulumi.Input[str] = (
            self._vpc_result.vpc.cidr_block  # type: ignore[union-attr]
            if self._vpc_result.vpc
            else "10.0.0.0/8"
        )

        return aws.ec2.SecurityGroup(
            sg_name,
            vpc_id=vpc_id,
            description=f"archer-managed SG for RDS {rds_cfg.name}",
            ingress=[
                aws.ec2.SecurityGroupIngressArgs(
                    protocol="tcp",
                    from_port=port,
                    to_port=port,
                    cidr_blocks=[vpc_cidr],  # type: ignore[list-item]
                    description=f"Allow {rds_cfg.engine} access from within the VPC",
                )
            ],
            egress=[
                aws.ec2.SecurityGroupEgressArgs(
                    protocol="-1",
                    from_port=0,
                    to_port=0,
                    cidr_blocks=["0.0.0.0/0"],
                )
            ],
            tags=self._tags(sg_name),
            opts=pulumi.ResourceOptions(depends_on=vpc_deps) if vpc_deps else None,
        )

    def _build_subnet_group(self, rds_cfg: Any) -> aws.rds.SubnetGroup:
        # Resolve subnets: prefer raw subnet_ids (existing infra), else look up
        # archer-declared subnets by name.
        subnet_id_inputs, subnet_deps = resolve_subnet_ids(
            rds_cfg.subnet_refs,
            rds_cfg.subnet_ids,
            self._subnet_result,
        )
        return aws.rds.SubnetGroup(
            f"{rds_cfg.name}-subnet-group",
            subnet_ids=subnet_id_inputs,  # type: ignore[arg-type]
            tags=self._tags(f"{rds_cfg.name}-subnet-group"),
            opts=pulumi.ResourceOptions(depends_on=subnet_deps) if subnet_deps else None,
        )

    def _build_instance(self, rds_cfg: Any, db_sg: aws.ec2.SecurityGroup | None, subnet_group: aws.rds.SubnetGroup) -> aws.rds.Instance:
        password = os.environ.get(rds_cfg.password_env_var)
        if not password:
            pulumi.log.warn(
                f"Environment variable '{rds_cfg.password_env_var}' is not set for RDS instance '{rds_cfg.name}'. Using a placeholder password - replace before production use!"
            )
            password = "ChangeMe123!"

        return aws.rds.Instance(
            rds_cfg.name,
            engine=rds_cfg.engine,
            engine_version=rds_cfg.engine_version,
            instance_class=rds_cfg.instance_class,
            allocated_storage=rds_cfg.allocated_storage,
            db_name=rds_cfg.db_name,
            username=rds_cfg.username,
            password=password,
            db_subnet_group_name=subnet_group.name,
            vpc_security_group_ids=[db_sg.id] if db_sg else [],
            multi_az=rds_cfg.multi_az,
            publicly_accessible=rds_cfg.publicly_accessible,
            skip_final_snapshot=True,
            tags=self._tags(rds_cfg.name, rds_cfg.tags),
        )

    def _tags(self, name: str, extra: dict[str, str] | None = None) -> dict[str, str]:
        return make_tags(self._config.project, self._config.stack, name, extra, global_tags=dict(self._config.tags))
