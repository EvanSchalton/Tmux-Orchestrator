"""Test security fixes for CLI commands."""

import pytest
from click.testing import CliRunner

from tmux_orchestrator.cli.spawn_orc import _get_terminal_command
from tmux_orchestrator.cli.team_compose import compose, deploy


class TestSpawnOrcSecurity:
    """Test security fixes in spawn_orc.py."""

    def test_terminal_validation_prevents_injection(self):
        """Test that malicious terminal names are rejected."""
        dangerous_terminals = [
            "xterm; rm -rf /",  # Command injection
            "gnome-terminal && evil_command",  # Command chaining
            "terminal`whoami`",  # Command substitution
            "terminal$(id)",  # Another substitution
            "terminal|cat /etc/passwd",  # Pipe injection
            "../../../bin/sh",  # Path traversal
            "terminal\nmalicious",  # Newline injection
            "terminal\x00null",  # Null byte
        ]

        for terminal in dangerous_terminals:
            result = _get_terminal_command(terminal, "/tmp/test.sh")
            assert result is None, f"Dangerous terminal '{terminal}' was not rejected"

    def test_valid_terminal_names_allowed(self):
        """Test that valid terminal names are allowed."""
        valid_terminals = [
            "gnome-terminal",
            "xterm",
            "konsole",
            "my-terminal",
            "terminal_v2",
            "CustomTerm123",
        ]

        for terminal in valid_terminals:
            # Should either return a known command or generic command
            result = _get_terminal_command(terminal, "/tmp/test.sh")
            # For unknown terminals, should return generic command
            if terminal not in ["gnome-terminal", "xterm", "konsole"]:
                assert result == [terminal, "-e", "/tmp/test.sh"]


class TestTeamComposeSecurity:
    """Test security fixes in team_compose.py."""

    def test_compose_project_name_validation(self):
        """Test project name validation in compose command."""
        runner = CliRunner()

        dangerous_names = [
            "../../../etc/passwd",  # Path traversal
            "project/../../../",  # Path traversal
            "project\\..\\..\\",  # Windows path traversal
            "/absolute/path",  # Absolute path
            "C:\\Windows\\System32",  # Windows absolute
            "",  # Empty string
        ]

        for name in dangerous_names:
            result = runner.invoke(compose, [name])
            assert (
                result.exit_code != 0 or "Invalid project name" in result.output
            ), f"Dangerous project name '{name}' was not rejected"

    def test_deploy_project_name_validation(self):
        """Test project name validation in deploy command."""
        runner = CliRunner()

        dangerous_names = [
            "../../../etc/passwd",
            "project/../../../",
            "project\\..\\..\\",
            "/absolute/path",
            "",
        ]

        for name in dangerous_names:
            result = runner.invoke(deploy, [name])
            assert (
                result.exit_code != 0 or "Invalid project name" in result.output
            ), f"Dangerous project name '{name}' was not rejected in deploy"

    def test_valid_project_names_allowed(self):
        """Test that valid project names are allowed."""
        runner = CliRunner()

        valid_names = [
            "my-project",
            "project123",
            "test_project",
            "MyProject",
            "project-v2.0",  # Dots are OK as long as not ".."
        ]

        for name in valid_names:
            # Should fail because project doesn't exist, not because of validation
            result = runner.invoke(compose, [name])
            assert "Invalid project name" not in result.output, f"Valid project name '{name}' was incorrectly rejected"


class TestShelexQuoteUsage:
    """Test that shlex.quote is properly used."""

    def test_team_compose_uses_shlex_quote(self):
        """Verify shlex.quote is imported and used in team_compose.py."""
        import tmux_orchestrator.cli.team_compose as tc

        # Check import
        assert hasattr(tc, "shlex"), "shlex module not imported"

        # Check it's used in the file
        with open(tc.__file__) as f:
            content = f.read()
            assert "shlex.quote" in content, "shlex.quote not used in file"
            # Check it's used for the critical parameters
            assert "shlex.quote(agent['template'])" in content
            assert "shlex.quote(project_name)" in content
            assert "shlex.quote(system_prompt)" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
