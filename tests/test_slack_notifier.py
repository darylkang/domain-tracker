"""
Tests for Slack notification functionality.

Following TDD approach - these tests define the expected behavior for
sending Slack alerts when domains become available.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import Mock, patch

import requests
from requests.exceptions import ConnectionError, Timeout

from domain_tracker.settings import Settings
from domain_tracker.slack_notifier import (
    format_domain_error_alert,
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
            assert str(call_args[0][0]) == "https://hooks.slack.com/test"

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
        check_time = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)

        # ACT: Format enhanced message
        message = format_enhanced_slack_message([domain_info], check_time)

        # ASSERT: Should include timestamp, domain details, and priority notification
        assert (
            "<!channel>" in message
        )  # Priority notification for available domain (new format)
        assert "9:30 AM EST • Jan 15, 2024" in message  # New York time format
        assert "✅ *example.com*" in message  # Available with markdown formatting
        assert "Status: Available" in message
        # Should NOT include missing fields
        assert "Expires:" not in message
        assert "Created:" not in message
        assert "Registrant:" not in message
        assert "Registrar:" not in message

    def test_format_enhanced_slack_message_single_unavailable_domain(self) -> None:
        """Test formatting enhanced message for single unavailable domain with full details."""
        # ARRANGE: Create domain info for unavailable domain with full details
        domain_info = DomainInfo(
            domain_name="google.com",
            is_available=False,
            problematic_statuses=[],
            expiration_date=datetime(2025, 9, 14, 4, 0, 0, tzinfo=UTC),
            creation_date=datetime(1997, 9, 15, 4, 0, 0, tzinfo=UTC),
            registrant_name="Domain Administrator",
            registrant_organization="Google LLC",
            registrar_name="MarkMonitor Inc.",
            name_servers=["ns1.google.com", "ns2.google.com"],
            has_error=False,
        )
        check_time = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)

        # ACT: Format enhanced message
        message = format_enhanced_slack_message([domain_info], check_time)

        # ASSERT: Should include all domain details without priority notification
        assert "<!channel>" not in message  # No priority for unavailable domain
        assert (
            "❌ *google.com*" in message
        )  # Unavailable status with markdown formatting
        assert "Status: Unavailable" in message
        assert "Expires: Sep 14, 2025" in message  # New York date format
        assert "Created: Sep 15, 1997" in message  # New York date format
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
        assert (
            "⚠️ *pending-example.com*" in message
        )  # Warning icon with markdown formatting
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
            expiration_date=datetime(2025, 6, 1, 0, 0, 0, tzinfo=UTC),
            creation_date=None,
            registrant_name="John Doe",
            registrant_organization=None,
            registrar_name="GoDaddy Inc.",
            name_servers=[],
            has_error=False,
        )
        domain_infos = [available_domain, unavailable_domain]
        check_time = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)

        # ACT: Format enhanced message
        message = format_enhanced_slack_message(domain_infos, check_time)

        # ASSERT: Should include both domains with summary
        assert "<!channel>" in message  # Priority for available domain (new format)
        assert "Domain Check Summary" in message
        assert "✅ *available.com*" in message  # Available with markdown formatting
        assert "❌ *taken.com*" in message  # Unavailable with markdown formatting
        assert (
            "Expires: May 31, 2025" in message
        )  # New York date format (UTC midnight becomes previous day evening in NY)
        assert "Registrant: John Doe" in message
        assert "Registrar: GoDaddy Inc." in message
        assert "📊 *Summary:*" in message  # New format has summary on separate lines
        assert "• 1 available • 1 unavailable • 0 errors" in message

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

        # ASSERT: Should include error notification (no priority alert in new format for errors)
        # Note: New format doesn't include channel notification for errors, only for available domains
        assert (
            "🚨 *error-domain.com*" in message
        )  # Error icon with markdown formatting
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
        check_time = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)

        # ACT: Format enhanced message
        message = format_enhanced_slack_message([domain_info], check_time)

        # ASSERT: Should handle missing dates gracefully by omitting them
        assert "❌ *no-dates.com*" in message  # Unavailable with markdown formatting
        assert "Registrant: Owner Name" in message
        # Should NOT show missing fields
        assert "Expires:" not in message
        assert "Created:" not in message
        assert "Registrar:" not in message

    def test_format_enhanced_slack_message_handles_partial_registrant_info(
        self,
    ) -> None:
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
        check_time = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)

        # ACT: Format enhanced message
        message = format_enhanced_slack_message([domain_info], check_time)

        # ASSERT: Should handle partial registrant info by showing only available data
        assert "Registrant: John Doe" in message
        # Should NOT show missing fields
        assert "Registrar:" not in message
        assert "Expires:" not in message
        assert "Created:" not in message


class TestImprovedSlackMessages:
    """Test improved Slack message formatting with user requirements."""

    def test_format_enhanced_message_uses_new_york_time(self) -> None:
        """Test that messages use New York local time instead of UTC."""
        # ARRANGE: Create domain info
        domain_info = DomainInfo(
            domain_name="example.com",
            is_available=True,
            problematic_statuses=[],
        )
        # Use a specific UTC time that would be different in ET
        utc_check_time = datetime(2024, 6, 15, 20, 30, 0, tzinfo=UTC)  # 8:30 PM UTC

        # ACT: Format the enhanced message
        result = format_enhanced_slack_message([domain_info], utc_check_time)

        # ASSERT: Should show New York time (4:30 PM EDT in June)
        assert "4:30 PM EDT" in result
        assert "Jun 15, 2024" in result
        assert "UTC" not in result

    def test_format_enhanced_message_omits_missing_fields(self) -> None:
        """Test that missing fields are omitted rather than showing 'Not available'."""
        # ARRANGE: Create domain info with minimal data (no expiration, registrant, etc.)
        domain_info = DomainInfo(
            domain_name="minimal.com",
            is_available=False,
            problematic_statuses=[],
            expiration_date=None,
            creation_date=None,
            registrant_name=None,
            registrant_organization=None,
            registrar_name=None,
        )
        check_time = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)

        # ACT: Format the enhanced message
        result = format_enhanced_slack_message([domain_info], check_time)

        # ASSERT: Should not contain "Not available" for any field
        assert "Not available" not in result
        assert "Expires:" not in result
        assert "Created:" not in result
        assert "Registrant:" not in result
        assert "Registrar:" not in result

    def test_format_enhanced_message_shows_multiple_status_codes(self) -> None:
        """Test that multiple status codes are properly displayed."""
        # ARRANGE: Create domain info with multiple problematic statuses
        domain_info = DomainInfo(
            domain_name="problematic.com",
            is_available=False,
            problematic_statuses=["pendingDelete", "serverHold", "clientHold"],
        )
        check_time = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)

        # ACT: Format the enhanced message
        result = format_enhanced_slack_message([domain_info], check_time)

        # ASSERT: Should show all status codes
        assert "pendingDelete" in result
        assert "serverHold" in result
        assert "clientHold" in result
        assert "Status: Problematic" in result

    def test_format_enhanced_message_includes_available_fields_only(self) -> None:
        """Test that only available metadata fields are included."""
        # ARRANGE: Create domain info with partial data
        domain_info = DomainInfo(
            domain_name="partial.com",
            is_available=False,
            problematic_statuses=[],
            expiration_date=datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC),
            creation_date=None,  # Missing
            registrant_name="John Doe",
            registrant_organization=None,  # Missing
            registrar_name=None,  # Missing
        )
        check_time = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)

        # ACT: Format the enhanced message
        result = format_enhanced_slack_message([domain_info], check_time)

        # ASSERT: Should include expiration and registrant, but not creation or registrar
        assert "Expires:" in result
        assert "Dec 31, 2025" in result
        assert "Registrant: John Doe" in result
        assert "Created:" not in result
        assert "Registrar:" not in result

    def test_format_enhanced_message_improved_visual_formatting(self) -> None:
        """Test that the message has improved visual formatting for easier scanning."""
        # ARRANGE: Create domain info
        domain_info = DomainInfo(
            domain_name="visual.com",
            is_available=True,
            problematic_statuses=[],
        )
        check_time = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)

        # ACT: Format the enhanced message
        result = format_enhanced_slack_message([domain_info], check_time)

        # ASSERT: Should have better formatting structure
        assert "🔍" in result  # Magnifying glass emoji for header
        assert "✅" in result  # Check mark for available domain
        assert "*visual.com*" in result  # Bold domain name
        # Should have clean section separation
        lines = result.split("\n")
        assert any(line.strip() == "" for line in lines)  # Has blank lines for spacing


class TestRedesignedSlackMessages:
    """Test the redesigned Slack message format with new structure and formatting."""

    def test_redesigned_format_header_structure(self) -> None:
        """Test that redesigned format has correct header structure."""
        # ARRANGE: Create domain info
        domain_info = DomainInfo(
            domain_name="example.com",
            is_available=True,
            problematic_statuses=[],
        )
        check_time = datetime(2024, 6, 29, 4, 56, 0, tzinfo=UTC)  # 12:56 AM EDT

        # ACT: Format the redesigned message
        result = format_enhanced_slack_message([domain_info], check_time)

        # ASSERT: Should have correct header structure
        assert "🔍 *Domain Check Summary*" in result
        assert "🗓️ 12:56 AM EDT • Jun 29, 2024" in result
        assert "👤 Triggered by: Scheduled hourly check" in result

    def test_redesigned_format_section_breaks(self) -> None:
        """Test that redesigned format includes proper section breaks."""
        # ARRANGE: Create multiple domains
        domain1 = DomainInfo(
            domain_name="example.com",
            is_available=True,
            problematic_statuses=[],
        )
        domain2 = DomainInfo(
            domain_name="test.com",
            is_available=False,
            problematic_statuses=[],
        )
        check_time = datetime(2024, 6, 29, 4, 56, 0, tzinfo=UTC)

        # ACT: Format the redesigned message
        result = format_enhanced_slack_message([domain1, domain2], check_time)

        # ASSERT: Should include section breaks
        section_break = "━━━━━━━━━━━━━━━━━━━━"
        assert section_break in result
        # Should have multiple section breaks for multiple domains
        assert result.count(section_break) >= 2

    def test_redesigned_format_available_domain_with_channel_ping(self) -> None:
        """Test that available domains include <@channel> ping under the domain."""
        # ARRANGE: Create available domain
        domain_info = DomainInfo(
            domain_name="spectre.cx",
            is_available=True,
            problematic_statuses=[],
        )
        check_time = datetime(2024, 6, 29, 4, 56, 0, tzinfo=UTC)

        # ACT: Format the redesigned message
        result = format_enhanced_slack_message([domain_info], check_time)

        # ASSERT: Should include domain with status and channel ping
        assert "✅ *spectre.cx*" in result
        assert "• Status: Available" in result
        assert "• 🔔 <!channel> — Action needed!" in result

    def test_redesigned_format_unavailable_domain_structure(self) -> None:
        """Test that unavailable domains have correct structure without channel ping."""
        # ARRANGE: Create unavailable domain with metadata
        domain_info = DomainInfo(
            domain_name="example.com",
            is_available=False,
            problematic_statuses=[],
            expiration_date=datetime(2025, 12, 15, 0, 0, 0, tzinfo=UTC),
            registrar_name="GoDaddy",
        )
        check_time = datetime(2024, 6, 29, 4, 56, 0, tzinfo=UTC)

        # ACT: Format the redesigned message
        result = format_enhanced_slack_message([domain_info], check_time)

        # ASSERT: Should have correct structure without channel ping for available domains only
        assert "❌ *example.com*" in result
        assert "• Status: Unavailable" in result
        assert "• Registrar: GoDaddy" in result
        assert (
            "• Expires: Dec 14, 2025" in result
        )  # UTC midnight becomes previous day in NY time
        # Should not have action needed for unavailable domains
        assert "Action needed!" not in result

    def test_redesigned_format_summary_structure(self) -> None:
        """Test that summary has correct structure with bullet separators."""
        # ARRANGE: Create mixed domain statuses
        available_domain = DomainInfo(
            domain_name="available.com",
            is_available=True,
            problematic_statuses=[],
        )
        unavailable_domain = DomainInfo(
            domain_name="taken.com",
            is_available=False,
            problematic_statuses=[],
        )
        check_time = datetime(2024, 6, 29, 4, 56, 0, tzinfo=UTC)

        # ACT: Format the redesigned message
        result = format_enhanced_slack_message(
            [available_domain, unavailable_domain], check_time
        )

        # ASSERT: Should have correct summary structure
        assert "📊 *Summary:*" in result
        assert "• 1 available • 1 unavailable • 0 errors" in result

    def test_redesigned_format_error_domain_message(self) -> None:
        """Test that error domains are handled in the main message format."""
        # ARRANGE: Create domain with error
        domain_info = DomainInfo(
            domain_name="error.com",
            is_available=False,
            problematic_statuses=[],
            has_error=True,
            error_message="API request timeout",
        )
        check_time = datetime(2024, 6, 29, 4, 56, 0, tzinfo=UTC)

        # ACT: Format the redesigned message
        result = format_enhanced_slack_message([domain_info], check_time)

        # ASSERT: Should include error in main format (separate error alerts tested separately)
        assert "🚨 *error.com*" in result
        assert "• Status: Error (API request timeout)" in result

    def test_redesigned_format_bullet_separators(self) -> None:
        """Test that bullet separators (•) are used consistently."""
        # ARRANGE: Create domain with various metadata
        domain_info = DomainInfo(
            domain_name="test.com",
            is_available=False,
            problematic_statuses=[],
            expiration_date=datetime(2025, 12, 15, 0, 0, 0, tzinfo=UTC),
            registrant_name="John Doe",
            registrar_name="GoDaddy",
        )
        check_time = datetime(2024, 6, 29, 4, 56, 0, tzinfo=UTC)

        # ACT: Format the redesigned message
        result = format_enhanced_slack_message([domain_info], check_time)

        # ASSERT: Should use bullet separators consistently
        assert "• Status: Unavailable" in result
        assert "• Registrar: GoDaddy" in result
        assert (
            "• Expires: Dec 14, 2025" in result
        )  # UTC midnight becomes previous day in NY time
        assert "• Registrant: John Doe" in result

    def test_redesigned_format_only_includes_present_metadata(self) -> None:
        """Test that only present metadata fields are included."""
        # ARRANGE: Create domain with minimal metadata
        domain_info = DomainInfo(
            domain_name="minimal.com",
            is_available=False,
            problematic_statuses=[],
            expiration_date=datetime(2025, 12, 15, 0, 0, 0, tzinfo=UTC),
            # No registrant, registrar, creation date, etc.
        )
        check_time = datetime(2024, 6, 29, 4, 56, 0, tzinfo=UTC)

        # ACT: Format the redesigned message
        result = format_enhanced_slack_message([domain_info], check_time)

        # ASSERT: Should only include present fields
        assert "• Status: Unavailable" in result
        assert (
            "• Expires: Dec 14, 2025" in result
        )  # UTC midnight becomes previous day in NY time
        # Should NOT include missing fields
        assert "• Registrant:" not in result
        assert "• Registrar:" not in result
        assert "• Created:" not in result

    def test_enhanced_message_trigger_type_manual(self) -> None:
        """Test that manual trigger type shows correct trigger message."""
        # ARRANGE: Create domain with any status
        domain_info = DomainInfo(
            domain_name="test.com",
            is_available=False,
            problematic_statuses=[],
        )
        check_time = datetime(2024, 6, 29, 4, 56, 0, tzinfo=UTC)

        # ACT: Format message with manual trigger type
        result = format_enhanced_slack_message([domain_info], check_time, trigger_type="manual")

        # ASSERT: Should show manual trigger message
        assert "👤 Triggered by: Manual CLI check" in result
        assert "Scheduled hourly check" not in result

    def test_enhanced_message_trigger_type_scheduled(self) -> None:
        """Test that scheduled trigger type shows correct trigger message."""
        # ARRANGE: Create domain with any status
        domain_info = DomainInfo(
            domain_name="test.com",
            is_available=False,
            problematic_statuses=[],
        )
        check_time = datetime(2024, 6, 29, 4, 56, 0, tzinfo=UTC)

        # ACT: Format message with scheduled trigger type
        result = format_enhanced_slack_message([domain_info], check_time, trigger_type="scheduled")

        # ASSERT: Should show scheduled trigger message
        assert "👤 Triggered by: Scheduled hourly check" in result
        assert "Manual CLI check" not in result

    def test_enhanced_message_trigger_type_default(self) -> None:
        """Test that default (no parameter) shows scheduled trigger message."""
        # ARRANGE: Create domain with any status
        domain_info = DomainInfo(
            domain_name="test.com",
            is_available=False,
            problematic_statuses=[],
        )
        check_time = datetime(2024, 6, 29, 4, 56, 0, tzinfo=UTC)

        # ACT: Format message without trigger_type parameter (uses default)
        result = format_enhanced_slack_message([domain_info], check_time)

        # ASSERT: Should default to scheduled trigger message
        assert "👤 Triggered by: Scheduled hourly check" in result
        assert "Manual CLI check" not in result


class TestSlackErrorAlerts:
    """Test separate error alert functionality for failed domain lookups."""

    def test_format_domain_error_alert_structure(self) -> None:
        """Test that error alert has correct structure and content."""
        # ARRANGE: Define error details
        domain_name = "failed-lookup.com"
        error_message = "Connection timeout"

        # ACT: Format the error alert
        result = format_domain_error_alert(domain_name, error_message)

        # ASSERT: Should have correct structure
        assert "🚨 *Domain Check Failed for: failed-lookup.com*" in result
        assert "❗ Error: Connection timeout" in result
        assert "🔁 Will retry at next scheduled interval" in result
        assert "🔔 <!channel> — Manual check may be needed" in result

    def test_format_domain_error_alert_with_various_errors(self) -> None:
        """Test error alert formatting with different error types."""
        # ARRANGE: Test various error scenarios
        test_cases = [
            ("timeout.com", "API request timeout"),
            ("invalid.com", "Invalid domain format"),
            ("network.com", "Network unreachable"),
            ("auth.com", "Authentication failed"),
        ]

        for domain, error in test_cases:
            # ACT: Format error alert
            result = format_domain_error_alert(domain, error)

            # ASSERT: Should include domain and error
            assert f"Domain Check Failed for: {domain}" in result
            assert f"Error: {error}" in result
            assert "<!channel>" in result

    def test_format_domain_error_alert_channel_notification(self) -> None:
        """Test that error alerts include channel notification for urgent attention."""
        # ARRANGE: Create error alert
        domain_name = "urgent.com"
        error_message = "Critical API failure"

        # ACT: Format error alert
        result = format_domain_error_alert(domain_name, error_message)

        # ASSERT: Should include channel ping for urgent attention
        assert "🔔 <!channel> — Manual check may be needed" in result

    def test_format_domain_error_alert_retry_message(self) -> None:
        """Test that error alerts include retry information."""
        # ARRANGE: Create error alert
        domain_name = "retry.com"
        error_message = "Temporary failure"

        # ACT: Format error alert
        result = format_domain_error_alert(domain_name, error_message)

        # ASSERT: Should include retry information
        assert "🔁 Will retry at next scheduled interval" in result

    def test_error_domains_still_in_main_message(self) -> None:
        """Test that error domains are still included in main message format."""
        # ARRANGE: Create domain with error
        domain_info = DomainInfo(
            domain_name="failed-lookup.com",
            is_available=False,
            problematic_statuses=[],
            has_error=True,
            error_message="Connection timeout",
        )
        check_time = datetime(2024, 6, 29, 4, 56, 0, tzinfo=UTC)

        # ACT: Format the main message
        result = format_enhanced_slack_message([domain_info], check_time)

        # ASSERT: Should include error in main message (in addition to separate alert)
        assert "🚨 *failed-lookup.com*" in result
        assert "• Status: Error (Connection timeout)" in result
        assert "📊 *Summary:*" in result
        assert "• 0 available • 0 unavailable • 1 errors" in result
