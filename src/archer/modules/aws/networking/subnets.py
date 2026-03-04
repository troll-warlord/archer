from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pulumi
import pulumi_aws as aws

from archer.modules.aws.networking.vpc import VpcBuildResult
from archer.modules.aws.utils import make_tags

if TYPE_CHECKING:
    from archer.models import AwsResources, InfrastructureConfig


@dataclass
class SubnetBuildResult:
    subnets: dict[str, aws.ec2.Subnet] = field(default_factory=dict)
    # private_route_tables: keyed by subnet name; created so NatGatewayBuilder can add routes
    private_route_tables: dict[str, aws.ec2.RouteTable] = field(default_factory=dict)
    outputs: dict[str, pulumi.Output[Any]] = field(default_factory=dict)


class SubnetBuilder:
    def __init__(self, config: InfrastructureConfig, vpc_result: VpcBuildResult) -> None:
        self._config = config
        self._vpc_result = vpc_result

    def build(self) -> SubnetBuildResult:
        resources: AwsResources = self._config.resources  # type: ignore[assignment]
        vpc = self._vpc_result.vpc
        igw = self._vpc_result.igw

        if not vpc or not resources.subnets:
            return SubnetBuildResult()

        result = SubnetBuildResult()
        public_route_table: aws.ec2.RouteTable | None = None

        if igw:
            vpc_name = resources.vpc.name if resources.vpc else "vpc"
            public_route_table = aws.ec2.RouteTable(
                f"{vpc_name}-public-rt",
                vpc_id=vpc.id,
                routes=[
                    aws.ec2.RouteTableRouteArgs(
                        cidr_block="0.0.0.0/0",
                        gateway_id=igw.id,
                    )
                ],
                tags=self._tags("public-route-table"),
            )
            result.outputs["public_route_table_id"] = public_route_table.id

        for subnet_cfg in resources.subnets:
            subnet = aws.ec2.Subnet(
                subnet_cfg.name,
                vpc_id=vpc.id,
                cidr_block=subnet_cfg.cidr_block,
                availability_zone=subnet_cfg.availability_zone,
                map_public_ip_on_launch=(subnet_cfg.type == "public"),
                tags=self._tags(subnet_cfg.name, {"Type": subnet_cfg.type}),
            )
            result.subnets[subnet_cfg.name] = subnet
            result.outputs[f"subnet_{subnet_cfg.name}_id"] = subnet.id

            if subnet_cfg.type == "public" and public_route_table:
                aws.ec2.RouteTableAssociation(
                    f"{subnet_cfg.name}-rta",
                    subnet_id=subnet.id,
                    route_table_id=public_route_table.id,
                )
            elif subnet_cfg.type == "private":
                private_rt = aws.ec2.RouteTable(
                    f"{subnet_cfg.name}-rt",
                    vpc_id=vpc.id,
                    tags=self._tags(f"{subnet_cfg.name}-rt"),
                )
                result.private_route_tables[subnet_cfg.name] = private_rt
                result.outputs[f"private_rt_{subnet_cfg.name}_id"] = private_rt.id
                aws.ec2.RouteTableAssociation(
                    f"{subnet_cfg.name}-rta",
                    subnet_id=subnet.id,
                    route_table_id=private_rt.id,
                )

        return result

    def _tags(self, name: str, extra: dict[str, str] | None = None) -> dict[str, str]:
        return make_tags(self._config.project, self._config.stack, name, extra, global_tags=dict(self._config.tags))
