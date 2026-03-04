from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CloudWatchLogGroupConfig(BaseModel):
    """CloudWatch Log Group."""

    model_config = ConfigDict(frozen=True)

    name: str
    retention_days: int | None = 30  # None = retain indefinitely
    kms_key_id: str | None = None
    tags: dict[str, str] = Field(default_factory=dict)


class CloudWatchAlarmConfig(BaseModel):
    """
    CloudWatch Metric Alarm.

    alarm_actions / ok_actions accept SNS topic ARNs.
    dimensions is a flat key→value map, e.g. {"InstanceId": "i-1234"}.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    metric_name: str
    namespace: str
    statistic: Literal["Average", "Sum", "Minimum", "Maximum", "SampleCount"] = "Average"
    period: int = 300  # seconds
    evaluation_periods: int = 1
    threshold: float
    comparison_operator: Literal[
        "GreaterThanOrEqualToThreshold",
        "GreaterThanThreshold",
        "LessThanOrEqualToThreshold",
        "LessThanThreshold",
    ]
    alarm_actions: list[str] = Field(default_factory=list)  # SNS topic ARNs
    ok_actions: list[str] = Field(default_factory=list)
    insufficient_data_actions: list[str] = Field(default_factory=list)
    dimensions: dict[str, str] = Field(default_factory=dict)
    treat_missing_data: Literal["breaching", "notBreaching", "ignore", "missing"] = "missing"
    alarm_description: str | None = None
    tags: dict[str, str] = Field(default_factory=dict)
