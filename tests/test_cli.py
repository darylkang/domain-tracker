"""
Tests for CLI domain checking functionality.

Following TDD approach - these tests define the expected behavior for
the CLI interface that checks domains and sends Slack alerts.
"""

from __future__ import annotations

import logging
from unittest.mock import ANY, Mock, patch

from typer.testing import CliRunner

from domain_tracker import __version__
from domain_tracker.cli import app
from domain_tracker.whois_client import DomainInfo


class TestCLIDomainsCommand:
    """Test CLI domain checking functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_check_domains_command_exists(self) -> None:
        """Test that check-domains command exists and is accessible."""
        # ARRANGE & ACT: Try to get help for check-domains command
        result = self.runner.invoke(app, ["check-domains", "--help"])

        # ASSERT: Command should exist and show help
        assert result.exit_code == 0
        assert "check-domains" in result.stdout
        assert "Check domain availability" in result.stdout

    @patch("domain_tracker.cli.load_domains")
    @patch("domain_tracker.cli.get_enhanced_domain_info")
    @patch("domain_tracker.cli._send_slack_alert_safely")
    def test_check_domains_loads_domains_and_checks_availability(
        self, mock_slack: Mock, mock_check: Mock, mock_load: Mock
    ) -> None:
        """Test that check-domains loads domains and checks each one."""
        # ARRANGE: Mock domain loading and availability checking
        mock_load.return_value = ["example.com", "test.org"]
        mock_check.side_effect = [
            DomainInfo(domain_name="example.com", is_available=True, problematic_statuses=[]),
            DomainInfo(domain_name="test.org", is_available=False, problematic_statuses=[]),
        ]

        # ACT: Run check-domains command
        result = self.runner.invoke(app, ["check-domains"])

        # ASSERT: Should load domains and check each one
        assert result.exit_code == 0
        mock_load.assert_called_once()
        assert mock_check.call_count == 2
        mock_check.assert_any_call("example.com", ANY)
        mock_check.assert_any_call("test.org", ANY)

    @patch("domain_tracker.cli.load_domains")
    @patch("domain_tracker.cli.get_enhanced_domain_info")
    @patch("domain_tracker.cli._send_slack_alert_safely")
    def test_check_domains_sends_slack_alert_for_available_domains(
        self, mock_slack: Mock, mock_check: Mock, mock_load: Mock
    ) -> None:
        """Test that Slack alerts are sent for available domains only."""
        # ARRANGE: Mock one available domain, one unavailable
        mock_load.return_value = ["available.com", "unavailable.com"]
        mock_check.side_effect = [
            DomainInfo(domain_name="available.com", is_available=True, problematic_statuses=[]),
            DomainInfo(domain_name="unavailable.com", is_available=False, problematic_statuses=[]),
        ]

        # ACT: Run check-domains command
        result = self.runner.invoke(app, ["check-domains"])

        # ASSERT: Should send enhanced Slack alert for available domain
        assert result.exit_code == 0
        mock_slack.assert_called_once()  # Enhanced message sent once for all domains

    @patch("domain_tracker.cli.load_domains")
    @patch("domain_tracker.cli.get_enhanced_domain_info")
    @patch("domain_tracker.cli._send_slack_alert_safely")
    def test_check_domains_with_notify_all_flag(
        self, mock_slack: Mock, mock_check: Mock, mock_load: Mock
    ) -> None:
        """Test that --notify-all sends alerts for all domains."""
        # ARRANGE: Mock domains with mixed availability
        mock_load.return_value = ["available.com", "unavailable.com"]
        mock_check.side_effect = [
            DomainInfo(domain_name="available.com", is_available=True, problematic_statuses=[]),
            DomainInfo(domain_name="unavailable.com", is_available=False, problematic_statuses=[]),
        ]

        # ACT: Run check-domains with --notify-all
        result = self.runner.invoke(app, ["check-domains", "--notify-all"])

        # ASSERT: Should send enhanced Slack alert for all domains
        assert result.exit_code == 0
        mock_slack.assert_called_once()  # Enhanced message sent once with all domains

    @patch("domain_tracker.cli.load_domains")
    @patch("domain_tracker.cli.get_enhanced_domain_info")
    @patch("domain_tracker.cli._send_slack_alert_safely")
    def test_check_domains_with_debug_flag_enables_logging(
        self, mock_slack: Mock, mock_check: Mock, mock_load: Mock
    ) -> None:
        """Test that --debug flag enables debug logging."""
        # ARRANGE: Mock domains
        mock_load.return_value = ["test.com"]
        mock_check.return_value = DomainInfo(domain_name="test.com", is_available=True, problematic_statuses=[])

        # ACT: Run check-domains with --debug
        with patch("domain_tracker.cli.logging.basicConfig") as mock_basic_config:
            result = self.runner.invoke(app, ["check-domains", "--debug"])

        # ASSERT: Should configure debug logging
        assert result.exit_code == 0
        mock_basic_config.assert_called_once_with(level=logging.DEBUG)

    @patch("domain_tracker.cli.load_domains")
    @patch("domain_tracker.cli.get_enhanced_domain_info")
    @patch("domain_tracker.cli._send_slack_alert_safely")
    def test_check_domains_prints_summary_when_no_domains_available(
        self, mock_slack: Mock, mock_check: Mock, mock_load: Mock
    ) -> None:
        """Test that a summary is printed when no domains are available."""
        # ARRANGE: Mock domains that are all unavailable
        mock_load.return_value = ["test1.com", "test2.com"]
        mock_check.return_value = DomainInfo(domain_name="test.com", is_available=False, problematic_statuses=[])

        # ACT: Run check-domains command
        result = self.runner.invoke(app, ["check-domains"])

        # ASSERT: Should print summary and not send Slack alerts
        assert result.exit_code == 0
        assert "No domains available" in result.stdout
        assert "Checked 2 domains" in result.stdout
        mock_slack.assert_not_called()

    @patch("domain_tracker.cli.load_domains")
    @patch("domain_tracker.cli.get_enhanced_domain_info")
    @patch("domain_tracker.cli._send_slack_alert_safely")
    def test_check_domains_handles_domain_loading_errors_gracefully(
        self, mock_slack: Mock, mock_check: Mock, mock_load: Mock
    ) -> None:
        """Test that domain loading errors are handled gracefully."""
        # ARRANGE: Mock domain loading to raise an exception
        mock_load.side_effect = FileNotFoundError("domains.txt not found")

        # ACT: Run check-domains command
        result = self.runner.invoke(app, ["check-domains"])

        # ASSERT: Should exit with error and show helpful message
        assert result.exit_code == 1
        assert "Error loading domains" in result.stdout
        mock_check.assert_not_called()
        mock_slack.assert_not_called()

    @patch("domain_tracker.cli.load_domains")
    @patch("domain_tracker.cli.get_enhanced_domain_info")
    @patch("domain_tracker.cli._send_slack_alert_safely")
    def test_check_domains_handles_api_errors_gracefully(
        self, mock_slack: Mock, mock_check: Mock, mock_load: Mock
    ) -> None:
        """Test that API errors during domain checking are handled gracefully."""
        # ARRANGE: Mock domain loading success but API failure
        mock_load.return_value = ["test.com"]
        mock_check.return_value = DomainInfo(
            domain_name="test.com",
            is_available=False,
            problematic_statuses=[],
            has_error=True,
            error_message="API error"
        )

        # ACT: Run check-domains command
        result = self.runner.invoke(app, ["check-domains"])

        # ASSERT: Should continue and not crash
        assert result.exit_code == 0
        assert "Error: API error" in result.stdout

    @patch("domain_tracker.cli.load_domains")
    @patch("domain_tracker.cli.get_enhanced_domain_info")
    @patch("domain_tracker.cli.send_slack_alert")
    def test_check_domains_handles_slack_errors_gracefully(
        self, mock_slack: Mock, mock_check: Mock, mock_load: Mock
    ) -> None:
        """Test that Slack alerts handle errors gracefully."""
        # ARRANGE: Mock available domain but Slack error at the lower level
        mock_load.return_value = ["test.com"]
        mock_check.return_value = DomainInfo(domain_name="test.com", is_available=True, problematic_statuses=[])
        mock_slack.side_effect = Exception("Slack API error")

        # ACT: Run check-domains command
        result = self.runner.invoke(app, ["check-domains"])

        # ASSERT: Should continue - Slack error is handled safely by _send_slack_alert_safely
        assert result.exit_code == 0
        assert "⚠️  Error sending Slack alert" in result.stdout

    @patch("domain_tracker.cli.load_domains")
    @patch("domain_tracker.cli.get_enhanced_domain_info")
    @patch("domain_tracker.cli._send_slack_alert_safely")
    def test_check_domains_displays_progress_information(
        self, mock_slack: Mock, mock_check: Mock, mock_load: Mock
    ) -> None:
        """Test that progress information is displayed during domain checking."""
        # ARRANGE: Mock domains with mixed availability
        mock_load.return_value = ["example.com", "test.org"]
        mock_check.side_effect = [
            DomainInfo(domain_name="example.com", is_available=True, problematic_statuses=[]),
            DomainInfo(domain_name="test.org", is_available=False, problematic_statuses=[]),
        ]

        # ACT: Run check-domains command
        result = self.runner.invoke(app, ["check-domains"])

        # ASSERT: Should show progress information
        assert result.exit_code == 0
        assert "Checking domain availability" in result.stdout
        assert "Checking example.com" in result.stdout
        assert "Checking test.org" in result.stdout


class TestCLISingleDomainCheck:
    """Test CLI single domain checking functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("domain_tracker.cli.get_enhanced_domain_info")
    @patch("domain_tracker.cli._send_slack_alert_safely")
    def test_single_domain_check_available_domain(
        self, mock_slack: Mock, mock_check: Mock
    ) -> None:
        """Test checking a single available domain via check command."""
        # ARRANGE: Mock domain as available
        mock_check.return_value = DomainInfo(domain_name="example.com", is_available=True, problematic_statuses=[])

        # ACT: Run CLI with check command
        result = self.runner.invoke(app, ["check", "example.com"])

        # ASSERT: Should check domain and show success message
        assert result.exit_code == 0
        mock_check.assert_called_once_with("example.com", ANY)
        mock_slack.assert_called_once()  # Enhanced message sent
        assert "✅ Available" in result.stdout

    @patch("domain_tracker.cli.get_enhanced_domain_info")
    @patch("domain_tracker.cli._send_slack_alert_safely")
    def test_single_domain_check_unavailable_domain(
        self, mock_slack: Mock, mock_check: Mock
    ) -> None:
        """Test checking a single unavailable domain via check command."""
        # ARRANGE: Mock domain as unavailable
        mock_check.return_value = DomainInfo(domain_name="unavailable.com", is_available=False, problematic_statuses=[])

        # ACT: Run CLI with check command
        result = self.runner.invoke(app, ["check", "unavailable.com"])

        # ASSERT: Should check domain and show unavailable message
        assert result.exit_code == 0
        mock_check.assert_called_once_with("unavailable.com", ANY)
        # Enhanced format does not send alerts for unavailable domains unless they have errors
        assert "❌ Unavailable" in result.stdout

    @patch("domain_tracker.cli.get_enhanced_domain_info")
    @patch("domain_tracker.cli._send_slack_alert_safely")
    def test_single_domain_check_handles_api_errors_gracefully(
        self, mock_slack: Mock, mock_check: Mock
    ) -> None:
        """Test that API errors during single domain check are handled gracefully."""
        # ARRANGE: Mock API failure
        mock_check.return_value = DomainInfo(
            domain_name="test.com",
            is_available=False,
            problematic_statuses=[],
            has_error=True,
            error_message="API connection failed"
        )

        # ACT: Run CLI with check command
        result = self.runner.invoke(app, ["check", "test.com"])

        # ASSERT: Should continue and show helpful message (enhanced format handles errors gracefully)
        assert result.exit_code == 0
        mock_check.assert_called_once_with("test.com", ANY)
        assert "❌ Error checking test.com: API connection failed" in result.stdout
        mock_slack.assert_called_once()  # Error alert sent

    @patch("domain_tracker.cli.get_enhanced_domain_info")
    @patch("domain_tracker.cli.send_slack_alert")
    def test_single_domain_check_handles_slack_errors_gracefully(
        self, mock_slack: Mock, mock_check: Mock
    ) -> None:
        """Test that Slack errors during single domain check are handled gracefully."""
        # ARRANGE: Mock available domain but Slack error at the lower level
        mock_check.return_value = DomainInfo(domain_name="test.com", is_available=True, problematic_statuses=[])
        mock_slack.side_effect = Exception("Slack webhook error")

        # ACT: Run CLI with check command
        result = self.runner.invoke(app, ["check", "test.com"])

        # ASSERT: Should continue - Slack error is handled safely by _send_slack_alert_safely
        assert result.exit_code == 0
        mock_check.assert_called_once_with("test.com", ANY)
        mock_slack.assert_called_once()  # Enhanced message attempted
        assert "⚠️  Error sending Slack alert" in result.stdout

    def test_no_domain_argument_falls_back_to_existing_behavior(self) -> None:
        """Test that running without arguments shows help."""
        # ACT: Run CLI without arguments
        result = self.runner.invoke(app, [])

        # ASSERT: Should show help or usage information (Typer shows help with exit code 2)
        assert result.exit_code == 2
        # Should show the main help output - check both stdout and output
        output_text = result.stdout or result.output or ""
        assert "Usage:" in output_text, (
            f"Expected 'Usage:' in output, got: {repr(output_text)}"
        )

    def test_single_domain_check_validates_domain_format(self) -> None:
        """Test that the check command accepts domain arguments."""
        # ACT: Run CLI with check command and invalid domain
        result = self.runner.invoke(app, ["check", "invalid-domain"])

        # ASSERT: Should still attempt to check (validation handled by whois client)
        # This test ensures the CLI accepts the argument and passes it through
        assert result.exit_code in [
            0,
            1,
        ]  # May succeed or fail depending on API response

    @patch("domain_tracker.cli.get_enhanced_domain_info")
    @patch("domain_tracker.cli._send_slack_alert_safely")
    def test_single_domain_check_with_problematic_status(
        self, mock_slack: Mock, mock_check: Mock
    ) -> None:
        """Test checking a domain with problematic status sends enhanced Slack message."""
        # ARRANGE: Mock domain as having problematic status
        mock_check.return_value = DomainInfo(
            domain_name="problematic.com",
            is_available=False,
            problematic_statuses=["pendingDelete"]
        )

        # ACT: Run CLI with check command
        result = self.runner.invoke(app, ["check", "problematic.com"])

        # ASSERT: Should check domain and show enhanced message
        assert result.exit_code == 0
        mock_check.assert_called_once_with("problematic.com", ANY)
        mock_slack.assert_called_once()  # Enhanced message sent
        assert "⚠️ Problematic status: pendingDelete" in result.stdout

    @patch("domain_tracker.cli.get_enhanced_domain_info")
    @patch("domain_tracker.cli._send_slack_alert_safely")
    def test_single_domain_check_with_multiple_problematic_statuses(
        self, mock_slack: Mock, mock_check: Mock
    ) -> None:
        """Test checking a domain with multiple problematic statuses."""
        # ARRANGE: Mock domain with multiple problematic statuses
        mock_check.return_value = DomainInfo(
            domain_name="multiple-issues.com",
            is_available=False,
            problematic_statuses=["pendingDelete", "serverHold"]
        )

        # ACT: Run CLI with check command
        result = self.runner.invoke(app, ["check", "multiple-issues.com"])

        # ASSERT: Should check domain and show enhanced message with all statuses
        assert result.exit_code == 0
        mock_check.assert_called_once_with("multiple-issues.com", ANY)
        mock_slack.assert_called_once()  # Enhanced message sent
        assert "⚠️ Problematic status: pendingDelete, serverHold" in result.stdout


