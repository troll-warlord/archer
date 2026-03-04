"""
cli.py — Click-based CLI for archer.

All presentation logic lives here (rich tables, spinners, colour).  Nothing
in engine.py, models.py, or providers/* touches the terminal directly.

Commands
────────
  archer up       --config infrastructure.yaml   Deploy / update stack
  archer preview  --config infrastructure.yaml   Dry-run, show changes
  archer destroy  --config infrastructure.yaml   Tear down all resources
  archer refresh  --config infrastructure.yaml   Reconcile state with cloud

Global options
──────────────
  --verbose / -v   Enable DEBUG-level loguru output (default: INFO)
  --version        Print archer version and exit
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any

import click
import yaml
from loguru import logger
from pydantic import ValidationError
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.spinner import Spinner
from rich.style import Style
from rich.table import Table
from rich.text import Text

from archer import __version__
from archer.engine import PulumiEngine
from archer.models import (
    AwsResources,
    AzureResources,
    GcpResources,
    InfrastructureConfig,
    OperationResult,
)

_console = Console(highlight=False)
_err_console = Console(stderr=True, highlight=False)

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------


def _configure_logging(verbose: bool) -> None:
    """Configure loguru to write to stderr at the appropriate level."""
    logger.remove()  # Remove any default handler
    level = "DEBUG" if verbose else "INFO"
    logger.add(
        sys.stderr,
        level=level,
        colorize=True,
        format=("<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> — {message}"),
    )


# ---------------------------------------------------------------------------
# Preflight checks
# ---------------------------------------------------------------------------


def _check_pulumi_binary() -> None:
    """
    Verify the Pulumi CLI binary is on PATH.

    archer uses the Pulumi Automation API which delegates to the Pulumi CLI
    binary at runtime.  If the binary is not found, we fail fast with clear
    installation instructions rather than with a cryptic internal error.
    """
    if shutil.which("pulumi") is not None:
        logger.debug(f"Pulumi CLI found at: {shutil.which('pulumi')}")
        return

    _err_console.print(
        Panel(
            "[bold red]Pulumi CLI not found on PATH.[/bold red]\n\n"
            "archer requires the Pulumi CLI to be installed. "
            "It uses the [bold]Pulumi Automation API[/bold] which delegates to the "
            "binary at runtime.\n\n"
            "[bold]Install Pulumi:[/bold]\n"
            "  macOS / Linux : [cyan]curl -fsSL https://get.pulumi.com | sh[/cyan]\n"
            "  Windows       : [cyan]winget install pulumi[/cyan]\n"
            "  Homebrew      : [cyan]brew install pulumi/tap/pulumi[/cyan]\n\n"
            "Full instructions: https://www.pulumi.com/docs/install/",
            title="[red]Missing dependency[/red]",
            border_style="red",
        )
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


def _load_config(config_path: str) -> InfrastructureConfig:
    """
    Load, parse, and validate an infrastructure YAML file.

    All Pydantic ValidationErrors are caught here and printed in a human-
    friendly table before exiting.  This keeps the CLI layer clean and means
    the engine never sees an invalid config object.
    """
    path = Path(config_path)
    if not path.exists():
        _err_console.print(f"[red]Config file not found:[/red] [bold]{config_path}[/bold]")
        sys.exit(1)

    with path.open() as fh:
        try:
            raw: dict[str, Any] = yaml.safe_load(fh) or {}
        except yaml.YAMLError as exc:
            _err_console.print(f"[red]Failed to parse YAML:[/red] {exc}")
            sys.exit(1)

    # Determine the resources type based on provider (before full validation)
    provider = raw.get("provider", "")
    resources_raw = raw.get("resources", {})
    if provider == "aws":
        raw["resources"] = AwsResources.model_validate(resources_raw)
    elif provider == "azure":
        raw["resources"] = AzureResources.model_validate(resources_raw)
    elif provider == "gcp":
        raw["resources"] = GcpResources.model_validate(resources_raw)

    try:
        return InfrastructureConfig.model_validate(raw)
    except ValidationError as exc:
        _err_console.print("\n[bold red]Configuration validation failed:[/bold red]\n")
        table = Table(box=box.ROUNDED, show_header=True, border_style="red")
        table.add_column("Field", style="yellow", no_wrap=True)
        table.add_column("Error", style="red")
        for error in exc.errors():
            field = " → ".join(str(loc) for loc in error["loc"]) or "(root)"
            table.add_row(field, error["msg"])
        _err_console.print(table)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Result rendering (presentation layer only)
# ---------------------------------------------------------------------------


def _render_result(result: OperationResult) -> None:
    """Print a structured, richly formatted OperationResult to the console."""
    _console.print()

    status_text = Text("✓ SUCCESS", style=Style(color="green", bold=True)) if result.success else Text("✗ FAILED", style=Style(color="red", bold=True))

    # Header panel
    header = Table.grid(padding=(0, 2))
    header.add_row("[bold]Operation[/bold]", f"[cyan]{result.operation}[/cyan]")
    header.add_row("[bold]Status[/bold]", status_text)
    header.add_row("[bold]Stack[/bold]", result.stack_name or "—")
    header.add_row("[bold]Elapsed[/bold]", f"{result.elapsed:.2f}s")

    panel_style = "green" if result.success else "red"
    _console.print(Panel(header, title="[bold]archer[/bold]", border_style=panel_style))

    # Resource changes table
    if result.summary:
        _op_colours = {
            "create": "green",
            "update": "yellow",
            "delete": "red",
            "replace": "magenta",
            "no changes": "dim",
        }
        changes_table = Table(
            title="Resource Changes",
            box=box.SIMPLE_HEAD,
            show_header=True,
            border_style="dim",
            show_lines=False,
        )
        changes_table.add_column("Resource Name", style="bold", no_wrap=True)
        changes_table.add_column("Type", style="cyan")
        changes_table.add_column("Operation", no_wrap=True)
        for change in result.summary:
            colour = _op_colours.get(change.operation.split()[0], "white")
            changes_table.add_row(
                change.name,
                change.type,
                Text(change.operation, style=Style(color=colour, bold=True)),
            )
        _console.print(changes_table)

    # Outputs table
    if result.outputs:
        outputs_table = Table(
            title="Stack Outputs",
            box=box.SIMPLE_HEAD,
            show_header=True,
            border_style="dim",
        )
        outputs_table.add_column("Key", style="bold cyan", no_wrap=True)
        outputs_table.add_column("Value", style="white")
        for key, val in sorted(result.outputs.items()):
            outputs_table.add_row(key, str(val))
        _console.print(outputs_table)

    # Error details
    if result.error:
        _err_console.print(
            Panel(
                result.error,
                title="[red]Error Detail[/red]",
                border_style="red",
                expand=False,
            )
        )

    _console.print()


# ---------------------------------------------------------------------------
# Shared option factories
# ---------------------------------------------------------------------------


def _config_option():
    """Reusable --config / -c option applied to every sub-command."""
    return click.option(
        "--config",
        "-c",
        default="infrastructure.yaml",
        show_default=True,
        metavar="PATH",
        help="Path to the infrastructure YAML configuration file.",
    )


def _stack_option():
    """Reusable --stack / -s option — overrides the stack name from the YAML."""
    return click.option(
        "--stack",
        "-s",
        default=None,
        metavar="NAME",
        help="Override the stack name declared in the config file.",
    )


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group()
@click.version_option(version=__version__, prog_name="archer")
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Enable DEBUG-level log output.",
)
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """
    archer — Infrastructure-as-Code wrapper around Pulumi.

    Deploy AWS, Azure, or GCP infrastructure from a single YAML file.
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    _configure_logging(verbose)
    _check_pulumi_binary()


# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------


@cli.command()
@_config_option()
@_stack_option()
@click.pass_context
def up(ctx: click.Context, config: str, stack: str | None) -> None:
    """Deploy or update infrastructure (pulumi up)."""
    cfg = _load_config(config)
    if stack:
        cfg = cfg.model_copy(update={"stack": stack})
    _console.print(f"[bold cyan]archer up[/bold cyan] · project=[green]{cfg.project}[/green] stack=[green]{cfg.stack}[/green] provider=[green]{cfg.provider}[/green]")
    with _console.status(Spinner("dots", text="Deploying infrastructure, this may take several minutes…")):
        result = PulumiEngine(cfg).up()
    _render_result(result)
    sys.exit(0 if result.success else 1)


@cli.command()
@_config_option()
@_stack_option()
@click.pass_context
def preview(ctx: click.Context, config: str, stack: str | None) -> None:
    """Preview infrastructure changes without deploying (pulumi preview)."""
    cfg = _load_config(config)
    if stack:
        cfg = cfg.model_copy(update={"stack": stack})
    _console.print(f"[bold cyan]archer preview[/bold cyan] · project=[green]{cfg.project}[/green] stack=[green]{cfg.stack}[/green]")
    result = PulumiEngine(cfg).preview()
    _render_result(result)
    sys.exit(0 if result.success else 1)


