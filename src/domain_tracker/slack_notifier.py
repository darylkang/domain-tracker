"""
Slack notification functionality for domain tracker.

Sends alerts when domains become available or experience issues.
"""

from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from requests.exceptions import ConnectionError, Timeout

from domain_tracker.settings import Settings
from domain_tracker.whois_client import DomainInfo


def send_slack_alert(message: str, settings: Settings | None = None) -> None:
    """
    Send an alert message to Slack via webhook.

    Args:
        message: The message text to send to Slack
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
            str(settings.slack_webhook_url),
            json=payload,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        logging.debug(f"Successfully sent Slack alert: {message[:100]}...")

    except (Timeout, ConnectionError) as e:
        logging.error(f"Failed to send Slack alert due to network error: {e}")
    except requests.HTTPError as e:
        logging.error(f"Failed to send Slack alert due to HTTP error: {e}")
    except Exception as e:
        logging.error(f"Failed to send Slack alert due to unexpected error: {e}")


def _format_ny_datetime(dt: datetime) -> str:
    """
    Format a datetime in New York timezone.

    Args:
        dt: The datetime to format

    Returns:
        Formatted string like "12:56 AM EDT • Jun 29, 2024"
    """
    # Convert to New York timezone
    ny_tz = ZoneInfo("America/New_York")
    if dt.tzinfo is None:
        # Assume UTC if no timezone
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))

    ny_time = dt.astimezone(ny_tz)

    # Format time (12-hour with AM/PM)
    time_str = ny_time.strftime("%-I:%M %p")

    # Format timezone (EDT/EST)
    tz_str = ny_time.strftime("%Z")

    # Format date (abbreviated month)
    date_str = ny_time.strftime("%b %-d, %Y")

    return f"{time_str} {tz_str} • {date_str}"


def _format_ny_date(dt: datetime) -> str:
    """
    Format a date in New York timezone.

    Args:
        dt: The datetime to format

    Returns:
        Formatted string like "Dec 15, 2025"
    """
    # Convert to New York timezone
    ny_tz = ZoneInfo("America/New_York")
    if dt.tzinfo is None:
        # Assume UTC if no timezone
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))

    ny_time = dt.astimezone(ny_tz)
    return ny_time.strftime("%b %-d, %Y")


def _get_domain_icon(domain_info: DomainInfo) -> str:
    """
    Get the appropriate icon for a domain based on its status.

    Args:
        domain_info: Domain information

    Returns:
        Emoji string for the domain status
    """
    if domain_info.has_error:
        return "🚨"
    elif domain_info.is_available:
        return "✅"
    elif domain_info.problematic_statuses:
        return "⚠️"
    else:
        return "❌"


def _format_domain_status(domain_info: DomainInfo) -> str:
    """
    Format the status line for a domain.

    Args:
        domain_info: Domain information

    Returns:
        Formatted status string
    """
    if domain_info.has_error:
        error_msg = getattr(domain_info, "error_message", "Unknown error")
        return f"Error ({error_msg})"
    elif domain_info.is_available:
        return "Available"
    elif domain_info.problematic_statuses:
        statuses = ", ".join(domain_info.problematic_statuses)
        return f"Problematic ({statuses})"
    else:
        return "Unavailable"


def format_enhanced_slack_message(
    domain_infos: list[DomainInfo], check_time: datetime
) -> str:
    """
    Format domain check results into a rich, redesigned Slack message.

    Args:
        domain_infos: List of domain information objects
        check_time: When the check was performed

    Returns:
        Formatted Slack message with rich formatting and section breaks
    """
    # Header section
    header_lines = [
        "🔍 **Domain Check Summary**",
        f"🗓️ {_format_ny_datetime(check_time)}",
        "👤 Triggered by: Scheduled hourly check",
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    # Domain sections
    domain_lines = []
    for domain_info in domain_infos:
        icon = _get_domain_icon(domain_info)
        status = _format_domain_status(domain_info)

        # Domain header
        domain_lines.append(f"{icon} **{domain_info.domain_name}**")
        domain_lines.append(f"• Status: {status}")

        # Add metadata only if present
        if domain_info.registrar_name:
            domain_lines.append(f"• Registrar: {domain_info.registrar_name}")

        if domain_info.expiration_date:
            exp_date = _format_ny_date(domain_info.expiration_date)
            domain_lines.append(f"• Expires: {exp_date}")

        if domain_info.creation_date:
            created_date = _format_ny_date(domain_info.creation_date)
            domain_lines.append(f"• Created: {created_date}")

        if domain_info.registrant_name:
            registrant = domain_info.registrant_name
            if domain_info.registrant_organization:
                registrant += f" ({domain_info.registrant_organization})"
            domain_lines.append(f"• Registrant: {registrant}")

        if domain_info.name_servers:
            ns_list = ", ".join(domain_info.name_servers)
            domain_lines.append(f"• Name Servers: {ns_list}")

        # Add channel notification for available domains
        if domain_info.is_available:
            domain_lines.append("• 🔔 <@channel> — Action needed!")

        # Section break after each domain
        domain_lines.extend(["", "━━━━━━━━━━━━━━━━━━━━", ""])

    # Summary section
    available_count = sum(1 for d in domain_infos if d.is_available)
    unavailable_count = sum(
        1 for d in domain_infos if not d.is_available and not d.has_error
    )
    error_count = sum(1 for d in domain_infos if d.has_error)

    summary_lines = [
        "📊 **Summary:**",
        f"• {available_count} available • {unavailable_count} unavailable • {error_count} errors",
    ]

    # Combine all sections
    all_lines = header_lines + domain_lines + summary_lines
    return "\n".join(all_lines)


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
            f"🚨 **Domain Check Failed for: {domain_name}**",
            f"❗ Error: {error_message}",
            "🔁 Will retry at next scheduled interval",
            "🔔 <@channel> — Manual check may be needed",
        ]
    )
