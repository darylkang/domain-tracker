"""
Slack notification functionality for domain tracker.

Sends alerts when domains become available or experience issues.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
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
            settings.slack_webhook_url,
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



def _get_relative_time_text(expiry_date: datetime | None) -> str:
    """
    Get relative time text for expiry dates.
    
    Args:
        expiry_date: The expiration date
        
    Returns:
        Relative time string like "(26 days ago)" or "(in 7 days)" or empty string
    """
    if not expiry_date:
        return ""
    
    now = datetime.now(timezone.utc)
    if expiry_date.tzinfo is None:
        expiry_date = expiry_date.replace(tzinfo=timezone.utc)
    
    delta = expiry_date - now
    days = delta.days
    
    if days < 0:
        return f"*({abs(days)} days ago)*"
    elif days == 0:
        return "*today*"
    elif days == 1:
        return "*(tomorrow)*"
    else:
        return f"*(in {days} days)*"


def _format_domain_link(domain_name: str) -> str:
    """
    Format domain as a clickable Slack link.
    
    Args:
        domain_name: The domain name
        
    Returns:
        Formatted Slack link
    """
    return f"<http://{domain_name}|{domain_name}>"


def _format_registrar_details(domain_info: DomainInfo) -> list[str]:
    """
    Format registrar information with contact details.
    
    Args:
        domain_info: Domain information
        
    Returns:
        List of formatted registrar detail lines
    """
    lines = []
    
    if domain_info.registrar_name:
        lines.append(f"• *Registrar:* {domain_info.registrar_name}")
        
        # Add registrar contact details if available (indented)
        if domain_info.registrar_address:
            lines.append(f"  🏢 {domain_info.registrar_address}")
        if domain_info.registrar_phone:
            lines.append(f"  📞 {domain_info.registrar_phone}")
        if domain_info.registrar_fax:
            lines.append(f"  📠 {domain_info.registrar_fax}")
    
    return lines


def _format_domain_section(domain_info: DomainInfo) -> list[str]:
    """
    Format a single domain's information section.
    
    Args:
        domain_info: Domain information
        
    Returns:
        List of formatted lines for this domain
    """
    lines = []
    domain_link = _format_domain_link(domain_info.domain_name)
    
    # Determine status and icon
    if domain_info.has_error:
        icon = ":warning:"
        status = "*Error*"
        lines.append(f"{icon} *{domain_link}* — {status}")
        lines.append("🔔 <!channel> — *System error requires attention!*")
        lines.append(f"• *Reason:* {domain_info.error_message}")
        
    elif domain_info.is_available:
        icon = ":white_check_mark:"
        status = "*Available*"
        lines.append(f"{icon} *{domain_link}* — {status}")
        lines.append("🔔 <!channel> — *Action needed!*")
        lines.append(f"• *Status:* `available`")
        
    else:
        icon = ":x:"
        status = "*Unavailable*"
        lines.append(f"{icon} *{domain_link}* — {status}")
        
        # Format status codes
        if domain_info.problematic_statuses:
            status_codes = ", ".join(f"`{status}`" for status in domain_info.problematic_statuses)
            lines.append(f"• *Status:* {status_codes}")
        else:
            lines.append(f"• *Status:* `unavailable`")
    
    # Add registrar details
    registrar_lines = _format_registrar_details(domain_info)
    lines.extend(registrar_lines)
    
    # Add expiry date with relative time
    if domain_info.expiration_date:
        expiry_formatted = domain_info.expiration_date.strftime("%b %-d, %Y")
        relative_time = _get_relative_time_text(domain_info.expiration_date)
        if relative_time:
            lines.append(f"📅 *Expiry:* `{expiry_formatted}` {relative_time}")
        else:
            lines.append(f"📅 *Expiry:* `{expiry_formatted}`")
    
    # Add creation date
    if domain_info.creation_date:
        created_formatted = domain_info.creation_date.strftime("%b %-d, %Y")
        lines.append(f"🆕 *Created:* `{created_formatted}`")
    
    return lines


def format_enhanced_slack_message(
    domain_infos: list[DomainInfo],
    check_time: datetime,
    trigger_type: str = "scheduled",
) -> str:
    """
    Format enhanced Slack message with the new template design.

    Args:
        domain_infos: List of domain information objects
        check_time: When the check was performed
        trigger_type: Type of trigger ("manual" or "scheduled")

    Returns:
        Formatted Slack message string
    """
    if not domain_infos:
        return ":warning: No domains to check"

    lines = []
    
    # Header section
    lines.append(":mag_right: *Domain Check Results*")
    
    # Format timestamp in New York timezone
    ny_tz = ZoneInfo("America/New_York")
    check_time_ny = check_time.astimezone(ny_tz)
    
    # Determine timezone abbreviation
    tz_name = "EST" if check_time_ny.dst() == timedelta(0) else "EDT"
    timestamp = check_time_ny.strftime(f"%-I:%M %p {tz_name} • %b %-d, %Y")
    
    lines.append(f"📅 *Checked at:* `{timestamp}`")
    
    # Trigger type
    trigger_text = "Manual CLI Check" if trigger_type == "manual" else "Scheduled hourly check"
    lines.append(f"🔁 *Triggered by:* {trigger_text}")
    lines.append("")
    
    # Domain sections with separators
    separator = "━━━━━━━━━━━━━━━━━━━━━━━"
    
    for i, domain_info in enumerate(domain_infos):
        lines.append(separator)
        domain_lines = _format_domain_section(domain_info)
        lines.extend(domain_lines)
    
    lines.append(separator)
    
    # Summary section
    available_count = sum(1 for info in domain_infos if info.is_available and not info.has_error)
    unavailable_count = sum(1 for info in domain_infos if not info.is_available and not info.has_error)
    error_count = sum(1 for info in domain_infos if info.has_error)
    
    lines.append("📊 *Summary*")
    lines.append(f":white_check_mark: *Available:* {available_count}")
    lines.append(f":x: *Unavailable:* {unavailable_count}")
    lines.append(f":warning: *Errors:* {error_count}")

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
