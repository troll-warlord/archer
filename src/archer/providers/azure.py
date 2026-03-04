"""
providers/azure.py — Azure provider implementation.

Current scope: Resource Group, Virtual Network, Subnets, and a Linux VM.
Uses pulumi-azure-native (v2 SDK).

Credentials are sourced from the standard Azure SDK chain:
  - AZURE_CLIENT_ID / AZURE_CLIENT_SECRET / AZURE_TENANT_ID env vars, or
  - Azure CLI (az login), or
  - Managed Identity when running inside Azure

Never supply credentials in the YAML.
"""

from __future__ import annotations

from typing import Any

import pulumi

from archer.models import InfrastructureConfig
from archer.modules.azure.vm import VmBuilder
from archer.modules.azure.vnet import VnetBuilder
from archer.providers.base import BaseProvider


class AzureProvider(BaseProvider):
    """
    Translates an InfrastructureConfig (Azure flavour) into live Pulumi Azure resources.

    Builder dependency order:
      VnetBuilder (resource group + vnet + subnets) → VmBuilder
    """

    def __init__(self, config: InfrastructureConfig) -> None:
        super().__init__(config)
        self._output_map: dict[str, pulumi.Output[Any]] = {}

    def build_resources(self) -> None:
        # 1. Resource Group + VNet + Subnets
        vnet_result = VnetBuilder(self.config).build()
        self._output_map.update(vnet_result.outputs)

        # 2. Virtual Machines
        vm_result = VmBuilder(self.config, vnet_result).build()
        self._output_map.update(vm_result.outputs)

    def get_outputs(self) -> dict[str, pulumi.Output[Any]]:
        return self._output_map


__all__ = ["AzureProvider"]
