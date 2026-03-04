"""
providers/aws.py - AWSProvider: orchestrates all AWS service builders.

Builder dependency order (each builder receives only results it needs):

  KMS → IAM → VPC → Subnets → SecurityGroups
  → NatGateway → TransitGateway → VpcEndpoints
  → S3 → EFS → ALB/NLB → Route53 → ACM
  → EC2 → ASG → EKS → ECS → RDS

All builder outputs are merged into a single map and exported via
pulumi.export() in get_outputs().
"""

from __future__ import annotations

from typing import Any

import pulumi

from archer.models import InfrastructureConfig
from archer.modules.aws.compute.asg import AsgBuilder
from archer.modules.aws.compute.ec2 import Ec2Builder
from archer.modules.aws.compute.ecs import EcsBuilder
from archer.modules.aws.compute.eks import EksBuilder
from archer.modules.aws.database.elasticache import ElastiCacheBuilder
from archer.modules.aws.database.rds import RdsBuilder
from archer.modules.aws.dns.acm import AcmBuilder
from archer.modules.aws.dns.route53 import Route53Builder
from archer.modules.aws.loadbalancing.alb import AlbBuilder
from archer.modules.aws.monitoring.cloudwatch import CloudWatchBuilder
from archer.modules.aws.networking.endpoints import VpcEndpointBuilder
from archer.modules.aws.networking.nat_gateway import NatGatewayBuilder
from archer.modules.aws.networking.security_groups import SecurityGroupBuilder
from archer.modules.aws.networking.subnets import SubnetBuilder
from archer.modules.aws.networking.transit_gateway import TransitGatewayBuilder
from archer.modules.aws.networking.vpc import VpcBuilder
from archer.modules.aws.security.iam import IamBuilder
from archer.modules.aws.security.kms import KmsBuilder
from archer.modules.aws.security.secrets_manager import SecretsManagerBuilder
from archer.modules.aws.storage.efs import EfsBuilder
from archer.modules.aws.storage.s3 import S3Builder
from archer.providers.base import BaseProvider


class AWSProvider(BaseProvider):
    """Top-level AWS provider - composes all service-specific builders."""

    def __init__(self, config: InfrastructureConfig) -> None:
        super().__init__(config)
        self._output_map: dict[str, pulumi.Output[Any]] = {}

    def build_resources(self) -> None:
        """Orchestrate all AWS service builders in dependency order."""

        # 1. KMS customer-managed keys (no dependencies)
        kms_result = KmsBuilder(self.config).build()
        self._output_map.update(kms_result.outputs)

        # 2. IAM roles + policies (no dependencies)
        iam_result = IamBuilder(self.config).build()
        self._output_map.update(iam_result.outputs)

        # 3. VPC + Internet Gateway
        vpc_result = VpcBuilder(self.config).build()
        self._output_map.update(vpc_result.outputs)

        # 4. Subnets + Route Tables (+ private route tables for NAT GW)
        subnet_result = SubnetBuilder(self.config, vpc_result).build()
        self._output_map.update(subnet_result.outputs)

        # 5. Default project-wide Security Group
        sg_result = SecurityGroupBuilder(self.config, vpc_result).build()
        self._output_map.update(sg_result.outputs)

        # 6. NAT Gateways (adds default routes to private route tables)
        nat_result = NatGatewayBuilder(self.config, subnet_result).build()
        self._output_map.update(nat_result.outputs)

        # 7. Transit Gateway (standalone - no VPC attachment wiring yet)
        tgw_result = TransitGatewayBuilder(self.config).build()
        self._output_map.update(tgw_result.outputs)

        # 8. VPC Endpoints (Gateway / Interface)
        endpoint_result = VpcEndpointBuilder(self.config, vpc_result, subnet_result).build()
        self._output_map.update(endpoint_result.outputs)

        # 9. S3 Buckets (no VPC dependency)
        s3_result = S3Builder(self.config).build()
        self._output_map.update(s3_result.outputs)

        # 10. EFS File Systems + Mount Targets
        efs_result = EfsBuilder(self.config, subnet_result).build()
        self._output_map.update(efs_result.outputs)

        # 11. Application + Network Load Balancers
        alb_result = AlbBuilder(self.config, vpc_result, subnet_result).build()
        self._output_map.update(alb_result.outputs)

        # 12. Route53 Hosted Zones + Records
        route53_result = Route53Builder(self.config, vpc_result).build()
        self._output_map.update(route53_result.outputs)

        # 13. ACM Certificates (auto DNS validation via Route53)
        acm_result = AcmBuilder(self.config, route53_result).build()
        self._output_map.update(acm_result.outputs)

        # 14. EC2 Instances
        ec2_result = Ec2Builder(self.config, subnet_result, sg_result).build()
        self._output_map.update(ec2_result.outputs)

        # 15. Auto Scaling Groups
        asg_result = AsgBuilder(self.config, subnet_result).build()
        self._output_map.update(asg_result.outputs)

        # 16. EKS Clusters + Node Groups
        eks_result = EksBuilder(self.config, subnet_result).build()
        self._output_map.update(eks_result.outputs)

        # 17. ECS Clusters + Fargate Services
        ecs_result = EcsBuilder(self.config, subnet_result).build()
        self._output_map.update(ecs_result.outputs)

        # 18. RDS Instances (own SG + SubnetGroup internally)
        rds_result = RdsBuilder(self.config, vpc_result, subnet_result).build()
        self._output_map.update(rds_result.outputs)

        # 19. ElastiCache clusters (Redis / Memcached)
        elasticache_result = ElastiCacheBuilder(self.config, subnet_result, sg_result).build()
        self._output_map.update(elasticache_result.outputs)

        # 20. Secrets Manager secrets
        secrets_result = SecretsManagerBuilder(self.config).build()
        self._output_map.update(secrets_result.outputs)

        # 21. CloudWatch Log Groups + Metric Alarms
        cloudwatch_result = CloudWatchBuilder(self.config).build()
        self._output_map.update(cloudwatch_result.outputs)

    def get_outputs(self) -> dict[str, pulumi.Output[Any]]:
        return self._output_map


__all__ = ["AWSProvider"]
