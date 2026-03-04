from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pulumi
import pulumi_aws as aws

from archer.modules.aws.subnets import SubnetBuildResult
from archer.modules.aws.utils import make_tags

if TYPE_CHECKING:
    from archer.models import AwsResources, InfrastructureConfig

_EKS_CLUSTER_ASSUME_ROLE_POLICY = json.dumps(
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "eks.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }
)

_EC2_ASSUME_ROLE_POLICY = json.dumps(
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "ec2.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }
)


@dataclass
class EksBuildResult:
    clusters: dict[str, aws.eks.Cluster] = field(default_factory=dict)
    node_groups: dict[str, aws.eks.NodeGroup] = field(default_factory=dict)
    cluster_roles: dict[str, aws.iam.Role] = field(default_factory=dict)
    node_roles: dict[str, aws.iam.Role] = field(default_factory=dict)
    outputs: dict[str, pulumi.Output[Any]] = field(default_factory=dict)


class EksBuilder:
    def __init__(
        self,
        config: InfrastructureConfig,
        subnet_result: SubnetBuildResult,
    ) -> None:
        self._config = config
        self._subnet_result = subnet_result

    def build(self) -> EksBuildResult:
        resources: AwsResources = self._config.resources  # type: ignore[assignment]
        if not resources.eks:
            return EksBuildResult()

        result = EksBuildResult()

        for eks_cfg in resources.eks:
            # --- Cluster IAM role ---
            cluster_role = aws.iam.Role(
                f"{eks_cfg.name}-cluster-role",
                assume_role_policy=_EKS_CLUSTER_ASSUME_ROLE_POLICY,
                tags=self._tags(f"{eks_cfg.name}-cluster-role"),
            )
            aws.iam.RolePolicyAttachment(
                f"{eks_cfg.name}-cluster-policy",
                role=cluster_role.name,
                policy_arn="arn:aws:iam::aws:policy/AmazonEKSClusterPolicy",
            )
            result.cluster_roles[eks_cfg.name] = cluster_role

            # --- Cluster subnets ---
            subnet_ids = [self._subnet_result.subnets[ref].id for ref in eks_cfg.subnet_refs if ref in self._subnet_result.subnets]

            cluster = aws.eks.Cluster(
                eks_cfg.name,
                role_arn=cluster_role.arn,
                version=eks_cfg.kubernetes_version,
                vpc_config=aws.eks.ClusterVpcConfigArgs(
                    subnet_ids=subnet_ids,
                    endpoint_public_access=eks_cfg.endpoint_public_access,
                    endpoint_private_access=eks_cfg.endpoint_private_access,
                ),
                tags=self._tags(eks_cfg.name, eks_cfg.tags),
            )
            result.clusters[eks_cfg.name] = cluster
            result.outputs[f"{eks_cfg.name}_cluster_name"] = cluster.name
            result.outputs[f"{eks_cfg.name}_cluster_endpoint"] = cluster.endpoint
            result.outputs[f"{eks_cfg.name}_kubeconfig_ca"] = cluster.certificate_authority.data

            # --- Node IAM role (shared across all node groups for this cluster) ---
            node_role = aws.iam.Role(
                f"{eks_cfg.name}-node-role",
                assume_role_policy=_EC2_ASSUME_ROLE_POLICY,
                tags=self._tags(f"{eks_cfg.name}-node-role"),
            )
            for policy_arn in [
                "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy",
                "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy",
                "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
            ]:
                short = policy_arn.split("/")[-1]
                aws.iam.RolePolicyAttachment(
                    f"{eks_cfg.name}-node-{short}",
                    role=node_role.name,
                    policy_arn=policy_arn,
                )
            result.node_roles[eks_cfg.name] = node_role

            # --- Node Groups ---
            for ng_cfg in eks_cfg.node_groups:
                ng_subnet_ids = [
                    self._subnet_result.subnets[ref].id for ref in ng_cfg.subnet_refs if ref in self._subnet_result.subnets
                ] or subnet_ids  # fall back to cluster subnets

                ng = aws.eks.NodeGroup(
                    f"{eks_cfg.name}-{ng_cfg.name}",
                    cluster_name=cluster.name,
                    node_role_arn=node_role.arn,
                    subnet_ids=ng_subnet_ids,
                    instance_types=ng_cfg.instance_types,
                    disk_size=ng_cfg.disk_size_gb,
                    ami_type=ng_cfg.ami_type,
                    labels=ng_cfg.labels,
                    scaling_config=aws.eks.NodeGroupScalingConfigArgs(
                        min_size=ng_cfg.min_size,
                        max_size=ng_cfg.max_size,
                        desired_size=ng_cfg.desired_size,
                    ),
                    tags=self._tags(f"{eks_cfg.name}-{ng_cfg.name}"),
                )
                result.node_groups[f"{eks_cfg.name}-{ng_cfg.name}"] = ng

        return result

    def _tags(self, name: str, extra: dict[str, str] | None = None) -> dict[str, str]:
        return make_tags(self._config.project, self._config.stack, name, extra, global_tags=dict(self._config.tags))
