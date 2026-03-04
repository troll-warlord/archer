from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pulumi
import pulumi_aws as aws

from archer.modules.aws.subnets import SubnetBuildResult
from archer.modules.aws.utils import make_tags

if TYPE_CHECKING:
    from archer.models import AwsResources, InfrastructureConfig


@dataclass
class NatGatewayBuildResult:
    nat_gateways: dict[str, aws.ec2.NatGateway] = field(default_factory=dict)
    eips: dict[str, aws.ec2.Eip] = field(default_factory=dict)
    outputs: dict[str, pulumi.Output[Any]] = field(default_factory=dict)


class NatGatewayBuilder:
    def __init__(
        self,
        config: InfrastructureConfig,
        subnet_result: SubnetBuildResult,
    ) -> None:
        self._config = config
        self._subnet_result = subnet_result

    def build(self) -> NatGatewayBuildResult:
        resources: AwsResources = self._config.resources  # type: ignore[assignment]
        if not resources.nat_gateways:
            return NatGatewayBuildResult()

        result = NatGatewayBuildResult()

        for nat_cfg in resources.nat_gateways:
            # Resolve subnet: prefer raw subnet_id (existing infra), else look up
            # the archer-declared subnet by name.
            if nat_cfg.subnet_id:
                subnet_id: pulumi.Input[str] = nat_cfg.subnet_id
                nat_subnet_deps: list[Any] = []
            elif nat_cfg.subnet_ref:
                subnet = self._subnet_result.subnets.get(nat_cfg.subnet_ref)
                if subnet is None:
                    raise ValueError(f"NAT Gateway '{nat_cfg.name}' references unknown subnet '{nat_cfg.subnet_ref}'")
                subnet_id = subnet.id
                nat_subnet_deps = [subnet]
            else:
                raise ValueError(f"NAT Gateway '{nat_cfg.name}' requires either subnet_ref or subnet_id")

            allocation_id: pulumi.Output[str] | str
            if nat_cfg.allocate_eip:
                eip = aws.ec2.Eip(
                    f"{nat_cfg.name}-eip",
                    domain="vpc",
                    tags=self._tags(f"{nat_cfg.name}-eip"),
                )
                result.eips[nat_cfg.name] = eip
                result.outputs[f"{nat_cfg.name}_eip_public_ip"] = eip.public_ip
                allocation_id = eip.id
            elif nat_cfg.eip_allocation_id:
                allocation_id = nat_cfg.eip_allocation_id
            else:
                raise ValueError(f"NAT Gateway '{nat_cfg.name}' requires either allocate_eip=true or an eip_allocation_id")

            nat_gw = aws.ec2.NatGateway(
                nat_cfg.name,
                subnet_id=subnet_id,
                allocation_id=allocation_id,
                tags=self._tags(nat_cfg.name),
                opts=pulumi.ResourceOptions(depends_on=nat_subnet_deps) if nat_subnet_deps else None,
            )
            result.nat_gateways[nat_cfg.name] = nat_gw
            result.outputs[f"{nat_cfg.name}_nat_gateway_id"] = nat_gw.id

        # Add default routes on private route tables if they were created
        private_rts = self._subnet_result.private_route_tables
        nat_gws = list(result.nat_gateways.values())
        if private_rts and nat_gws:
            # Use the first NAT GW as the default route for all private subnets;
            # more refined multi-AZ routing can be done via explicit route tables later
            primary_nat = nat_gws[0]
            for rt_name, rt in private_rts.items():
                aws.ec2.Route(
                    f"{rt_name}-nat-route",
                    route_table_id=rt.id,
                    destination_cidr_block="0.0.0.0/0",
                    nat_gateway_id=primary_nat.id,
                )

        return result

    def _tags(self, name: str, extra: dict[str, str] | None = None) -> dict[str, str]:
        return make_tags(self._config.project, self._config.stack, name, extra, global_tags=dict(self._config.tags))
