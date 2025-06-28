"""
Slack notification client for domain availability alerts.

This module provides functionality to send Slack notifications when domains
become available for registration.
"""

from __future__ import annotations

import logging

import requests
from requests.exceptions import ConnectionError, RequestException, Timeout

from domain_tracker.settings import Settings

# Configuration Constants
DEFAULT_TIMEOUT_SECONDS = 10
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
    """
    try:
        # Load settings
        if settings is None:
            settings = Settings()  # type: ignore[call-arg]

        # Prepare request data
        webhook_url = str(settings.slack_webhook_url)
        payload = {"text": message}
        headers = {"Content-Type": "application/json", "User-Agent": USER_AGENT}

        # Send request to Slack
        response = requests.post(
            webhook_url, json=payload, headers=headers, timeout=DEFAULT_TIMEOUT_SECONDS
        )

        # Check for HTTP errors
        response.raise_for_status()

        # Verify Slack's response
        if response.text.strip() != "ok":
            logging.warning(f"Slack returned unexpected response: {response.text}")

        # Log successful send
        logging.debug(
            f"Successfully sent Slack alert: {message[:MAX_MESSAGE_PREVIEW_LENGTH]}..."
        )

    except (ConnectionError, Timeout, RequestException) as e:
        # Log network errors gracefully
        logging.error(f"Failed to send Slack alert: {type(e).__name__}: {e}")

    except Exception as e:
        # Log any other unexpected errors
        logging.error(f"Failed to send Slack alert: Unexpected error: {e}")
