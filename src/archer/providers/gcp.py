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

from archer.models import InfrastructureConfig
from archer.modules.gcp.compute import InstanceBuilder
from archer.modules.gcp.vpc import VpcBuilder
from archer.providers.base import BaseProvider


class GCPProvider(BaseProvider):
    """
    Translates an InfrastructureConfig (GCP flavour) into live Pulumi GCP resources.

    Builder dependency order:
      VpcBuilder (VPC network + subnetworks) → InstanceBuilder
    """

    def __init__(self, config: InfrastructureConfig) -> None:
        super().__init__(config)
        self._output_map: dict[str, pulumi.Output[Any]] = {}

    def build_resources(self) -> None:
        # 1. VPC Network + Subnetworks
        vpc_result = VpcBuilder(self.config).build()
        self._output_map.update(vpc_result.outputs)

        # 2. Compute Instances
        instance_result = InstanceBuilder(self.config, vpc_result).build()
        self._output_map.update(instance_result.outputs)

    def get_outputs(self) -> dict[str, pulumi.Output[Any]]:
        return self._output_map


__all__ = ["GCPProvider"]
