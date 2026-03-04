from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pulumi
import pulumi_aws as aws

from archer.modules.aws.networking.subnets import SubnetBuildResult
from archer.modules.aws.networking.vpc import VpcBuildResult
from archer.modules.aws.utils import make_tags, resolve_subnet_ids, resolve_vpc_id

if TYPE_CHECKING:
    from archer.models import AwsResources, InfrastructureConfig
    from archer.models.aws.loadbalancing import TargetGroupConfig


@dataclass
class AlbBuildResult:
    albs: dict[str, aws.lb.LoadBalancer] = field(default_factory=dict)
    nlbs: dict[str, aws.lb.LoadBalancer] = field(default_factory=dict)
    target_groups: dict[str, aws.lb.TargetGroup] = field(default_factory=dict)
    listeners: dict[str, aws.lb.Listener] = field(default_factory=dict)
    security_groups: dict[str, aws.ec2.SecurityGroup] = field(default_factory=dict)
    outputs: dict[str, pulumi.Output[Any]] = field(default_factory=dict)


def _build_target_groups(
    lb_name: str,
    tg_configs: list[TargetGroupConfig],
    vpc_id: pulumi.Input[str],
    tags_fn: Any,
) -> dict[str, aws.lb.TargetGroup]:
    tgs: dict[str, aws.lb.TargetGroup] = {}
    for tg_cfg in tg_configs:
        tg = aws.lb.TargetGroup(
            f"{lb_name}-{tg_cfg.name}",
            port=tg_cfg.port,
            protocol=tg_cfg.protocol,
            target_type=tg_cfg.target_type,
            vpc_id=vpc_id,
            health_check=aws.lb.TargetGroupHealthCheckArgs(
                path=tg_cfg.health_check_path,
                interval=tg_cfg.health_check_interval,
                healthy_threshold=tg_cfg.health_check_healthy_threshold,
                unhealthy_threshold=tg_cfg.health_check_unhealthy_threshold,
            ),
            tags=tags_fn(f"{lb_name}-{tg_cfg.name}", tg_cfg.tags),
        )
        tgs[tg_cfg.name] = tg
    return tgs


