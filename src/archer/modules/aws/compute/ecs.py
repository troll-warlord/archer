from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pulumi
import pulumi_aws as aws

from archer.modules.aws.networking.subnets import SubnetBuildResult
from archer.modules.aws.utils import make_tags

if TYPE_CHECKING:
    from archer.models import AwsResources, InfrastructureConfig

_ECS_TASK_ASSUME_ROLE_POLICY = json.dumps(
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "ecs-tasks.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }
)


@dataclass
class EcsBuildResult:
    clusters: dict[str, aws.ecs.Cluster] = field(default_factory=dict)
    task_definitions: dict[str, aws.ecs.TaskDefinition] = field(default_factory=dict)
    services: dict[str, aws.ecs.Service] = field(default_factory=dict)
    execution_roles: dict[str, aws.iam.Role] = field(default_factory=dict)
    outputs: dict[str, pulumi.Output[Any]] = field(default_factory=dict)


class EcsBuilder:
    def __init__(
        self,
        config: InfrastructureConfig,
        subnet_result: SubnetBuildResult,
    ) -> None:
        self._config = config
        self._subnet_result = subnet_result

    def build(self) -> EcsBuildResult:
        resources: AwsResources = self._config.resources  # type: ignore[assignment]
        if not resources.ecs:
            return EcsBuildResult()

        result = EcsBuildResult()

        for ecs_cfg in resources.ecs:
            cluster = aws.ecs.Cluster(
                ecs_cfg.name,
                tags=self._tags(ecs_cfg.name, ecs_cfg.tags),
            )
            result.clusters[ecs_cfg.name] = cluster
            result.outputs[f"{ecs_cfg.name}_cluster_arn"] = cluster.arn

            for svc_cfg in ecs_cfg.services:
                svc_key = f"{ecs_cfg.name}-{svc_cfg.name}"

                # Execution role - needed to pull images + write logs
                exec_role = svc_cfg.execution_role_arn
                if exec_role is None:
                    auto_exec_role = aws.iam.Role(
                        f"{svc_key}-exec-role",
                        assume_role_policy=_ECS_TASK_ASSUME_ROLE_POLICY,
                        tags=self._tags(f"{svc_key}-exec-role"),
                    )
                    aws.iam.RolePolicyAttachment(
                        f"{svc_key}-exec-policy",
                        role=auto_exec_role.name,
                        policy_arn="arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy",
                    )
                    result.execution_roles[svc_key] = auto_exec_role
                    exec_role = auto_exec_role.arn

                # Container definitions
                container_defs: list[dict[str, Any]] = []
                for container in svc_cfg.containers:
                    cdef: dict[str, Any] = {
                        "name": container.name,
                        "image": container.image,
                        "cpu": container.cpu,
                        "memory": container.memory_mb,
                        "essential": True,
                    }
                    if container.port:
                        cdef["portMappings"] = [{"containerPort": container.port, "protocol": "tcp"}]
                    if container.environment:
                        cdef["environment"] = [{"name": k, "value": v} for k, v in container.environment.items()]
                    container_defs.append(cdef)

                task_def = aws.ecs.TaskDefinition(
                    f"{svc_key}-td",
                    family=svc_key,
                    network_mode="awsvpc",
                    requires_compatibilities=["FARGATE"],
                    cpu=str(svc_cfg.task_cpu),
                    memory=str(svc_cfg.task_memory_mb),
                    execution_role_arn=exec_role,
                    task_role_arn=svc_cfg.task_role_arn,
                    container_definitions=pulumi.Output.json_dumps(container_defs),
                    tags=self._tags(svc_key, svc_cfg.tags),
                )
                result.task_definitions[svc_key] = task_def

                subnet_ids = [self._subnet_result.subnets[ref].id for ref in svc_cfg.subnet_refs if ref in self._subnet_result.subnets]

                svc_kwargs: dict[str, Any] = {
                    "cluster": cluster.arn,
                    "task_definition": task_def.arn,
                    "desired_count": svc_cfg.desired_count,
                    "launch_type": "FARGATE",
                    "network_configuration": aws.ecs.ServiceNetworkConfigurationArgs(
                        subnets=subnet_ids,
                        assign_public_ip=svc_cfg.assign_public_ip,
                    ),
                    "tags": self._tags(svc_key, svc_cfg.tags),
                }
                if svc_cfg.target_group_arn:
                    first_port = next((c.port for c in svc_cfg.containers if c.port), None)
                    svc_kwargs["load_balancers"] = [
                        aws.ecs.ServiceLoadBalancerArgs(
                            target_group_arn=svc_cfg.target_group_arn,
                            container_name=svc_cfg.containers[0].name if svc_cfg.containers else svc_cfg.name,
                            container_port=first_port or 80,
                        )
                    ]

                service = aws.ecs.Service(svc_key, **svc_kwargs)
                result.services[svc_key] = service
                result.outputs[f"{svc_key}_service_name"] = service.name

        return result

    def _tags(self, name: str, extra: dict[str, str] | None = None) -> dict[str, str]:
        return make_tags(self._config.project, self._config.stack, name, extra, global_tags=dict(self._config.tags))
