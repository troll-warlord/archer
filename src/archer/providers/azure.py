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

import os
from typing import Any

import pulumi
import pulumi_azure_native as azure

from archer.models import AzureResources, InfrastructureConfig
from archer.providers.base import BaseProvider


class AzureProvider(BaseProvider):
    """
    Translates an InfrastructureConfig (Azure flavour) into live Pulumi Azure resources.

    Current resource types supported:
      - Resource Group (auto-created, named after the project)
      - Virtual Network
      - Subnets
      - Linux Virtual Machines
    """

    def __init__(self, config: InfrastructureConfig) -> None:
        super().__init__(config)
        self._resource_group: azure.resources.ResourceGroup | None = None
        self._vnet: azure.network.VirtualNetwork | None = None
        self._subnets: dict[str, azure.network.Subnet] = {}
        self._output_map: dict[str, pulumi.Output[Any]] = {}

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def build_resources(self) -> None:
        resources: AzureResources = self.config.resources  # type: ignore[assignment]
        self._build_resource_group(resources)
        self._build_vnet(resources)
        self._build_subnets(resources)
        self._build_vms(resources)

    def get_outputs(self) -> dict[str, pulumi.Output[Any]]:
        return self._output_map

    # ------------------------------------------------------------------
    # Private builders
    # ------------------------------------------------------------------

    def _tags(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        base = {
            "Project": self.config.project,
            "Stack": self.config.stack,
            "ManagedBy": "archer",
        }
        if extra:
            base.update(extra)
        return base

    def _build_resource_group(self, resources: AzureResources) -> None:
        rg_name = resources.vnet.resource_group if resources.vnet else f"{self.config.project}-rg"
        self._resource_group = azure.resources.ResourceGroup(
            rg_name,
            resource_group_name=rg_name,
            location=self.config.region,
            tags=self._tags(),
        )
        self._output_map["resource_group_name"] = self._resource_group.name

    def _build_vnet(self, resources: AzureResources) -> None:
        if not resources.vnet or not self._resource_group:
            return

        vnet_cfg = resources.vnet
        self._vnet = azure.network.VirtualNetwork(
            vnet_cfg.name,
            virtual_network_name=vnet_cfg.name,
            resource_group_name=self._resource_group.name,
            location=self.config.region,
            address_space=azure.network.AddressSpaceArgs(
                address_prefixes=vnet_cfg.address_space,
            ),
            tags=self._tags({"Name": vnet_cfg.name}),
        )
        self._output_map["vnet_id"] = self._vnet.id
        self._output_map["vnet_name"] = self._vnet.name

    def _build_subnets(self, resources: AzureResources) -> None:
        if not self._vnet or not self._resource_group or not resources.subnets:
            return

        for subnet_cfg in resources.subnets:
            subnet = azure.network.Subnet(
                subnet_cfg.name,
                subnet_name=subnet_cfg.name,
                resource_group_name=self._resource_group.name,
                virtual_network_name=self._vnet.name,
                address_prefix=subnet_cfg.address_prefix,
            )
            self._subnets[subnet_cfg.name] = subnet
            self._output_map[f"subnet_{subnet_cfg.name}_id"] = subnet.id

    def _build_vms(self, resources: AzureResources) -> None:
        if not self._resource_group:
            return

        for vm_cfg in resources.vms:
            subnet = self._subnets.get(vm_cfg.subnet_ref)
            admin_password = os.environ.get(vm_cfg.admin_password_env_var, "ChangeMe123!")

            nic = azure.network.NetworkInterface(
                f"{vm_cfg.name}-nic",
                network_interface_name=f"{vm_cfg.name}-nic",
                resource_group_name=self._resource_group.name,
                location=self.config.region,
                ip_configurations=[
                    azure.network.NetworkInterfaceIPConfigurationArgs(
                        name="ipconfig1",
                        subnet=azure.network.SubnetArgs(id=subnet.id) if subnet else None,
                        private_ip_allocation_method="Dynamic",
                    )
                ],
                tags=self._tags({"Name": f"{vm_cfg.name}-nic"}),
            )

            vm = azure.compute.VirtualMachine(
                vm_cfg.name,
                vm_name=vm_cfg.name,
                resource_group_name=self._resource_group.name,
                location=self.config.region,
                hardware_profile=azure.compute.HardwareProfileArgs(vm_size=vm_cfg.size),
                os_profile=azure.compute.OSProfileArgs(
                    computer_name=vm_cfg.name,
                    admin_username=vm_cfg.admin_username,
                    admin_password=admin_password,
                ),
                storage_profile=azure.compute.StorageProfileArgs(
                    image_reference=azure.compute.ImageReferenceArgs(
                        publisher="Canonical",
                        offer="0001-com-ubuntu-server-jammy",
                        sku="22_04-lts",
                        version="latest",
                    ),
                    os_disk=azure.compute.OSDiskArgs(
                        create_option="FromImage",
                        managed_disk=azure.compute.ManagedDiskParametersArgs(
                            storage_account_type="Standard_LRS",
                        ),
                    ),
                ),
                network_profile=azure.compute.NetworkProfileArgs(network_interfaces=[azure.compute.NetworkInterfaceReferenceArgs(id=nic.id, primary=True)]),
                tags=self._tags({"Name": vm_cfg.name}),
            )

            self._output_map[f"vm_{vm_cfg.name}_id"] = vm.id
