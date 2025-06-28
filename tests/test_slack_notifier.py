"""
Tests for Slack notification functionality.

Following TDD approach - these tests define the expected behavior for
sending Slack alerts when domains become available.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import requests
from requests.exceptions import ConnectionError, Timeout

from domain_tracker.settings import Settings
from domain_tracker.slack_notifier import send_slack_alert


class TestSlackNotifier:
    """Test Slack notification functionality."""

    def test_send_slack_alert_sends_message_successfully(self) -> None:
        """Test that messages are sent successfully to Slack."""
        # ARRANGE: Mock successful Slack webhook response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "ok"

        with patch("requests.post", return_value=mock_response) as mock_post:
            # ACT: Send a slack alert
            send_slack_alert("Test domain available: example.com")

            # ASSERT: Should make POST request to Slack
            mock_post.assert_called_once()

    def test_send_slack_alert_loads_webhook_url_from_settings(
        self, test_settings: Settings
    ) -> None:
        """Test that webhook URL is loaded from settings configuration."""
        # ARRANGE: Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "ok"

        with patch("requests.post", return_value=mock_response) as mock_post:
            # ACT: Send slack alert with test settings
            send_slack_alert("Test message", test_settings)

            # ASSERT: Should use webhook URL from settings
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "https://hooks.slack.com/test"

    def test_send_slack_alert_uses_correct_json_payload(self) -> None:
        """Test that correct JSON payload is sent to Slack."""
        # ARRANGE: Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "ok"

        with patch("requests.post", return_value=mock_response) as mock_post:
            # ACT: Send slack alert with specific message
            test_message = "🎉 Domain now available: awesome-domain.com"
            send_slack_alert(test_message)

            # ASSERT: Should send correct JSON payload
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "json" in call_args[1]
            assert call_args[1]["json"] == {"text": test_message}

    def test_send_slack_alert_handles_network_timeout_gracefully(self) -> None:
        """Test graceful handling of network timeouts."""
        # ARRANGE: Mock timeout exception
        with (
            patch("requests.post", side_effect=Timeout("Request timed out")),
            patch("domain_tracker.slack_notifier.logging") as mock_logging,
        ):
            # ACT: Send slack alert with timeout
            send_slack_alert("Test timeout message")

            # ASSERT: Should log error instead of crashing
            mock_logging.error.assert_called_once()
            error_message = mock_logging.error.call_args[0][0]
            assert "Failed to send Slack alert" in error_message

    def test_send_slack_alert_handles_connection_error_gracefully(self) -> None:
        """Test graceful handling of connection errors."""
        # ARRANGE: Mock connection error
        with (
            patch("requests.post", side_effect=ConnectionError("Unable to connect")),
            patch("domain_tracker.slack_notifier.logging") as mock_logging,
        ):
            # ACT: Send slack alert with connection error
            send_slack_alert("Test connection error message")

            # ASSERT: Should log error instead of crashing
            mock_logging.error.assert_called_once()
            error_message = mock_logging.error.call_args[0][0]
            assert "Failed to send Slack alert" in error_message

    def test_send_slack_alert_handles_http_error_response(self) -> None:
        """Test handling of HTTP error responses from Slack."""
        # ARRANGE: Mock HTTP error response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "invalid_payload"
        mock_response.raise_for_status.side_effect = requests.HTTPError(
            "400 Bad Request"
        )

        with (
            patch("requests.post", return_value=mock_response),
            patch("domain_tracker.slack_notifier.logging") as mock_logging,
        ):
            # ACT: Send slack alert with HTTP error
            send_slack_alert("Test HTTP error message")

            # ASSERT: Should log error instead of crashing
            mock_logging.error.assert_called_once()
            error_message = mock_logging.error.call_args[0][0]
            assert "Failed to send Slack alert" in error_message

    def test_send_slack_alert_uses_appropriate_timeout(self) -> None:
        """Test that requests use appropriate timeout."""
        # ARRANGE: Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "ok"

        with patch("requests.post", return_value=mock_response) as mock_post:
            # ACT: Send slack alert
            send_slack_alert("Test timeout message")

            # ASSERT: Should use timeout in request
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "timeout" in call_args[1]
            assert call_args[1]["timeout"] > 0  # Should have reasonable timeout

    def test_send_slack_alert_handles_empty_message(self) -> None:
        """Test handling of empty messages."""
        # ARRANGE: Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "ok"

        with patch("requests.post", return_value=mock_response) as mock_post:
            # ACT: Send empty message
            send_slack_alert("")

            # ASSERT: Should still send request (Slack can handle empty messages)
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[1]["json"] == {"text": ""}

    def test_send_slack_alert_handles_very_long_message(self) -> None:
        """Test handling of very long messages."""
        # ARRANGE: Mock successful response and very long message
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "ok"
        long_message = "A" * 4000  # Very long message

        with patch("requests.post", return_value=mock_response) as mock_post:
            # ACT: Send very long message
            send_slack_alert(long_message)

            # ASSERT: Should send request without modification
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[1]["json"] == {"text": long_message}

    def test_send_slack_alert_logs_successful_sends(self) -> None:
        """Test that successful sends are logged at debug level."""
        # ARRANGE: Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "ok"

        with (
            patch("requests.post", return_value=mock_response),
            patch("domain_tracker.slack_notifier.logging") as mock_logging,
        ):
            # ACT: Send slack alert
            send_slack_alert("Success test message")

            # ASSERT: Should log successful send
            mock_logging.debug.assert_called_once()
            debug_message = mock_logging.debug.call_args[0][0]
            assert "Successfully sent Slack alert" in debug_message

    def test_send_slack_alert_includes_user_agent(self) -> None:
        """Test that requests include appropriate User-Agent header."""
        # ARRANGE: Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "ok"

        with patch("requests.post", return_value=mock_response) as mock_post:
            # ACT: Send slack alert
            send_slack_alert("Test user agent message")

            # ASSERT: Should include User-Agent header
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "headers" in call_args[1]
            headers = call_args[1]["headers"]
            assert "User-Agent" in headers
            assert "Domain-Tracker" in headers["User-Agent"]

    def test_send_slack_alert_sets_content_type_header(self) -> None:
        """Test that Content-Type header is set correctly."""
        # ARRANGE: Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "ok"

        with patch("requests.post", return_value=mock_response) as mock_post:
            # ACT: Send slack alert
            send_slack_alert("Test content type message")

            # ASSERT: Should set Content-Type header
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            headers = call_args[1]["headers"]
            assert "Content-Type" in headers
            assert headers["Content-Type"] == "application/json"
