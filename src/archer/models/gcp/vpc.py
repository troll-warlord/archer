"""
models/gcp/vpc.py — GCP VPC Network and Subnet models.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


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
