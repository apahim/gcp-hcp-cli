"""Authentication commands for GCP HCP CLI."""

import click
from rich.panel import Panel
from rich.text import Text

from ...auth.exceptions import AuthenticationError


@click.group("auth")
def auth_group() -> None:
    """Manage authentication and authorization."""
    pass


@auth_group.command("login")
@click.option(
    "--force",
    is_flag=True,
    help="Force re-authentication even if already logged in",
)
@click.pass_obj
def login(cli_context, force: bool) -> None:
    """Authenticate with Google Cloud Platform.

    This command will open a web browser to complete the OAuth 2.0 flow
    and store credentials for future use.
    """
    try:
        if not force and cli_context.auth.is_authenticated():
            if not cli_context.quiet:
                cli_context.console.print(
                    "[green]✓[/green] Already authenticated. Use --force to re-authenticate."
                )
            return

        if not cli_context.quiet:
            cli_context.console.print("🔐 Starting authentication flow...")

        # Perform authentication
        access_token, user_email = cli_context.auth.authenticate(force_reauth=force)

        if not cli_context.quiet:
            # Create success panel
            success_text = Text()
            success_text.append("✓ Authentication successful!\n\n", style="green bold")
            success_text.append(f"User: {user_email}\n", style="bright_blue")
            success_text.append(
                "Credentials have been saved for future use.", style="dim"
            )

            panel = Panel(
                success_text,
                title="[green]Authentication Complete[/green]",
                border_style="green",
            )
            cli_context.console.print(panel)

    except AuthenticationError as e:
        cli_context.console.print(f"[red]Authentication failed: {e}[/red]")
        raise click.ClickException(str(e))
    except Exception as e:
        cli_context.console.print(
            f"[red]Unexpected error during authentication: {e}[/red]"
        )
        raise click.ClickException(str(e))


@auth_group.command("logout")
@click.option(
    "--all",
    "logout_all",
    is_flag=True,
    help="Remove all stored credentials",
)
@click.pass_obj
def logout(cli_context, logout_all: bool) -> None:
    """Remove stored authentication credentials.

    This will require you to run 'gcphcp auth login' again before making API calls.
    """
    try:
        if not cli_context.auth.is_authenticated():
            if not cli_context.quiet:
                cli_context.console.print(
                    "[yellow]No active authentication found.[/yellow]"
                )
            return

        # Confirm logout
        if not cli_context.quiet:
            if not click.confirm("Are you sure you want to logout?"):
                cli_context.console.print("Logout cancelled.")
                return

        # Perform logout
        cli_context.auth.logout()

        if not cli_context.quiet:
            cli_context.console.print("[green]✓[/green] Successfully logged out.")
            if logout_all:
                cli_context.console.print(
                    "[dim]All stored credentials have been removed.[/dim]"
                )

    except Exception as e:
        cli_context.console.print(f"[red]Error during logout: {e}[/red]")
        raise click.ClickException(str(e))


@auth_group.command("status")
@click.pass_obj
def status(cli_context) -> None:
    """Show current authentication status."""
    try:
        is_authenticated = cli_context.auth.is_authenticated()

        if is_authenticated:
            # Get user info
            try:
                headers = cli_context.auth.get_auth_headers()
                user_email = headers.get("X-User-Email", "Unknown")

                status_text = Text()
                status_text.append("✓ Authenticated\n\n", style="green bold")
                status_text.append(f"User: {user_email}\n", style="bright_blue")
                status_text.append("Ready to make API calls.", style="dim")

                panel = Panel(
                    status_text,
                    title="[green]Authentication Status[/green]",
                    border_style="green",
                )
            except Exception as e:
                # Show authenticated but with warning
                status_text = Text()
                status_text.append(
                    "⚠ Authenticated (with issues)\n\n", style="yellow bold"
                )
                status_text.append(f"Warning: {e}\n", style="yellow")
                status_text.append("You may need to re-authenticate.", style="dim")

                panel = Panel(
                    status_text,
                    title="[yellow]Authentication Status[/yellow]",
                    border_style="yellow",
                )

            cli_context.console.print(panel)

        else:
            status_text = Text()
            status_text.append("✗ Not authenticated\n\n", style="red bold")
            status_text.append("Run 'gcphcp auth login' to authenticate.", style="dim")

            panel = Panel(
                status_text,
                title="[red]Authentication Status[/red]",
                border_style="red",
            )
            cli_context.console.print(panel)

    except Exception as e:
        cli_context.console.print(
            f"[red]Error checking authentication status: {e}[/red]"
        )
        raise click.ClickException(str(e))


@auth_group.command("token")
@click.option(
    "--format",
    "token_format",
    type=click.Choice(["token", "headers"], case_sensitive=False),
    default="token",
    help="Output format for token information",
)
@click.pass_obj
def token(cli_context, token_format: str) -> None:
    """Display current access token or authentication headers.

    This is useful for debugging or integration with other tools.
    """
    try:
        if not cli_context.auth.is_authenticated():
            cli_context.console.print(
                "[red]Not authenticated. Run 'gcphcp auth login' first.[/red]"
            )
            raise click.ClickException("Authentication required")

        if token_format == "token":
            access_token, _ = cli_context.auth.authenticate()
            cli_context.console.print(access_token)
        else:  # headers
            headers = cli_context.auth.get_auth_headers()
            for header, value in headers.items():
                cli_context.console.print(f"{header}: {value}")

    except AuthenticationError as e:
        cli_context.console.print(f"[red]Authentication error: {e}[/red]")
        raise click.ClickException(str(e))
    except Exception as e:
        cli_context.console.print(f"[red]Error retrieving token: {e}[/red]")
        raise click.ClickException(str(e))
