"""
Slack notification functionality for domain tracker.

Sends alerts when domains become available or experience issues.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from requests.exceptions import ConnectionError, Timeout

from domain_tracker.settings import Settings
from domain_tracker.whois_client import DomainInfo


def send_slack_alert(message: str, settings: Settings | None = None) -> None:
    """
    Send an alert message to Slack via webhook.

    Args:
        message: The message to send to Slack
        settings: Optional settings object (uses default if None)

    Raises:
        No exceptions - errors are logged instead of propagated
    """
    if settings is None:
        settings = Settings()  # type: ignore[call-arg]

    payload = {"text": message}
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Domain-Tracker/1.0",
    }

    try:
        response = requests.post(
            str(settings.slack_webhook_url),  # Cast HttpUrl to str
            json=payload,
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
        logging.debug(f"Successfully sent Slack alert: {message[:100]}...")

    except (Timeout, ConnectionError) as e:
        logging.error(f"Failed to send Slack alert due to network error: {e}")
    except requests.HTTPError as e:
        logging.error(f"Failed to send Slack alert due to HTTP error: {e}")
    except Exception as e:
        logging.error(f"Failed to send Slack alert due to unexpected error: {e}")


def _format_domain_section(domain_info: DomainInfo) -> list[str]:
    """
    Format a single domain's information section.

    Args:
        domain_info: Domain information

    Returns:
        List of formatted lines for this domain
    """
    lines = []

    # Determine status and format based on test expectations
    if domain_info.has_error:
        lines.append(f"🚨 *{domain_info.domain_name}*")
        if domain_info.error_message:
            lines.append(f"• Status: Error ({domain_info.error_message})")
        else:
            lines.append("• Status: Error")

    elif domain_info.is_available:
        lines.append(f"✅ *{domain_info.domain_name}*")
        lines.append("• Status: Available")
        lines.append("• 🔔 <!channel> — Action needed!")

    else:
        lines.append(f"❌ *{domain_info.domain_name}*")
        lines.append("• Status: Unavailable")

        # Add expiration metadata
        if domain_info.expiration_date:
            # Convert to New York timezone for consistent display
            ny_tz = ZoneInfo("America/New_York")
            expiry_ny = domain_info.expiration_date.astimezone(ny_tz)
            expiry_formatted = expiry_ny.strftime("%b %-d, %Y")
            lines.append(f"• Expires: {expiry_formatted}")

        # Add creation date metadata
        if domain_info.creation_date:
            ny_tz = ZoneInfo("America/New_York")
            created_ny = domain_info.creation_date.astimezone(ny_tz)
            created_formatted = created_ny.strftime("%b %-d, %Y")
            lines.append(f"• Created: {created_formatted}")

        # Add registrant information if available
        if domain_info.registrant_name:
            lines.append(f"• Registrant: {domain_info.registrant_name}")

        if domain_info.registrant_organization:
            lines.append(f"• Organization: {domain_info.registrant_organization}")

        # Add registrar details
        if domain_info.registrar_name:
            lines.append(f"• Registrar: {domain_info.registrar_name}")

    return lines


def format_enhanced_slack_message(
    domain_infos: list[DomainInfo],
    check_time: datetime,
    trigger_type: str = "scheduled",
) -> str:
    """
    Format enhanced Slack message with the test-expected design.

    Args:
        domain_infos: List of domain information objects
        check_time: When the check was performed
        trigger_type: Type of trigger ("manual" or "scheduled")

    Returns:
        Formatted Slack message string
    """
    if not domain_infos:
        # Special heartbeat message format for when no domains available
        ny_tz = ZoneInfo("America/New_York")
        check_time_ny = check_time.astimezone(ny_tz)
        tz_name = "EST" if check_time_ny.dst() == timedelta(0) else "EDT"
        timestamp = check_time_ny.strftime(f"%-I:%M %p {tz_name} • %b %-d, %Y")

        trigger_text = (
            "Manual CLI Check" if trigger_type == "manual" else "Scheduled hourly check"
        )

        lines = [
            ":robot_face: *Domain Tracker: "
            + (
                "Scheduled Hourly Check"
                if trigger_type == "scheduled"
                else "Manual Check"
            )
            + "*",
            "",
            ":bar_chart: No domains currently being monitored",
            "",
            f":clock10: Check completed at: {timestamp}",
            f":repeat: Trigger: {trigger_text}",
            ":heartbeat: This is a heartbeat notification confirming the automation is running correctly.",
        ]
        return "\n".join(lines)

    lines = []

    # Header section - test expected format
    lines.append("🔍 *Domain Check Summary*")

    # Format timestamp in New York timezone
    ny_tz = ZoneInfo("America/New_York")
    check_time_ny = check_time.astimezone(ny_tz)

    # Determine timezone abbreviation
    tz_name = "EST" if check_time_ny.dst() == timedelta(0) else "EDT"
    timestamp = check_time_ny.strftime(f"%-I:%M %p {tz_name} • %b %-d, %Y")

    lines.append(f"🗓️ {timestamp}")

    # Trigger type
    trigger_text = (
        "Manual CLI Check" if trigger_type == "manual" else "Scheduled hourly check"
    )
    lines.append(f"🔁 *Triggered by:* {trigger_text}")
    lines.append("")

    # Domain sections with separators - test expected format
    section_break = "━━━━━━━━━━━━━━━━━━━━"

    for i, domain_info in enumerate(domain_infos):
        # Add section break before each domain for multiple domains
        if len(domain_infos) > 1:
            lines.append(section_break)
        domain_lines = _format_domain_section(domain_info)
        lines.extend(domain_lines)

    # Add final section break for multiple domains
    if len(domain_infos) > 1:
        lines.append(section_break)

    lines.append("")

    # Summary section - test expected format
    available_count = sum(
        1 for info in domain_infos if info.is_available and not info.has_error
    )
    unavailable_count = sum(
        1 for info in domain_infos if not info.is_available and not info.has_error
    )
    error_count = sum(1 for info in domain_infos if info.has_error)

    lines.append("📊 *Summary:*")
    lines.append(
        f"• {available_count} available • {unavailable_count} unavailable • {error_count} errors"
    )

    return "\n".join(lines)


def format_domain_error_alert(domain_name: str, error_message: str) -> str:
    """
    Format a separate error alert for failed domain lookups.

    Args:
        domain_name: The domain that failed
        error_message: The error that occurred

    Returns:
        Formatted error alert message
    """
    return "\n".join(
        [
            f"🚨 *Domain Check Failed for: {domain_name}*",
            f"❗ Error: {error_message}",
            "🔁 Will retry at next scheduled interval",
            "🔔 <!channel> — Manual check may be needed",
        ]
    )
