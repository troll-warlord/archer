"""
models/azure/vnet.py — Azure Virtual Network models.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


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
