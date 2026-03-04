from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pulumi
import pulumi_aws as aws

from archer.modules.aws.networking.subnets import SubnetBuildResult
from archer.modules.aws.utils import make_tags, resolve_subnet_ids

if TYPE_CHECKING:
    from archer.models import AwsResources, InfrastructureConfig


@dataclass
class AsgBuildResult:
    launch_templates: dict[str, aws.ec2.LaunchTemplate] = field(default_factory=dict)
    asgs: dict[str, aws.autoscaling.Group] = field(default_factory=dict)
    outputs: dict[str, pulumi.Output[Any]] = field(default_factory=dict)


class AsgBuilder:
    def __init__(
        self,
        config: InfrastructureConfig,
        subnet_result: SubnetBuildResult,
    ) -> None:
        self._config = config
        self._subnet_result = subnet_result

    def build(self) -> AsgBuildResult:
        resources: AwsResources = self._config.resources  # type: ignore[assignment]
        if not resources.asg:
            return AsgBuildResult()

        result = AsgBuildResult()

        for asg_cfg in resources.asg:
            lt_cfg = asg_cfg.launch_template
            lt_name = f"{asg_cfg.name}-lt"

            lt_kwargs: dict[str, Any] = {
                "name_prefix": f"{lt_name}-",
                "image_id": lt_cfg.ami,
                "instance_type": lt_cfg.instance_type,
                "tags": self._tags(lt_name),
                "tag_specifications": [
                    aws.ec2.LaunchTemplateTagSpecificationArgs(
                        resource_type="instance",
                        tags=self._tags(lt_name),
                    )
                ],
            }
            if lt_cfg.key_name:
                lt_kwargs["key_name"] = lt_cfg.key_name
            if lt_cfg.user_data:
                import base64

                lt_kwargs["user_data"] = base64.b64encode(lt_cfg.user_data.encode()).decode()
            if lt_cfg.security_group_refs:
                lt_kwargs["vpc_security_group_ids"] = lt_cfg.security_group_refs
            if lt_cfg.iam_instance_profile_arn:
                lt_kwargs["iam_instance_profile"] = aws.ec2.LaunchTemplateIamInstanceProfileArgs(arn=lt_cfg.iam_instance_profile_arn)

            launch_template = aws.ec2.LaunchTemplate(lt_name, **lt_kwargs)
            result.launch_templates[lt_name] = launch_template

            # Resolve subnets: prefer raw subnet_ids (existing infra), else look
            # up archer-declared subnets by name.
            subnet_id_inputs, subnet_deps = resolve_subnet_ids(
                asg_cfg.subnet_refs,
                asg_cfg.subnet_ids,
                self._subnet_result,
            )

            asg_kwargs: dict[str, Any] = {
                "desired_capacity": asg_cfg.desired_capacity,
                "min_size": asg_cfg.min_size,
                "max_size": asg_cfg.max_size,
                "vpc_zone_identifiers": subnet_id_inputs,
                "health_check_type": asg_cfg.health_check_type,
                "health_check_grace_period": asg_cfg.health_check_grace_period,
                "launch_template": aws.autoscaling.GroupLaunchTemplateArgs(
                    id=launch_template.id,
                    version="$Latest",
                ),
                "tags": [
                    aws.autoscaling.GroupTagArgs(
                        key=k,
                        value=v,
                        propagate_at_launch=True,
                    )
                    for k, v in self._tags(asg_cfg.name).items()
                ],
            }
            if asg_cfg.target_group_arns:
                asg_kwargs["target_group_arns"] = asg_cfg.target_group_arns

            asg = aws.autoscaling.Group(
                asg_cfg.name,
                **asg_kwargs,
                opts=pulumi.ResourceOptions(depends_on=subnet_deps) if subnet_deps else None,
            )
            result.asgs[asg_cfg.name] = asg
            result.outputs[f"{asg_cfg.name}_asg_name"] = asg.name

        return result

    def _tags(self, name: str, extra: dict[str, str] | None = None) -> dict[str, str]:
        return make_tags(self._config.project, self._config.stack, name, extra, global_tags=dict(self._config.tags))
