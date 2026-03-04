from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from archer.models.aws.cache import ElastiCacheClusterConfig
from archer.models.aws.compute import (
    AsgConfig,
    AsgLaunchTemplateConfig,
    EbsVolumeConfig,
    Ec2Config,
    Ec2SecurityGroupConfig,
    EcsConfig,
    EcsContainerConfig,
    EcsServiceConfig,
    EksConfig,
    EksNodeGroupConfig,
    SecurityGroupRuleConfig,
)
from archer.models.aws.database import RdsConfig
from archer.models.aws.dns import AcmCertificateConfig, Route53RecordConfig, Route53ZoneConfig
from archer.models.aws.loadbalancing import AlbConfig, ListenerConfig, NlbConfig, TargetGroupConfig
from archer.models.aws.monitoring import CloudWatchAlarmConfig, CloudWatchLogGroupConfig
from archer.models.aws.networking import NatGatewayConfig, SubnetConfig, TransitGatewayConfig, VpcConfig, VpcEndpointConfig
from archer.models.aws.secrets import SecretsManagerSecretConfig
from archer.models.aws.security import IamPolicyConfig, IamRoleConfig, KmsKeyConfig, SecurityGroupConfig
from archer.models.aws.storage import EfsConfig, S3Config


class AwsResources(BaseModel):
    model_config = ConfigDict(frozen=True)

    # --- Networking ---
    vpc: VpcConfig | None = None
    subnets: list[SubnetConfig] = Field(default_factory=list)
    nat_gateways: list[NatGatewayConfig] = Field(default_factory=list)
    transit_gateways: list[TransitGatewayConfig] = Field(default_factory=list)
    vpc_endpoints: list[VpcEndpointConfig] = Field(default_factory=list)
    # Named security groups (referenced by other resources via security_group_refs)
    security_groups: list[SecurityGroupConfig] = Field(default_factory=list)

    # --- Compute ---
    ec2: list[Ec2Config] = Field(default_factory=list)
    asg: list[AsgConfig] = Field(default_factory=list)
    eks: list[EksConfig] = Field(default_factory=list)
    ecs: list[EcsConfig] = Field(default_factory=list)

    # --- Database ---
    rds: list[RdsConfig] = Field(default_factory=list)
    elasticache: list[ElastiCacheClusterConfig] = Field(default_factory=list)

    # --- Storage ---
    s3: list[S3Config] = Field(default_factory=list)
    efs: list[EfsConfig] = Field(default_factory=list)

    # --- Load Balancing ---
    alb: list[AlbConfig] = Field(default_factory=list)
    nlb: list[NlbConfig] = Field(default_factory=list)

    # --- DNS / TLS ---
    route53_zones: list[Route53ZoneConfig] = Field(default_factory=list)
    route53_records: list[Route53RecordConfig] = Field(default_factory=list)
    acm_certificates: list[AcmCertificateConfig] = Field(default_factory=list)

    # --- Security ---
    iam_roles: list[IamRoleConfig] = Field(default_factory=list)
    kms_keys: list[KmsKeyConfig] = Field(default_factory=list)
    secrets: list[SecretsManagerSecretConfig] = Field(default_factory=list)

    # --- Observability ---
    log_groups: list[CloudWatchLogGroupConfig] = Field(default_factory=list)
    cloudwatch_alarms: list[CloudWatchAlarmConfig] = Field(default_factory=list)


__all__ = [
    "VALID_AWS_REGIONS",
    "VALID_EC2_INSTANCE_TYPES",
    "VALID_RDS_ENGINES",
    "VALID_RDS_INSTANCE_CLASSES",
    "AcmCertificateConfig",
    "AlbConfig",
    "AsgConfig",
    "AsgLaunchTemplateConfig",
    "AwsResources",
    "EbsVolumeConfig",
    "Ec2Config",
    "Ec2SecurityGroupConfig",
    "EcsConfig",
    "EcsContainerConfig",
    "EcsServiceConfig",
    "EfsConfig",
    "EksConfig",
    "EksNodeGroupConfig",
    "IamPolicyConfig",
    "IamRoleConfig",
    "KmsKeyConfig",
    "ListenerConfig",
    "NatGatewayConfig",
    "NlbConfig",
    "RdsConfig",
    "Route53RecordConfig",
    "Route53ZoneConfig",
    "S3Config",
    "SecurityGroupRuleConfig",
    "SubnetConfig",
    "TargetGroupConfig",
    "TransitGatewayConfig",
    "VpcConfig",
    "VpcEndpointConfig",
]
