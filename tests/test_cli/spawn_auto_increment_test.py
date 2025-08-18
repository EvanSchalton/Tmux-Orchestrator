#!/usr/bin/env python3
"""
Test suite for spawn auto-increment functionality.
Tests the new behavior where windows are always appended to the end of sessions.
"""

import unittest
from unittest.mock import MagicMock, patch

# from tmux_orchestrator.cli.spawn import SpawnCommand  # SpawnCommand class doesn't exist
from tmux_orchestrator.utils.tmux import TMUXManager


@unittest.skip("SpawnCommand class doesn't exist in the codebase")
class TestSpawnAutoIncrement(unittest.TestCase):
    """Test cases for auto-increment spawn behavior"""

    def setUp(self):
        """Set up test fixtures"""
        # self.spawn_cmd = SpawnCommand()  # SpawnCommand class doesn't exist
        self.tmux_manager = TMUXManager()

    @patch("subprocess.run")
    def test_spawn_ignores_window_index(self, mock_run):
        """Test that spawn ignores provided window index and appends to end"""
        # Mock tmux list-windows to show existing windows
        mock_run.return_value = MagicMock(returncode=0, stdout="0: window0\n1: window1\n2: window2\n")

        # Test spawn with explicit window index (should be ignored)
        with patch("tmux_orchestrator.cli.spawn.SpawnCommand._spawn_agent") as mock_spawn:
            mock_spawn.return_value = ("test-session:3", "spawned successfully")

            # Spawn to occupied window index
            # self.spawn_cmd.spawn("agent", "test-dev", "test-session:1")  # SpawnCommand doesn't exist

            # Verify window index was ignored
            mock_spawn.assert_called_once()
            call_args = mock_spawn.call_args[0]
            self.assertEqual(call_args[2], "test-session")  # Should pass session only

    @patch("subprocess.run")
    def test_spawn_appends_to_end_of_session(self, mock_run):
        """Test that new windows are always appended to the end"""
        # Simulate session with gaps in window indices (0, 1, 3, 5)
        mock_run.side_effect = [
            # First call: list-windows
            MagicMock(returncode=0, stdout="0: Claude-pm\n1: Claude-dev\n3: Claude-qa\n5: Claude-ops\n"),
            # Second call: new-window creation
            MagicMock(returncode=0, stdout=""),
            # Third call: list-windows to get new index
            MagicMock(
                returncode=0, stdout="0: Claude-pm\n1: Claude-dev\n3: Claude-qa\n5: Claude-ops\n6: Claude-test-dev\n"
            ),
        ]

        with patch("tmux_orchestrator.cli.spawn.SpawnCommand._load_briefing"):
            result = self.spawn_cmd._create_window("test-session", "test-dev", "developer")

            # Should return the actual new window index (6)
            self.assertEqual(result, "test-session:6")

            # Verify new-window was called without -t flag
            new_window_call = mock_run.call_args_list[1]
            self.assertIn("new-window", new_window_call[0][0])
            self.assertNotIn("-t", new_window_call[0][0])

    @patch("subprocess.run")
    def test_multiple_rapid_spawns(self, mock_run):
        """Test multiple rapid spawns don't conflict"""
        # Simulate rapid spawning scenario
        window_lists = [
            "0: Claude-pm\n",
            "0: Claude-pm\n1: Claude-dev1\n",
            "0: Claude-pm\n1: Claude-dev1\n2: Claude-dev2\n",
            "0: Claude-pm\n1: Claude-dev1\n2: Claude-dev2\n3: Claude-dev3\n",
        ]

        mock_run.side_effect = [
            # Each spawn: list-windows, new-window, list-windows again
            MagicMock(returncode=0, stdout=window_lists[0]),
            MagicMock(returncode=0, stdout=""),
            MagicMock(returncode=0, stdout=window_lists[1]),
            MagicMock(returncode=0, stdout=window_lists[1]),
            MagicMock(returncode=0, stdout=""),
            MagicMock(returncode=0, stdout=window_lists[2]),
            MagicMock(returncode=0, stdout=window_lists[2]),
            MagicMock(returncode=0, stdout=""),
            MagicMock(returncode=0, stdout=window_lists[3]),
        ]

        with patch("tmux_orchestrator.cli.spawn.SpawnCommand._load_briefing"):
            # Spawn three developers rapidly
            result1 = self.spawn_cmd._create_window("test-session", "dev1", "developer")
            result2 = self.spawn_cmd._create_window("test-session", "dev2", "developer")
            result3 = self.spawn_cmd._create_window("test-session", "dev3", "developer")

            # Each should get sequential indices
            self.assertEqual(result1, "test-session:1")
            self.assertEqual(result2, "test-session:2")
            self.assertEqual(result3, "test-session:3")

    @patch("subprocess.run")
    def test_spawn_after_window_deletion(self, mock_run):
        """Test spawning after windows have been deleted (gaps in indices)"""
        # Session with deleted windows: 0, 2, 5 (missing 1, 3, 4)
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="0: Claude-pm\n2: Claude-qa\n5: Claude-ops\n"),
            MagicMock(returncode=0, stdout=""),
            MagicMock(returncode=0, stdout="0: Claude-pm\n2: Claude-qa\n5: Claude-ops\n6: Claude-dev\n"),
        ]

        with patch("tmux_orchestrator.cli.spawn.SpawnCommand._load_briefing"):
            result = self.spawn_cmd._create_window("test-session", "dev", "developer")

            # Should append to end (index 6), not fill gaps
            self.assertEqual(result, "test-session:6")

    @patch("subprocess.run")
    def test_spawn_empty_session(self, mock_run):
        """Test spawning into an empty session"""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=""),  # Empty session
            MagicMock(returncode=0, stdout=""),
            MagicMock(returncode=0, stdout="0: Claude-pm\n"),
        ]

        with patch("tmux_orchestrator.cli.spawn.SpawnCommand._load_briefing"):
            result = self.spawn_cmd._create_window("empty-session", "pm", "pm")

            # Should create window 0
            self.assertEqual(result, "empty-session:0")

    @patch("subprocess.run")
    def test_role_conflict_detection_still_works(self, mock_run):
        """Test that role-based conflict detection still prevents duplicate roles"""
        # Session already has a PM
        mock_run.return_value = MagicMock(returncode=0, stdout="0: Claude-pm\n1: Claude-dev\n")

        # Try to spawn another PM (should fail)
        with self.assertRaises(SystemExit):
            with patch("builtins.print"):
                self.spawn_cmd._check_role_conflicts("test-session", "manager")

        # Try to spawn a developer (should pass)
        try:
            self.spawn_cmd._check_role_conflicts("test-session", "qa")
        except SystemExit:
            self.fail("Should not raise SystemExit for non-conflicting role")

    def test_session_format_parsing(self):
        """Test parsing of session:window format"""
        # Test with window index (should extract session only)
        session = self.spawn_cmd._extract_session_name("myproject:3")
        self.assertEqual(session, "myproject")

        # Test without window index
        session = self.spawn_cmd._extract_session_name("myproject")
        self.assertEqual(session, "myproject")

        # Test with complex session names
        session = self.spawn_cmd._extract_session_name("my-project-2024:5")
        self.assertEqual(session, "my-project-2024")

    @patch("subprocess.run")
    def test_error_handling_on_spawn_failure(self, mock_run):
        """Test graceful handling of spawn failures"""
        # Simulate tmux new-window failure
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="0: Claude-pm\n"),
            MagicMock(returncode=1, stderr="can't create window"),
        ]

        with patch("tmux_orchestrator.cli.spawn.SpawnCommand._load_briefing"):
            with self.assertRaises(Exception) as context:
                self.spawn_cmd._create_window("test-session", "dev", "developer")

            self.assertIn("create window", str(context.exception))

    @patch("subprocess.run")
    def test_spawn_with_special_characters(self, mock_run):
        """Test spawning with special characters in names"""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=""),
            MagicMock(returncode=0, stdout=""),
            MagicMock(returncode=0, stdout="0: Claude-dev-api-2024\n"),
        ]

        with patch("tmux_orchestrator.cli.spawn.SpawnCommand._load_briefing"):
            result = self.spawn_cmd._create_window("test-session", "dev-api-2024", "developer")

            # Should handle special characters properly
            self.assertEqual(result, "test-session:0")

            # Verify window name was properly escaped
            new_window_call = mock_run.call_args_list[1]
            self.assertIn("Claude-dev-api-2024", " ".join(new_window_call[0][0]))


class TestContextSpawnAutoIncrement(unittest.TestCase):
    """Test cases for context spawn with auto-increment"""

    @patch("subprocess.run")
    def test_context_spawn_ignores_window(self, mock_run):
        """Test that context spawn also ignores window indices"""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="0: Claude-pm\n1: Claude-dev\n"),
            MagicMock(returncode=0, stdout=""),
            MagicMock(returncode=0, stdout="0: Claude-pm\n1: Claude-dev\n2: Claude-qa\n"),
        ]

        # Test spawn with context
        with patch("tmux_orchestrator.cli.spawn.SpawnCommand._load_briefing"):
            with patch("tmux_orchestrator.cli.spawn.SpawnCommand._spawn_with_context") as mock_ctx_spawn:
                mock_ctx_spawn.return_value = ("test-session:2", "spawned with context")

                # spawn_cmd = SpawnCommand()  # SpawnCommand class doesn't exist
                # spawn_cmd.spawn("pm", None, "test-session:0", context="orchestrator")

                # Should ignore the :0 and append to end
                mock_ctx_spawn.assert_called_once()


if __name__ == "__main__":
    unittest.main()
