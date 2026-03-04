"""
models/azure/__init__.py — Azure models package.

Re-exports all Azure resource config models so that existing code using
  `from archer.models.azure import AzureResources`
continues to work.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from archer.models.azure.vm import AzureVmConfig
from archer.models.azure.vnet import AzureSubnetConfig, AzureVnetConfig


class AzureResources(BaseModel):
    """Container for all Azure resource configs."""

    model_config = ConfigDict(frozen=True)

    vnet: AzureVnetConfig | None = None
    subnets: list[AzureSubnetConfig] = []
    vms: list[AzureVmConfig] = []


__all__ = [
    "AzureResources",
    "AzureSubnetConfig",
    "AzureVmConfig",
    "AzureVnetConfig",
]
