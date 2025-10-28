"""Configuration management commands for GCP HCP CLI."""

import click
from typing import Union, TYPE_CHECKING
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from ..main import CLIContext


@click.group("config")
def config_group() -> None:
    """Manage CLI configuration."""
    pass


@config_group.command("list")
@click.pass_obj
def list_config(cli_context: "CLIContext") -> None:
    """Show current configuration values."""
    try:
        config_data = cli_context.config.get_all()

        if cli_context.output_format == "table":
            table = Table(
                title="Configuration", show_header=True, header_style="bold blue"
            )
            table.add_column("Setting", style="cyan")
            table.add_column("Value", style="white")
            table.add_column("Source", style="dim")

            for key, value in config_data.items():
                # Don't show sensitive values
                if "secret" in key.lower() or "token" in key.lower():
                    display_value = "[hidden]"
                else:
                    display_value = str(value) if value is not None else "[not set]"

                table.add_row(key, display_value, "config file")

            cli_context.console.print(table)
        else:
            cli_context.formatter.print_data(config_data)

    except Exception as e:
        cli_context.console.print(f"[red]Error reading configuration: {e}[/red]")
        raise click.ClickException(str(e))


@config_group.command("get")
@click.argument("key")
@click.pass_obj
def get_config(cli_context: "CLIContext", key: str) -> None:
    """Get a specific configuration value.

    KEY: Configuration key to retrieve.
    """
    try:
        value = cli_context.config.get(key)

        if value is None:
            if not cli_context.quiet:
                cli_context.console.print(
                    f"[yellow]Configuration key '{key}' is not set.[/yellow]"
                )
            return

        if cli_context.output_format == "value":
            cli_context.console.print(str(value))
        else:
            cli_context.console.print(f"{key}: {value}")

    except Exception as e:
        cli_context.console.print(f"[red]Error reading configuration: {e}[/red]")
        raise click.ClickException(str(e))


@config_group.command("set")
@click.argument("key")
@click.argument("value")
@click.pass_obj
def set_config(cli_context: "CLIContext", key: str, value: str) -> None:
    """Set a configuration value.

    KEY: Configuration key to set.
    VALUE: Value to set for the key.
    """
    try:
        # Convert string values to appropriate types
        typed_value: Union[bool, int, str]
        if value.lower() in ("true", "false"):
            typed_value = value.lower() == "true"
        elif value.isdigit():
            typed_value = int(value)
        else:
            typed_value = value

        cli_context.config.set(key, typed_value)
        cli_context.config.save()

        if not cli_context.quiet:
            cli_context.console.print(f"[green]✓[/green] Set {key} = {value}")

    except Exception as e:
        cli_context.console.print(f"[red]Error setting configuration: {e}[/red]")
        raise click.ClickException(str(e))


@config_group.command("unset")
@click.argument("key")
@click.pass_obj
def unset_config(cli_context: "CLIContext", key: str) -> None:
    """Remove a configuration value.

    KEY: Configuration key to remove.
    """
    try:
        if cli_context.config.get(key) is None:
            if not cli_context.quiet:
                cli_context.console.print(
                    f"[yellow]Configuration key '{key}' is not set.[/yellow]"
                )
            return

        cli_context.config.unset(key)
        cli_context.config.save()

        if not cli_context.quiet:
            cli_context.console.print(f"[green]✓[/green] Unset {key}")

    except Exception as e:
        cli_context.console.print(f"[red]Error removing configuration: {e}[/red]")
        raise click.ClickException(str(e))


@config_group.command("init")
@click.option(
    "--api-endpoint",
    prompt="API endpoint URL",
    help="API endpoint URL",
)
@click.option(
    "--project",
    prompt="Default project ID",
    help="Default project ID",
)
@click.pass_obj
def init_config(cli_context: "CLIContext", api_endpoint: str, project: str) -> None:
    """Initialize configuration with interactive prompts."""
    try:
        # Set basic configuration
        cli_context.config.set("api_endpoint", api_endpoint)
        cli_context.config.set("default_project", project)
        cli_context.config.save()

        if not cli_context.quiet:
            success_text = f"""✓ Configuration initialized successfully!

API Endpoint: {api_endpoint}
Default Project: {project}

Configuration saved to: {cli_context.config.config_path}

Next steps:
1. Run 'gcphcp auth login' to authenticate
2. Run 'gcphcp clusters list' to test the connection
"""

            panel = Panel(
                success_text,
                title="[green]Configuration Complete[/green]",
                border_style="green",
            )
            cli_context.console.print(panel)

    except Exception as e:
        cli_context.console.print(f"[red]Error initializing configuration: {e}[/red]")
        raise click.ClickException(str(e))


@config_group.command("path")
@click.pass_obj
def config_path(cli_context: "CLIContext") -> None:
    """Show the path to the configuration file."""
    cli_context.console.print(str(cli_context.config.config_path))
