"""Shared pytest fixtures for archer tests."""

from __future__ import annotations

import pytest

from archer.models import AwsResources, InfrastructureConfig
from archer.models.aws.vpc import SubnetConfig, VpcConfig


@pytest.fixture()
def minimal_aws_config() -> InfrastructureConfig:
    """Bare-minimum valid AWS config — VPC only, no other resources."""
    return InfrastructureConfig(
        project="test-project",
        stack="test",
        provider="aws",
        region="us-east-1",
        resources=AwsResources(
            vpc=VpcConfig(name="test-vpc", cidr_block="10.0.0.0/16"),
        ),
    )


@pytest.fixture()
def aws_config_with_subnets() -> InfrastructureConfig:
    """AWS config with a VPC, one public and one private subnet."""
    return InfrastructureConfig(
        project="test-project",
        stack="test",
        provider="aws",
        region="us-east-1",
        resources=AwsResources(
            vpc=VpcConfig(name="test-vpc", cidr_block="10.0.0.0/16"),
            subnets=[
                SubnetConfig(
                    name="public-1",
                    cidr_block="10.0.1.0/24",
                    availability_zone="us-east-1a",
                    type="public",
                ),
                SubnetConfig(
                    name="private-1",
                    cidr_block="10.0.10.0/24",
                    availability_zone="us-east-1a",
                    type="private",
                ),
            ],
        ),
    )
