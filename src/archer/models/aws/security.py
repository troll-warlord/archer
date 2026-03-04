from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from archer.models.aws.compute import SecurityGroupRuleConfig


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


class IamPolicyConfig(BaseModel):
    """Inline IAM managed policy."""

    model_config = ConfigDict(frozen=True)

    name: str
    description: str | None = None
    # JSON policy document string
    document: str
    tags: dict[str, str] = Field(default_factory=dict)


class IamRoleConfig(BaseModel):
    """IAM Role with optional inline and managed policy attachments."""

    model_config = ConfigDict(frozen=True)

    name: str
    description: str | None = None
    # JSON assume-role trust policy document
    assume_role_policy: str
    # ARNs of existing managed policies to attach
    managed_policy_arns: list[str] = Field(default_factory=list)
    # Inline policies defined in this config
    inline_policies: list[IamPolicyConfig] = Field(default_factory=list)
    # Path defaults to "/"
    path: str = "/"
    max_session_duration: int = 3600
    tags: dict[str, str] = Field(default_factory=dict)


class KmsKeyConfig(BaseModel):
    """Customer-managed KMS key."""

    model_config = ConfigDict(frozen=True)

    name: str
    description: str | None = None
    # JSON key policy document — if None, the default key policy is used
    key_policy: str | None = None
    deletion_window_days: int = 30
    enable_key_rotation: bool = True
    multi_region: bool = False
    tags: dict[str, str] = Field(default_factory=dict)
