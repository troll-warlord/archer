from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# EC2
# ---------------------------------------------------------------------------


class SecurityGroupRuleConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    protocol: str = "tcp"
    from_port: int
    to_port: int
    cidr_blocks: list[str] = Field(default_factory=lambda: ["0.0.0.0/0"])
    description: str | None = None


class Ec2SecurityGroupConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str | None = None
    description: str | None = None
    ingress: list[SecurityGroupRuleConfig] = Field(default_factory=list)
    egress: list[SecurityGroupRuleConfig] = Field(default_factory=list)


class EbsVolumeConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    # Required for extra_volumes; omit for root_volume (uses the AMI default device)
    device_name: str | None = None
    volume_type: str = "gp3"
    volume_size_gb: int = 20
    encrypted: bool = True
    kms_key_id: str | None = None
    delete_on_termination: bool = True


class Ec2Config(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    instance_type: str = "t3.micro"
    ami: str
    # Subnet: use subnet_ref to point at an archer-declared subnet, OR
    # subnet_id to reference an existing subnet (e.g. created by Terraform).
    subnet_ref: str | None = None
    subnet_id: str | None = None
    # VPC: only needed when creating an inline security_group without an archer VPC.
    vpc_id: str | None = None
    assign_public_ip: bool = False
    key_name: str | None = None
    security_group: Ec2SecurityGroupConfig | None = None
    security_group_refs: list[str] = Field(default_factory=list)
    # Existing SG IDs from outside archer (e.g. Terraform-managed SGs).
    existing_security_group_ids: list[str] = Field(default_factory=list)
    root_volume: EbsVolumeConfig | None = None
    extra_volumes: list[EbsVolumeConfig] = Field(default_factory=list)
    tags: dict[str, str] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Auto Scaling Group
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# EKS
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# ECS
# ---------------------------------------------------------------------------


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
