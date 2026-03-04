from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pulumi
import pulumi_aws as aws

from archer.modules.aws.utils import make_tags

if TYPE_CHECKING:
    from archer.models import InfrastructureConfig
    from archer.models.aws import AwsResources


@dataclass
class SecretsManagerBuildResult:
    secrets: dict[str, aws.secretsmanager.Secret] = field(default_factory=dict)
    outputs: dict[str, pulumi.Output[Any]] = field(default_factory=dict)


class SecretsManagerBuilder:
    """Builds AWS Secrets Manager secrets with optional initial versions."""

    def __init__(self, config: InfrastructureConfig) -> None:
        self._config = config

    def build(self) -> SecretsManagerBuildResult:
        resources: AwsResources = self._config.resources  # type: ignore[assignment]
        if not resources.secrets:
            return SecretsManagerBuildResult()

        result = SecretsManagerBuildResult()

        for cfg in resources.secrets:
            secret_kwargs: dict[str, Any] = {}
            if cfg.description:
                secret_kwargs["description"] = cfg.description
            if cfg.kms_key_id:
                secret_kwargs["kms_key_id"] = cfg.kms_key_id
            if cfg.recovery_window_days == 0:
                secret_kwargs["force_overwrite_replica_secret"] = True
                secret_kwargs["recovery_window_in_days"] = 0
            else:
                secret_kwargs["recovery_window_in_days"] = cfg.recovery_window_days

            secret = aws.secretsmanager.Secret(
                cfg.name,
                name=cfg.name,
                tags=self._tags(cfg.name, cfg.tags),
                **secret_kwargs,
            )
            result.secrets[cfg.name] = secret
            result.outputs[f"secret_{cfg.name}_arn"] = secret.arn

            # Populate an initial version if a value source is configured
            secret_value: str | None = None
            if cfg.env_var:
                secret_value = os.environ.get(cfg.env_var)
            elif cfg.secret_string:
                secret_value = cfg.secret_string

            if secret_value is not None:
                aws.secretsmanager.SecretVersion(
                    f"{cfg.name}-version",
                    secret_id=secret.id,
                    secret_string=secret_value,
                    opts=pulumi.ResourceOptions(depends_on=[secret]),
                )

        return result

    def _tags(self, name: str, extra: dict[str, str] | None = None) -> dict[str, str]:
        return make_tags(self._config.project, self._config.stack, name, extra, global_tags=dict(self._config.tags))
