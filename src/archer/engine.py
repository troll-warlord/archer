"""
engine.py — Pulumi Automation API wrapper.

PulumiEngine is the single point of contact between archer's CLI layer
and Pulumi's inline program execution.  It:

  1. Builds a LocalWorkspace-backed Stack from the InfrastructureConfig.
  2. Instantiates the correct provider class via PROVIDER_REGISTRY.
  3. Embeds the Pulumi program as a plain Python callable (no Pulumi.yaml needed).
  4. Runs up / preview / destroy / refresh and wraps the output in OperationResult.

All logging uses loguru.  Pulumi stdout is piped through a per-line callback
so it appears in the terminal at the right verbosity level.

State backend
─────────────
  type: local  → file:///<abs-path>/.archer-state   (default)
  type: cloud  → https://api.pulumi.com              (requires PULUMI_ACCESS_TOKEN)
  type: cloud  + url field → custom self-hosted backend

Credentials
────────────
  Cloud credentials are NEVER passed through archer.  Configure them via
  the standard SDK credential chain before running any archer command:

    AWS   : AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_PROFILE
    Azure : AZURE_CLIENT_ID + AZURE_CLIENT_SECRET + AZURE_TENANT_ID  (or `az login`)
    GCP   : GOOGLE_APPLICATION_CREDENTIALS  (or `gcloud auth application-default login`)
"""

from __future__ import annotations

import io
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger

try:
    import pulumi.automation as auto
except ImportError as exc:  # pragma: no cover
    raise ImportError("pulumi-automation is not installed. Run: uv pip install pulumi") from exc

# ---------------------------------------------------------------------------
# Pulumi SDK bug workaround (https://github.com/pulumi/pulumi/issues/)
# When a preview event payload contains `"detailedDiff": null` the SDK's
# from_json classmethod calls `.items()` on None and raises AttributeError.
# We patch it once at import time so the engine is unaffected.
# ---------------------------------------------------------------------------
try:
    import pulumi.automation.events as _auto_events

    for _cls_name in ("StepEventMetadata", "StepEventStateMetadata"):
        _cls = getattr(_auto_events, _cls_name, None)
        if _cls is None:
            continue
        # Access via the class (not __dict__) so we get the already-bound
        # classmethod callable: _bound(data) → works without passing cls.
        _bound = getattr(_cls, "from_json", None)
        if not callable(_bound):
            continue

        def _make_patched(bound_method):
            def _patched(data):
                if isinstance(data, dict) and data.get("detailedDiff") is None:
                    data = {**data, "detailedDiff": {}}
                return bound_method(data)

            return staticmethod(_patched)

        _cls.from_json = _make_patched(_bound)  # type: ignore[method-assign]

except Exception:  # pragma: no cover — best-effort patch; never crash the engine
    pass

from archer.models import InfrastructureConfig, OperationResult, ResourceChange
from archer.providers import PROVIDER_REGISTRY

if TYPE_CHECKING:
    pass