class AlbBuilder:
    def __init__(
        self,
        config: InfrastructureConfig,
        vpc_result: VpcBuildResult,
        subnet_result: SubnetBuildResult,
    ) -> None:
        self._config = config
        self._vpc_result = vpc_result
        self._subnet_result = subnet_result

    def build(self) -> AlbBuildResult:
        resources: AwsResources = self._config.resources  # type: ignore[assignment]
        result = AlbBuildResult()

        if not resources.alb and not resources.nlb:
            return result

        # --- ALBs ---
        for alb_cfg in resources.alb:
            # Resolve VPC: prefer raw vpc_id on config (existing infra), else archer VPC.
            vpc_id, vpc_deps = resolve_vpc_id(self._vpc_result, alb_cfg.vpc_id)
            if not vpc_id:
                pulumi.log.warn(f"ALB '{alb_cfg.name}' skipped: no VPC available. Set alb.vpc_id or declare a vpc block.")
                continue

            # Security group for ALB
            sg = aws.ec2.SecurityGroup(
                f"{alb_cfg.name}-sg",
                vpc_id=vpc_id,
                description=f"SG for ALB {alb_cfg.name}",
                ingress=[
                    aws.ec2.SecurityGroupIngressArgs(
                        from_port=0,
                        to_port=0,
                        protocol="-1",
                        cidr_blocks=["0.0.0.0/0"],
                    )
                ],
                egress=[
                    aws.ec2.SecurityGroupEgressArgs(
                        from_port=0,
                        to_port=0,
                        protocol="-1",
                        cidr_blocks=["0.0.0.0/0"],
                    )
                ],
                tags=self._tags(f"{alb_cfg.name}-sg"),
                opts=pulumi.ResourceOptions(depends_on=vpc_deps) if vpc_deps else None,
            )
            result.security_groups[alb_cfg.name] = sg

            subnet_id_inputs, subnet_deps = resolve_subnet_ids(
                alb_cfg.subnet_refs,
                alb_cfg.subnet_ids,
                self._subnet_result,
            )

            alb = aws.lb.LoadBalancer(
                alb_cfg.name,
                load_balancer_type="application",
                internal=alb_cfg.internal,
                security_groups=[sg.id],
                subnets=subnet_id_inputs,
                enable_deletion_protection=alb_cfg.deletion_protection,
                tags=self._tags(alb_cfg.name, alb_cfg.tags),
                opts=pulumi.ResourceOptions(depends_on=subnet_deps) if subnet_deps else None,
            )
            result.albs[alb_cfg.name] = alb
            result.outputs[f"{alb_cfg.name}_alb_dns"] = alb.dns_name
            result.outputs[f"{alb_cfg.name}_alb_zone_id"] = alb.zone_id
            result.outputs[f"{alb_cfg.name}_alb_arn"] = alb.arn

            tgs = _build_target_groups(alb_cfg.name, alb_cfg.target_groups, vpc_id, self._tags)
            result.target_groups.update(tgs)

            for i, listener_cfg in enumerate(alb_cfg.listeners):
                tg = tgs.get(listener_cfg.target_group_ref)
                listener_kwargs: dict[str, Any] = {
                    "load_balancer_arn": alb.arn,
                    "port": listener_cfg.port,
                    "protocol": listener_cfg.protocol,
                    "tags": self._tags(f"{alb_cfg.name}-listener-{i}"),
                }
                if listener_cfg.redirect_to_https:
                    listener_kwargs["default_actions"] = [
                        aws.lb.ListenerDefaultActionArgs(
                            type="redirect",
                            redirect=aws.lb.ListenerDefaultActionRedirectArgs(
                                port="443",
                                protocol="HTTPS",
                                status_code="HTTP_301",
                            ),
                        )
                    ]
                elif tg:
                    listener_kwargs["default_actions"] = [
                        aws.lb.ListenerDefaultActionArgs(
                            type="forward",
                            target_group_arn=tg.arn,
                        )
                    ]
                if listener_cfg.certificate_arn:
                    listener_kwargs["certificate_arn"] = listener_cfg.certificate_arn
                if listener_cfg.ssl_policy:
                    listener_kwargs["ssl_policy"] = listener_cfg.ssl_policy

                listener = aws.lb.Listener(f"{alb_cfg.name}-listener-{i}", **listener_kwargs)
                result.listeners[f"{alb_cfg.name}-listener-{i}"] = listener

        # --- NLBs ---
        for nlb_cfg in resources.nlb:
            # Resolve VPC and subnets for NLB.
            vpc_id, vpc_deps = resolve_vpc_id(self._vpc_result, nlb_cfg.vpc_id)
            if not vpc_id:
                pulumi.log.warn(f"NLB '{nlb_cfg.name}' skipped: no VPC available. Set nlb.vpc_id or declare a vpc block.")
                continue

            subnet_id_inputs, subnet_deps = resolve_subnet_ids(
                nlb_cfg.subnet_refs,
                nlb_cfg.subnet_ids,
                self._subnet_result,
            )

            nlb = aws.lb.LoadBalancer(
                nlb_cfg.name,
                load_balancer_type="network",
                internal=nlb_cfg.internal,
                subnets=subnet_id_inputs,
                enable_cross_zone_load_balancing=nlb_cfg.cross_zone,
                tags=self._tags(nlb_cfg.name, nlb_cfg.tags),
                opts=pulumi.ResourceOptions(depends_on=subnet_deps) if subnet_deps else None,
            )
            result.nlbs[nlb_cfg.name] = nlb
            result.outputs[f"{nlb_cfg.name}_nlb_dns"] = nlb.dns_name
            result.outputs[f"{nlb_cfg.name}_nlb_arn"] = nlb.arn

            tgs = _build_target_groups(nlb_cfg.name, nlb_cfg.target_groups, vpc_id, self._tags)
            result.target_groups.update(tgs)

            for i, listener_cfg in enumerate(nlb_cfg.listeners):
                tg = tgs.get(listener_cfg.target_group_ref)
                if not tg:
                    continue
                listener_kwargs = {
                    "load_balancer_arn": nlb.arn,
                    "port": listener_cfg.port,
                    "protocol": listener_cfg.protocol,
                    "default_actions": [
                        aws.lb.ListenerDefaultActionArgs(
                            type="forward",
                            target_group_arn=tg.arn,
                        )
                    ],
                    "tags": self._tags(f"{nlb_cfg.name}-listener-{i}"),
                }
                if listener_cfg.certificate_arn:
                    listener_kwargs["certificate_arn"] = listener_cfg.certificate_arn

                listener = aws.lb.Listener(f"{nlb_cfg.name}-listener-{i}", **listener_kwargs)
                result.listeners[f"{nlb_cfg.name}-listener-{i}"] = listener

        return result

    def _tags(self, name: str, extra: dict[str, str] | None = None) -> dict[str, str]:
        return make_tags(self._config.project, self._config.stack, name, extra, global_tags=dict(self._config.tags))
