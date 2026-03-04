"""
models/aws/acm.py — AWS Certificate Manager (ACM) models.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AcmCertificateConfig(BaseModel):
    """ACM certificate with DNS validation."""

    model_config = ConfigDict(frozen=True)

    name: str
    domain_name: str
    subject_alternative_names: list[str] = Field(default_factory=list)
    validation_method: Literal["DNS", "EMAIL"] = "DNS"
    # If zone_ref is provided, validation CNAME records are created automatically
    zone_ref: str | None = None
    tags: dict[str, str] = Field(default_factory=dict)