class PulumiEngine:
    """
    Wraps the Pulumi Automation API for a single InfrastructureConfig.

    Each public method (up, preview, destroy, refresh) returns a fully
    populated OperationResult so the caller (CLI layer) never needs to
    handle raw Pulumi exceptions.

    Usage::

        engine = PulumiEngine(config)
        result = engine.up()
        if not result.success:
            print(result.error)
    """

    def __init__(self, config: InfrastructureConfig) -> None:
        self.config = config

    # ------------------------------------------------------------------
    # Public API — one method per Pulumi command
    # ------------------------------------------------------------------

    def up(self) -> OperationResult:
        """Deploy or update the stack (pulumi up)."""
        return self._run_operation("up")

    def preview(self) -> OperationResult:
        """Preview pending changes without deploying (pulumi preview)."""
        return self._run_operation("preview")

    def destroy(self) -> OperationResult:
        """Destroy all stack resources (pulumi destroy)."""
        return self._run_operation("destroy")

    def refresh(self) -> OperationResult:
        """Reconcile stack state with the real cloud state (pulumi refresh)."""
        return self._run_operation("refresh")

    def output(self) -> OperationResult:
        """Fetch the current stack outputs without running any operation."""
        start = time.monotonic()
        try:
            stack = self._get_stack()
            raw = stack.outputs()
            elapsed = time.monotonic() - start
            return OperationResult(
                success=True,
                operation="output",
                elapsed=elapsed,
                outputs={k: v.value for k, v in raw.items()},
                stack_name=self.config.stack,
            )
        except Exception as exc:
            elapsed = time.monotonic() - start
            logger.error(f"Failed to fetch stack outputs: {exc}")
            return OperationResult(
                success=False,
                operation="output",
                elapsed=elapsed,
                error=str(exc),
                stack_name=self.config.stack,
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_backend_url(self) -> str:
        """Resolve the state-backend URL from the config."""
        backend = self.config.backend
        if backend.type == "cloud":
            return backend.url or "https://api.pulumi.com"
        # Local filesystem backend
        state_path = Path(backend.path).resolve()
        state_path.mkdir(parents=True, exist_ok=True)
        # Pulumi expects forward-slash URIs even on Windows
        posix_path = state_path.as_posix()
        return f"file://{posix_path}"

    def _build_inline_program(self):
        """
        Return a no-argument callable that Pulumi's LocalWorkspace will invoke
        as the inline program during stack operations.

        The closure captures `self.config` so no global state is needed.
        """
        provider_cls = PROVIDER_REGISTRY.get(self.config.provider)
        if not provider_cls:
            raise ValueError(f"No provider registered for '{self.config.provider}'. Available: {sorted(PROVIDER_REGISTRY)}")

        config = self.config  # capture for closure

        def _pulumi_program() -> None:
            import pulumi  # local import — runs inside Pulumi's context

            provider = provider_cls(config)
            provider.build_resources()
            for key, output in provider.get_outputs().items():
                pulumi.export(key, output)

        return _pulumi_program

    def _get_stack(self) -> auto.Stack:
        """Create or select the Pulumi stack backed by the configured backend."""
        backend_url = self._get_backend_url()
        logger.debug(f"Using backend: {backend_url}")

        program = self._build_inline_program()

        workspace_opts = auto.LocalWorkspaceOptions(
            env_vars={
                # Point Pulumi at our chosen backend.  This overrides any
                # PULUMI_BACKEND_URL already in the environment.
                "PULUMI_BACKEND_URL": backend_url,
                # Suppress the "welcome to Pulumi" first-run prompt.
                "PULUMI_SKIP_UPDATE_CHECK": "true",
                # The local backend requires a passphrase for state encryption.
                # Default to empty string so plain local usage works out of the box;
                # users can override by setting PULUMI_CONFIG_PASSPHRASE in their shell.
                "PULUMI_CONFIG_PASSPHRASE": os.environ.get("PULUMI_CONFIG_PASSPHRASE", ""),
            },
        )

        stack = auto.create_or_select_stack(
            stack_name=self.config.stack,
            project_name=self.config.project,
            program=program,
            opts=workspace_opts,
        )
        logger.debug(f"Stack '{self.config.stack}' ready (project: {self.config.project})")

        # Push provider-specific Pulumi config values
        self._configure_stack(stack)

        return stack

    def _configure_stack(self, stack: auto.Stack) -> None:
        """Set Pulumi config values (e.g. aws:region) for the resolved stack."""
        region = self.config.region
        provider = self.config.provider

        if provider == "aws":
            stack.set_config("aws:region", auto.ConfigValue(value=region))
        elif provider == "azure":
            stack.set_config("azure-native:location", auto.ConfigValue(value=region))
        elif provider == "gcp":
            stack.set_config("gcp:region", auto.ConfigValue(value=region))

        logger.debug(f"Set provider config: {provider}:region = {region}")

    # ------------------------------------------------------------------
    # Operation dispatcher
    # ------------------------------------------------------------------

    def _run_operation(self, operation: str, on_change=None) -> OperationResult:
        start = time.monotonic()
        stdout_buf = io.StringIO()
        step_events: list[Any] = []  # populated only for preview via on_event

        def _on_output(line: str) -> None:
            stdout_buf.write(line + "\n")
            logger.info(line)

        def _on_event(event: Any) -> None:
            pre = getattr(event, "resource_pre_event", None)
            if pre is None:
                return
            step_events.append(pre)
            if on_change is None:
                return
            # Fire the live callback immediately for actionable changes
            meta = getattr(pre, "metadata", None)
            if not meta:
                return
            op_name: str = getattr(meta, "op", "") or ""
            if op_name in ("", "same", "read"):
                return
            urn: str = getattr(meta, "urn", "") or ""
            parts = urn.split("::")
            name = parts[-1] if len(parts) >= 4 else urn
            res_type: str = getattr(meta, "type", "") or "(unknown)"
            on_change(ResourceChange(name=name, type=res_type, operation=op_name))

        try:
            stack = self._get_stack()
            logger.info(f"Running '{operation}' · project={self.config.project} stack={self.config.stack} provider={self.config.provider}")

            result = self._dispatch(
                stack,
                operation,
                _on_output,
                _on_event if operation == "preview" else None,
            )
            elapsed = time.monotonic() - start

            return OperationResult(
                success=True,
                operation=operation,
                elapsed=elapsed,
                outputs=self._extract_outputs(result, operation),
                summary=self._extract_changes(result, operation, step_events),
                stack_name=self.config.stack,
                raw_stdout=stdout_buf.getvalue(),
            )

        except auto.CommandError as exc:
            elapsed = time.monotonic() - start
            logger.error(f"Pulumi command failed: {exc}")
            return OperationResult(
                success=False,
                operation=operation,
                elapsed=elapsed,
                error=str(exc),
                summary=self._extract_changes(None, operation, step_events),
                stack_name=self.config.stack,
                raw_stdout=stdout_buf.getvalue(),
            )
        except Exception as exc:
            elapsed = time.monotonic() - start
            logger.error(f"Unexpected error during '{operation}': {exc}")
            return OperationResult(
                success=False,
                operation=operation,
                elapsed=elapsed,
                error=str(exc),
                summary=self._extract_changes(None, operation, step_events),
                stack_name=self.config.stack,
                raw_stdout=stdout_buf.getvalue(),
            )

    def _dispatch(
        self,
        stack: auto.Stack,
        operation: str,
        on_output,
        on_event=None,
    ) -> Any:
        """Route to the correct stack method based on operation name."""
        if operation == "up":
            return stack.up(on_output=on_output, color="never")
        if operation == "preview":
            kwargs: dict[str, Any] = {"on_output": on_output, "color": "never"}
            if on_event is not None:
                kwargs["on_event"] = on_event
            return stack.preview(**kwargs)
        if operation == "destroy":
            return stack.destroy(on_output=on_output, color="never")
        if operation == "refresh":
            return stack.refresh(on_output=on_output, color="never")
        raise ValueError(f"Unknown operation: '{operation}'")

    # ------------------------------------------------------------------
    # Result parsing helpers
    # ------------------------------------------------------------------

    def _extract_outputs(self, result: Any, operation: str) -> dict[str, Any]:
        """Pull stack outputs from the result object (only available after 'up')."""
        if operation not in {"up"}:
            return {}
        try:
            return {k: v.value for k, v in (result.outputs or {}).items()}
        except Exception:
            return {}

    def _extract_changes(
        self,
        result: Any,
        operation: str,
        step_events: list[Any] | None = None,
    ) -> list[ResourceChange]:
        """Parse the resource-change summary from the Pulumi result.

        For preview, we prefer the per-resource event stream (``step_events``).
        ``same`` resources are filtered out so only actionable changes appear.
        For other operations we fall back to the aggregate ``resource_changes``
        dict on the result summary.
        """
        changes: list[ResourceChange] = []

        # --- preview: use per-resource events for full detail ---
        if operation == "preview" and step_events:
            for evt in step_events:
                meta = getattr(evt, "metadata", None)
                if not meta:
                    continue
                op_name: str = getattr(meta, "op", "") or ""
                if op_name in ("", "same", "read"):
                    continue  # skip unchanged and read-only resources
                urn: str = getattr(meta, "urn", "") or ""
                # URN format: urn:pulumi:<stack>::<project>::<type>::<name>
                parts = urn.split("::")
                name = parts[-1] if len(parts) >= 4 else urn
                res_type: str = getattr(meta, "type", "") or "(unknown)"
                changes.append(ResourceChange(name=name, type=res_type, operation=op_name))
            if changes:
                return changes
            # If every resource is "same", report that explicitly
            if step_events:
                changes.append(ResourceChange(name="(all)", type="—", operation="no changes"))
                return changes

        # --- up / destroy / refresh: use aggregate summary dict ---
        change_dict: dict[str, int] | None = None
        if operation == "preview":
            change_dict = getattr(result, "change_summary", None)
        else:
            summary = getattr(result, "summary", None)
            if summary:
                change_dict = getattr(summary, "resource_changes", None)

        if not change_dict:
            return changes

        for op_name, count in change_dict.items():
            if count and count > 0:
                changes.append(
                    ResourceChange(
                        name="(multiple)",
                        type="—",
                        operation=f"{op_name} x{count}",
                    )
                )
        return changes
