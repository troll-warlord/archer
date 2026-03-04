"""
models/aws/s3.py — Amazon S3 models.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class S3Config(BaseModel):
    """S3 bucket configuration."""

    model_config = ConfigDict(frozen=True)

    name: str
    # versioning
    versioning: bool = False
    # server-side encryption
    sse_algorithm: Literal["AES256", "aws:kms"] = "AES256"
    kms_master_key_id: str | None = None
    # access
    block_public_acls: bool = True
    block_public_policy: bool = True
    ignore_public_acls: bool = True
    restrict_public_buckets: bool = True
    force_destroy: bool = False
    tags: dict[str, str] = Field(default_factory=dict)
