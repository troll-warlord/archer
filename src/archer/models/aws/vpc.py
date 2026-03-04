"""
models/aws/vpc.py — VPC service models.

Covers: VPC, Subnets, NAT Gateways, VPC Endpoints, Transit Gateways.
All of these belong to the aws.ec2 / aws.networkmanager API namespace.
"""

from __future__ import annotations

import ipaddress
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from archer.models.base import VALID_SUBNET_TYPES


class VpcConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = "main-vpc"
    cidr_block: str = "10.0.0.0/16"
    enable_dns_hostnames: bool = True
    enable_dns_support: bool = True

    @field_validator("cidr_block")
    @classmethod
    def validate_cidr(cls, value: str) -> str:
        try:
            ipaddress.ip_network(value, strict=False)
        except ValueError as exc:
            raise ValueError(f"Invalid CIDR block '{value}': {exc}") from exc
        return value


class SubnetConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    cidr_block: str
    availability_zone: str
    type: Literal["public", "private"] = "private"

    @field_validator("cidr_block")
    @classmethod
    def validate_cidr(cls, value: str) -> str:
        try:
            ipaddress.ip_network(value, strict=False)
        except ValueError as exc:
            raise ValueError(f"Invalid subnet CIDR '{value}': {exc}") from exc
        return value

    @field_validator("availability_zone")
    @classmethod
    def validate_az_format(cls, value: str) -> str:
        if not value or not value[-1].isalpha():
            raise ValueError(f"Availability zone '{value}' appears malformed. Expected format: us-east-1a")
        return value

    @field_validator("type")
    @classmethod
    def validate_subnet_type(cls, value: str) -> str:
        if value not in VALID_SUBNET_TYPES:
            raise ValueError(f"subnet type must be one of {sorted(VALID_SUBNET_TYPES)}, got '{value}'")
        return value


class NatGatewayConfig(BaseModel):
    """One NAT Gateway per public subnet reference; placed in the named public subnet."""

    model_config = ConfigDict(frozen=True)

    name: str
    # Use subnet_ref for an archer-declared subnet, or subnet_id for an existing one.
    subnet_ref: str | None = None
    subnet_id: str | None = None
    # Set to True to allocate a new EIP automatically; set to False to supply an existing EIP allocation ID
    allocate_eip: bool = True
    eip_allocation_id: str | None = None
    tags: dict[str, str] = Field(default_factory=dict)


class VpcEndpointConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    service_name: str
    endpoint_type: Literal["Gateway", "Interface"] = "Gateway"
    # Use subnet_refs for archer-declared subnets, or subnet_ids for existing ones.
    subnet_refs: list[str] = Field(default_factory=list)
    subnet_ids: list[str] = Field(default_factory=list)
    # Use vpc_id when provisioning into an existing VPC (not declared in this YAML).
    vpc_id: str | None = None
    private_dns_enabled: bool = False
    tags: dict[str, str] = Field(default_factory=dict)


class TransitGatewayConfig(BaseModel):
    """AWS Transit Gateway for inter-VPC and on-premises routing."""

    model_config = ConfigDict(frozen=True)

    name: str
    amazon_side_asn: int = 64512
    auto_accept_shared_attachments: bool = False
    default_route_table_association: bool = True
    default_route_table_propagation: bool = True
    dns_support: bool = True
    vpn_ecmp_support: bool = True
    tags: dict[str, str] = Field(default_factory=dict)
