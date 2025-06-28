"""
Tests for CLI domain checking functionality.

Following TDD approach - these tests define the expected behavior for 
the CLI interface that checks domains and sends Slack alerts.
"""

from __future__ import annotations

import logging
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from domain_tracker import __version__
from domain_tracker.cli import app


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

    @patch('domain_tracker.cli.load_domains')
    @patch('domain_tracker.cli.check_domain_availability')
    @patch('domain_tracker.cli.send_slack_alert')
    def test_check_domains_loads_domains_and_checks_availability(
        self, 
        mock_slack: Mock, 
        mock_check: Mock, 
        mock_load: Mock
    ) -> None:
        """Test that check-domains loads domains and checks each one."""
        # ARRANGE: Mock domain loading and availability checking
        mock_load.return_value = ["example.com", "test.org"]
        mock_check.side_effect = [True, False]  # First available, second not
        
        # ACT: Run check-domains command
        result = self.runner.invoke(app, ["check-domains"])
        
        # ASSERT: Should load domains and check each one
        assert result.exit_code == 0
        mock_load.assert_called_once()
        assert mock_check.call_count == 2
        mock_check.assert_any_call("example.com")
        mock_check.assert_any_call("test.org")

    @patch('domain_tracker.cli.load_domains')
    @patch('domain_tracker.cli.check_domain_availability')
    @patch('domain_tracker.cli.send_slack_alert')
    def test_check_domains_sends_slack_alert_for_available_domains(
        self, 
        mock_slack: Mock, 
        mock_check: Mock, 
        mock_load: Mock
    ) -> None:
        """Test that Slack alerts are sent for available domains only."""
        # ARRANGE: Mock one available domain, one unavailable
        mock_load.return_value = ["available.com", "unavailable.com"]
        mock_check.side_effect = [True, False]
        
        # ACT: Run check-domains command
        result = self.runner.invoke(app, ["check-domains"])
        
        # ASSERT: Should send Slack alert only for available domain
        assert result.exit_code == 0
        mock_slack.assert_called_once_with("✅ Domain available: available.com")

    @patch('domain_tracker.cli.load_domains')
    @patch('domain_tracker.cli.check_domain_availability')
    @patch('domain_tracker.cli.send_slack_alert')
    def test_check_domains_with_notify_all_flag(
        self, 
        mock_slack: Mock, 
        mock_check: Mock, 
        mock_load: Mock
    ) -> None:
        """Test that --notify-all sends alerts for all domains."""
        # ARRANGE: Mock domains with mixed availability
        mock_load.return_value = ["available.com", "unavailable.com"]
        mock_check.side_effect = [True, False]
        
        # ACT: Run check-domains with --notify-all
        result = self.runner.invoke(app, ["check-domains", "--notify-all"])
        
        # ASSERT: Should send Slack alerts for both domains
        assert result.exit_code == 0
        assert mock_slack.call_count == 2
        mock_slack.assert_any_call("✅ Domain available: available.com")
        mock_slack.assert_any_call("❌ Domain unavailable: unavailable.com")

    @patch('domain_tracker.cli.load_domains')
    @patch('domain_tracker.cli.check_domain_availability')
    @patch('domain_tracker.cli.send_slack_alert')
    def test_check_domains_with_debug_flag_enables_logging(
        self, 
        mock_slack: Mock, 
        mock_check: Mock, 
        mock_load: Mock
    ) -> None:
        """Test that --debug flag enables debug logging."""
        # ARRANGE: Mock domains
        mock_load.return_value = ["test.com"]
        mock_check.return_value = True
        
        # ACT: Run check-domains with --debug
        with patch('domain_tracker.cli.logging.basicConfig') as mock_basic_config:
            result = self.runner.invoke(app, ["check-domains", "--debug"])
        
        # ASSERT: Should configure debug logging
        assert result.exit_code == 0
        mock_basic_config.assert_called_once_with(level=logging.DEBUG)

    @patch('domain_tracker.cli.load_domains')
    @patch('domain_tracker.cli.check_domain_availability')
    @patch('domain_tracker.cli.send_slack_alert')
    def test_check_domains_prints_summary_when_no_domains_available(
        self, 
        mock_slack: Mock, 
        mock_check: Mock, 
        mock_load: Mock
    ) -> None:
        """Test that a summary is printed when no domains are available."""
        # ARRANGE: Mock domains that are all unavailable
        mock_load.return_value = ["test1.com", "test2.com"]
        mock_check.return_value = False
        
        # ACT: Run check-domains command
        result = self.runner.invoke(app, ["check-domains"])
        
        # ASSERT: Should print summary and not send Slack alerts
        assert result.exit_code == 0
        assert "No domains available" in result.stdout
        assert "Checked 2 domains" in result.stdout
        mock_slack.assert_not_called()

    @patch('domain_tracker.cli.load_domains')
    @patch('domain_tracker.cli.check_domain_availability')
    @patch('domain_tracker.cli.send_slack_alert')
    def test_check_domains_handles_domain_loading_errors_gracefully(
        self, 
        mock_slack: Mock, 
        mock_check: Mock, 
        mock_load: Mock
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

    @patch('domain_tracker.cli.load_domains')
    @patch('domain_tracker.cli.check_domain_availability')
    @patch('domain_tracker.cli.send_slack_alert')
    def test_check_domains_handles_api_errors_gracefully(
        self, 
        mock_slack: Mock, 
        mock_check: Mock, 
        mock_load: Mock
    ) -> None:
        """Test that API errors during domain checking are handled gracefully."""
        # ARRANGE: Mock domain loading success but API failure
        mock_load.return_value = ["test.com"]
        mock_check.side_effect = Exception("API error")
        
        # ACT: Run check-domains command
        result = self.runner.invoke(app, ["check-domains"])
        
        # ASSERT: Should continue and not crash
        assert result.exit_code == 0
        assert "Error checking test.com" in result.stdout
        mock_slack.assert_not_called()

    @patch('domain_tracker.cli.load_domains')
    @patch('domain_tracker.cli.check_domain_availability')
    @patch('domain_tracker.cli.send_slack_alert')
    def test_check_domains_handles_slack_errors_gracefully(
        self, 
        mock_slack: Mock, 
        mock_check: Mock, 
        mock_load: Mock
    ) -> None:
        """Test that Slack notification errors are handled gracefully."""
        # ARRANGE: Mock available domain but Slack failure
        mock_load.return_value = ["available.com"]
        mock_check.return_value = True
        mock_slack.side_effect = Exception("Slack webhook error")
        
        # ACT: Run check-domains command
        result = self.runner.invoke(app, ["check-domains"])
        
        # ASSERT: Should continue and report the error
        assert result.exit_code == 0
        assert "Error sending Slack alert" in result.stdout

    def test_check_domains_displays_progress_information(self) -> None:
        """Test that progress information is displayed during domain checking."""
        # ARRANGE & ACT: Mock domains and run command
        with patch('domain_tracker.cli.load_domains') as mock_load, \
             patch('domain_tracker.cli.check_domain_availability') as mock_check, \
             patch('domain_tracker.cli.send_slack_alert'):
            
            mock_load.return_value = ["test1.com", "test2.com", "test3.com"]
            mock_check.side_effect = [True, False, True]
            
            result = self.runner.invoke(app, ["check-domains"])
        
        # ASSERT: Should show progress information
        assert result.exit_code == 0
        assert "Checking domain availability" in result.stdout
        assert "Found 2 available domains" in result.stdout


class TestCLIOtherCommands:
    """Test other CLI commands for completeness."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_cli_app_exists_and_shows_help(self) -> None:
        """Test that the CLI app exists and shows helpful information."""
        # ARRANGE & ACT: Get help for main app
        result = self.runner.invoke(app, ["--help"])
        
        # ASSERT: Should show help with domain tracker information
        assert result.exit_code == 0
        assert "Domain Drop Tracker" in result.stdout

    def test_version_command_works(self) -> None:
        """Test that version information is displayed correctly."""
        # ARRANGE & ACT: Get version information
        result = self.runner.invoke(app, ["--version"])
        
        # ASSERT: Should show version and exit successfully
        assert result.exit_code == 0
        # Note: Version output depends on the actual version
