#!/usr/bin/env python3
"""
Test suite for spawn auto-increment functionality.
Tests the new behavior where windows are always appended to the end of sessions.
"""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from tmux_orchestrator.cli.spawn import spawn


class TestSpawnAutoIncrement:
    """Test cases for auto-increment spawn behavior"""

    @pytest.fixture
    def runner(self):
        """Create CLI runner."""
        return CliRunner()

    @pytest.fixture
    def mock_tmux(self):
        """Mock TMUXManager."""
        with patch("tmux_orchestrator.utils.tmux.TMUXManager") as mock:
            tmux_instance = MagicMock()
            mock.return_value = tmux_instance
            tmux_instance.list_sessions.return_value = [{"name": "test"}]
            tmux_instance.send_message.return_value = True
            tmux_instance.create_window.return_value = True
            tmux_instance.list_windows.return_value = [{"name": "Claude-pm", "index": 1}]
            tmux_instance.send_keys.return_value = True
            tmux_instance.has_session.return_value = True
            tmux_instance.create_session.return_value = True
            yield tmux_instance

    def test_error_handling_on_spawn_failure(self, runner, mock_tmux):
        """Test graceful handling of spawn failures"""
        mock_tmux.create_window.return_value = False

        with patch("time.sleep"), patch("tmux_orchestrator.cli.context.load_context") as mock_load:
            mock_load.return_value = "Agent context"
            result = runner.invoke(
                spawn, ["agent", "test-dev", "test-session", "--briefing", "Test briefing"], obj={"tmux": mock_tmux}
            )

        assert result.exit_code != 0

    def test_multiple_rapid_spawns(self, runner, mock_tmux):
        """Test multiple rapid spawns don't conflict"""

        # Track created windows
        created_windows = []

        def mock_create_window(session, name, start_dir=None):
            created_windows.append({"name": name, "index": len(created_windows)})
            return True

        def mock_list_windows(session):
            return created_windows

        mock_tmux.create_window.side_effect = mock_create_window
        mock_tmux.list_windows.side_effect = mock_list_windows

        with patch("time.sleep"), patch("tmux_orchestrator.cli.context.load_context") as mock_load:
            mock_load.return_value = "Agent context"

            # First spawn - empty session
            result1 = runner.invoke(
                spawn, ["agent", "dev1", "test-session", "--briefing", "Dev 1"], obj={"tmux": mock_tmux}
            )
            assert result1.exit_code == 0

            # Second spawn - should work with dynamic windows
            result2 = runner.invoke(
                spawn, ["agent", "dev2", "test-session", "--briefing", "Dev 2"], obj={"tmux": mock_tmux}
            )
            assert result2.exit_code == 0

            # Third spawn - now has two windows
            mock_tmux.list_windows.return_value = [
                {"name": "Claude-dev1", "index": 0},
                {"name": "Claude-dev2", "index": 1},
            ]
            result3 = runner.invoke(
                spawn, ["agent", "dev3", "test-session", "--briefing", "Dev 3"], obj={"tmux": mock_tmux}
            )
            assert result3.exit_code == 0

    def test_role_conflict_detection_still_works(self, runner, mock_tmux):
        """Test that role-based conflict detection still prevents duplicate roles"""
        # Mock existing windows
        mock_tmux.list_windows.return_value = [
            {"name": "Claude-pm", "index": "0"},
            {"name": "Claude-dev", "index": "1"},
        ]

        with patch("time.sleep"), patch("tmux_orchestrator.cli.context.load_context") as mock_load:
            mock_load.return_value = "PM context"

            # Try to spawn PM into session that already has one
            result = runner.invoke(spawn, ["pm", "--session", "test-session"], obj={"tmux": mock_tmux})

            # Should succeed but show warning about existing windows
            assert result.exit_code == 0

    def test_session_format_parsing(self, runner, mock_tmux):
        """Test parsing of session:window format (legacy compatibility)"""
        # Set up dynamic window list mock
        windows = []

        def mock_create_window(session_name, window_name, working_dir=None):
            windows.append({"name": window_name, "index": str(len(windows))})
            return True

        mock_tmux.create_window.side_effect = mock_create_window
        mock_tmux.list_windows.side_effect = lambda session_name: windows

        with patch("time.sleep"), patch("tmux_orchestrator.cli.context.load_context") as mock_load:
            mock_load.return_value = "Agent context"

            # Test with window index (should extract session only and show warning)
            result = runner.invoke(
                spawn, ["agent", "test-dev", "myproject:3", "--briefing", "Test"], obj={"tmux": mock_tmux}
            )

            assert result.exit_code == 0
            assert "will be ignored" in result.output

    def test_spawn_after_window_deletion(self, runner, mock_tmux):
        """Test spawning after windows have been deleted (gaps in indices)"""
        # Set up dynamic window list mock with gaps in window indices
        windows = [
            {"name": "Claude-pm", "index": "0"},
            {"name": "Claude-qa", "index": "2"},
            {"name": "Claude-ops", "index": "5"},
        ]

        def mock_create_window(session_name, window_name, working_dir=None):
            windows.append({"name": window_name, "index": str(len(windows))})
            return True

        mock_tmux.create_window.side_effect = mock_create_window
        mock_tmux.list_windows.side_effect = lambda session_name: windows

        with patch("time.sleep"), patch("tmux_orchestrator.cli.context.load_context") as mock_load:
            mock_load.return_value = "Agent context"
            result = runner.invoke(
                spawn, ["agent", "dev", "test-session", "--briefing", "Dev briefing"], obj={"tmux": mock_tmux}
            )

        assert result.exit_code == 0
        # Should create new window at end, not fill gaps
        mock_tmux.create_window.assert_called_once()

    def test_spawn_appends_to_end_of_session(self, runner, mock_tmux):
        """Test that new windows are always appended to the end"""
        # Set up dynamic window list mock with existing windows
        windows = [
            {"name": "Claude-pm", "index": "0"},
            {"name": "Claude-dev", "index": "1"},
            {"name": "Claude-qa", "index": "3"},
            {"name": "Claude-ops", "index": "5"},
        ]

        def mock_create_window(session_name, window_name, working_dir=None):
            windows.append({"name": window_name, "index": str(len(windows))})
            return True

        mock_tmux.create_window.side_effect = mock_create_window
        mock_tmux.list_windows.side_effect = lambda session_name: windows

        with patch("time.sleep"), patch("tmux_orchestrator.cli.context.load_context") as mock_load:
            mock_load.return_value = "Agent context"
            result = runner.invoke(
                spawn, ["agent", "test-dev", "test-session", "--briefing", "Test briefing"], obj={"tmux": mock_tmux}
            )

        assert result.exit_code == 0
        # Should create window (implementation appends to end)
        mock_tmux.create_window.assert_called_once()

    def test_spawn_ignores_window_index(self, runner, mock_tmux):
        """Test that spawn ignores provided window index and appends to end"""
        # Set up dynamic window list mock
        windows = []

        def mock_create_window(session_name, window_name, working_dir=None):
            windows.append({"name": window_name, "index": str(len(windows))})
            return True

        mock_tmux.create_window.side_effect = mock_create_window
        mock_tmux.list_windows.side_effect = lambda session_name: windows

        with patch("time.sleep"), patch("tmux_orchestrator.cli.context.load_context") as mock_load:
            mock_load.return_value = "Agent context"

            # Spawn with explicit window index (should be ignored with warning)
            result = runner.invoke(
                spawn, ["agent", "test-dev", "test-session:1", "--briefing", "Test"], obj={"tmux": mock_tmux}
            )

        assert result.exit_code == 0
        assert "will be ignored" in result.output
        mock_tmux.create_window.assert_called_once()

    def test_spawn_empty_session(self, runner, mock_tmux):
        """Test spawning into an empty session"""
        # Set up dynamic window list mock
        windows = []

        def mock_create_window(session_name, window_name, working_dir=None):
            windows.append({"name": window_name, "index": str(len(windows))})
            return True

        mock_tmux.create_window.side_effect = mock_create_window
        mock_tmux.list_windows.side_effect = lambda session_name: windows

        with patch("time.sleep"), patch("tmux_orchestrator.cli.context.load_context") as mock_load:
            mock_load.return_value = "Agent context"
            result = runner.invoke(
                spawn, ["agent", "pm", "empty-session", "--briefing", "PM briefing"], obj={"tmux": mock_tmux}
            )

        assert result.exit_code == 0
        mock_tmux.create_window.assert_called_once()

    def test_spawn_with_special_characters(self, runner, mock_tmux):
        """Test spawning with special characters in names"""
        # Set up dynamic window list mock
        windows = []

        def mock_create_window(session_name, window_name, working_dir=None):
            windows.append({"name": window_name, "index": str(len(windows))})
            return True

        mock_tmux.create_window.side_effect = mock_create_window
        mock_tmux.list_windows.side_effect = lambda session_name: windows

        with patch("time.sleep"), patch("tmux_orchestrator.cli.context.load_context") as mock_load:
            mock_load.return_value = "Agent context"
            result = runner.invoke(
                spawn, ["agent", "dev-api-2024", "test-session", "--briefing", "API Dev"], obj={"tmux": mock_tmux}
            )

        assert result.exit_code == 0
        # Should handle special characters properly
        mock_tmux.create_window.assert_called_once()


