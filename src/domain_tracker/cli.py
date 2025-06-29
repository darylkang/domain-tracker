"""
Command-line interface for the Domain Drop Tracker.

This module provides the main CLI entry point for checking domain availability
and sending Slack notifications when domains become available.
"""

from __future__ import annotations

import logging
from typing import Annotated

import typer

from domain_tracker.core import (
    DomainCheckService,
    format_domain_check_progress,
    format_domain_summary,
    get_domain_status_display,
    get_legacy_domain_message,
)
from domain_tracker.settings import Settings

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


def _load_settings() -> Settings:
    """Load settings with error handling."""
    try:
        return Settings()  # type: ignore[call-arg]
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        print("   Make sure WHOIS_API_KEY and SLACK_WEBHOOK_URL are set.")
        raise typer.Exit(code=1) from e


def _send_slack_alert_safely(service: DomainCheckService, message: str) -> None:
    """Send simple Slack alert with error handling (legacy format)."""
    try:
        from domain_tracker.slack_notifier import send_slack_alert

        send_slack_alert(message, service.settings)
    except Exception as e:
        print(f"⚠️  Error sending Slack alert: {e}")


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
    domains: Annotated[
        list[str],
        typer.Argument(help="Domains to check (e.g., example.com anotherdomain.org)"),
    ],
    legacy_slack: Annotated[
        bool,
        typer.Option(
            "--legacy-slack",
            help="Use legacy simple Slack message format instead of enhanced format",
        ),
    ] = False,
    debug: Annotated[
        bool,
        typer.Option("--debug", help="Enable debug output including raw API responses"),
    ] = False,
) -> None:
    """Check availability of one or more domains and send Slack alert."""
    # Configure logging if debug mode is enabled
    if debug:
        logging.basicConfig(level=logging.DEBUG)

    settings = _load_settings()
    service = DomainCheckService(settings)

    # Handle single domain case for backwards compatibility
    if len(domains) == 1:
        domain = domains[0]
        print(f"🔍 Checking {domain}...")

        try:
            if not legacy_slack:
                # Use enhanced domain info for rich Slack messages
                domain_info = service.check_single_domain(
                    domain, use_enhanced_format=True, debug=debug
                )

                # Display CLI-friendly status
                status_display = get_domain_status_display(domain_info)
                print(status_display)

                # Always send enhanced Slack notification
                service.send_slack_notification(
                    [domain_info], trigger_type="manual", notify_all=True
                )
            else:
                # Use legacy simple format
                domain_info = service.check_single_domain(
                    domain, use_enhanced_format=False, debug=debug
                )
                message = get_legacy_domain_message(
                    domain, domain_info.is_available, domain_info.problematic_statuses
                )
                print(message)
                _send_slack_alert_safely(service, message)

        except Exception as e:
            print(f"❌ Error checking domain {domain}: {e}")
            raise typer.Exit(code=1) from e

    else:
        # Handle multiple domains case
        print(f"🔍 Checking {len(domains)} domains...")

        try:
            if not legacy_slack:
                # Use enhanced format with multiple domains
                result = service.check_multiple_domains(
                    domains=domains, use_enhanced_format=True, debug=debug
                )

                if result.total_domains == 0:
                    print("⚠️  No domains found to check.")
                    return

                # Display progress for each domain with consistent formatting
                print("")  # Add spacing before results
                for domain_info in result.domain_infos:
                    status_display = get_domain_status_display(domain_info)
                    formatted_line = format_domain_check_progress(
                        domain_info.domain_name, status_display
                    )
                    print(formatted_line)

                # Always send enhanced Slack notification for batch check
                service.send_slack_notification(
                    result.domain_infos, trigger_type="manual", notify_all=True
                )

                # Print summary
                print(
                    f"\n{format_domain_summary(result.total_domains, result.available_domains)}"
                )
            else:
                # Use legacy format for multiple domains
                for domain in domains:
                    domain_info = service.check_single_domain(
                        domain, use_enhanced_format=False, debug=debug
                    )
                    message = get_legacy_domain_message(
                        domain,
                        domain_info.is_available,
                        domain_info.problematic_statuses,
                    )
                    status_display = get_domain_status_display(domain_info)
                    formatted_line = format_domain_check_progress(
                        domain, status_display
                    )
                    print(formatted_line)
                    # Send individual alerts for legacy mode
                    _send_slack_alert_safely(service, message)

        except Exception as e:
            print(f"❌ Error checking domains: {e}")
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
    legacy_slack: Annotated[
        bool,
        typer.Option(
            "--legacy-slack",
            help="Use legacy simple Slack message format instead of enhanced format",
        ),
    ] = False,
    debug: Annotated[
        bool,
        typer.Option(
            "--debug", help="Enable debug-level logging and raw API response output"
        ),
    ] = False,
    scheduled: Annotated[
        bool,
        typer.Option(
            "--scheduled",
            help="Indicate this is a scheduled run (affects trigger type in notifications)",
        ),
    ] = False,
    manual: Annotated[
        bool,
        typer.Option(
            "--manual",
            help="Indicate this is a manual run (affects trigger type in notifications)",
        ),
    ] = False,
    heartbeat: Annotated[
        bool,
        typer.Option(
            "--heartbeat",
            help="Send heartbeat notification even when no domains are available",
        ),
    ] = False,
) -> None:
    """Check domain availability and send Slack alerts for available domains."""
    # Configure logging if debug mode is enabled
    if debug:
        logging.basicConfig(level=logging.DEBUG)
        print("🔧 Debug mode enabled - will show raw API responses")

    # Add logging for scheduled runs (GitHub Actions debugging)
    if scheduled:
        print("🤖 Scheduled run detected - trigger_type: scheduled")
        print("🔧 Environment check:")
        import os

        api_key_status = "SET" if os.getenv("WHOIS_API_KEY") else "MISSING"
        webhook_status = "SET" if os.getenv("SLACK_WEBHOOK_URL") else "MISSING"
        print(f"   WHOIS_API_KEY: {api_key_status}")
        print(f"   SLACK_WEBHOOK_URL: {webhook_status}")

    # Determine trigger type
    if scheduled and manual:
        print("❌ Error: Cannot specify both --scheduled and --manual flags")
        raise typer.Exit(code=1)

    trigger_type = "scheduled" if scheduled else "manual"

    # Enable notify_all for heartbeat or when explicitly requested
    should_notify_all = notify_all or heartbeat

    if heartbeat:
        print(
            "💓 Heartbeat mode enabled - will send notification regardless of results"
        )

    settings = _load_settings()
    service = DomainCheckService(settings)

    try:
        # Load and check domains
        print("🔍 Checking domain availability...")

        if not legacy_slack:
            # Use enhanced format with service layer
            result = service.check_multiple_domains(
                use_enhanced_format=True, debug=debug
            )

            if result.total_domains == 0:
                print("⚠️  No domains found to check.")

                # Send heartbeat notification if requested, even with no domains
                if heartbeat:
                    print("💓 Sending heartbeat notification for empty domain list...")
                    notification_sent = service.send_slack_notification(
                        [], trigger_type=trigger_type, notify_all=True
                    )
                    if notification_sent:
                        trigger_desc = "scheduled" if scheduled else "manual"
                        print(
                            f"💓 Heartbeat notification sent ({trigger_desc} trigger)"
                        )
                    else:
                        print("⚠️  Heartbeat requested but notification failed to send")

                return

            # Display progress for each domain with consistent formatting
            print("")  # Add spacing before results
            for domain_info in result.domain_infos:
                status_display = get_domain_status_display(domain_info)
                formatted_line = format_domain_check_progress(
                    domain_info.domain_name, status_display
                )
                print(formatted_line)

            # Send enhanced Slack notification
            notification_sent = service.send_slack_notification(
                result.domain_infos,
                trigger_type=trigger_type,
                notify_all=should_notify_all,
            )

            # Print notification status
            if notification_sent:
                trigger_desc = "scheduled" if scheduled else "manual"
                if (
                    heartbeat
                    and not result.available_domains
                    and not any(info.has_error for info in result.domain_infos)
                ):
                    print(f"💓 Heartbeat notification sent ({trigger_desc} trigger)")
                else:
                    print(f"📢 Slack notification sent ({trigger_desc} trigger)")
            elif heartbeat:
                print("⚠️  Heartbeat requested but notification failed to send")

            # Print summary
            print(
                f"\n{format_domain_summary(result.total_domains, result.available_domains)}"
            )

        else:
            # Use legacy format
            result = service.check_multiple_domains(
                use_enhanced_format=False, debug=debug
            )

            if result.total_domains == 0:
                print("⚠️  No domains found to check.")
                return

            # Process each domain with legacy logic
            for domain_info in result.domain_infos:
                message = get_legacy_domain_message(
                    domain_info.domain_name,
                    domain_info.is_available,
                    domain_info.problematic_statuses,
                )

                status_display = get_domain_status_display(domain_info)
                formatted_line = format_domain_check_progress(
                    domain_info.domain_name, status_display
                )
                print(formatted_line)

                # Send individual alerts for legacy mode
                if domain_info.is_available:
                    _send_slack_alert_safely(service, message)
                elif should_notify_all:
                    _send_slack_alert_safely(service, message)

            # Print summary
            print(
                f"\n{format_domain_summary(result.total_domains, result.available_domains)}"
            )

    except FileNotFoundError as e:
        print(f"❌ Error loading domains: {e}")
        print("   Make sure domains.txt exists in the current directory.")
        raise typer.Exit(code=1) from e
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        raise typer.Exit(code=1) from e


if __name__ == "__main__":
    app()
