"""Unit tests for archer Pydantic models and validators."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from archer.models import AwsResources, InfrastructureConfig
from archer.models.aws.compute import Ec2Config
from archer.models.aws.database import RdsConfig
from archer.models.aws.networking import SubnetConfig, VpcConfig

# ---------------------------------------------------------------------------
# InfrastructureConfig — top-level validation
# ---------------------------------------------------------------------------


class TestInfrastructureConfig:
    def test_valid_minimal_config(self):
        cfg = InfrastructureConfig(
            project="my-app",
            stack="dev",
            provider="aws",
            region="us-east-1",
        )
        assert cfg.project == "my-app"
        assert cfg.stack == "dev"

    def test_invalid_provider_raises(self):
        with pytest.raises(ValidationError, match="Unsupported provider"):
            InfrastructureConfig(
                project="x",
                stack="dev",
                provider="digitalocean",
                region="nyc1",
            )

    def test_stack_defaults_to_dev(self):
        cfg = InfrastructureConfig(project="x", provider="aws", region="us-east-1")
        assert cfg.stack == "dev"


# ---------------------------------------------------------------------------
# VpcConfig
# ---------------------------------------------------------------------------


class TestVpcConfig:
    def test_valid_cidr(self):
        vpc = VpcConfig(name="vpc", cidr_block="10.0.0.0/16")
        assert vpc.cidr_block == "10.0.0.0/16"

    def test_invalid_cidr_raises(self):
        with pytest.raises(ValidationError, match="Invalid CIDR"):
            VpcConfig(name="vpc", cidr_block="not-a-cidr")

    def test_defaults(self):
        vpc = VpcConfig()
        assert vpc.name == "main-vpc"
        assert vpc.enable_dns_hostnames is True
        assert vpc.enable_dns_support is True


# ---------------------------------------------------------------------------
# SubnetConfig
# ---------------------------------------------------------------------------


class TestSubnetConfig:
    def test_valid_private_subnet(self):
        s = SubnetConfig(
            name="private-1",
            cidr_block="10.0.1.0/24",
            availability_zone="us-east-1a",
            type="private",
        )
        assert s.type == "private"

    def test_malformed_az_raises(self):
        with pytest.raises(ValidationError, match="malformed"):
            SubnetConfig(
                name="s",
                cidr_block="10.0.1.0/24",
                availability_zone="us-east-1",  # missing trailing letter
            )

    def test_invalid_subnet_type_raises(self):
        with pytest.raises(ValidationError):
            SubnetConfig(
                name="s",
                cidr_block="10.0.1.0/24",
                availability_zone="us-east-1a",
                type="dmz",  # not public or private
            )


# ---------------------------------------------------------------------------
# Cross-field validators on InfrastructureConfig
# ---------------------------------------------------------------------------


class TestSubnetCidrContainment:
    def test_subnet_inside_vpc_passes(self):
        cfg = InfrastructureConfig(
            project="x",
            provider="aws",
            region="us-east-1",
            resources=AwsResources(
                vpc=VpcConfig(cidr_block="10.0.0.0/16"),
                subnets=[
                    SubnetConfig(
                        name="sub-1",
                        cidr_block="10.0.1.0/24",
                        availability_zone="us-east-1a",
                    )
                ],
            ),
        )
        assert len(cfg.resources.subnets) == 1

    def test_subnet_outside_vpc_raises(self):
        with pytest.raises(ValidationError, match="does not fit within VPC"):
            InfrastructureConfig(
                project="x",
                provider="aws",
                region="us-east-1",
                resources=AwsResources(
                    vpc=VpcConfig(cidr_block="10.0.0.0/16"),
                    subnets=[
                        SubnetConfig(
                            name="sub-1",
                            cidr_block="192.168.1.0/24",  # outside 10.0.0.0/16
                            availability_zone="us-east-1a",
                        )
                    ],
                ),
            )


class TestSubnetNameUniqueness:
    def test_duplicate_subnet_names_raises(self):
        with pytest.raises(ValidationError, match="Duplicate subnet"):
            InfrastructureConfig(
                project="x",
                provider="aws",
                region="us-east-1",
                resources=AwsResources(
                    vpc=VpcConfig(cidr_block="10.0.0.0/16"),
                    subnets=[
                        SubnetConfig(
                            name="public-1",
                            cidr_block="10.0.1.0/24",
                            availability_zone="us-east-1a",
                        ),
                        SubnetConfig(
                            name="public-1",  # duplicate
                            cidr_block="10.0.2.0/24",
                            availability_zone="us-east-1b",
                        ),
                    ],
                ),
            )


class TestResourceReferences:
    def test_ec2_unknown_subnet_ref_raises(self):
        with pytest.raises(ValidationError, match="unknown subnet"):
            InfrastructureConfig(
                project="x",
                provider="aws",
                region="us-east-1",
                resources=AwsResources(
                    vpc=VpcConfig(cidr_block="10.0.0.0/16"),
                    subnets=[
                        SubnetConfig(
                            name="public-1",
                            cidr_block="10.0.1.0/24",
                            availability_zone="us-east-1a",
                        )
                    ],
                    ec2=[
                        Ec2Config(
                            name="bastion",
                            instance_type="t3.micro",
                            ami="ami-12345678",
                            subnet_ref="nonexistent-subnet",  # bad ref
                        )
                    ],
                ),
            )

    def test_rds_unknown_subnet_ref_raises(self):
        with pytest.raises(ValidationError, match="unknown subnet"):
            InfrastructureConfig(
                project="x",
                provider="aws",
                region="us-east-1",
                resources=AwsResources(
                    vpc=VpcConfig(cidr_block="10.0.0.0/16"),
                    subnets=[
                        SubnetConfig(
                            name="private-1",
                            cidr_block="10.0.10.0/24",
                            availability_zone="us-east-1a",
                        )
                    ],
                    rds=[
                        RdsConfig(
                            name="db",
                            db_name="mydb",
                            username="admin",
                            subnet_refs=["ghost-subnet"],  # bad ref
                        )
                    ],
                ),
            )


# ---------------------------------------------------------------------------
# RdsConfig
# ---------------------------------------------------------------------------


class TestRdsConfig:
    def test_storage_below_minimum_raises(self):
        with pytest.raises(ValidationError, match="at least 20"):
            RdsConfig(
                name="db",
                db_name="mydb",
                username="admin",
                allocated_storage=5,
            )

    def test_defaults(self):
        rds = RdsConfig(name="db", db_name="mydb", username="admin")
        assert rds.engine == "postgres"
        assert rds.multi_az is False
        assert rds.publicly_accessible is False
