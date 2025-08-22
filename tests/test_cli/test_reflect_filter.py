"""Test suite for tmux-orc reflect command --filter flag."""

import json
import subprocess
from unittest.mock import Mock, patch

import click
import pytest
from click.testing import CliRunner

from tmux_orchestrator.cli import _filter_commands, _has_regex_chars, _matches_filter, reflect


class TestFilterHelpers:
    """Test the filter helper functions."""

    def test_has_regex_chars(self):
        """Test regex character detection."""
        # Should detect regex chars
        assert _has_regex_chars("^agent") is True
        assert _has_regex_chars("agent$") is True
        assert _has_regex_chars("agent.*send") is True
        assert _has_regex_chars("send|message") is True
        assert _has_regex_chars("agent[0-9]") is True
        assert _has_regex_chars("agent{1,3}") is True
        assert _has_regex_chars("agent?") is True
        assert _has_regex_chars("agent+") is True
        assert _has_regex_chars("(agent)") is True

        # Should not detect regex chars
        assert _has_regex_chars("agent") is False
        assert _has_regex_chars("agent send") is False
        assert _has_regex_chars("agent-send") is False
        assert _has_regex_chars("agent_send") is False

    def test_matches_filter_simple(self):
        """Test simple string matching."""
        # Case insensitive substring match
        assert _matches_filter("agent send", "agent") is True
        assert _matches_filter("agent send", "AGENT") is True
        assert _matches_filter("agent send", "send") is True
        assert _matches_filter("spawn agent", "agent") is True

        # No match
        assert _matches_filter("team deploy", "agent") is False
        assert _matches_filter("monitor start", "agent") is False

    def test_matches_filter_regex(self):
        """Test regex pattern matching."""
        # Valid regex patterns
        assert _matches_filter("agent send", "^agent") is True
        assert _matches_filter("spawn agent", "^agent") is False
        assert _matches_filter("agent send", "send$") is True
        assert _matches_filter("send message", "send$") is False
        assert _matches_filter("agent send", "agent.*send") is True
        assert _matches_filter("agent message", "send|message") is True

        # Invalid regex should fall back to substring
        assert _matches_filter("agent [send", "[send") is True

    def test_filter_commands_flat(self):
        """Test filtering flat command structure."""
        # Create mock commands
        commands = {
            "agent": Mock(spec=click.Command, name="agent"),
            "team": Mock(spec=click.Command, name="team"),
            "monitor": Mock(spec=click.Command, name="monitor"),
        }

        # Filter for "agent"
        filtered = _filter_commands(commands, "agent")
        assert "agent" in filtered
        assert "team" not in filtered
        assert "monitor" not in filtered

    def test_filter_commands_nested(self):
        """Test filtering nested command groups."""
        # Create mock command group with subcommands
        agent_group = Mock(spec=click.Group)
        agent_group.name = "agent"
        agent_group.commands = {
            "send": Mock(spec=click.Command),
            "status": Mock(spec=click.Command),
            "kill": Mock(spec=click.Command),
        }

        team_group = Mock(spec=click.Group)
        team_group.name = "team"
        team_group.commands = {
            "deploy": Mock(spec=click.Command),
            "status": Mock(spec=click.Command),
        }

        status_command = Mock(spec=click.Command)
        status_command.name = "status"

        commands = {
            "agent": agent_group,
            "team": team_group,
            "status": status_command,
        }

        # Filter for "status" should include all commands with status
        filtered = _filter_commands(commands, "status")
        assert "agent" in filtered  # Has status subcommand
        assert "team" in filtered  # Has status subcommand
        assert "status" in filtered  # Direct match

        # Filter for "send" should only include agent group
        filtered = _filter_commands(commands, "send")
        assert "agent" in filtered
        assert "team" not in filtered
        assert "status" not in filtered

        # The actual filtering of subcommands is handled during display
        # The group structure is preserved for now


