"""
Tests for Slack notification functionality.

Following TDD approach - these tests define the expected behavior for
sending Slack alerts when domains become available.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import Mock, patch

import requests
from requests.exceptions import ConnectionError, Timeout

from domain_tracker.settings import Settings
from domain_tracker.slack_notifier import (
    format_enhanced_slack_message,
    send_slack_alert,
)
from domain_tracker.whois_client import DomainInfo


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


class TestEnhancedSlackMessages:
    """Test enhanced Slack message formatting with rich domain information."""

    def test_format_enhanced_slack_message_single_available_domain(self) -> None:
        """Test formatting enhanced message for single available domain."""
        # ARRANGE: Create domain info for available domain
        domain_info = DomainInfo(
            domain_name="example.com",
            is_available=True,
            problematic_statuses=[],
            expiration_date=None,
            creation_date=None,
            registrant_name=None,
            registrant_organization=None,
            registrar_name=None,
            name_servers=[],
            has_error=False,
        )
        check_time = datetime(2024, 1, 15, 14, 30, 0)

        # ACT: Format enhanced message
        message = format_enhanced_slack_message([domain_info], check_time)

        # ASSERT: Should include timestamp, domain details, and priority notification
        assert "<!channel>" in message  # Priority notification for available domain
        assert "2024-01-15 14:30:00 UTC" in message  # Timestamp
        assert "✅ **example.com**" in message  # Available status with markdown formatting
        assert "Status: Available" in message

    def test_format_enhanced_slack_message_single_unavailable_domain(self) -> None:
        """Test formatting enhanced message for single unavailable domain with full details."""
        # ARRANGE: Create domain info for unavailable domain with full details
        domain_info = DomainInfo(
            domain_name="google.com",
            is_available=False,
            problematic_statuses=[],
            expiration_date=datetime(2025, 9, 14, 4, 0, 0),
            creation_date=datetime(1997, 9, 15, 4, 0, 0),
            registrant_name="Domain Administrator",
            registrant_organization="Google LLC",
            registrar_name="MarkMonitor Inc.",
            name_servers=["ns1.google.com", "ns2.google.com"],
            has_error=False,
        )
        check_time = datetime(2024, 1, 15, 14, 30, 0)

        # ACT: Format enhanced message
        message = format_enhanced_slack_message([domain_info], check_time)

        # ASSERT: Should include all domain details without priority notification
        assert "<!channel>" not in message  # No priority for unavailable domain
        assert "❌ **google.com**" in message  # Unavailable status with markdown formatting
        assert "Status: Unavailable" in message
        assert "Expires: 2025-09-14 04:00:00 UTC" in message
        assert "Created: 1997-09-15 04:00:00 UTC" in message
        assert "Registrant: Domain Administrator (Google LLC)" in message
        assert "Registrar: MarkMonitor Inc." in message
        assert "Name Servers: ns1.google.com, ns2.google.com" in message

    def test_format_enhanced_slack_message_domain_with_problematic_status(self) -> None:
        """Test formatting message for domain with problematic status."""
        # ARRANGE: Create domain info with problematic status
        domain_info = DomainInfo(
            domain_name="pending-example.com",
            is_available=False,
            problematic_statuses=["pendingDelete", "serverHold"],
            expiration_date=datetime(2024, 1, 15, 12, 0, 0),
            creation_date=datetime(2020, 5, 1, 10, 30, 0),
            registrant_name="Previous Owner",
            registrant_organization="Old Company Inc.",
            registrar_name="Example Registrar",
            name_servers=[],
            has_error=False,
        )
        check_time = datetime(2024, 1, 15, 14, 30, 0)

        # ACT: Format enhanced message
        message = format_enhanced_slack_message([domain_info], check_time)

        # ASSERT: Should highlight problematic statuses
        assert "⚠️ **pending-example.com**" in message  # Warning icon with markdown formatting
        assert "Status: Problematic (pendingDelete, serverHold)" in message
        assert "Registrant: Previous Owner (Old Company Inc.)" in message

    def test_format_enhanced_slack_message_multiple_domains(self) -> None:
        """Test formatting message for multiple domains with mixed statuses."""
        # ARRANGE: Create multiple domain infos
        available_domain = DomainInfo(
            domain_name="available.com",
            is_available=True,
            problematic_statuses=[],
            expiration_date=None,
            creation_date=None,
            registrant_name=None,
            registrant_organization=None,
            registrar_name=None,
            name_servers=[],
            has_error=False,
        )
        unavailable_domain = DomainInfo(
            domain_name="taken.com",
            is_available=False,
            problematic_statuses=[],
            expiration_date=datetime(2025, 6, 1, 0, 0, 0),
            creation_date=None,
            registrant_name="John Doe",
            registrant_organization=None,
            registrar_name="GoDaddy Inc.",
            name_servers=[],
            has_error=False,
        )
        domain_infos = [available_domain, unavailable_domain]
        check_time = datetime(2024, 1, 15, 14, 30, 0)

        # ACT: Format enhanced message
        message = format_enhanced_slack_message(domain_infos, check_time)

        # ASSERT: Should include both domains with summary
        assert "<!channel>" in message  # Priority for available domain
        assert "Domain Check Summary" in message
        assert "✅ **available.com**" in message  # Available with markdown formatting
        assert "❌ **taken.com**" in message  # Unavailable with markdown formatting
        assert "Expires: 2025-06-01 00:00:00 UTC" in message
        assert "Registrant: John Doe" in message
        assert "Registrar: GoDaddy Inc." in message

    def test_format_enhanced_slack_message_with_api_errors(self) -> None:
        """Test formatting message when API errors occur."""
        # ARRANGE: Create domain info with error
        error_domain = DomainInfo(
            domain_name="error-domain.com",
            is_available=False,
            problematic_statuses=[],
            expiration_date=None,
            creation_date=None,
            registrant_name=None,
            registrant_organization=None,
            registrar_name=None,
            name_servers=[],
            has_error=True,
            error_message="API request timeout",
        )
        check_time = datetime(2024, 1, 15, 14, 30, 0)

        # ACT: Format enhanced message
        message = format_enhanced_slack_message([error_domain], check_time)

        # ASSERT: Should include error notification with priority alert
        assert "<!channel>" in message  # Priority notification for system error
        assert "🚨 **error-domain.com**" in message  # Error icon with markdown formatting
        assert "Status: Error (API request timeout)" in message

    def test_format_enhanced_slack_message_handles_missing_dates(self) -> None:
        """Test formatting gracefully handles missing date information."""
        # ARRANGE: Create domain info with missing dates
        domain_info = DomainInfo(
            domain_name="no-dates.com",
            is_available=False,
            problematic_statuses=[],
            expiration_date=None,
            creation_date=None,
            registrant_name="Owner Name",
            registrant_organization=None,
            registrar_name=None,
            name_servers=[],
            has_error=False,
        )
        check_time = datetime(2024, 1, 15, 14, 30, 0)

        # ACT: Format enhanced message
        message = format_enhanced_slack_message([domain_info], check_time)

        # ASSERT: Should handle missing dates gracefully
        assert "❌ **no-dates.com**" in message  # Unavailable with markdown formatting
        assert "Expires: Not available" in message
        assert "Created: Not available" in message
        assert "Registrant: Owner Name" in message

    def test_format_enhanced_slack_message_handles_partial_registrant_info(self) -> None:
        """Test formatting handles partial registrant information."""
        # ARRANGE: Create domain info with only registrant name
        domain_info = DomainInfo(
            domain_name="partial-info.com",
            is_available=False,
            problematic_statuses=[],
            expiration_date=None,
            creation_date=None,
            registrant_name="John Doe",
            registrant_organization=None,
            registrar_name=None,
            name_servers=[],
            has_error=False,
        )
        check_time = datetime(2024, 1, 15, 14, 30, 0)

        # ACT: Format enhanced message
        message = format_enhanced_slack_message([domain_info], check_time)

        # ASSERT: Should handle partial registrant info
        assert "Registrant: John Doe" in message
        assert "Registrar: Not available" in message
