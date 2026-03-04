"""
models/azure/vm.py — Azure Virtual Machine models.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class AzureVmConfig(BaseModel):
    """Azure Virtual Machine configuration."""

    model_config = ConfigDict(frozen=True)

    name: str
    size: str = "Standard_B2s"
    resource_group: str
    subnet_ref: str
    admin_username: str = "azureuser"
    admin_password_env_var: str = "AZURE_VM_PASSWORD"
