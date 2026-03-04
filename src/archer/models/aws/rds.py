"""
models/aws/rds.py — Amazon RDS (Relational Database Service) models.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RdsConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    engine: str = "postgres"
    engine_version: str = "15.3"
    instance_class: str = "db.t3.micro"
    allocated_storage: int = 20
    db_name: str
    username: str
    password_env_var: str = "DB_PASSWORD"
    # Subnet refs (archer-declared) OR raw subnet IDs (existing infra).
    subnet_refs: list[str] = Field(default_factory=list)
    subnet_ids: list[str] = Field(default_factory=list)
    # VPC: provide vpc_id when using existing VPC (for SG creation).
    vpc_id: str | None = None
    multi_az: bool = False
    publicly_accessible: bool = False
    tags: dict[str, str] = Field(default_factory=dict)

    @field_validator("allocated_storage")
    @classmethod
    def validate_storage(cls, value: int) -> int:
        if value < 20:
            raise ValueError("allocated_storage must be at least 20 GiB")
        return value
