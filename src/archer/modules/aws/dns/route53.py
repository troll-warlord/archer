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
class Route53BuildResult:
    zones: dict[str, aws.route53.Zone] = field(default_factory=dict)
    records: dict[str, aws.route53.Record] = field(default_factory=dict)
    outputs: dict[str, pulumi.Output[Any]] = field(default_factory=dict)


class Route53Builder:
    def __init__(
        self,
        config: InfrastructureConfig,
        vpc_result: VpcBuildResult,
    ) -> None:
        self._config = config
        self._vpc_result = vpc_result

    def build(self) -> Route53BuildResult:
        resources: AwsResources = self._config.resources  # type: ignore[assignment]
        if not resources.route53_zones and not resources.route53_records:
            return Route53BuildResult()

        result = Route53BuildResult()

        for zone_cfg in resources.route53_zones:
            zone_kwargs: dict[str, Any] = {
                "comment": zone_cfg.comment or f"Managed by archer - {zone_cfg.name}",
                "tags": self._tags(zone_cfg.name, zone_cfg.tags),
            }
            if zone_cfg.private and self._vpc_result.vpc:
                zone_kwargs["vpcs"] = [aws.route53.ZoneVpcArgs(vpc_id=self._vpc_result.vpc.id)]

            zone = aws.route53.Zone(zone_cfg.name, **zone_kwargs)
            result.zones[zone_cfg.name] = zone
            result.outputs[f"{zone_cfg.name}_zone_id"] = zone.zone_id

        for rec_cfg in resources.route53_records:
            zone = result.zones.get(rec_cfg.zone_ref)
            if zone is None:
                raise ValueError(f"Route53 record '{rec_cfg.name}' references unknown zone '{rec_cfg.zone_ref}'")

            rec_kwargs: dict[str, Any] = {
                "zone_id": zone.zone_id,
                "name": rec_cfg.name,
                "type": rec_cfg.type,
            }

            if rec_cfg.alias_dns_name and rec_cfg.alias_zone_id:
                rec_kwargs["aliases"] = [
                    aws.route53.RecordAliasArgs(
                        name=rec_cfg.alias_dns_name,
                        zone_id=rec_cfg.alias_zone_id,
                        evaluate_target_health=rec_cfg.alias_evaluate_target_health,
                    )
                ]
            else:
                rec_kwargs["ttl"] = rec_cfg.ttl
                rec_kwargs["records"] = rec_cfg.records

            record = aws.route53.Record(rec_cfg.name, **rec_kwargs)
            result.records[rec_cfg.name] = record
            result.outputs[f"{rec_cfg.name}_fqdn"] = record.fqdn

        return result

    def _tags(self, name: str, extra: dict[str, str] | None = None) -> dict[str, str]:
        return make_tags(self._config.project, self._config.stack, name, extra, global_tags=dict(self._config.tags))
