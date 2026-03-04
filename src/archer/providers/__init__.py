"""
providers/__init__.py — Central provider registry.

PROVIDER_REGISTRY maps the string key used in infrastructure.yaml (e.g. "aws")
to the concrete BaseProvider subclass that handles resource creation for that cloud.

To add a new provider:
  1. Create a new module under providers/ (e.g. providers/digitalocean.py).
  2. Implement a class that inherits BaseProvider.
  3. Add a new entry to PROVIDER_REGISTRY below.
  4. Add the corresponding valid region frozenset to models.py.

No if/elif chains elsewhere. The engine looks up the class from this dict.

AWS is a package (providers/aws/) — each service lives in its own module:
  providers/aws/vpc.py, subnets.py, security_groups.py, ec2.py, rds.py
  providers/aws/__init__.py  ← AWSProvider orchestrates them all
"""

# AWS is now a package — imports AWSProvider from providers/aws/__init__.py
from archer.providers.aws import AWSProvider
from archer.providers.azure import AzureProvider
from archer.providers.base import BaseProvider
from archer.providers.gcp import GCPProvider

PROVIDER_REGISTRY: dict[str, type[BaseProvider]] = {
    "aws": AWSProvider,
    "azure": AzureProvider,
    "gcp": GCPProvider,
}

__all__ = ["PROVIDER_REGISTRY", "AWSProvider", "AzureProvider", "BaseProvider", "GCPProvider"]
