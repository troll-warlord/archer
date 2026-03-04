from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TargetGroupConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    port: int = 80
    protocol: Literal["HTTP", "HTTPS", "TCP", "TLS", "UDP", "TCP_UDP"] = "HTTP"
    target_type: Literal["instance", "ip", "lambda", "alb"] = "ip"
    health_check_path: str = "/"
    health_check_interval: int = 30
    health_check_healthy_threshold: int = 3
    health_check_unhealthy_threshold: int = 3
    tags: dict[str, str] = Field(default_factory=dict)


class ListenerConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    port: int = 80
    protocol: Literal["HTTP", "HTTPS", "TCP", "TLS"] = "HTTP"
    target_group_ref: str  # references TargetGroupConfig.name
    # HTTPS / TLS only
    certificate_arn: str | None = None
    ssl_policy: str | None = None
    # HTTP → HTTPS redirect instead of forwarding
    redirect_to_https: bool = False


class AlbConfig(BaseModel):
    """Application Load Balancer configuration."""

    model_config = ConfigDict(frozen=True)

    name: str
    internal: bool = False
    # Subnet refs (archer-declared) OR raw subnet IDs (existing infra).
    subnet_refs: list[str] = Field(default_factory=list)
    subnet_ids: list[str] = Field(default_factory=list)
    # VPC: provide vpc_id when using existing VPC (for SG + target group creation).
    vpc_id: str | None = None
    target_groups: list[TargetGroupConfig] = Field(default_factory=list)
    listeners: list[ListenerConfig] = Field(default_factory=list)
    deletion_protection: bool = False
    access_logs_bucket: str | None = None
    tags: dict[str, str] = Field(default_factory=dict)


class NlbConfig(BaseModel):
    """Network Load Balancer configuration."""

    model_config = ConfigDict(frozen=True)

    name: str
    internal: bool = True
    cross_zone: bool = True
    # Subnet refs (archer-declared) OR raw subnet IDs (existing infra).
    subnet_refs: list[str] = Field(default_factory=list)
    subnet_ids: list[str] = Field(default_factory=list)
    # VPC: provide vpc_id when using existing VPC (for target group creation).
    vpc_id: str | None = None
    target_groups: list[TargetGroupConfig] = Field(default_factory=list)
    listeners: list[ListenerConfig] = Field(default_factory=list)
    tags: dict[str, str] = Field(default_factory=dict)
