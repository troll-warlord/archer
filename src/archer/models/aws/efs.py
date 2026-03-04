"""
models/aws/efs.py — Amazon EFS (Elastic File System) models.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EfsConfig(BaseModel):
    """Elastic File System configuration."""

    model_config = ConfigDict(frozen=True)

    name: str
    performance_mode: Literal["generalPurpose", "maxIO"] = "generalPurpose"
    throughput_mode: Literal["bursting", "provisioned", "elastic"] = "bursting"
    provisioned_throughput_mibps: float | None = None
    encrypted: bool = True
    kms_key_id: str | None = None
    # mount target in each of these subnets
    # Use subnet_refs for archer-declared subnets, or subnet_ids for existing ones.
    subnet_refs: list[str] = Field(default_factory=list)
    subnet_ids: list[str] = Field(default_factory=list)
    tags: dict[str, str] = Field(default_factory=dict)
