from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pulumi
import pulumi_aws as aws

from archer.modules.aws.networking.subnets import SubnetBuildResult
from archer.modules.aws.networking.vpc import VpcBuildResult
from archer.modules.aws.utils import make_tags, resolve_subnet_ids, resolve_vpc_id

if TYPE_CHECKING:
    from archer.models import AwsResources, InfrastructureConfig


@dataclass
class VpcEndpointBuildResult:
    endpoints: dict[str, aws.ec2.VpcEndpoint] = field(default_factory=dict)
    outputs: dict[str, pulumi.Output[Any]] = field(default_factory=dict)


class VpcEndpointBuilder:
    def __init__(
        self,
        config: InfrastructureConfig,
        vpc_result: VpcBuildResult,
        subnet_result: SubnetBuildResult,
    ) -> None:
        self._config = config
        self._vpc_result = vpc_result
        self._subnet_result = subnet_result

    def build(self) -> VpcEndpointBuildResult:
        resources: AwsResources = self._config.resources  # type: ignore[assignment]
        if not resources.vpc_endpoints:
            return VpcEndpointBuildResult()

        result = VpcEndpointBuildResult()

        for ep_cfg in resources.vpc_endpoints:
            # Resolve VPC: prefer raw vpc_id on config (existing infra), else archer VPC.
            vpc_id, vpc_deps = resolve_vpc_id(self._vpc_result, ep_cfg.vpc_id)
            if not vpc_id:
                pulumi.log.warn(f"VPC Endpoint '{ep_cfg.name}' skipped: no VPC available. Set endpoint.vpc_id or declare a vpc block.")
                continue

            # Resolve subnets (Interface endpoints only).
            subnet_id_inputs, subnet_deps = resolve_subnet_ids(
                ep_cfg.subnet_refs,
                ep_cfg.subnet_ids,
                self._subnet_result,
            )
            all_deps = vpc_deps + subnet_deps

            kwargs: dict[str, Any] = {
                "vpc_id": vpc_id,
                "service_name": ep_cfg.service_name,
                "vpc_endpoint_type": ep_cfg.endpoint_type,
                "tags": self._tags(ep_cfg.name),
            }
            if ep_cfg.endpoint_type == "Interface" and subnet_id_inputs:
                kwargs["subnet_ids"] = subnet_id_inputs
                kwargs["private_dns_enabled"] = ep_cfg.private_dns_enabled

            endpoint = aws.ec2.VpcEndpoint(
                ep_cfg.name,
                **kwargs,
                opts=pulumi.ResourceOptions(depends_on=all_deps) if all_deps else None,
            )
            result.endpoints[ep_cfg.name] = endpoint
            result.outputs[f"{ep_cfg.name}_endpoint_id"] = endpoint.id

        return result

    def _tags(self, name: str, extra: dict[str, str] | None = None) -> dict[str, str]:
        return make_tags(self._config.project, self._config.stack, name, extra, global_tags=dict(self._config.tags))
