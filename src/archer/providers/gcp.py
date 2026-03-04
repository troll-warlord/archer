"""
providers/gcp.py — GCP provider implementation.

Current scope: VPC Network, Subnetworks, Compute Instances.
Uses pulumi-gcp (v7 SDK).

Credentials are sourced from the standard GCP ADC chain:
  - GOOGLE_APPLICATION_CREDENTIALS env var (path to service account JSON), or
  - gcloud auth application-default login, or
  - Attached service account when running inside GCP

Never supply credentials in the YAML.
"""

from __future__ import annotations

from typing import Any

import pulumi
import pulumi_gcp as gcp

from archer.models import GcpResources, InfrastructureConfig
from archer.providers.base import BaseProvider


class GCPProvider(BaseProvider):
    """
    Translates an InfrastructureConfig (GCP flavour) into live Pulumi GCP resources.

    Current resource types supported:
      - VPC Network (custom subnet mode)
      - Subnetworks
      - Compute Instances
    """

    def __init__(self, config: InfrastructureConfig) -> None:
        super().__init__(config)
        self._network: gcp.compute.Network | None = None
        self._subnets: dict[str, gcp.compute.Subnetwork] = {}
        self._output_map: dict[str, pulumi.Output[Any]] = {}

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def build_resources(self) -> None:
        resources: GcpResources = self.config.resources  # type: ignore[assignment]
        self._build_network(resources)
        self._build_subnets(resources)
        self._build_instances(resources)

    def get_outputs(self) -> dict[str, pulumi.Output[Any]]:
        return self._output_map

    # ------------------------------------------------------------------
    # Private builders
    # ------------------------------------------------------------------

    def _labels(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        """GCP uses 'labels' rather than 'tags' for metadata."""
        base = {
            "project": self.config.project.lower().replace(" ", "-"),
            "stack": self.config.stack.lower(),
            "managed-by": "archer",
        }
        if extra:
            base.update(extra)
        return base

    def _build_network(self, resources: GcpResources) -> None:
        if not resources.vpc:
            return

        vpc_cfg = resources.vpc
        self._network = gcp.compute.Network(
            vpc_cfg.name,
            name=vpc_cfg.name,
            auto_create_subnetworks=vpc_cfg.auto_create_subnetworks,
        )
        self._output_map["network_id"] = self._network.id
        self._output_map["network_name"] = self._network.name
        self._output_map["network_self_link"] = self._network.self_link

    def _build_subnets(self, resources: GcpResources) -> None:
        if not self._network or not resources.subnets:
            return

        for subnet_cfg in resources.subnets:
            subnet = gcp.compute.Subnetwork(
                subnet_cfg.name,
                name=subnet_cfg.name,
                ip_cidr_range=subnet_cfg.ip_cidr_range,
                region=subnet_cfg.region or self.config.region,
                network=self._network.id,
            )
            self._subnets[subnet_cfg.name] = subnet
            self._output_map[f"subnet_{subnet_cfg.name}_id"] = subnet.id
            self._output_map[f"subnet_{subnet_cfg.name}_self_link"] = subnet.self_link

    def _build_instances(self, resources: GcpResources) -> None:
        if not resources.instances:
            return

        for inst_cfg in resources.instances:
            subnet = self._subnets.get(inst_cfg.subnet_ref)

            network_interfaces = [
                gcp.compute.InstanceNetworkInterfaceArgs(
                    network=self._network.id if self._network else None,
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

            self._output_map[f"instance_{inst_cfg.name}_id"] = instance.id
            self._output_map[f"instance_{inst_cfg.name}_self_link"] = instance.self_link
