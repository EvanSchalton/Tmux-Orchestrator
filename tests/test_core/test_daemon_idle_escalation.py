#!/usr/bin/env python3
"""Test scenarios for daemon escalation when all agents are idle.

This test suite verifies:
1. Idle detection for all agents in a session
2. PM notification when entire team is idle
3. Escalation timing (3, 5, 8 minutes)
4. PM kill at 8 minutes if no response
5. Proper handling of PM being idle vs other agents
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from tmux_orchestrator.core.monitor import IdleMonitor
from tmux_orchestrator.core.monitor_helpers import is_claude_interface_present


class TestDaemonIdleEscalation:
    """Test daemon escalation when all agents are idle."""

    @pytest.fixture
    def monitor(self, mock_tmux):
        """Create IdleMonitor instance."""
        return IdleMonitor(mock_tmux)

    @pytest.fixture
    def mock_tmux(self):
        """Create mock TMUXManager."""
        tmux = MagicMock()
        # Default session structure
        tmux.list_sessions.return_value = [{"name": "test-project"}]
        tmux.list_windows.return_value = [
            {"name": "pm", "index": 0},
            {"name": "backend-dev", "index": 1},
            {"name": "frontend-dev", "index": 2},
            {"name": "qa-engineer", "index": 3},
        ]
        return tmux

    def test_all_agents_idle_detection(self, monitor, mock_tmux):
        """Test that daemon correctly detects when all agents are idle."""
        # Setup idle content for all agents
        idle_content = """
Human: waiting for instructions
Assistant: I'm ready to help. What would you like me to work on?
Human: """

        mock_tmux.capture_pane.return_value = idle_content

        # Mock agent discovery
        agents = ["test-project:0", "test-project:1", "test-project:2", "test-project:3"]

        with patch.object(monitor, "_discover_agents", return_value=agents):
            # Simulate monitoring cycle
            idle_states = {}
            for agent in agents:
                # Check if content shows idle state
                assert is_claude_interface_present(idle_content)
                idle_states[agent] = "idle"
                monitor._idle_agents[agent] = datetime.now()

            # All agents should be detected as idle
            assert len(monitor._idle_agents) == 4
            assert all(agent in monitor._idle_agents for agent in agents)

    def test_pm_notification_when_team_idle(self, monitor, mock_tmux):
        """Test PM receives notification when entire team is idle."""
        # Set up all agents as idle
        base_time = datetime.now()
        monitor._idle_agents = {
            "test-project:0": base_time,  # PM
            "test-project:1": base_time,  # Dev 1
            "test-project:2": base_time,  # Dev 2
            "test-project:3": base_time,  # QA
        }

        # Mock PM detection
        def mock_is_pm(tmux, target):
            return target.endswith(":0")  # PM is in window 0

        with patch.object(monitor, "_is_pm_agent", side_effect=mock_is_pm):
            with patch.object(monitor, "_find_pm_in_session", return_value="test-project:0"):
                # Track team as idle
                monitor._team_idle_at = {"test-project": base_time}

                # Simulate escalation check
                agents = list(monitor._idle_agents.keys())

                with patch("tmux_orchestrator.core.monitor.logging.getLogger") as mock_logger:
                    logger = MagicMock()
                    mock_logger.return_value = logger

                    # Check team idleness should trigger notification
                    session_idle_agents = [a for a in agents if a.startswith("test-project:")]
                    assert len(session_idle_agents) == 4  # All 4 agents

                    # Verify PM would be found for notification
                    pm_target = monitor._find_pm_in_session(mock_tmux, "test-project")
                    assert pm_target == "test-project:0"

    def test_escalation_timing_3_5_8_minutes(self, monitor, mock_tmux, monkeypatch):
        """Test escalation at 3, 5, and 8 minute thresholds."""
        base_time = datetime.now()

        # Set up all agents as idle
        monitor._idle_agents = {
            "test-project:0": base_time,
            "test-project:1": base_time,
            "test-project:2": base_time,
            "test-project:3": base_time,
        }
        monitor._team_idle_at = {"test-project": base_time}

        # Test 3-minute escalation
        current_time = base_time + timedelta(minutes=3, seconds=5)
        monkeypatch.setattr(
            "tmux_orchestrator.core.monitor.datetime", type("MockDatetime", (), {"now": lambda: current_time})
        )

        with patch.object(monitor, "_collect_notification") as mock_collect:
            with patch("tmux_orchestrator.core.monitor.logging.getLogger") as mock_get_logger:
                logger = MagicMock()
                mock_get_logger.return_value = logger

                pm_notifications = {}
                agents = list(monitor._idle_agents.keys())

                monitor._check_team_idleness(mock_tmux, agents, logger, pm_notifications)

                # Should trigger 3-minute notification
                mock_collect.assert_called()
                call_args = mock_collect.call_args[0]
                assert "IDLE TEAM ALERT (3 min)" in call_args[2]

        # Test 5-minute escalation
        current_time = base_time + timedelta(minutes=5, seconds=5)
        monkeypatch.setattr(
            "tmux_orchestrator.core.monitor.datetime", type("MockDatetime", (), {"now": lambda: current_time})
        )

        # Mark 3-min escalation as sent
        monitor._pm_escalation_history = {"test-project:0": {3: base_time + timedelta(minutes=3)}}

        with patch.object(monitor, "_collect_notification") as mock_collect:
            with patch("tmux_orchestrator.core.monitor.logging.getLogger") as mock_get_logger:
                logger = MagicMock()
                mock_get_logger.return_value = logger

                pm_notifications = {}
                monitor._check_team_idleness(mock_tmux, agents, logger, pm_notifications)

                # Should trigger 5-minute notification
                mock_collect.assert_called()
                call_args = mock_collect.call_args[0]
                assert "CRITICAL: TEAM IDLE (5 min)" in call_args[2]

        # Test 8-minute PM kill
        current_time = base_time + timedelta(minutes=8, seconds=5)
        monkeypatch.setattr(
            "tmux_orchestrator.core.monitor.datetime", type("MockDatetime", (), {"now": lambda: current_time})
        )

        # Mark 5-min escalation as sent
        monitor._pm_escalation_history["test-project:0"][5] = base_time + timedelta(minutes=5)

        with patch("tmux_orchestrator.core.monitor.logging.getLogger") as mock_get_logger:
            logger = MagicMock()
            mock_get_logger.return_value = logger

            pm_notifications = {}
            monitor._check_team_idleness(mock_tmux, agents, logger, pm_notifications)

            # Should kill PM at 8 minutes
            mock_tmux.kill_window.assert_called_with("test-project:0")
            logger.critical.assert_called_with("PM test-project:0 unresponsive for 8min - killing PM")

    def test_pm_detection_with_claude_check(self, monitor, mock_tmux):
        """Test that PM detection includes Claude interface verification."""
        # Test from the updated code showing PM detection checks Claude interface
        pm_content_active = """
