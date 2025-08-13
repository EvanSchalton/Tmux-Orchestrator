"""Integration tests for PM escalation system."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from tmux_orchestrator.core.monitor import IdleMonitor


class TestPMEscalationIntegration:
    """Integration tests for full PM escalation cycle."""

    @pytest.fixture
    def mock_tmux(self):
        """Create mock TMUXManager with realistic responses."""
        tmux = MagicMock()
        tmux.list_windows.return_value = [
            "test-session:0",  # PM
            "test-session:1",  # Dev 1
            "test-session:2",  # Dev 2
            "test-session:3",  # QA
        ]
        return tmux

    @pytest.fixture
    def monitor(self, mock_tmux):
        """Create IdleMonitor instance."""
        return IdleMonitor(mock_tmux)

    def test_full_escalation_cycle_to_pm_kill(self, monitor, mock_tmux, monkeypatch):
        """Test complete escalation cycle from idle detection to PM kill."""
        # Mock time progression
        base_time = datetime.now()
        times = [
            base_time,  # Initial
            base_time + timedelta(minutes=1),  # Still under threshold
            base_time + timedelta(minutes=3, seconds=5),  # 3 min threshold
            base_time + timedelta(minutes=5, seconds=5),  # 5 min threshold
            base_time + timedelta(minutes=8, seconds=5),  # 8 min kill threshold
        ]
        time_iter = iter(times)

        def mock_now():
            return next(time_iter)

        monkeypatch.setattr("tmux_orchestrator.core.monitor.datetime", type("MockDatetime", (), {"now": mock_now}))

        # Setup mock capture_pane to return idle state
        idle_content = """
