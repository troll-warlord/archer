from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pulumi
import pulumi_aws as aws

from archer.modules.aws.utils import make_tags

if TYPE_CHECKING:
    from archer.models import AwsResources, InfrastructureConfig


@dataclass
class S3BuildResult:
    buckets: dict[str, aws.s3.BucketV2] = field(default_factory=dict)
    outputs: dict[str, pulumi.Output[Any]] = field(default_factory=dict)


class S3Builder:
    def __init__(self, config: InfrastructureConfig) -> None:
        self._config = config

    def build(self) -> S3BuildResult:
        resources: AwsResources = self._config.resources  # type: ignore[assignment]
        if not resources.s3:
            return S3BuildResult()

        result = S3BuildResult()

        for s3_cfg in resources.s3:
            bucket = aws.s3.BucketV2(
                s3_cfg.name,
                force_destroy=s3_cfg.force_destroy,
                tags=self._tags(s3_cfg.name, s3_cfg.tags),
            )
            result.buckets[s3_cfg.name] = bucket
            result.outputs[f"{s3_cfg.name}_bucket_id"] = bucket.id
            result.outputs[f"{s3_cfg.name}_bucket_arn"] = bucket.arn

            # Versioning
            aws.s3.BucketVersioningV2(
                f"{s3_cfg.name}-versioning",
                bucket=bucket.id,
                versioning_configuration=aws.s3.BucketVersioningV2VersioningConfigurationArgs(status="Enabled" if s3_cfg.versioning else "Suspended"),
            )

            # Server-side encryption
            sse_rule = aws.s3.BucketServerSideEncryptionConfigurationV2RuleArgs(
                apply_server_side_encryption_by_default=aws.s3.BucketServerSideEncryptionConfigurationV2RuleApplyServerSideEncryptionByDefaultArgs(
                    sse_algorithm=s3_cfg.sse_algorithm,
                    kms_master_key_id=s3_cfg.kms_master_key_id,
                ),
                bucket_key_enabled=(s3_cfg.sse_algorithm == "aws:kms"),
            )
            aws.s3.BucketServerSideEncryptionConfigurationV2(
                f"{s3_cfg.name}-sse",
                bucket=bucket.id,
                rules=[sse_rule],
            )

            # Block public access
            aws.s3.BucketPublicAccessBlock(
                f"{s3_cfg.name}-public-access",
                bucket=bucket.id,
                block_public_acls=s3_cfg.block_public_acls,
                block_public_policy=s3_cfg.block_public_policy,
                ignore_public_acls=s3_cfg.ignore_public_acls,
                restrict_public_buckets=s3_cfg.restrict_public_buckets,
            )

        return result

    def _tags(self, name: str, extra: dict[str, str] | None = None) -> dict[str, str]:
        return make_tags(self._config.project, self._config.stack, name, extra, global_tags=dict(self._config.tags))
