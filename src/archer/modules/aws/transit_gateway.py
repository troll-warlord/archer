from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pulumi
import pulumi_aws as aws

from archer.modules.aws.utils import make_tags

if TYPE_CHECKING:
    from archer.models import AwsResources, InfrastructureConfig


@dataclass
class TransitGatewayBuildResult:
    transit_gateways: dict[str, aws.ec2transitgateway.TransitGateway] = field(default_factory=dict)
    outputs: dict[str, pulumi.Output[Any]] = field(default_factory=dict)


class TransitGatewayBuilder:
    def __init__(self, config: InfrastructureConfig) -> None:
        self._config = config

    def build(self) -> TransitGatewayBuildResult:
        resources: AwsResources = self._config.resources  # type: ignore[assignment]
        if not resources.transit_gateways:
            return TransitGatewayBuildResult()

        result = TransitGatewayBuildResult()

        for tgw_cfg in resources.transit_gateways:
            tgw = aws.ec2transitgateway.TransitGateway(
                tgw_cfg.name,
                amazon_side_asn=tgw_cfg.amazon_side_asn,
                auto_accept_shared_attachments=("enable" if tgw_cfg.auto_accept_shared_attachments else "disable"),
                default_route_table_association=("enable" if tgw_cfg.default_route_table_association else "disable"),
                default_route_table_propagation=("enable" if tgw_cfg.default_route_table_propagation else "disable"),
                dns_support="enable" if tgw_cfg.dns_support else "disable",
                vpn_ecmp_support="enable" if tgw_cfg.vpn_ecmp_support else "disable",
                tags=self._tags(tgw_cfg.name),
            )
            result.transit_gateways[tgw_cfg.name] = tgw
            result.outputs[f"{tgw_cfg.name}_tgw_id"] = tgw.id

        return result

    def _tags(self, name: str, extra: dict[str, str] | None = None) -> dict[str, str]:
        return make_tags(self._config.project, self._config.stack, name, extra, global_tags=dict(self._config.tags))
