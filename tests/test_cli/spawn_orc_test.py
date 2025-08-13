"""Tests for spawn-orc command."""

import subprocess
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from tmux_orchestrator.cli.spawn_orc import _command_exists, _get_terminal_command, spawn_orc


class TestSpawnOrc:
    """Test spawn-orc command functionality."""

    def test_spawn_orc_help(self):
        """Test help output."""
        runner = CliRunner()
        result = runner.invoke(spawn_orc, ["--help"])

        assert result.exit_code == 0
        assert "Launch Claude Code as an orchestrator" in result.output
        assert "--profile" in result.output
        assert "--terminal" in result.output
        assert "--no-launch" in result.output
        assert "--no-gui" in result.output

    def test_spawn_orc_no_launch(self):
        """Test --no-launch creates script without launching."""
        runner = CliRunner()

        with patch("tmux_orchestrator.cli.spawn_orc.Path.write_text") as mock_write:
            with patch("tmux_orchestrator.cli.spawn_orc.Path.chmod") as mock_chmod:
                result = runner.invoke(spawn_orc, ["--no-launch"])

        assert result.exit_code == 0
        assert "Startup script created at:" in result.output
        assert "/tmp/tmux-orc-startup.sh" in result.output
        mock_write.assert_called_once()
        mock_chmod.assert_called_once_with(0o755)

        # Check script content includes tmux-orc context show
        script_content = mock_write.call_args[0][0]
        assert "tmux-orc context show orchestrator" in script_content
        assert "claude --dangerously-skip-permissions" in script_content

    def test_spawn_orc_no_gui(self):
        """Test --no-gui runs in current terminal."""
        runner = CliRunner()

        with patch("time.sleep"):
            with patch("subprocess.run") as mock_run:
                result = runner.invoke(spawn_orc, ["--no-gui"])

        assert result.exit_code == 0
        assert "Running orchestrator in current terminal..." in result.output
        mock_run.assert_called_once()

        # Check the script was executed
        call_args = mock_run.call_args[0][0]
        assert "/tmp/tmux-orc-startup.sh" in call_args[0]

    def test_spawn_orc_with_profile(self):
        """Test --profile option is passed to claude command."""
        runner = CliRunner()

        with patch("tmux_orchestrator.cli.spawn_orc.Path.write_text") as mock_write:
            with patch("tmux_orchestrator.cli.spawn_orc.Path.chmod"):
                result = runner.invoke(spawn_orc, ["--no-launch", "--profile", "my-profile"])

        assert result.exit_code == 0

        # Check script content includes profile
        script_content = mock_write.call_args[0][0]
        assert "claude --profile my-profile --dangerously-skip-permissions" in script_content

    def test_spawn_orc_terminal_not_found(self):
        """Test error when terminal cannot be detected."""
        runner = CliRunner()

        with patch("tmux_orchestrator.cli.spawn_orc._get_terminal_command", return_value=None):
            result = runner.invoke(spawn_orc, [])

        assert result.exit_code == 1
        assert "Error: Could not detect terminal emulator" in result.output
        assert "Use --no-gui flag" in result.output
        assert "Specify --terminal explicitly" in result.output

    def test_spawn_orc_terminal_launch_success(self):
        """Test successful terminal launch."""
        runner = CliRunner()

        with patch(
            "tmux_orchestrator.cli.spawn_orc._get_terminal_command",
            return_value=["gnome-terminal", "--", "/tmp/tmux-orc-startup.sh"],
        ):
            with patch("subprocess.Popen") as mock_popen:
                with patch("tmux_orchestrator.cli.spawn_orc.Path.write_text"):
                    with patch("tmux_orchestrator.cli.spawn_orc.Path.chmod"):
                        result = runner.invoke(spawn_orc, [])

        assert result.exit_code == 0
        assert "Launching orchestrator in new" in result.output
        assert "Orchestrator terminal launched!" in result.output
        mock_popen.assert_called_once()

    def test_spawn_orc_terminal_launch_error(self):
        """Test error handling when terminal launch fails."""
        runner = CliRunner()

        with patch(
            "tmux_orchestrator.cli.spawn_orc._get_terminal_command",
            return_value=["gnome-terminal", "--", "/tmp/tmux-orc-startup.sh"],
        ):
            with patch("subprocess.Popen", side_effect=Exception("Launch failed")):
                with patch("tmux_orchestrator.cli.spawn_orc.Path.write_text"):
                    with patch("tmux_orchestrator.cli.spawn_orc.Path.chmod"):
                        result = runner.invoke(spawn_orc, [])

        assert result.exit_code == 1
        assert "Error launching terminal: Launch failed" in result.output
        assert "Manual launch instructions:" in result.output
        assert "OR use: spawn-orc --no-gui" in result.output


class TestTerminalDetection:
    """Test terminal detection functionality."""

    def test_command_exists_true(self):
        """Test _command_exists returns True for existing command."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert _command_exists("ls") is True
            mock_run.assert_called_once_with(["which", "ls"], capture_output=True, check=True)

    def test_command_exists_false(self):
        """Test _command_exists returns False for missing command."""
        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "which")):
            assert _command_exists("nonexistent") is False

    def test_get_terminal_command_explicit(self):
        """Test _get_terminal_command with explicit terminal."""
        # Known terminal
        cmd = _get_terminal_command("gnome-terminal", "/path/to/script")
        assert cmd == ["gnome-terminal", "--", "/path/to/script"]

        # Unknown terminal - uses generic format
        cmd = _get_terminal_command("myterm", "/path/to/script")
        assert cmd == ["myterm", "-e", "/path/to/script"]

    def test_get_terminal_command_auto_linux(self):
        """Test _get_terminal_command auto-detection on Linux."""
        with patch("sys.platform", "linux"):
            with patch("tmux_orchestrator.cli.spawn_orc._command_exists") as mock_exists:
                # Simulate gnome-terminal exists
                def command_exists_side_effect(cmd):
                    return cmd == "gnome-terminal"

                mock_exists.side_effect = command_exists_side_effect

                cmd = _get_terminal_command("auto", "/path/to/script")
                assert cmd == ["gnome-terminal", "--", "/path/to/script"]

    def test_get_terminal_command_auto_macos(self):
        """Test _get_terminal_command auto-detection on macOS."""
        with patch("sys.platform", "darwin"):
            with patch("tmux_orchestrator.cli.spawn_orc._command_exists", return_value=True):
                cmd = _get_terminal_command("auto", "/path/to/script")
                # Should prefer iTerm2 on macOS
                assert cmd == ["open", "-a", "iTerm", "/path/to/script"]

    def test_get_terminal_command_auto_none_found(self):
        """Test _get_terminal_command returns None when no terminal found."""
        with patch("sys.platform", "linux"):
            with patch("tmux_orchestrator.cli.spawn_orc._command_exists", return_value=False):
                cmd = _get_terminal_command("auto", "/path/to/script")
                assert cmd is None