Human: waiting for task
Assistant: I'm ready to help. What would you like me to work on?
Human:
"""
        mock_tmux.capture_pane.return_value = idle_content

        # Mock _find_agent_sessions to return our test agents
        with patch.object(
            monitor,
            "_find_agent_sessions",
            return_value={
                "test-session:0": "pm",
                "test-session:1": "dev",
                "test-session:2": "dev",
                "test-session:3": "qa",
            },
        ):
            # Mock logger
            with patch("tmux_orchestrator.core.monitor.logging.getLogger") as mock_get_logger:
                mock_logger = MagicMock()
                mock_get_logger.return_value = mock_logger

                # Track notifications
                all_notifications = []

                def capture_notification(pm_notifications, session, message, tmux):
                    all_notifications.append((session, message))
                    if session not in pm_notifications:
                        pm_notifications[session] = []
                    pm_notifications[session].append(message)

                with patch.object(monitor, "_collect_notification", side_effect=capture_notification):
                    # Cycle 1: Initial detection (time = base_time)
                    monitor._monitor_cycle()

                    # Verify team became idle
                    assert "test-session" in monitor._team_idle_at
                    assert monitor._team_idle_at["test-session"] is not None

                    # Cycle 2: Under threshold (time = base_time + 1 min)
                    monitor._monitor_cycle()

                    # No escalation yet
                    assert len(all_notifications) == 0

                    # Cycle 3: 3 minute threshold (time = base_time + 3 min)
                    monitor._monitor_cycle()

                    # Verify 3-min escalation sent
                    assert len(all_notifications) == 1
                    assert "IDLE TEAM ALERT (3 min)" in all_notifications[0][1]

                    # Cycle 4: 5 minute threshold (time = base_time + 5 min)
                    monitor._monitor_cycle()

                    # Verify 5-min escalation sent
                    assert len(all_notifications) == 2
                    assert "CRITICAL: TEAM IDLE (5 min)" in all_notifications[1][1]

                    # Cycle 5: 8 minute kill threshold (time = base_time + 8 min)
                    monitor._monitor_cycle()

                    # Verify PM kill was attempted
                    mock_tmux.kill_window.assert_called_once_with("test-session:0")
                    mock_logger.critical.assert_called_with("PM test-session:0 unresponsive for 8min - killing PM")

    def test_pm_recovery_after_kill(self, monitor, mock_tmux):
        """Test that system recovers properly after PM is killed."""
        # Setup initial idle state with PM marked for kill
        monitor._idle_agents = {
            "test-session:0": datetime.now() - timedelta(minutes=9),
            "test-session:1": datetime.now() - timedelta(minutes=9),
        }
        monitor._team_idle_at = {"test-session": datetime.now() - timedelta(minutes=9)}

        # Mock successful kill
        mock_tmux.kill_window.return_value = True

        with patch("tmux_orchestrator.core.monitor.logging.getLogger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            pm_notifications = {}
            agents = ["test-session:0", "test-session:1"]

            # Execute team idleness check
            monitor._check_team_idleness(mock_tmux, agents, mock_logger, pm_notifications)

            # Verify PM was killed
            mock_tmux.kill_window.assert_called_once_with("test-session:0")

            # Verify team idle tracking was reset
            assert monitor._team_idle_at["test-session"] is None

            # Simulate new PM spawning and team becoming active
            monitor._idle_agents.clear()
            new_agents = ["test-session:0", "test-session:1"]  # New PM in window 0

            # Next check should not escalate
            monitor._check_team_idleness(mock_tmux, new_agents, mock_logger, pm_notifications)

            # Verify no new escalations
            assert "test-session" not in monitor._team_idle_at or monitor._team_idle_at["test-session"] is None

    def test_escalation_with_mixed_agent_states(self, monitor, mock_tmux):
        """Test escalation behavior with some agents active and some idle."""
        with patch("tmux_orchestrator.core.monitor.logging.getLogger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            # Test 1: All agents idle - should escalate
            all_agents = ["test-session:0", "test-session:1", "test-session:2"]
            monitor._idle_agents = {agent: datetime.now() for agent in all_agents}
            monitor._team_idle_at = {"test-session": datetime.now() - timedelta(minutes=3, seconds=5)}

            pm_notifications = {}
            monitor._check_team_idleness(mock_tmux, all_agents, mock_logger, pm_notifications)

            # Should have escalation
            assert "test-session:0" in monitor._pm_escalation_history

            # Test 2: One agent becomes active - should reset
            monitor._idle_agents.pop("test-session:1")  # Agent 1 is now active

            pm_notifications = {}
            monitor._check_team_idleness(mock_tmux, all_agents, mock_logger, pm_notifications)

            # Should reset tracking
            assert monitor._team_idle_at["test-session"] is None
            assert "test-session:0" not in monitor._pm_escalation_history

    def test_notification_collection_and_delivery(self, monitor, mock_tmux):
        """Test that notifications are properly collected and would be delivered."""
        # Setup multiple sessions with different idle times
        sessions = {
            "session1": ["session1:0", "session1:1"],
            "session2": ["session2:0", "session2:1"],
            "session3": ["session3:0", "session3:1"],
        }

        all_agents = []
        for agents in sessions.values():
            all_agents.extend(agents)
            for agent in agents:
                monitor._idle_agents[agent] = datetime.now()

        # Set different idle times
        monitor._team_idle_at = {
            "session1": datetime.now() - timedelta(minutes=3, seconds=5),  # 3 min
            "session2": datetime.now() - timedelta(minutes=5, seconds=5),  # 5 min
            "session3": datetime.now() - timedelta(minutes=1),  # 1 min (no escalation)
        }

        with patch("tmux_orchestrator.core.monitor.logging.getLogger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            pm_notifications = {}
            monitor._check_team_idleness(mock_tmux, all_agents, mock_logger, pm_notifications)

            # Check notifications were collected
            assert len(pm_notifications) >= 2  # At least session1 and session2

            # Verify escalation history
            assert "session1:0" in monitor._pm_escalation_history
            assert 3 in monitor._pm_escalation_history["session1:0"]

            assert "session2:0" in monitor._pm_escalation_history
            assert 5 in monitor._pm_escalation_history["session2:0"]

            # Session3 should not have escalation (under threshold)
            assert "session3:0" not in monitor._pm_escalation_history

    @pytest.mark.parametrize(
        "threshold,expected_message_fragment",
        [
            (3, "IDLE TEAM ALERT"),
            (5, "CRITICAL: TEAM IDLE"),
        ],
    )
    def test_escalation_message_content(self, monitor, mock_tmux, threshold, expected_message_fragment):
        """Test that escalation messages contain expected content."""
        agents = ["test-session:0", "test-session:1"]
        monitor._idle_agents = {agent: datetime.now() for agent in agents}
        monitor._team_idle_at = {"test-session": datetime.now() - timedelta(minutes=threshold, seconds=5)}

        with patch("tmux_orchestrator.core.monitor.logging.getLogger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            collected_messages = []

            def capture_notification(pm_notifications, session, message, tmux):
                collected_messages.append(message)
                if session not in pm_notifications:
                    pm_notifications[session] = []
                pm_notifications[session].append(message)

            with patch.object(monitor, "_collect_notification", side_effect=capture_notification):
                pm_notifications = {}
                monitor._check_team_idleness(mock_tmux, agents, mock_logger, pm_notifications)

                # Verify message content
                assert len(collected_messages) == 1
                assert expected_message_fragment in collected_messages[0]

                # Verify message includes helpful instructions
                if threshold == 3:
                    assert "Check your team plan" in collected_messages[0]
                    assert "tmux-orc context show pm" in collected_messages[0]
                elif threshold == 5:
                    assert "rehydrate your context" in collected_messages[0]