@cli.command()
@_config_option()
@_stack_option()
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    default=False,
    help="Skip the destroy confirmation prompt.",
)
@click.pass_context
def destroy(ctx: click.Context, config: str, stack: str | None, yes: bool) -> None:
    """Destroy all infrastructure resources (pulumi destroy)."""
    cfg = _load_config(config)
    if stack:
        cfg = cfg.model_copy(update={"stack": stack})

    if not yes:
        _console.print(
            Panel(
                f"[bold yellow]This will permanently destroy ALL resources in stack "
                f"'[cyan]{cfg.stack}[/cyan]' (project: [cyan]{cfg.project}[/cyan]).[/bold yellow]\n\n"
                "This action [bold red]cannot be undone[/bold red].",
                border_style="yellow",
            )
        )
        click.confirm("Are you sure you want to destroy these resources?", abort=True)

    _console.print(f"[bold red]archer destroy[/bold red] · project=[green]{cfg.project}[/green] stack=[green]{cfg.stack}[/green]")
    with _console.status(Spinner("dots", text="Destroying infrastructure…")):
        result = PulumiEngine(cfg).destroy()
    _render_result(result)
    sys.exit(0 if result.success else 1)


@cli.command()
@_config_option()
@_stack_option()
@click.pass_context
def refresh(ctx: click.Context, config: str, stack: str | None) -> None:
    """Reconcile local stack state with the real cloud state (pulumi refresh)."""
    cfg = _load_config(config)
    if stack:
        cfg = cfg.model_copy(update={"stack": stack})
    _console.print(f"[bold cyan]archer refresh[/bold cyan] · project=[green]{cfg.project}[/green] stack=[green]{cfg.stack}[/green]")
    with _console.status(Spinner("dots", text="Refreshing state…")):
        result = PulumiEngine(cfg).refresh()
    _render_result(result)
    sys.exit(0 if result.success else 1)


# ---------------------------------------------------------------------------
# Entry point guard (also invoked via [project.scripts] entry point)
# ---------------------------------------------------------------------------


@cli.command()
@_config_option()
@_stack_option()
@click.pass_context
def validate(ctx: click.Context, config: str, stack: str | None) -> None:
    """Validate the configuration file without connecting to any cloud API."""
    cfg = _load_config(config)
    if stack:
        cfg = cfg.model_copy(update={"stack": stack})
    info = [
        f"  project  : [cyan]{cfg.project}[/cyan]",
        f"  stack    : [cyan]{cfg.stack}[/cyan]",
        f"  provider : [cyan]{cfg.provider}[/cyan]",
        f"  region   : [cyan]{cfg.region}[/cyan]",
    ]
    _console.print(
        Panel(
            "\n".join(info),
            title="[bold green]✓ Configuration is valid[/bold green]",
            border_style="green",
            expand=False,
        )
    )


@cli.command("output")
@_config_option()
@_stack_option()
@click.pass_context
def output_cmd(ctx: click.Context, config: str, stack: str | None) -> None:
    """Print the current stack outputs without running any operation."""
    cfg = _load_config(config)
    if stack:
        cfg = cfg.model_copy(update={"stack": stack})
    _console.print(f"[bold cyan]archer output[/bold cyan] · project=[green]{cfg.project}[/green] stack=[green]{cfg.stack}[/green]")
    result = PulumiEngine(cfg).output()
    _render_result(result)
    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    cli()
