from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pulumi
import pulumi_aws as aws

from archer.modules.aws.subnets import SubnetBuildResult
from archer.modules.aws.utils import make_tags, resolve_subnet_ids

if TYPE_CHECKING:
    from archer.models import AwsResources, InfrastructureConfig


@dataclass
class EfsBuildResult:
    file_systems: dict[str, aws.efs.FileSystem] = field(default_factory=dict)
    mount_targets: dict[str, list[aws.efs.MountTarget]] = field(default_factory=dict)
    outputs: dict[str, pulumi.Output[Any]] = field(default_factory=dict)


class EfsBuilder:
    def __init__(
        self,
        config: InfrastructureConfig,
        subnet_result: SubnetBuildResult,
    ) -> None:
        self._config = config
        self._subnet_result = subnet_result

    def build(self) -> EfsBuildResult:
        resources: AwsResources = self._config.resources  # type: ignore[assignment]
        if not resources.efs:
            return EfsBuildResult()

        result = EfsBuildResult()

        for efs_cfg in resources.efs:
            efs_kwargs: dict[str, Any] = {
                "performance_mode": efs_cfg.performance_mode,
                "throughput_mode": efs_cfg.throughput_mode,
                "encrypted": efs_cfg.encrypted,
                "tags": self._tags(efs_cfg.name, efs_cfg.tags),
            }
            if efs_cfg.kms_key_id:
                efs_kwargs["kms_key_id"] = efs_cfg.kms_key_id
            if efs_cfg.provisioned_throughput_mibps is not None:
                efs_kwargs["provisioned_throughput_in_mibps"] = efs_cfg.provisioned_throughput_mibps

            fs = aws.efs.FileSystem(efs_cfg.name, **efs_kwargs)
            result.file_systems[efs_cfg.name] = fs
            result.outputs[f"{efs_cfg.name}_efs_id"] = fs.id
            result.outputs[f"{efs_cfg.name}_efs_arn"] = fs.arn

            mount_targets: list[aws.efs.MountTarget] = []
            # Resolve subnets: prefer raw subnet_ids (existing infra), else look up
            # archer-declared subnets by name.
            efs_subnet_ids, efs_subnet_deps = resolve_subnet_ids(
                efs_cfg.subnet_refs,
                efs_cfg.subnet_ids,
                self._subnet_result,
            )
            for i, subnet_id in enumerate(efs_subnet_ids):
                label = efs_cfg.subnet_ids[i] if efs_cfg.subnet_ids else efs_cfg.subnet_refs[i]
                mt = aws.efs.MountTarget(
                    f"{efs_cfg.name}-mt-{label}",
                    file_system_id=fs.id,
                    subnet_id=subnet_id,
                    opts=pulumi.ResourceOptions(depends_on=efs_subnet_deps) if efs_subnet_deps else None,
                )
                mount_targets.append(mt)

            result.mount_targets[efs_cfg.name] = mount_targets

        return result

    def _tags(self, name: str, extra: dict[str, str] | None = None) -> dict[str, str]:
        return make_tags(self._config.project, self._config.stack, name, extra, global_tags=dict(self._config.tags))
