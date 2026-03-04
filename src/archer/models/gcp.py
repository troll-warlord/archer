"""
models/gcp.py — GCP-specific Pydantic models and valid-value frozensets.

Contains:
  - GCP region frozenset
  - GcpVpcConfig, GcpSubnetConfig, GcpInstanceConfig
  - GcpResources (container for all GCP resource configs)
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# GCP resource sub-models
# ---------------------------------------------------------------------------


class GcpVpcConfig(BaseModel):
    """GCP VPC Network configuration."""

    model_config = ConfigDict(frozen=True)

    name: str = "main-vpc"
    auto_create_subnetworks: bool = False


class GcpSubnetConfig(BaseModel):
    """GCP Subnet configuration."""

    model_config = ConfigDict(frozen=True)

    name: str
    ip_cidr_range: str
    region: str


class GcpInstanceConfig(BaseModel):
    """GCP Compute Instance configuration."""

    model_config = ConfigDict(frozen=True)

    name: str
    machine_type: str = "e2-micro"
    zone: str
    image: str = "debian-cloud/debian-12"
    subnet_ref: str


# ---------------------------------------------------------------------------
# Top-level GCP resources container
# ---------------------------------------------------------------------------


class GcpResources(BaseModel):
    """Container for all GCP resource configs."""

    model_config = ConfigDict(frozen=True)

    vpc: GcpVpcConfig | None = None
    subnets: list[GcpSubnetConfig] = []
    instances: list[GcpInstanceConfig] = []
