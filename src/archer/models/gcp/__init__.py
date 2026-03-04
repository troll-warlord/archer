"""
models/gcp/__init__.py — GCP models package.

Re-exports all GCP resource config models so that existing code using
  `from archer.models.gcp import GcpResources`
continues to work.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from archer.models.gcp.compute import GcpInstanceConfig
from archer.models.gcp.vpc import GcpSubnetConfig, GcpVpcConfig


class GcpResources(BaseModel):
    """Container for all GCP resource configs."""

    model_config = ConfigDict(frozen=True)

    vpc: GcpVpcConfig | None = None
    subnets: list[GcpSubnetConfig] = []
    instances: list[GcpInstanceConfig] = []


__all__ = [
    "GcpInstanceConfig",
    "GcpResources",
    "GcpSubnetConfig",
    "GcpVpcConfig",
]
