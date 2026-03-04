from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pulumi
import pulumi_aws as aws

from archer.modules.aws.utils import make_tags

if TYPE_CHECKING:
    from archer.models import AwsResources, InfrastructureConfig


@dataclass
class KmsBuildResult:
    keys: dict[str, aws.kms.Key] = field(default_factory=dict)
    aliases: dict[str, aws.kms.Alias] = field(default_factory=dict)
    outputs: dict[str, pulumi.Output[Any]] = field(default_factory=dict)


class KmsBuilder:
    def __init__(self, config: InfrastructureConfig) -> None:
        self._config = config

    def build(self) -> KmsBuildResult:
        resources: AwsResources = self._config.resources  # type: ignore[assignment]
        if not resources.kms_keys:
            return KmsBuildResult()

        result = KmsBuildResult()

        for key_cfg in resources.kms_keys:
            key_kwargs: dict[str, Any] = {
                "deletion_window_in_days": key_cfg.deletion_window_days,
                "enable_key_rotation": key_cfg.enable_key_rotation,
                "multi_region": key_cfg.multi_region,
                "tags": self._tags(key_cfg.name, key_cfg.tags),
            }
            if key_cfg.description:
                key_kwargs["description"] = key_cfg.description
            if key_cfg.key_policy:
                key_kwargs["policy"] = key_cfg.key_policy

            key = aws.kms.Key(key_cfg.name, **key_kwargs)
            result.keys[key_cfg.name] = key
            result.outputs[f"{key_cfg.name}_key_id"] = key.id
            result.outputs[f"{key_cfg.name}_key_arn"] = key.arn

            alias = aws.kms.Alias(
                f"alias/{key_cfg.name}",
                name=f"alias/{key_cfg.name}",
                target_key_id=key.id,
            )
            result.aliases[key_cfg.name] = alias

        return result

    def _tags(self, name: str, extra: dict[str, str] | None = None) -> dict[str, str]:
        return make_tags(self._config.project, self._config.stack, name, extra, global_tags=dict(self._config.tags))
