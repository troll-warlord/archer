from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pulumi
import pulumi_aws as aws

from archer.modules.aws.security_groups import SecurityGroupBuildResult
from archer.modules.aws.subnets import SubnetBuildResult
from archer.modules.aws.utils import make_tags, resolve_subnet_ids

if TYPE_CHECKING:
    from archer.models import InfrastructureConfig
    from archer.models.aws import AwsResources


@dataclass
class ElastiCacheBuildResult:
    clusters: dict[str, Any] = field(default_factory=dict)  # name → ReplicationGroup | Cluster
    subnet_groups: dict[str, Any] = field(default_factory=dict)  # name → SubnetGroup
    outputs: dict[str, pulumi.Output[Any]] = field(default_factory=dict)


class ElastiCacheBuilder:
    """Builds ElastiCache clusters (Redis ReplicationGroup / Memcached Cluster)."""

    def __init__(
        self,
        config: InfrastructureConfig,
        subnet_result: SubnetBuildResult | None = None,
        sg_result: SecurityGroupBuildResult | None = None,
    ) -> None:
        self._config = config
        self._subnet_result = subnet_result
        self._sg_result = sg_result

    def build(self) -> ElastiCacheBuildResult:
        resources: AwsResources = self._config.resources  # type: ignore[assignment]
        if not resources.elasticache:
            return ElastiCacheBuildResult()

        result = ElastiCacheBuildResult()

        for cfg in resources.elasticache:
            # -----------------------------------------------------------------
            # Subnet Group
            # -----------------------------------------------------------------
            subnet_ids, subnet_depends = resolve_subnet_ids(
                cfg.subnet_refs,
                cfg.subnet_ids,
                self._subnet_result,
            )

            sg_name = f"{cfg.name}-subnet-group"
            subnet_group = aws.elasticache.SubnetGroup(
                sg_name,
                name=sg_name,
                subnet_ids=subnet_ids,  # type: ignore[arg-type]
                tags=self._tags(sg_name, cfg.tags),
                opts=pulumi.ResourceOptions(depends_on=subnet_depends),
            )
            result.subnet_groups[cfg.name] = subnet_group

            # -----------------------------------------------------------------
            # Security groups
            # -----------------------------------------------------------------
            security_group_ids: list[pulumi.Input[str]] = list(cfg.existing_security_group_ids)
            if self._sg_result:
                for ref in cfg.security_group_refs:
                    sg = self._sg_result.sg_map.get(ref)
                    if sg:
                        security_group_ids.append(sg.id)

            # -----------------------------------------------------------------
            # Redis → ReplicationGroup; Memcached → Cluster
            # -----------------------------------------------------------------
            if cfg.engine == "redis":
                extra_kwargs: dict[str, Any] = {}
                if cfg.engine_version:
                    extra_kwargs["engine_version"] = cfg.engine_version
                if cfg.port:
                    extra_kwargs["port"] = cfg.port
                if cfg.maintenance_window:
                    extra_kwargs["maintenance_window"] = cfg.maintenance_window
                if cfg.kms_key_id:
                    extra_kwargs["kms_key_id"] = cfg.kms_key_id
                if cfg.at_rest_encryption:
                    extra_kwargs["at_rest_encryption_enabled"] = True
                if cfg.transit_encryption:
                    extra_kwargs["transit_encryption_enabled"] = True
                    if cfg.auth_token_env_var:
                        token = os.environ.get(cfg.auth_token_env_var, "")
                        if token:
                            extra_kwargs["auth_token"] = token
                if cfg.automatic_failover_enabled:
                    extra_kwargs["automatic_failover_enabled"] = True
                if cfg.multi_az_enabled:
                    extra_kwargs["multi_az_enabled"] = True
                if cfg.snapshot_retention_limit > 0:
                    extra_kwargs["snapshot_retention_limit"] = cfg.snapshot_retention_limit

                cluster = aws.elasticache.ReplicationGroup(
                    cfg.name,
                    description=f"archer-managed Redis cluster {cfg.name}",
                    node_type=cfg.node_type,
                    num_cache_clusters=max(1, cfg.num_cache_nodes),
                    subnet_group_name=subnet_group.name,
                    security_group_ids=security_group_ids,  # type: ignore[arg-type]
                    tags=self._tags(cfg.name, cfg.tags),
                    opts=pulumi.ResourceOptions(depends_on=[subnet_group, *subnet_depends]),
                    **extra_kwargs,
                )
                result.clusters[cfg.name] = cluster
                result.outputs[f"elasticache_{cfg.name}_primary_endpoint"] = cluster.primary_endpoint_address
                result.outputs[f"elasticache_{cfg.name}_reader_endpoint"] = cluster.reader_endpoint_address

            else:  # memcached
                extra_kwargs = {}
                if cfg.engine_version:
                    extra_kwargs["engine_version"] = cfg.engine_version
                if cfg.port:
                    extra_kwargs["port"] = cfg.port
                if cfg.maintenance_window:
                    extra_kwargs["preferred_maintenance_window"] = cfg.maintenance_window

                cluster = aws.elasticache.Cluster(
                    cfg.name,
                    engine="memcached",
                    node_type=cfg.node_type,
                    num_cache_nodes=max(1, cfg.num_cache_nodes),
                    subnet_group_name=subnet_group.name,
                    security_group_ids=security_group_ids,  # type: ignore[arg-type]
                    tags=self._tags(cfg.name, cfg.tags),
                    opts=pulumi.ResourceOptions(depends_on=[subnet_group, *subnet_depends]),
                    **extra_kwargs,
                )
                result.clusters[cfg.name] = cluster
                result.outputs[f"elasticache_{cfg.name}_config_endpoint"] = cluster.configuration_endpoint

        return result

    def _tags(self, name: str, extra: dict[str, str] | None = None) -> dict[str, str]:
        return make_tags(self._config.project, self._config.stack, name, extra, global_tags=dict(self._config.tags))
