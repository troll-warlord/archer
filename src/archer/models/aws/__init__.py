from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from archer.models.aws.acm import AcmCertificateConfig
from archer.models.aws.asg import AsgConfig, AsgLaunchTemplateConfig
from archer.models.aws.cloudwatch import CloudWatchAlarmConfig, CloudWatchLogGroupConfig
from archer.models.aws.ec2 import (
    EbsVolumeConfig,
    Ec2Config,
    Ec2SecurityGroupConfig,
    SecurityGroupConfig,
    SecurityGroupRuleConfig,
)
from archer.models.aws.ecs import EcsConfig, EcsContainerConfig, EcsServiceConfig
from archer.models.aws.efs import EfsConfig
from archer.models.aws.eks import EksConfig, EksNodeGroupConfig
from archer.models.aws.elasticache import ElastiCacheClusterConfig, ElastiCacheSubnetGroupConfig
from archer.models.aws.elb import AlbConfig, ListenerConfig, NlbConfig, RedirectConfig, TargetGroupConfig
from archer.models.aws.iam import IamPolicyConfig, IamRoleConfig
from archer.models.aws.kms import KmsKeyConfig
from archer.models.aws.rds import RdsConfig
from archer.models.aws.route53 import Route53RecordConfig, Route53ZoneConfig
from archer.models.aws.s3 import S3Config
from archer.models.aws.secrets_manager import SecretsManagerSecretConfig
from archer.models.aws.vpc import NatGatewayConfig, SubnetConfig, TransitGatewayConfig, VpcConfig, VpcEndpointConfig


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
    "AcmCertificateConfig",
    "AlbConfig",
    "AsgConfig",
    "AsgLaunchTemplateConfig",
    "AwsResources",
    "CloudWatchAlarmConfig",
    "CloudWatchLogGroupConfig",
    "EbsVolumeConfig",
    "Ec2Config",
    "Ec2SecurityGroupConfig",
    "EcsConfig",
    "EcsContainerConfig",
    "EcsServiceConfig",
    "EfsConfig",
    "EksConfig",
    "EksNodeGroupConfig",
    "ElastiCacheClusterConfig",
    "ElastiCacheSubnetGroupConfig",
    "IamPolicyConfig",
    "IamRoleConfig",
    "KmsKeyConfig",
    "ListenerConfig",
    "NatGatewayConfig",
    "NlbConfig",
    "RdsConfig",
    "RedirectConfig",
    "Route53RecordConfig",
    "Route53ZoneConfig",
    "S3Config",
    "SecretsManagerSecretConfig",
    "SecurityGroupConfig",
    "SecurityGroupRuleConfig",
    "SubnetConfig",
    "TargetGroupConfig",
    "TransitGatewayConfig",
    "VpcConfig",
    "VpcEndpointConfig",
]
