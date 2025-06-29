"""
Core business logic for domain availability checking.

This module contains the main business logic for domain checking operations,
separated from CLI presentation concerns for better modularity and testing.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import NamedTuple

from domain_tracker.domain_management import load_domains
from domain_tracker.settings import Settings
from domain_tracker.slack_notifier import (
    format_enhanced_slack_message,
    send_slack_alert,
)
from domain_tracker.whois_client import (
    DomainInfo,
    check_domain_status_detailed,
    get_enhanced_domain_info,
)


class DomainCheckResult(NamedTuple):
    """Results from a domain availability check operation."""

    total_domains: int
    available_domains: list[str]
    domain_infos: list[DomainInfo]
    errors: list[str]


class DomainCheckService:
    """Service class for handling domain check operations."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize the service with optional settings."""
        self.settings = settings or Settings()  # type: ignore[call-arg]

    def check_single_domain(
        self, domain: str, use_enhanced_format: bool = True, debug: bool = False
    ) -> DomainInfo:
        """
        Check a single domain and return detailed information.

        Args:
            domain: Domain name to check
            use_enhanced_format: Whether to use enhanced domain info format
            debug: Enable debug output including raw API responses

        Returns:
            DomainInfo object with check results
        """
        if use_enhanced_format:
            return get_enhanced_domain_info(domain, self.settings, debug=debug)
        else:
            # Legacy format - convert to DomainInfo
            is_available, problematic_statuses = check_domain_status_detailed(
                domain, self.settings, debug=debug
            )
            return DomainInfo(
                domain_name=domain,
                is_available=is_available,
                problematic_statuses=problematic_statuses,
                has_error=False,
            )

    def check_multiple_domains(
        self,
        domains: list[str] | None = None,
        use_enhanced_format: bool = True,
        debug: bool = False,
    ) -> DomainCheckResult:
        """
        Check multiple domains for availability.

        Args:
            domains: List of domains to check. If None, loads from domains.txt
            use_enhanced_format: Whether to use enhanced domain info format
            debug: Enable debug output including raw API responses

        Returns:
            DomainCheckResult with all check results
        """
        if domains is None:
            domains = load_domains()

        available_domains = []
        domain_infos = []
        errors = []

        for domain in domains:
            try:
                domain_info = self.check_single_domain(
                    domain, use_enhanced_format, debug=debug
                )
                domain_infos.append(domain_info)

                if domain_info.has_error:
                    errors.append(f"{domain}: {domain_info.error_message}")
                elif domain_info.is_available:
                    available_domains.append(domain)

            except Exception as e:
                error_msg = f"{domain}: {e}"
                errors.append(error_msg)
                logging.error(f"Error checking domain {domain}: {e}")

        return DomainCheckResult(
            total_domains=len(domains),
            available_domains=available_domains,
            domain_infos=domain_infos,
            errors=errors,
        )

    def send_slack_notification(
        self,
        domain_infos: list[DomainInfo],
        trigger_type: str = "manual",
        notify_all: bool = False,
    ) -> bool:
        """
        Send Slack notification based on domain check results.

        Args:
            domain_infos: List of domain information objects
            trigger_type: Type of trigger ("manual" or "scheduled")
            notify_all: Whether to notify for all domains regardless of availability

        Returns:
            True if notification was sent successfully, False otherwise
        """
        try:
            # Determine if we should send notification
            has_available = any(info.is_available for info in domain_infos)
            has_errors = any(info.has_error for info in domain_infos)
            
            should_notify = (
                has_available
                or has_errors  # Always notify for errors (system issues)
                or notify_all  # Always notify when explicitly requested
            )

            if should_notify and domain_infos:
                check_time = datetime.now(UTC)
                enhanced_message = format_enhanced_slack_message(
                    domain_infos, check_time, trigger_type=trigger_type
                )
                send_slack_alert(enhanced_message, self.settings)
                return True

        except Exception as e:
            logging.error(f"Error sending Slack notification: {e}")

        return False


def get_legacy_domain_message(
    domain: str, is_available: bool, problematic_statuses: list[str]
) -> str:
    """Create enhanced domain status message based on detailed status information."""
    # Message templates
    available_domain_message = "✅ Domain available: {domain}"
    unavailable_domain_message = "❌ Domain NOT available: {domain}"
    problematic_status_message = "⚠️ Domain appears available but still in {status}: {domain}. May not be fully released yet."

    if not is_available:
        if problematic_statuses:
            # Domain appears available but has problematic statuses
            status_list = ", ".join(problematic_statuses)
            return problematic_status_message.format(domain=domain, status=status_list)
        else:
            # Domain is genuinely unavailable
            return unavailable_domain_message.format(domain=domain)
    else:
        # Domain is truly available
        return available_domain_message.format(domain=domain)


def format_domain_summary(total_domains: int, available_domains: list[str]) -> str:
    """Format a summary of domain checking results."""
    available_count = len(available_domains)

    summary_lines = [
        "📊 Summary:",
        f"  Checked {total_domains} domains",
        f"  Found {available_count} available domains",
    ]

    if available_count == 0:
        summary_lines.append("  No domains available at this time.")
    else:
        summary_lines.append(f"  Available domains: {', '.join(available_domains)}")

    return "\n".join(summary_lines)


def get_domain_status_display(domain_info: DomainInfo) -> str:
    """Get a CLI-friendly display string for domain status."""
    if domain_info.has_error:
        return f"❌ Error: {domain_info.error_message}"
    elif domain_info.is_available:
        return "✅ Available"
    elif domain_info.problematic_statuses:
        return f"⚠️ Problematic status: {', '.join(domain_info.problematic_statuses)}"
    else:
        return "❌ Unavailable"
