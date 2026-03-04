"""
providers/base.py — Abstract base class for all cloud provider handlers.

Every provider is responsible for:
  1. Declaring Pulumi resources inside build_resources().
  2. Returning a dict of named outputs from get_outputs().

The Pulumi Automation API inline program calls these two methods in sequence.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pulumi

    from archer.models import InfrastructureConfig


class BaseProvider(ABC):
    """
    Abstract base for cloud provider handlers.

    Subclasses MUST implement:
      - build_resources() — declare all Pulumi resources for the config.
      - get_outputs()     — return exportable stack outputs.

    Subclasses SHOULD NOT emit any logging or printing; that belongs in
    the CLI layer. Use pulumi.log.* for Pulumi-specific diagnostic messages.
    """

    def __init__(self, config: InfrastructureConfig) -> None:
        self.config = config
        self._outputs: dict[str, Any] = {}

    @abstractmethod
    def build_resources(self) -> None:
        """Declare all Pulumi resources.  Called inside the inline program."""
        ...

    @abstractmethod
    def get_outputs(self) -> dict[str, pulumi.Output[Any]]:
        """Return a mapping of output key → Pulumi Output to export."""
        ...
