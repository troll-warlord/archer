"""
models/aws/asg.py — Auto Scaling Group models.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AsgLaunchTemplateConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    instance_type: str = "t3.micro"
    ami: str
    key_name: str | None = None
    security_group_refs: list[str] = Field(default_factory=list)
    user_data: str | None = None
    iam_instance_profile_arn: str | None = None


class AsgConfig(BaseModel):
    """Auto Scaling Group with a Launch Template."""

    model_config = ConfigDict(frozen=True)

    name: str
    min_size: int = 1
    max_size: int = 3
    desired_capacity: int = 1
    # Subnet refs (archer-declared) OR raw subnet IDs (existing infra).
    subnet_refs: list[str] = Field(default_factory=list)
    subnet_ids: list[str] = Field(default_factory=list)
    launch_template: AsgLaunchTemplateConfig
    target_group_arns: list[str] = Field(default_factory=list)
    health_check_type: Literal["EC2", "ELB"] = "EC2"
    health_check_grace_period: int = 300
    tags: dict[str, str] = Field(default_factory=dict)
