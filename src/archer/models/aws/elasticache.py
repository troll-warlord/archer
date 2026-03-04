"""
models/aws/elasticache.py — Amazon ElastiCache models.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ElastiCacheSubnetGroupConfig(BaseModel):
    """Dedicated subnet group for ElastiCache — usually auto-created alongside the cluster."""

    model_config = ConfigDict(frozen=True)

    name: str | None = None  # defaults to <cluster-name>-subnet-group
    subnet_refs: list[str] = Field(default_factory=list)
    subnet_ids: list[str] = Field(default_factory=list)


class ElastiCacheClusterConfig(BaseModel):
    """
    ElastiCache cluster configuration.

    For Redis: uses a ReplicationGroup (supports both single-node and multi-AZ).
    For Memcached: uses a plain Cache Cluster.

    Secrets / auth:
      auth_token_env_var — name of the env var holding the AUTH token (Redis ≥ 6 + transit_encryption).
    """

    model_config = ConfigDict(frozen=True)

    name: str
    engine: Literal["redis", "memcached"] = "redis"
    node_type: str = "cache.t3.micro"
    # Number of cache nodes.  For Redis ReplicationGroup this is the number of *replicas*
    # in addition to the primary; for Memcached it is the total node count.
    num_cache_nodes: int = 1
    engine_version: str | None = None
    # 6379 for Redis, 11211 for Memcached — omit to use the engine default
    port: int | None = None

    # Networking
    subnet_refs: list[str] = Field(default_factory=list)
    subnet_ids: list[str] = Field(default_factory=list)
    security_group_refs: list[str] = Field(default_factory=list)
    existing_security_group_ids: list[str] = Field(default_factory=list)

    # Security
    at_rest_encryption: bool = True
    transit_encryption: bool = True  # Redis only; requires auth_token when True
    # Name of the env var holding the Redis AUTH token (only used when transit_encryption=True)
    auth_token_env_var: str | None = None
    kms_key_id: str | None = None

    # Redis replication
    automatic_failover_enabled: bool = False  # requires num_cache_nodes >= 2
    multi_az_enabled: bool = False  # requires automatic_failover_enabled

    # Maintenance
    maintenance_window: str | None = None  # e.g. "sun:05:00-sun:06:00"
    snapshot_retention_limit: int = 0  # 0 = no snapshots; Redis only

    tags: dict[str, str] = Field(default_factory=dict)
