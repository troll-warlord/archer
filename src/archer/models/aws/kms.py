"""
models/aws/kms.py — AWS Key Management Service (KMS) models.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


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
