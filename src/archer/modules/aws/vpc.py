from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pulumi
import pulumi_aws as aws

from archer.modules.aws.utils import make_tags

if TYPE_CHECKING:
    from archer.models import AwsResources, InfrastructureConfig


@dataclass
class VpcBuildResult:
    vpc: aws.ec2.Vpc | None
    igw: aws.ec2.InternetGateway | None
    outputs: dict[str, pulumi.Output[Any]] = field(default_factory=dict)


class VpcBuilder:
    def __init__(self, config: InfrastructureConfig) -> None:
        self._config = config

    def build(self) -> VpcBuildResult:
        resources: AwsResources = self._config.resources  # type: ignore[assignment]
        if not resources.vpc:
            return VpcBuildResult(vpc=None, igw=None)

        vpc_cfg = resources.vpc

        vpc = aws.ec2.Vpc(
            vpc_cfg.name,
            cidr_block=vpc_cfg.cidr_block,
            enable_dns_hostnames=vpc_cfg.enable_dns_hostnames,
            enable_dns_support=vpc_cfg.enable_dns_support,
            tags=self._tags(vpc_cfg.name),
        )

        outputs: dict[str, pulumi.Output[Any]] = {
            "vpc_id": vpc.id,
            "vpc_cidr_block": vpc.cidr_block,
        }

        igw: aws.ec2.InternetGateway | None = None
        has_public_subnets = any(subnet.type == "public" for subnet in resources.subnets)
        if has_public_subnets:
            igw = aws.ec2.InternetGateway(
                f"{vpc_cfg.name}-igw",
                vpc_id=vpc.id,
                tags=self._tags(f"{vpc_cfg.name}-igw"),
            )
            outputs["internet_gateway_id"] = igw.id

        return VpcBuildResult(vpc=vpc, igw=igw, outputs=outputs)

    def _tags(self, name: str, extra: dict[str, str] | None = None) -> dict[str, str]:
        return make_tags(self._config.project, self._config.stack, name, extra, global_tags=dict(self._config.tags))
