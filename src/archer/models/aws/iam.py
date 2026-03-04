"""
models/aws/iam.py — AWS Identity and Access Management (IAM) models.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


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
