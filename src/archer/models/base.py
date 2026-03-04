"""
models/base.py — Shared configuration and result models.

Contains:
  - Provider and backend frozensets (shared across all cloud providers)
  - BackendConfig
  - OperationResult
  - ResourceChange
"""

from __future__ import annotations

from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, model_validator

# ---------------------------------------------------------------------------
# Shared valid-value frozensets
# ---------------------------------------------------------------------------

VALID_PROVIDERS: frozenset[str] = frozenset({"aws", "azure", "gcp"})
VALID_BACKEND_TYPES: frozenset[str] = frozenset({"local", "cloud"})
VALID_SUBNET_TYPES: frozenset[str] = frozenset({"public", "private"})


# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------


class BackendConfig(BaseModel):
    """Pulumi state backend configuration."""

    model_config = ConfigDict(frozen=True)

    type: Literal["local", "cloud"] = "local"
    path: str = ".archer-state"
    url: str | None = None

    @model_validator(mode="after")
    def cloud_requires_url_or_token(self) -> Self:
        # 'cloud' type without 'url' is valid - Pulumi Cloud honors PULUMI_ACCESS_TOKEN
        return self


# ---------------------------------------------------------------------------
# Operation result models
# ---------------------------------------------------------------------------


class ResourceChange(BaseModel):
    """Represents a single resource change from a Pulumi operation summary."""

    name: str
    type: str
    operation: str  # "create", "update", "delete", "same", "replace"


class OperationResult(BaseModel):
    """
    Structured result returned by every PulumiEngine method.

    success   — whether the operation completed without error
    operation — the command that was run (up / preview / destroy / refresh)
    elapsed   — wall-clock seconds
    error     — human-readable error message if success=False
    outputs   — key/value outputs exported from the Pulumi stack
    summary   — list of resource changes
    stack_name — the Pulumi stack that was targeted
    """

    success: bool
    operation: str
    elapsed: float
    error: str | None = None
    outputs: dict[str, Any] = {}
    summary: list[ResourceChange] = []
    stack_name: str = ""
    raw_stdout: str = ""
