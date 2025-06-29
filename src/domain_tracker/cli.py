"""
Command-line interface for the Domain Drop Tracker.

This module provides the main CLI entry point for checking domain availability
and sending Slack notifications when domains become available.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated

import typer

from domain_tracker.domain_management import load_domains
from domain_tracker.settings import Settings
from domain_tracker.slack_notifier import (
    format_enhanced_slack_message,
    send_slack_alert,
)
from domain_tracker.whois_client import (
    check_domain_status_detailed,
    get_enhanced_domain_info,
)

# Message templates
AVAILABLE_DOMAIN_MESSAGE = "✅ Domain available: {domain}"
UNAVAILABLE_DOMAIN_MESSAGE = "❌ Domain NOT available: {domain}"
PROBLEMATIC_STATUS_MESSAGE = "⚠️ Domain appears available but still in {status}: {domain}. May not be fully released yet."

# Create the Typer app
app = typer.Typer(
    name="domain-tracker",
    help="Domain Drop Tracker - Monitor domain availability and send Slack alerts.",
)


def version_callback(value: bool) -> None:
    """Print version information and exit."""
    if value:
        from domain_tracker import __version__

        print(f"Domain Tracker version: {__version__}")
        raise typer.Exit()


def _send_slack_alert_safely(message: str, settings: Settings) -> None:
    """Send Slack alert with error handling."""
    try:
        send_slack_alert(message, settings)
    except Exception as e:
        print(f"⚠️  Error sending Slack alert: {e}")


def _load_settings() -> Settings:
    """Load settings with error handling."""
    try:
        return Settings()  # type: ignore[call-arg]
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        print("   Make sure WHOIS_API_KEY and SLACK_WEBHOOK_URL are set.")
        raise typer.Exit(code=1) from e


def _get_enhanced_domain_message(
    domain: str, is_available: bool, problematic_statuses: list[str]
) -> str:
    """Create enhanced domain status message based on detailed status information."""
    if not is_available:
        if problematic_statuses:
            # Domain appears available but has problematic statuses
            status_list = ", ".join(problematic_statuses)
            return PROBLEMATIC_STATUS_MESSAGE.format(domain=domain, status=status_list)
        else:
            # Domain is genuinely unavailable
            return UNAVAILABLE_DOMAIN_MESSAGE.format(domain=domain)
    else:
        # Domain is truly available
        return AVAILABLE_DOMAIN_MESSAGE.format(domain=domain)


def _print_domain_summary(total_domains: int, available_domains: list[str]) -> None:
    """Print a summary of domain checking results."""
    available_count = len(available_domains)

    print("\n📊 Summary:")
    print(f"  Checked {total_domains} domains")
    print(f"  Found {available_count} available domains")

    if available_count == 0:
        print("  No domains available at this time.")
    else:
        print(f"  Available domains: {', '.join(available_domains)}")


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", "-v", callback=version_callback, help="Show version"),
    ] = False,
) -> None:
    """Domain Drop Tracker - Monitor domain availability and send Slack alerts."""
    pass


@app.command("check")
def check_single_domain_command(
    domain: Annotated[str, typer.Argument(help="Domain to check (e.g., example.com)")],
    enhanced_slack: Annotated[
        bool,
        typer.Option(
            "--enhanced-slack",
            help="Use enhanced Slack message format with detailed domain information",
        ),
    ] = False,
) -> None:
    """Check availability of a single domain and send Slack alert."""
    try:
        settings = _load_settings()

        print(f"🔍 Checking {domain}...")

        if enhanced_slack:
            # Use enhanced domain info for rich Slack messages
            domain_info = get_enhanced_domain_info(domain, settings)

            # Keep CLI output lightweight
            if domain_info.has_error:
                print(f"❌ Error checking {domain}: {domain_info.error_message}")
            elif domain_info.is_available:
                print("✅ Available")
            elif domain_info.problematic_statuses:
                print(
                    f"⚠️ Problematic status: {', '.join(domain_info.problematic_statuses)}"
                )
            else:
                print("❌ Unavailable")

            # Send enhanced Slack message
            if not domain_info.has_error:
                check_time = datetime.utcnow()
                enhanced_message = format_enhanced_slack_message(
                    [domain_info], check_time
                )
                _send_slack_alert_safely(enhanced_message, settings)
            else:
                # Send simple error message for API errors
                error_message = (
                    f"🚨 Error checking {domain}: {domain_info.error_message}"
                )
                _send_slack_alert_safely(error_message, settings)
        else:
            # Use legacy simple format
            is_available, problematic_statuses = check_domain_status_detailed(
                domain, settings
            )

            # Create enhanced message based on detailed status
            message = _get_enhanced_domain_message(
                domain, is_available, problematic_statuses
            )
            print(message)
            _send_slack_alert_safely(message, settings)

    except Exception as e:
        print(f"❌ Error checking domain {domain}: {e}")
        raise typer.Exit(code=1) from e


@app.command("check-domains")
def check_domains(
    notify_all: Annotated[
        bool,
        typer.Option(
            "--notify-all",
            help="Send Slack alerts for all domains, regardless of availability",
        ),
    ] = False,
    enhanced_slack: Annotated[
        bool,
        typer.Option(
            "--enhanced-slack",
            help="Use enhanced Slack message format with detailed domain information",
        ),
    ] = False,
    debug: Annotated[
        bool,
        typer.Option("--debug", help="Enable debug-level logging"),
    ] = False,
) -> None:
    """Check domain availability and send Slack alerts for available domains."""
    # Configure logging if debug mode is enabled
    if debug:
        logging.basicConfig(level=logging.DEBUG)

    settings = _load_settings()

    try:
        # Load domains from file
        print("🔍 Checking domain availability...")
        domains = load_domains()

        if not domains:
            print("⚠️  No domains found to check.")
            return

        available_domains = []
        domain_infos = []

        # Check each domain
        for domain in domains:
            try:
                print(f"  Checking {domain}...", end=" ")

                if enhanced_slack:
                    # Use enhanced domain info for rich Slack messages
                    domain_info = get_enhanced_domain_info(domain, settings)
                    domain_infos.append(domain_info)

                    # Keep CLI output lightweight
                    if domain_info.has_error:
                        print(f"❌ Error: {domain_info.error_message}")
                    elif domain_info.is_available:
                        print("✅ Available")
                        available_domains.append(domain)
                    elif domain_info.problematic_statuses:
                        print(
                            f"⚠️ Problematic status: {', '.join(domain_info.problematic_statuses)}"
                        )
                    else:
                        print("❌ Unavailable")
                else:
                    # Use legacy simple format
                    is_available, problematic_statuses = check_domain_status_detailed(
                        domain, settings
                    )

                    # Create enhanced message for this domain
                    message = _get_enhanced_domain_message(
                        domain, is_available, problematic_statuses
                    )

                    if is_available:
                        print("✅ Available")
                        available_domains.append(domain)
                        _send_slack_alert_safely(message, settings)
                    else:
                        if problematic_statuses:
                            print(
                                f"⚠️ Problematic status: {', '.join(problematic_statuses)}"
                            )
                        else:
                            print("❌ Unavailable")

                        if notify_all:
                            _send_slack_alert_safely(message, settings)

            except Exception as e:
                print(f"❌ Error checking {domain}: {e}")

        # Send enhanced Slack message summary if using enhanced mode
        if enhanced_slack and domain_infos:
            # Only send if there are available domains, errors, or notify_all is enabled
            should_notify = (
                any(info.is_available for info in domain_infos)
                or any(info.has_error for info in domain_infos)
                or notify_all
            )

            if should_notify:
                check_time = datetime.utcnow()
                enhanced_message = format_enhanced_slack_message(
                    domain_infos, check_time
                )
                _send_slack_alert_safely(enhanced_message, settings)

        # Print summary
        _print_domain_summary(len(domains), available_domains)

    except FileNotFoundError as e:
        print(f"❌ Error loading domains: {e}")
        print("   Make sure domains.txt exists in the current directory.")
        raise typer.Exit(code=1) from e
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        raise typer.Exit(code=1) from e


if __name__ == "__main__":
    app()