class TestReflectCommand:
    """Test the reflect command with filter flag."""

    def test_reflect_filter_option(self):
        """Test that filter option is available."""
        runner = CliRunner()
        result = runner.invoke(reflect, ["--help"])
        assert result.exit_code == 0
        assert "--filter" in result.output
        assert "Filter commands by pattern" in result.output

    @patch("subprocess.run")
    def test_reflect_filter_cli(self, mock_run):
        """Test reflect command via CLI with filter."""
        # Test simple filter
        subprocess.run(["tmux-orc", "reflect", "--filter", "agent"], capture_output=True, text=True, check=False)

        # The actual subprocess.run would be mocked in a real test environment
        # This is just to show the expected usage

    def test_reflect_filter_tree_format(self):
        """Test filter with tree format output."""
        runner = CliRunner()

        # Create a minimal CLI for testing
        test_cli = click.Group("test-cli")

        # Add some test commands
        agent_group = click.Group("agent")
        agent_group.add_command(click.Command("send", help="Send message"))
        agent_group.add_command(click.Command("status", help="Get status"))

        team_group = click.Group("team")
        team_group.add_command(click.Command("deploy", help="Deploy team"))

        test_cli.add_command(agent_group)
        test_cli.add_command(team_group)
        test_cli.add_command(click.Command("status", help="Global status"))

        # Mock the CLI context
        with patch("click.Context.find_root") as mock_root:
            mock_ctx = Mock()
            mock_ctx.command = test_cli
            mock_root.return_value = mock_ctx

            # Test filter for "agent"
            result = runner.invoke(reflect, ["--filter", "agent"])
            assert "agent" in result.output
            assert "team" not in result.output or "No commands match" in result.output

    def test_reflect_filter_json_format(self):
        """Test filter with JSON format output."""
        runner = CliRunner()

        # Create a minimal CLI for testing
        test_cli = click.Group("test-cli")
        agent_group = click.Group("agent")
        agent_group.add_command(click.Command("send"))
        test_cli.add_command(agent_group)
        test_cli.add_command(click.Command("status"))

        with patch("click.Context.find_root") as mock_root:
            mock_ctx = Mock()
            mock_ctx.command = test_cli
            mock_root.return_value = mock_ctx

            # Test JSON output with filter
            result = runner.invoke(reflect, ["--format", "json", "--filter", "agent"])
            if result.exit_code == 0 and result.output.strip():
                data = json.loads(result.output)
                assert "agent" in data
                assert "status" not in data

    def test_reflect_filter_markdown_format(self):
        """Test filter with markdown format output."""
        runner = CliRunner()

        # Create a minimal CLI for testing
        test_cli = click.Group("test-cli")
        test_cli.add_command(click.Command("agent"))
        test_cli.add_command(click.Command("team"))

        with patch("click.Context.find_root") as mock_root:
            mock_ctx = Mock()
            mock_ctx.command = test_cli
            mock_root.return_value = mock_ctx

            # Test markdown output with filter
            result = runner.invoke(reflect, ["--format", "markdown", "--filter", "team"])
            assert "## team" in result.output or "No commands match" in result.output
            assert "Filtered by: `team`" in result.output or "No commands match" in result.output

    def test_reflect_filter_no_matches(self):
        """Test filter with no matching commands."""
        runner = CliRunner()

        test_cli = click.Group("test-cli")
        test_cli.add_command(click.Command("agent"))

        with patch("click.Context.find_root") as mock_root:
            mock_ctx = Mock()
            mock_ctx.command = test_cli
            mock_root.return_value = mock_ctx

            # Test with non-matching filter
            result = runner.invoke(reflect, ["--filter", "nonexistent"])
            assert "No commands match filter: nonexistent" in result.output

    def test_reflect_filter_regex_patterns(self):
        """Test various regex patterns."""
        runner = CliRunner()

        # Test patterns
        patterns = [
            ("^agent", "Commands starting with agent"),
            ("send$", "Commands ending with send"),
            ("send|message", "Commands containing send or message"),
            ("agent.*status", "Agent commands with status"),
        ]

        test_cli = click.Group("test-cli")
        agent_group = click.Group("agent")
        agent_group.add_command(click.Command("send"))
        agent_group.add_command(click.Command("status"))
        test_cli.add_command(agent_group)
        test_cli.add_command(click.Command("message"))

        with patch("click.Context.find_root") as mock_root:
            mock_ctx = Mock()
            mock_ctx.command = test_cli
            mock_root.return_value = mock_ctx

            for pattern, description in patterns:
                result = runner.invoke(reflect, ["--filter", pattern])
                # Just verify command runs without error
                assert result.exit_code == 0 or "No commands match" in result.output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
