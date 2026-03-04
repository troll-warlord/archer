"""
models/gcp/compute.py — GCP Compute Engine models.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class GcpInstanceConfig(BaseModel):
    """GCP Compute Instance configuration."""

    model_config = ConfigDict(frozen=True)

    name: str
    machine_type: str = "e2-micro"
    zone: str
    image: str = "debian-cloud/debian-12"
    subnet_ref: str
