"""
modules/azure/vnet.py — Azure Virtual Network and Subnet builders.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pulumi
import pulumi_azure_native as azure

if TYPE_CHECKING:
    from archer.models import InfrastructureConfig
    from archer.models.azure import AzureResources


@dataclass
class VnetBuildResult:
    resource_group: azure.resources.ResourceGroup | None = None
    vnet: azure.network.VirtualNetwork | None = None
    subnets: dict[str, azure.network.Subnet] = field(default_factory=dict)
    outputs: dict[str, pulumi.Output[Any]] = field(default_factory=dict)


class VnetBuilder:
    """Builds Azure Resource Group, Virtual Network, and Subnets."""

    def __init__(self, config: InfrastructureConfig) -> None:
        self._config = config

    def build(self) -> VnetBuildResult:
        resources: AzureResources = self._config.resources  # type: ignore[assignment]
        result = VnetBuildResult()

        # Resource Group
        rg_name = resources.vnet.resource_group if resources.vnet else f"{self._config.project}-rg"
        rg = azure.resources.ResourceGroup(
            rg_name,
            resource_group_name=rg_name,
            location=self._config.region,
            tags=self._tags(),
        )
        result.resource_group = rg
        result.outputs["resource_group_name"] = rg.name

        # VNet
        if resources.vnet:
            vnet_cfg = resources.vnet
            vnet = azure.network.VirtualNetwork(
                vnet_cfg.name,
                virtual_network_name=vnet_cfg.name,
                resource_group_name=rg.name,
                location=self._config.region,
                address_space=azure.network.AddressSpaceArgs(
                    address_prefixes=vnet_cfg.address_space,
                ),
                tags=self._tags({"Name": vnet_cfg.name}),
            )
            result.vnet = vnet
            result.outputs["vnet_id"] = vnet.id
            result.outputs["vnet_name"] = vnet.name

            # Subnets
            for subnet_cfg in resources.subnets:
                subnet = azure.network.Subnet(
                    subnet_cfg.name,
                    subnet_name=subnet_cfg.name,
                    resource_group_name=rg.name,
                    virtual_network_name=vnet.name,
                    address_prefix=subnet_cfg.address_prefix,
                )
                result.subnets[subnet_cfg.name] = subnet
                result.outputs[f"subnet_{subnet_cfg.name}_id"] = subnet.id

        return result

    def _tags(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        base: dict[str, str] = {
            "Project": self._config.project,
            "Stack": self._config.stack,
            "ManagedBy": "archer",
        }
        if self._config.tags:
            base.update(self._config.tags)
        if extra:
            base.update(extra)
        return base
