"""
models/aws/ec2.py — EC2 service models.

Covers: EC2 instances, EBS volumes, Security Groups (aws.ec2.SecurityGroup),
Security Group rules, and standalone named Security Groups.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Security Group
# ---------------------------------------------------------------------------


class SecurityGroupRuleConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    protocol: str = "tcp"
    from_port: int
    to_port: int
    cidr_blocks: list[str] = Field(default_factory=lambda: ["0.0.0.0/0"])
    description: str | None = None


class Ec2SecurityGroupConfig(BaseModel):
    """Inline security group attached to a single EC2 instance."""

    model_config = ConfigDict(frozen=True)

    name: str | None = None
    description: str | None = None
    ingress: list[SecurityGroupRuleConfig] = Field(default_factory=list)
    egress: list[SecurityGroupRuleConfig] = Field(default_factory=list)


class SecurityGroupConfig(BaseModel):
    """
    Top-level named Security Group.

    Declare standalone SGs here and reference them by name from ec2, rds, alb,
    elasticache etc. via ``security_group_refs``.

    Example YAML::

        security_groups:
          - name: app-sg
            description: "App tier ingress"
            ingress_rules:
              - protocol: tcp
                from_port: 8080
                to_port: 8080
                cidr_blocks: ["10.0.0.0/8"]
            egress_rules:
              - protocol: "-1"
                from_port: 0
                to_port: 0
                cidr_blocks: ["0.0.0.0/0"]
    """

    model_config = ConfigDict(frozen=True)

    name: str
    description: str = "archer-managed security group"
    ingress_rules: list[SecurityGroupRuleConfig] = Field(default_factory=list)
    egress_rules: list[SecurityGroupRuleConfig] = Field(default_factory=list)
    tags: dict[str, str] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# EBS
# ---------------------------------------------------------------------------


class EbsVolumeConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    # Required for extra_volumes; omit for root_volume (uses the AMI default device)
    device_name: str | None = None
    volume_type: str = "gp3"
    volume_size_gb: int = 20
    encrypted: bool = True
    kms_key_id: str | None = None
    delete_on_termination: bool = True


# ---------------------------------------------------------------------------
# EC2
# ---------------------------------------------------------------------------


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