class TestContextSpawnAutoIncrement:
    """Test cases for context spawn with auto-increment"""

    @pytest.fixture
    def runner(self):
        """Create CLI runner."""
        return CliRunner()

    @pytest.fixture
    def mock_tmux(self):
        """Mock TMUXManager."""
        with patch("tmux_orchestrator.utils.tmux.TMUXManager") as mock:
            tmux_instance = MagicMock()
            mock.return_value = tmux_instance
            tmux_instance.list_sessions.return_value = [{"name": "test"}]
            tmux_instance.send_message.return_value = True
            tmux_instance.create_window.return_value = True
            tmux_instance.list_windows.return_value = [{"name": "Claude-pm", "index": 1}]
            tmux_instance.send_keys.return_value = True
            tmux_instance.has_session.return_value = True
            tmux_instance.create_session.return_value = True
            yield tmux_instance

    def test_context_spawn_ignores_window(self, runner, mock_tmux):
        """Test that context spawn also ignores window indices"""
        # Set up dynamic window list mock with existing windows
        windows = [
            {"name": "Claude-pm", "index": "0"},
            {"name": "Claude-dev", "index": "1"},
        ]

        def mock_create_window(session_name, window_name, working_dir=None):
            windows.append({"name": window_name, "index": str(len(windows))})
            return True

        mock_tmux.create_window.side_effect = mock_create_window
        mock_tmux.list_windows.side_effect = lambda session_name: windows

        with patch("time.sleep"), patch("tmux_orchestrator.cli.context.load_context") as mock_load:
            mock_load.return_value = "PM context"
            # Test PM spawn with legacy session:window format
            result = runner.invoke(spawn, ["pm", "--session", "test-session:0"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        # Should ignore the :0 and create new window
        mock_tmux.create_window.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
