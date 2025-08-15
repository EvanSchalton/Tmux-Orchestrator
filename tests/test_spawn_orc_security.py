#!/usr/bin/env python3
"""Test suite for spawn_orc.py security vulnerabilities."""

from unittest.mock import patch

from tmux_orchestrator.cli.spawn_orc import spawn_orc


class TestSpawnOrcSecurity:
    """Test security aspects of spawn_orc function."""

    @patch("tmux_orchestrator.cli.spawn_orc.Console")
    @patch("tmux_orchestrator.cli.spawn_orc.Path.write_text")
    @patch("tmux_orchestrator.cli.spawn_orc.Path.chmod")
    def test_shell_injection_via_profile(self, mock_chmod, mock_write, mock_console):
        """Test that malicious profile names cannot inject shell commands."""
        # Attempt shell injection via profile parameter
        malicious_profile = 'test"; rm -rf /tmp/*; echo "pwned'

        with patch("tmux_orchestrator.cli.spawn_orc.subprocess.run") as mock_run:
            spawn_orc(profile=malicious_profile, terminal="gnome-terminal", no_launch=True, no_gui=False)

            # Verify the script was written
            mock_write.assert_called_once()
            written_script = mock_write.call_args[0][0]

            # The vulnerability: Check if the malicious command would be executed
            # Currently, this test will FAIL because the profile is directly interpolated
            assert "rm -rf /tmp/*" not in written_script
            assert "pwned" not in written_script

    @patch("tmux_orchestrator.cli.spawn_orc.Console")
    @patch("tmux_orchestrator.cli.spawn_orc.Path.write_text")
    @patch("tmux_orchestrator.cli.spawn_orc.Path.chmod")
    def test_profile_with_special_chars(self, mock_chmod, mock_write, mock_console):
        """Test that profiles with special characters are handled safely."""
        # Test various special characters that could be problematic
        test_profiles = [
            "test$USER",
            "test`date`",
            "test$(whoami)",
            "test&&ls",
            "test||ls",
            "test;ls",
            "test\nls",
            "test|cat /etc/passwd",
            "test > /tmp/output",
            "test < /etc/passwd",
        ]

        for profile in test_profiles:
            mock_write.reset_mock()

            with patch("tmux_orchestrator.cli.spawn_orc.subprocess.run") as mock_run:
                spawn_orc(profile=profile, terminal="gnome-terminal", no_launch=True, no_gui=False)

                written_script = mock_write.call_args[0][0]

                # These should be properly escaped in the final command
                # Currently failing due to vulnerability
                assert not any(char in written_script for char in ["$USER", "`date`", "$(whoami)"])

    @patch("tmux_orchestrator.cli.spawn_orc.Console")
    @patch("tmux_orchestrator.cli.spawn_orc.Path.write_text")
    @patch("tmux_orchestrator.cli.spawn_orc.Path.chmod")
    def test_safe_profile_handling(self, mock_chmod, mock_write, mock_console):
        """Test that normal profiles work correctly."""
        safe_profile = "test-profile"

        with patch("tmux_orchestrator.cli.spawn_orc.subprocess.run") as mock_run:
            spawn_orc(profile=safe_profile, terminal="gnome-terminal", no_launch=True, no_gui=False)

            written_script = mock_write.call_args[0][0]

            # Should contain the profile in a safe way
            assert safe_profile in written_script
            assert "--profile" in written_script
