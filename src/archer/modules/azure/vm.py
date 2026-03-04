"""
modules/azure/vm.py — Azure Virtual Machine builder.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pulumi
import pulumi_azure_native as azure

from archer.modules.azure.vnet import VnetBuildResult

if TYPE_CHECKING:
    from archer.models import InfrastructureConfig
    from archer.models.azure import AzureResources


@dataclass
class VmBuildResult:
    vms: dict[str, azure.compute.VirtualMachine] = field(default_factory=dict)
    outputs: dict[str, pulumi.Output[Any]] = field(default_factory=dict)


class VmBuilder:
    """Builds Azure Virtual Machines."""

    def __init__(self, config: InfrastructureConfig, vnet_result: VnetBuildResult) -> None:
        self._config = config
        self._vnet_result = vnet_result

    def build(self) -> VmBuildResult:
        resources: AzureResources = self._config.resources  # type: ignore[assignment]
        result = VmBuildResult()

        rg = self._vnet_result.resource_group
        if not rg or not resources.vms:
            return result

        for vm_cfg in resources.vms:
            subnet = self._vnet_result.subnets.get(vm_cfg.subnet_ref)
            admin_password = os.environ.get(vm_cfg.admin_password_env_var, "ChangeMe123!")

            nic = azure.network.NetworkInterface(
                f"{vm_cfg.name}-nic",
                network_interface_name=f"{vm_cfg.name}-nic",
                resource_group_name=rg.name,
                location=self._config.region,
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
                resource_group_name=rg.name,
                location=self._config.region,
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
            result.vms[vm_cfg.name] = vm
            result.outputs[f"vm_{vm_cfg.name}_id"] = vm.id

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
