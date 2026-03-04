"""
models/aws/route53.py — Amazon Route 53 models.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Route53ZoneConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str  # zone domain name e.g. "example.com"
    comment: str | None = None
    private: bool = False
    # VPC refs for private zones
    vpc_refs: list[str] = Field(default_factory=list)
    tags: dict[str, str] = Field(default_factory=dict)


class Route53RecordConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str  # record name e.g. "api.example.com"
    zone_ref: str  # references Route53ZoneConfig.name
    type: Literal["A", "AAAA", "CNAME", "MX", "NS", "PTR", "SOA", "SPF", "SRV", "TXT"] = "A"
    ttl: int = 300
    records: list[str] = Field(default_factory=list)
    # alias target (e.g. ALB DNS name) — mutually exclusive with records/ttl
    alias_dns_name: str | None = None
    alias_zone_id: str | None = None
    alias_evaluate_target_health: bool = True
