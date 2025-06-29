"""
Slack notification client for domain availability alerts.

This module provides functionality to send Slack notifications when domains
become available for registration with robust error handling.
"""

from __future__ import annotations

import logging
import zoneinfo
from datetime import datetime

import requests
from requests.exceptions import ConnectionError, RequestException, Timeout

from domain_tracker.settings import Settings
from domain_tracker.whois_client import DomainInfo

# Configuration constants
REQUEST_TIMEOUT_SECONDS = 10
USER_AGENT = "Domain-Tracker/1.0"
MAX_MESSAGE_PREVIEW_LENGTH = 50


def send_slack_alert(message: str, settings: Settings | None = None) -> None:
    """
    Send a Slack alert message using webhook URL from settings.

    Args:
        message: The alert message to send to Slack.
        settings: Settings instance with Slack configuration. If None, loads from environment.

    Raises:
        Does not raise exceptions - logs errors instead for graceful handling.

    Example:
        >>> settings = Settings(whois_api_key="key", slack_webhook_url="url")
        >>> send_slack_alert("Domain available: example.com", settings)
    """
    try:
        # Load settings configuration
        if settings is None:
            settings = Settings()  # type: ignore[call-arg]

        # Prepare request data
        webhook_url = str(settings.slack_webhook_url)
        request_payload = {"text": message}
        request_headers = {
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        }

        # Send request to Slack webhook
        response = requests.post(
            webhook_url,
            json=request_payload,
            headers=request_headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        # Check for HTTP errors
        response.raise_for_status()

        # Verify Slack's response (should be "ok")
        response_text = response.text.strip()
        if response_text != "ok":
            logging.warning(f"Slack returned unexpected response: {response_text}")

        # Log successful send for debugging
        message_preview = message[:MAX_MESSAGE_PREVIEW_LENGTH]
        if len(message) > MAX_MESSAGE_PREVIEW_LENGTH:
            message_preview += "..."

        logging.debug(f"Successfully sent Slack alert: {message_preview}")

    except (ConnectionError, Timeout, RequestException) as network_error:
        # Log network errors gracefully
        error_type = type(network_error).__name__
        logging.error(f"Failed to send Slack alert: {error_type}: {network_error}")

    except Exception as unexpected_error:
        # Log any other unexpected errors
        logging.error(
            f"Failed to send Slack alert: Unexpected error: {unexpected_error}"
        )


def format_enhanced_slack_message(
    domain_infos: list[DomainInfo], check_time: datetime
) -> str:
    """
    Format enhanced Slack message with rich domain information.

    Creates a comprehensive message including timestamp in New York time,
    detailed domain status, registrant information (when available),
    and priority notifications for available domains or system errors.
    Only shows fields that have actual data, omitting empty/null fields.

    Args:
        domain_infos: List of domain information objects
        check_time: UTC timestamp when the check was performed

    Returns:
        Formatted Slack message string with improved visual layout
    """
    # Determine if we need priority notification
    has_available = any(info.is_available for info in domain_infos)
    has_errors = any(info.has_error for info in domain_infos)
    needs_priority = has_available or has_errors

    # Start building the message
    lines = []

    # Add priority notification if needed
    if needs_priority:
        lines.append("<!channel> 🚨 **ATTENTION REQUIRED**")

    # Convert UTC time to New York time and format nicely
    ny_timezone = zoneinfo.ZoneInfo("America/New_York")
    ny_time = check_time.astimezone(ny_timezone)

    # Format with timezone abbreviation (EDT/EST)
    time_str = ny_time.strftime("%-I:%M %p %Z")
    date_str = ny_time.strftime("%b %-d, %Y")
    timestamp_str = f"{time_str} • {date_str}"

    # Add header with New York timestamp
    lines.append(f"🔍 **Domain Check Summary** - {timestamp_str}")
    lines.append("")

    # Add domain details
    for domain_info in domain_infos:
        lines.extend(_format_domain_details_improved(domain_info))
        lines.append("")  # Blank line between domains

    # Add summary statistics if multiple domains
    if len(domain_infos) > 1:
        available_count = sum(1 for info in domain_infos if info.is_available)
        error_count = sum(1 for info in domain_infos if info.has_error)
        unavailable_count = len(domain_infos) - available_count - error_count

        lines.append(
            f"📊 **Summary:** {available_count} available • "
            f"{unavailable_count} unavailable • {error_count} errors"
        )

    return "\n".join(lines)


def _format_domain_details_improved(domain_info: DomainInfo) -> list[str]:
    """
    Format detailed information for a single domain with improved layout.

    Only includes fields that have actual data, omitting null/empty fields
    to provide a cleaner, more scannable format.

    Args:
        domain_info: Domain information object

    Returns:
        List of formatted message lines for the domain
    """
    lines = []

    # Determine status icon and text
    if domain_info.has_error:
        icon = "🚨"
        status_text = f"Error ({domain_info.error_message})"
    elif domain_info.is_available:
        icon = "✅"
        status_text = "Available"
    elif domain_info.problematic_statuses:
        icon = "⚠️"
        # Show all status codes for transparency
        status_codes = ", ".join(domain_info.problematic_statuses)
        status_text = f"Problematic ({status_codes})"
    else:
        icon = "❌"
        status_text = "Unavailable"

    # Domain name and status
    lines.append(f"{icon} **{domain_info.domain_name}**")
    lines.append(f"  • Status: {status_text}")

    # Skip additional details for error domains
    if domain_info.has_error:
        return lines

    # Only include fields that have actual data

    # Expiration date (if available)
    if domain_info.expiration_date:
        ny_timezone = zoneinfo.ZoneInfo("America/New_York")
        exp_ny = domain_info.expiration_date.astimezone(ny_timezone)
        exp_str = exp_ny.strftime("%b %-d, %Y")
        lines.append(f"  • Expires: {exp_str}")

    # Creation date (if available)
    if domain_info.creation_date:
        ny_timezone = zoneinfo.ZoneInfo("America/New_York")
        created_ny = domain_info.creation_date.astimezone(ny_timezone)
        created_str = created_ny.strftime("%b %-d, %Y")
        lines.append(f"  • Created: {created_str}")

    # Registrant information (if available)
    if domain_info.registrant_name:
        registrant = domain_info.registrant_name
        if domain_info.registrant_organization:
            registrant += f" ({domain_info.registrant_organization})"
        lines.append(f"  • Registrant: {registrant}")

    # Registrar (if available)
    if domain_info.registrar_name:
        lines.append(f"  • Registrar: {domain_info.registrar_name}")

    # Name servers (if available and not empty)
    if domain_info.name_servers and len(domain_info.name_servers) > 0:
        if len(domain_info.name_servers) <= 2:
            ns_str = ", ".join(domain_info.name_servers)
            lines.append(f"  • Name Servers: {ns_str}")
        else:
            # Show count if many name servers
            lines.append(
                f"  • Name Servers: {len(domain_info.name_servers)} configured"
            )

    return lines
