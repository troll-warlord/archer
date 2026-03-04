"""
models/__init__.py — Public surface of the archer models package.

InfrastructureConfig lives here because it cross-references all three
provider resource containers (AwsResources, AzureResources, GcpResources).

Everything is re-exported so that existing code using
  `from archer.models import X`
continues to work without changes.
"""

from __future__ import annotations

import ipaddress

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Re-export shared models
from archer.models.aws import (
    AwsResources,
    CloudWatchAlarmConfig,
    CloudWatchLogGroupConfig,
    Ec2Config,
    ElastiCacheClusterConfig,
    RdsConfig,
    SecretsManagerSecretConfig,
    SecurityGroupConfig,
    SubnetConfig,
    VpcConfig,
)
from archer.models.azure import (
    AzureResources,
    AzureSubnetConfig,
    AzureVmConfig,
    AzureVnetConfig,
)
from archer.models.base import (
    VALID_BACKEND_TYPES,
    VALID_PROVIDERS,
    VALID_SUBNET_TYPES,
    BackendConfig,
    OperationResult,
    ResourceChange,
)
from archer.models.gcp import (
    GcpInstanceConfig,
    GcpResources,
    GcpSubnetConfig,
    GcpVpcConfig,
)

# ---------------------------------------------------------------------------
# Root infrastructure config
# ---------------------------------------------------------------------------


class InfrastructureConfig(BaseModel):
    """
    Root configuration model.

    Loaded from a YAML file and fully validated before any Pulumi operation
    begins. Cross-field semantic checks (e.g. CIDR containment, subnet
    reference integrity) are performed in @model_validator methods.
    """

    model_config = ConfigDict(frozen=True)

    project: str
    stack: str = "dev"
    provider: str
    region: str
    backend: BackendConfig = BackendConfig()
    # Global tags applied to every resource (merged before per-resource tags).
    tags: dict[str, str] = Field(default_factory=dict)

    # Provider-specific resource blocks (only one is used at a time)
    resources: AwsResources | AzureResources | GcpResources = AwsResources()

    # -----------------------------------------------------------------------
    # Field validators
    # -----------------------------------------------------------------------

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        if v not in VALID_PROVIDERS:
            raise ValueError(f"Unsupported provider '{v}'. Supported providers: {sorted(VALID_PROVIDERS)}")
        return v

    # -----------------------------------------------------------------------
    # Cross-field model validators
    # -----------------------------------------------------------------------

    @model_validator(mode="after")
    def validate_region_for_provider(self) -> InfrastructureConfig:
        """Region is validated by the cloud provider at deploy/preview time."""
        return self

    @model_validator(mode="after")
    def validate_resources_match_provider(self) -> InfrastructureConfig:
        """Ensure the resources block type matches the declared provider."""
        return self

    @model_validator(mode="after")
    def validate_aws_subnet_cidrs_fit_vpc(self) -> InfrastructureConfig:
        """Ensure every AWS subnet CIDR is fully contained within the VPC CIDR."""
        if not isinstance(self.resources, AwsResources):
            return self
        if not self.resources.vpc or not self.resources.subnets:
            return self

        vpc_network = ipaddress.ip_network(self.resources.vpc.cidr_block, strict=False)
        for subnet in self.resources.subnets:
            try:
                subnet_network = ipaddress.ip_network(subnet.cidr_block, strict=False)
            except ValueError:
                continue
            if subnet_network.version != vpc_network.version or not (subnet_network.network_address in vpc_network and subnet_network.broadcast_address in vpc_network):
                raise ValueError(f"Subnet '{subnet.name}' CIDR {subnet.cidr_block} does not fit within VPC CIDR {self.resources.vpc.cidr_block}")
        return self

    @model_validator(mode="after")
    def validate_aws_subnet_name_uniqueness(self) -> InfrastructureConfig:
        """Reject duplicate subnet names in the same config."""
        if not isinstance(self.resources, AwsResources):
            return self
        names = [s.name for s in self.resources.subnets]
        if len(names) != len(set(names)):
            duplicates = {n for n in names if names.count(n) > 1}
            raise ValueError(f"Duplicate subnet name(s) found: {duplicates}")
        return self

    @model_validator(mode="after")
    def validate_aws_resource_references(self) -> InfrastructureConfig:
        """Validate that EC2/RDS subnet refs point to declared subnets."""
        if not isinstance(self.resources, AwsResources):
            return self

        subnet_names = {s.name for s in self.resources.subnets}

        for ec2 in self.resources.ec2:
            if ec2.subnet_ref and ec2.subnet_ref not in subnet_names:
                raise ValueError(f"EC2 instance '{ec2.name}' references unknown subnet '{ec2.subnet_ref}'. Declared subnets: {sorted(subnet_names)}")

        for rds in self.resources.rds:
            for ref in rds.subnet_refs:
                if ref not in subnet_names:
                    raise ValueError(f"RDS instance '{rds.name}' references unknown subnet '{ref}'. Declared subnets: {sorted(subnet_names)}")
        return self


__all__ = [
    "VALID_BACKEND_TYPES",
    "VALID_PROVIDERS",
    "VALID_SUBNET_TYPES",
    "AwsResources",
    "AzureResources",
    "AzureSubnetConfig",
    "AzureVmConfig",
    "AzureVnetConfig",
    "BackendConfig",
    "CloudWatchAlarmConfig",
    "CloudWatchLogGroupConfig",
    "Ec2Config",
    "ElastiCacheClusterConfig",
    "GcpInstanceConfig",
    "GcpResources",
    "GcpSubnetConfig",
    "GcpVpcConfig",
    "InfrastructureConfig",
    "OperationResult",
    "RdsConfig",
    "ResourceChange",
    "SecretsManagerSecretConfig",
    "SecurityGroupConfig",
    "SubnetConfig",
    "VpcConfig",
]
