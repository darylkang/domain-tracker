"""
Slack notification client for domain availability alerts.

This module provides functionality to send Slack notifications when domains
become available for registration with robust error handling.
"""

from __future__ import annotations

import logging

import requests
from requests.exceptions import ConnectionError, RequestException, Timeout

from domain_tracker.settings import Settings

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
