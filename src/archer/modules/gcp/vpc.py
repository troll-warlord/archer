"""
modules/gcp/vpc.py — GCP VPC Network and Subnetwork builders.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pulumi
import pulumi_gcp as gcp

if TYPE_CHECKING:
    from archer.models import InfrastructureConfig
    from archer.models.gcp import GcpResources


@dataclass
class VpcBuildResult:
    network: gcp.compute.Network | None = None
    subnets: dict[str, gcp.compute.Subnetwork] = field(default_factory=dict)
    outputs: dict[str, pulumi.Output[Any]] = field(default_factory=dict)


class VpcBuilder:
    """Builds GCP VPC Network and Subnetworks."""

    def __init__(self, config: InfrastructureConfig) -> None:
        self._config = config

    def build(self) -> VpcBuildResult:
        resources: GcpResources = self._config.resources  # type: ignore[assignment]
        result = VpcBuildResult()

        if not resources.vpc:
            return result

        vpc_cfg = resources.vpc
        network = gcp.compute.Network(
            vpc_cfg.name,
            name=vpc_cfg.name,
            auto_create_subnetworks=vpc_cfg.auto_create_subnetworks,
        )
        result.network = network
        result.outputs["network_id"] = network.id
        result.outputs["network_name"] = network.name
        result.outputs["network_self_link"] = network.self_link

        for subnet_cfg in resources.subnets:
            subnet = gcp.compute.Subnetwork(
                subnet_cfg.name,
                name=subnet_cfg.name,
                ip_cidr_range=subnet_cfg.ip_cidr_range,
                region=subnet_cfg.region or self._config.region,
                network=network.id,
            )
            result.subnets[subnet_cfg.name] = subnet
            result.outputs[f"subnet_{subnet_cfg.name}_id"] = subnet.id
            result.outputs[f"subnet_{subnet_cfg.name}_self_link"] = subnet.self_link

        return result
