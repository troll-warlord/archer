"""
modules/gcp/compute.py — GCP Compute Engine (Instance) builder.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pulumi
import pulumi_gcp as gcp

from archer.modules.gcp.vpc import VpcBuildResult

if TYPE_CHECKING:
    from archer.models import InfrastructureConfig
    from archer.models.gcp import GcpResources


@dataclass
class InstanceBuildResult:
    instances: dict[str, gcp.compute.Instance] = field(default_factory=dict)
    outputs: dict[str, pulumi.Output[Any]] = field(default_factory=dict)


class InstanceBuilder:
    """Builds GCP Compute Instances."""

    def __init__(self, config: InfrastructureConfig, vpc_result: VpcBuildResult) -> None:
        self._config = config
        self._vpc_result = vpc_result

    def build(self) -> InstanceBuildResult:
        resources: GcpResources = self._config.resources  # type: ignore[assignment]
        result = InstanceBuildResult()

        if not resources.instances:
            return result

        for inst_cfg in resources.instances:
            subnet = self._vpc_result.subnets.get(inst_cfg.subnet_ref)

            network_interfaces = [
                gcp.compute.InstanceNetworkInterfaceArgs(
                    network=self._vpc_result.network.id if self._vpc_result.network else None,
                    subnetwork=subnet.id if subnet else None,
                )
            ]

            instance = gcp.compute.Instance(
                inst_cfg.name,
                name=inst_cfg.name,
                machine_type=inst_cfg.machine_type,
                zone=inst_cfg.zone,
                boot_disk=gcp.compute.InstanceBootDiskArgs(
                    initialize_params=gcp.compute.InstanceBootDiskInitializeParamsArgs(
                        image=inst_cfg.image,
                    )
                ),
                network_interfaces=network_interfaces,
                labels=self._labels({"name": inst_cfg.name.lower().replace(" ", "-")}),
            )
            result.instances[inst_cfg.name] = instance
            result.outputs[f"instance_{inst_cfg.name}_id"] = instance.id
            result.outputs[f"instance_{inst_cfg.name}_self_link"] = instance.self_link

        return result

    def _labels(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        """GCP uses 'labels' rather than 'tags' for metadata."""
        base: dict[str, str] = {
            "project": self._config.project.lower().replace(" ", "-"),
            "stack": self._config.stack.lower(),
            "managed-by": "archer",
        }
        if extra:
            base.update(extra)
        return base