class TestCLIBulkProblematicStatuses:
    """Test CLI bulk domain checking with problematic statuses."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("domain_tracker.cli.load_domains")
    @patch("domain_tracker.cli.get_enhanced_domain_info")
    @patch("domain_tracker.cli._send_slack_alert_safely")
    def test_check_domains_displays_problematic_statuses(
        self, mock_slack: Mock, mock_check: Mock, mock_load: Mock
    ) -> None:
        """Test that problematic statuses are displayed in bulk checking."""
        # ARRANGE: Mock domains with mixed availability and problematic statuses
        mock_load.return_value = ["available.com", "problematic.com", "unavailable.com"]
        mock_check.side_effect = [
            DomainInfo(domain_name="available.com", is_available=True, problematic_statuses=[]),
            DomainInfo(domain_name="problematic.com", is_available=False, problematic_statuses=["pendingDelete"]),
            DomainInfo(domain_name="unavailable.com", is_available=False, problematic_statuses=[]),
        ]

        # ACT: Run check-domains command
        result = self.runner.invoke(app, ["check-domains"])

        # ASSERT: Should show appropriate status for each domain
        assert result.exit_code == 0
        assert "✅ Available" in result.stdout  # available.com
        assert "⚠️ Problematic status: pendingDelete" in result.stdout  # problematic.com
        assert "❌ Unavailable" in result.stdout  # unavailable.com

        # Should send enhanced alert for available domain
        mock_slack.assert_called_once()  # Enhanced message sent

    @patch("domain_tracker.cli.load_domains")
    @patch("domain_tracker.cli.get_enhanced_domain_info")
    @patch("domain_tracker.cli._send_slack_alert_safely")
    def test_check_domains_with_notify_all_sends_enhanced_alerts(
        self, mock_slack: Mock, mock_check: Mock, mock_load: Mock
    ) -> None:
        """Test that --notify-all sends enhanced alerts for problematic statuses."""
        # ARRANGE: Mock domains with problematic statuses
        mock_load.return_value = ["available.com", "problematic.com"]
        mock_check.side_effect = [
            DomainInfo(domain_name="available.com", is_available=True, problematic_statuses=[]),
            DomainInfo(domain_name="problematic.com", is_available=False, problematic_statuses=["serverHold", "clientHold"]),
        ]

        # ACT: Run check-domains with --notify-all
        result = self.runner.invoke(app, ["check-domains", "--notify-all"])

        # ASSERT: Should send enhanced alert once for all domains
        assert result.exit_code == 0
        mock_slack.assert_called_once()  # Enhanced message sent once with all domains


class TestCLIOtherCommands:
    """Test other CLI commands and general functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_cli_app_exists_and_shows_help(self) -> None:
        """Test that the CLI app exists and shows help information."""
        # ARRANGE & ACT: Get help for main app
        result = self.runner.invoke(app, ["--help"])

        # ASSERT: Should show help and available commands
        assert result.exit_code == 0
        assert "Domain Drop Tracker" in result.stdout

    def test_version_command_works(self) -> None:
        """Test that version information can be displayed."""
        # ACT: Get version information
        result = self.runner.invoke(app, ["--version"])

        # ASSERT: Should show version and exit cleanly
        assert result.exit_code == 0
        assert __version__ in result.stdout
