"""
models/azure.py — Azure-specific Pydantic models and valid-value frozensets.

Contains:
  - Azure location frozenset
  - AzureVnetConfig, AzureSubnetConfig, AzureVmConfig
  - AzureResources (container for all Azure resource configs)
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Azure resource sub-models
# ---------------------------------------------------------------------------


class AzureVnetConfig(BaseModel):
    """Azure Virtual Network configuration."""

    model_config = ConfigDict(frozen=True)

    name: str = "main-vnet"
    address_space: list[str] = ["10.0.0.0/16"]
    resource_group: str


class AzureSubnetConfig(BaseModel):
    """Azure Subnet configuration."""

    model_config = ConfigDict(frozen=True)

    name: str
    address_prefix: str
    type: Literal["public", "private"] = "private"


class AzureVmConfig(BaseModel):
    """Azure Virtual Machine configuration."""

    model_config = ConfigDict(frozen=True)

    name: str
    size: str = "Standard_B2s"
    resource_group: str
    subnet_ref: str
    admin_username: str = "azureuser"
    admin_password_env_var: str = "AZURE_VM_PASSWORD"


# ---------------------------------------------------------------------------
# Top-level Azure resources container
# ---------------------------------------------------------------------------


class AzureResources(BaseModel):
    """Container for all Azure resource configs."""

    model_config = ConfigDict(frozen=True)

    vnet: AzureVnetConfig | None = None
    subnets: list[AzureSubnetConfig] = []
    vms: list[AzureVmConfig] = []