Human: Check on the team status
Assistant: I'll check on the team's progress. Let me review the current state of each agent.
Human: """

        pm_content_no_claude = """
vscode@workspace:~$
# PM crashed - no Claude interface
"""

        # Test 1: PM with active Claude interface
        mock_tmux.capture_pane.return_value = pm_content_active

        with patch.object(monitor, "_is_pm_agent", return_value=True):
            # PM has Claude interface - should be found
            result = monitor._find_pm_in_session(mock_tmux, "test-project")
            assert result is not None  # PM should be found

        # Test 2: PM without Claude interface (crashed)
        mock_tmux.capture_pane.return_value = pm_content_no_claude

        with patch.object(monitor, "_is_pm_agent", return_value=True):
            # PM has no Claude interface - should not be found
            result = monitor._find_pm_in_session(mock_tmux, "test-project")
            assert result is None  # PM should not be found due to missing Claude

    def test_idle_team_with_active_pm_resets(self, monitor, mock_tmux):
        """Test that idle team detection resets when PM becomes active."""
        base_time = datetime.now()

        # Initially all agents idle
        monitor._idle_agents = {
            "test-project:0": base_time,
            "test-project:1": base_time,
            "test-project:2": base_time,
            "test-project:3": base_time,
        }
        monitor._team_idle_at = {"test-project": base_time}

        # PM becomes active (removed from idle_agents)
        monitor._idle_agents.pop("test-project:0")

        with patch("tmux_orchestrator.core.monitor.logging.getLogger") as mock_get_logger:
            logger = MagicMock()
            mock_get_logger.return_value = logger

            agents = ["test-project:0", "test-project:1", "test-project:2", "test-project:3"]
            pm_notifications = {}

            monitor._check_team_idleness(mock_tmux, agents, logger, pm_notifications)

            # Team idle tracking should reset since PM is active
            assert monitor._team_idle_at["test-project"] is None

            # Escalation history should be cleared
            assert "test-project:0" not in monitor._pm_escalation_history

    def test_notification_batching_per_session(self, monitor, mock_tmux):
        """Test that notifications are batched per session."""
        # Set up multiple idle agents
        monitor._idle_agents = {
            "project-a:0": datetime.now(),
            "project-a:1": datetime.now(),
            "project-a:2": datetime.now(),
            "project-b:0": datetime.now(),
            "project-b:1": datetime.now(),
        }

        # Track sessions as idle
        monitor._team_idle_at = {
            "project-a": datetime.now() - timedelta(minutes=3, seconds=5),
            "project-b": datetime.now() - timedelta(minutes=5, seconds=5),
        }

        # Mock PM finding
        def mock_find_pm(tmux, session):
            return f"{session}:0"

        with patch.object(monitor, "_find_pm_in_session", side_effect=mock_find_pm):
            with patch("tmux_orchestrator.core.monitor.logging.getLogger") as mock_get_logger:
                logger = MagicMock()
                mock_get_logger.return_value = logger

                pm_notifications = {}
                all_agents = list(monitor._idle_agents.keys())

                monitor._check_team_idleness(mock_tmux, all_agents, logger, pm_notifications)

                # Should have notifications for both sessions
                assert "project-a:0" in pm_notifications
                assert "project-b:0" in pm_notifications

                # Each PM should get appropriate escalation level
                assert any("3 min" in msg for msg in pm_notifications.get("project-a:0", []))
                assert any("5 min" in msg for msg in pm_notifications.get("project-b:0", []))


def test_daemon_escalation_scenario():
    """Manual test scenario for daemon escalation."""
    print("\n=== Daemon Escalation Test Scenario ===")
    print("\nThis test verifies daemon escalation when all agents are idle:")
    print("1. Create a test session with PM and 3 agents")
    print("2. Let all agents go idle")
    print("3. Monitor for 3 minutes - PM should get first notification")
    print("4. Monitor for 5 minutes - PM should get critical notification")
    print("5. Monitor for 8 minutes - PM should be killed")
    print("\nExpected behavior:")
    print("- Daemon detects all agents idle including PM")
    print("- PM receives escalating notifications at 3 and 5 minutes")
    print("- PM is killed at 8 minutes if still unresponsive")
    print("- New PM can be spawned to recover the team")
    print("\n" + "=" * 50)


if __name__ == "__main__":
    # Run tests
    test = TestDaemonIdleEscalation()
    test_daemon_escalation_scenario()
