"""
models/aws/ecs.py — Amazon ECS (Elastic Container Service) models.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class EcsContainerConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    image: str
    cpu: int = 256
    memory_mb: int = 512
    port: int | None = None
    environment: dict[str, str] = Field(default_factory=dict)


class EcsServiceConfig(BaseModel):
    """ECS Fargate Service."""

    model_config = ConfigDict(frozen=True)

    name: str
    task_cpu: int = 256
    task_memory_mb: int = 512
    desired_count: int = 1
    subnet_refs: list[str] = Field(default_factory=list)
    subnet_ids: list[str] = Field(default_factory=list)
    assign_public_ip: bool = False
    containers: list[EcsContainerConfig] = Field(default_factory=list)
    target_group_arn: str | None = None
    execution_role_arn: str | None = None
    task_role_arn: str | None = None
    tags: dict[str, str] = Field(default_factory=dict)


class EcsConfig(BaseModel):
    """ECS Cluster + one or more Fargate services."""

    model_config = ConfigDict(frozen=True)

    name: str
    services: list[EcsServiceConfig] = Field(default_factory=list)
    tags: dict[str, str] = Field(default_factory=dict)
