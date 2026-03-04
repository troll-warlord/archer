"""Unit tests for AWS builder early-return guards.

These tests verify that builders return empty results (no Pulumi resources)
when the corresponding resource list is empty or None in the config.

Pulumi resource constructors are mocked so tests run outside a Pulumi program
context — no real AWS calls are made.
"""

from __future__ import annotations

from archer.models import AwsResources, InfrastructureConfig
from archer.models.aws.networking import SubnetConfig
from archer.modules.aws.compute.asg import AsgBuilder
from archer.modules.aws.compute.ec2 import Ec2Builder
from archer.modules.aws.compute.ecs import EcsBuilder
from archer.modules.aws.compute.eks import EksBuilder
from archer.modules.aws.database.rds import RdsBuilder
from archer.modules.aws.dns.acm import AcmBuilder
from archer.modules.aws.dns.route53 import Route53Builder
from archer.modules.aws.networking.nat_gateway import NatGatewayBuilder
from archer.modules.aws.networking.subnets import SubnetBuilder, SubnetBuildResult
from archer.modules.aws.networking.transit_gateway import TransitGatewayBuilder
from archer.modules.aws.networking.vpc import VpcBuilder, VpcBuildResult
from archer.modules.aws.security.iam import IamBuilder
from archer.modules.aws.security.kms import KmsBuilder
from archer.modules.aws.storage.efs import EfsBuilder
from archer.modules.aws.storage.s3 import S3Builder


def _empty_config(**overrides) -> InfrastructureConfig:
    """Return a config with no resources (all lists empty, vpc=None)."""
    return InfrastructureConfig(
        project="test",
        stack="test",
        provider="aws",
        region="us-east-1",
        resources=AwsResources(**overrides),
    )


def _empty_vpc_result() -> VpcBuildResult:
    return VpcBuildResult(vpc=None, igw=None)


def _empty_subnet_result() -> SubnetBuildResult:
    return SubnetBuildResult()


# ---------------------------------------------------------------------------
# Networking builders
# ---------------------------------------------------------------------------


class TestVpcBuilderEarlyReturn:
    def test_no_vpc_returns_empty(self):
        cfg = _empty_config()
        result = VpcBuilder(cfg).build()
        assert result.vpc is None
        assert result.igw is None
        assert result.outputs == {}


class TestSubnetBuilderEarlyReturn:
    def test_no_subnets_returns_empty(self):
        cfg = _empty_config()
        result = SubnetBuilder(cfg, _empty_vpc_result()).build()
        assert result.subnets == {}
        assert result.outputs == {}

    def test_no_vpc_returns_empty(self):
        cfg = _empty_config(subnets=[SubnetConfig(name="s", cidr_block="10.0.1.0/24", availability_zone="us-east-1a")])
        # vpc_result has no vpc object — subnets cannot be built
        result = SubnetBuilder(cfg, _empty_vpc_result()).build()
        assert result.subnets == {}


class TestNatGatewayBuilderEarlyReturn:
    def test_no_nat_gateways_returns_empty(self):
        cfg = _empty_config()
        result = NatGatewayBuilder(cfg, _empty_subnet_result()).build()
        assert result.outputs == {}


class TestTransitGatewayBuilderEarlyReturn:
    def test_no_tgw_returns_empty(self):
        cfg = _empty_config()
        result = TransitGatewayBuilder(cfg).build()
        assert result.outputs == {}


# ---------------------------------------------------------------------------
# Compute builders
# ---------------------------------------------------------------------------


class TestEc2BuilderEarlyReturn:
    def test_no_ec2_returns_empty(self):
        cfg = _empty_config()
        from archer.modules.aws.networking.security_groups import SecurityGroupBuildResult

        result = Ec2Builder(cfg, _empty_subnet_result(), SecurityGroupBuildResult()).build()
        assert result.instances == {}
        assert result.outputs == {}


class TestAsgBuilderEarlyReturn:
    def test_no_asg_returns_empty(self):
        cfg = _empty_config()
        result = AsgBuilder(cfg, _empty_subnet_result()).build()
        assert result.outputs == {}


class TestEksBuilderEarlyReturn:
    def test_no_eks_returns_empty(self):
        cfg = _empty_config()
        result = EksBuilder(cfg, _empty_subnet_result()).build()
        assert result.outputs == {}


class TestEcsBuilderEarlyReturn:
    def test_no_ecs_returns_empty(self):
        cfg = _empty_config()
        result = EcsBuilder(cfg, _empty_subnet_result()).build()
        assert result.outputs == {}


# ---------------------------------------------------------------------------
# Database builders
# ---------------------------------------------------------------------------


class TestRdsBuilderEarlyReturn:
    def test_no_rds_returns_empty(self):
        cfg = _empty_config()
        result = RdsBuilder(cfg, _empty_vpc_result(), _empty_subnet_result()).build()
        assert result.outputs == {}


# ---------------------------------------------------------------------------
# Storage builders
# ---------------------------------------------------------------------------


class TestS3BuilderEarlyReturn:
    def test_no_s3_returns_empty(self):
        cfg = _empty_config()
        result = S3Builder(cfg).build()
        assert result.outputs == {}


class TestEfsBuilderEarlyReturn:
    def test_no_efs_returns_empty(self):
        cfg = _empty_config()
        result = EfsBuilder(cfg, _empty_subnet_result()).build()
        assert result.outputs == {}


# ---------------------------------------------------------------------------
# Security builders
# ---------------------------------------------------------------------------


class TestKmsBuilderEarlyReturn:
    def test_no_kms_returns_empty(self):
        cfg = _empty_config()
        result = KmsBuilder(cfg).build()
        assert result.outputs == {}


class TestIamBuilderEarlyReturn:
    def test_no_iam_returns_empty(self):
        cfg = _empty_config()
        result = IamBuilder(cfg).build()
        assert result.outputs == {}


# ---------------------------------------------------------------------------
# DNS builders
# ---------------------------------------------------------------------------


class TestRoute53BuilderEarlyReturn:
    def test_no_route53_returns_empty(self):
        cfg = _empty_config()
        result = Route53Builder(cfg, _empty_vpc_result()).build()
        assert result.outputs == {}


class TestAcmBuilderEarlyReturn:
    def test_no_acm_returns_empty(self):
        from archer.modules.aws.dns.route53 import Route53BuildResult

        cfg = _empty_config()
        result = AcmBuilder(cfg, Route53BuildResult()).build()
        assert result.outputs == {}
