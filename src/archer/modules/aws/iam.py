from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pulumi
import pulumi_aws as aws

from archer.modules.aws.utils import make_tags

if TYPE_CHECKING:
    from archer.models import AwsResources, InfrastructureConfig


@dataclass
class IamBuildResult:
    roles: dict[str, aws.iam.Role] = field(default_factory=dict)
    policies: dict[str, aws.iam.Policy] = field(default_factory=dict)
    outputs: dict[str, pulumi.Output[Any]] = field(default_factory=dict)


class IamBuilder:
    def __init__(self, config: InfrastructureConfig) -> None:
        self._config = config

    def build(self) -> IamBuildResult:
        resources: AwsResources = self._config.resources  # type: ignore[assignment]
        if not resources.iam_roles:
            return IamBuildResult()

        result = IamBuildResult()

        for role_cfg in resources.iam_roles:
            role_kwargs: dict[str, Any] = {
                "assume_role_policy": role_cfg.assume_role_policy,
                "path": role_cfg.path,
                "max_session_duration": role_cfg.max_session_duration,
                "tags": self._tags(role_cfg.name, role_cfg.tags),
            }
            if role_cfg.description:
                role_kwargs["description"] = role_cfg.description

            role = aws.iam.Role(role_cfg.name, **role_kwargs)
            result.roles[role_cfg.name] = role
            result.outputs[f"{role_cfg.name}_role_arn"] = role.arn

            # Attach managed policies
            for i, policy_arn in enumerate(role_cfg.managed_policy_arns):
                aws.iam.RolePolicyAttachment(
                    f"{role_cfg.name}-managed-{i}",
                    role=role.name,
                    policy_arn=policy_arn,
                )

            # Inline policies
            for inline_cfg in role_cfg.inline_policies:
                aws.iam.RolePolicy(
                    f"{role_cfg.name}-inline-{inline_cfg.name}",
                    role=role.id,
                    policy=inline_cfg.document,
                )

                # Also register as a named policy resource for referencing
                policy = aws.iam.Policy(
                    inline_cfg.name,
                    policy=inline_cfg.document,
                    description=inline_cfg.description,
                    tags=self._tags(inline_cfg.name, inline_cfg.tags),
                )
                result.policies[inline_cfg.name] = policy
                result.outputs[f"{inline_cfg.name}_policy_arn"] = policy.arn

        return result

    def _tags(self, name: str, extra: dict[str, str] | None = None) -> dict[str, str]:
        return make_tags(self._config.project, self._config.stack, name, extra, global_tags=dict(self._config.tags))
