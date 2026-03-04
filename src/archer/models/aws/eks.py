"""
models/aws/eks.py — Amazon EKS (Elastic Kubernetes Service) models.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EksNodeGroupConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    instance_types: list[str] = Field(default_factory=lambda: ["t3.medium"])
    min_size: int = 1
    max_size: int = 3
    desired_size: int = 1
    subnet_refs: list[str] = Field(default_factory=list)
    subnet_ids: list[str] = Field(default_factory=list)
    disk_size_gb: int = 20
    ami_type: Literal[
        "AL2_x86_64",
        "AL2_x86_64_GPU",
        "AL2_ARM_64",
        "BOTTLEROCKET_x86_64",
        "BOTTLEROCKET_ARM_64",
    ] = "AL2_x86_64"
    labels: dict[str, str] = Field(default_factory=dict)


class EksConfig(BaseModel):
    """Managed EKS Cluster."""

    model_config = ConfigDict(frozen=True)

    name: str
    kubernetes_version: str = "1.31"
    subnet_refs: list[str] = Field(default_factory=list)
    subnet_ids: list[str] = Field(default_factory=list)
    endpoint_public_access: bool = True
    endpoint_private_access: bool = True
    node_groups: list[EksNodeGroupConfig] = Field(default_factory=list)
    tags: dict[str, str] = Field(default_factory=dict)
