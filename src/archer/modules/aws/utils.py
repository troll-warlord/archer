"""
modules/aws/utils.py — Shared helpers for all AWS service builders.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pulumi

if TYPE_CHECKING:
    from archer.modules.aws.subnets import SubnetBuildResult
    from archer.modules.aws.vpc import VpcBuildResult


def resolve_subnet_ids(
    refs: list[str],
    raw_ids: list[str],
    subnet_result: SubnetBuildResult | None = None,
) -> tuple[list[pulumi.Input[str]], list[Any]]:
    """
    Resolve subnet IDs from either raw AWS IDs (existing infra) or archer-created subnets.

    Returns:
        (subnet_id_inputs, archer_subnet_objects_for_depends_on)

    Priority: raw_ids > subnet_refs from subnet_result.
    When raw_ids are provided, depends_on is empty (resources are external to Pulumi).
    """
    if raw_ids:
        return list(raw_ids), []
    if subnet_result is None:
        return [], []
    archer_subnets = [subnet_result.subnets[ref] for ref in refs if ref in subnet_result.subnets]
    return [s.id for s in archer_subnets], archer_subnets


def resolve_vpc_id(
    vpc_result: VpcBuildResult | None,
    raw_vpc_id: str | None,
) -> tuple[pulumi.Input[str] | None, list[Any]]:
    """
    Resolve a VPC ID from either a raw AWS ID (existing VPC) or an archer-created VPC.

    Returns:
        (vpc_id_input, archer_vpc_objects_for_depends_on)
    """
    if raw_vpc_id:
        return raw_vpc_id, []
    if vpc_result and vpc_result.vpc:
        return vpc_result.vpc.id, [vpc_result.vpc]
    return None, []


def make_tags(
    project: str,
    stack: str,
    name: str,
    extra: dict[str, str] | None = None,
    global_tags: dict[str, str] | None = None,
) -> dict[str, str]:
    """
    Return a standard AWS tag dictionary.

    Merge order (later overrides earlier):
      base defaults → global_tags (from InfrastructureConfig.tags) → resource-level extra

    Every archer-managed resource gets at minimum:
      Name, Project, Stack, ManagedBy
    """
    base: dict[str, str] = {
        "Name": name,
        "Project": project,
        "Stack": stack,
        "ManagedBy": "archer",
    }
    if global_tags:
        base.update(global_tags)
    if extra:
        base.update(extra)
    return base
