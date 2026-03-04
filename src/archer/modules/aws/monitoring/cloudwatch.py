from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pulumi
import pulumi_aws as aws

from archer.modules.aws.utils import make_tags

if TYPE_CHECKING:
    from archer.models import InfrastructureConfig
    from archer.models.aws import AwsResources


@dataclass
class CloudWatchBuildResult:
    log_groups: dict[str, aws.cloudwatch.LogGroup] = field(default_factory=dict)
    alarms: dict[str, aws.cloudwatch.MetricAlarm] = field(default_factory=dict)
    outputs: dict[str, pulumi.Output[Any]] = field(default_factory=dict)


class CloudWatchBuilder:
    """Builds CloudWatch Log Groups and Metric Alarms."""

    def __init__(self, config: InfrastructureConfig) -> None:
        self._config = config

    def build(self) -> CloudWatchBuildResult:
        resources: AwsResources = self._config.resources  # type: ignore[assignment]
        has_log_groups = bool(getattr(resources, "log_groups", None))
        has_alarms = bool(getattr(resources, "cloudwatch_alarms", None))
        if not has_log_groups and not has_alarms:
            return CloudWatchBuildResult()

        result = CloudWatchBuildResult()

        # ---------------------------------------------------------------
        # Log Groups
        # ---------------------------------------------------------------
        for cfg in getattr(resources, "log_groups", []):
            lg_kwargs: dict[str, Any] = {}
            if cfg.retention_days is not None:
                lg_kwargs["retention_in_days"] = cfg.retention_days
            if cfg.kms_key_id:
                lg_kwargs["kms_key_id"] = cfg.kms_key_id

            log_group = aws.cloudwatch.LogGroup(
                cfg.name,
                name=cfg.name,
                tags=self._tags(cfg.name, cfg.tags),
                **lg_kwargs,
            )
            result.log_groups[cfg.name] = log_group
            result.outputs[f"log_group_{cfg.name.replace('/', '_')}_arn"] = log_group.arn

        # ---------------------------------------------------------------
        # Metric Alarms
        # ---------------------------------------------------------------
        for cfg in getattr(resources, "cloudwatch_alarms", []):
            alarm_kwargs: dict[str, Any] = {}
            if cfg.alarm_description:
                alarm_kwargs["alarm_description"] = cfg.alarm_description
            if cfg.alarm_actions:
                alarm_kwargs["alarm_actions"] = cfg.alarm_actions
            if cfg.ok_actions:
                alarm_kwargs["ok_actions"] = cfg.ok_actions
            if cfg.insufficient_data_actions:
                alarm_kwargs["insufficient_data_actions"] = cfg.insufficient_data_actions
            if cfg.dimensions:
                alarm_kwargs["dimensions"] = cfg.dimensions

            alarm = aws.cloudwatch.MetricAlarm(
                cfg.name,
                name=cfg.name,
                metric_name=cfg.metric_name,
                namespace=cfg.namespace,
                statistic=cfg.statistic,
                period=cfg.period,
                evaluation_periods=cfg.evaluation_periods,
                threshold=cfg.threshold,
                comparison_operator=cfg.comparison_operator,
                treat_missing_data=cfg.treat_missing_data,
                tags=self._tags(cfg.name, cfg.tags),
                **alarm_kwargs,
            )
            result.alarms[cfg.name] = alarm
            result.outputs[f"alarm_{cfg.name}_arn"] = alarm.arn

        return result

    def _tags(self, name: str, extra: dict[str, str] | None = None) -> dict[str, str]:
        return make_tags(self._config.project, self._config.stack, name, extra, global_tags=dict(self._config.tags))
