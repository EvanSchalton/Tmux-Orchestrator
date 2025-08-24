"""Unit tests for PM escalation timing logic."""

import logging
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from tmux_orchestrator.core.monitor import IdleMonitor
from tmux_orchestrator.core.monitor_helpers import NONRESPONSIVE_PM_ESCALATIONS_MINUTES, DaemonAction


class TestPMEscalationTiming:
    """Test PM escalation timing logic."""

    @pytest.fixture
    def mock_tmux(self):
        """Create mock TMUXManager."""
        tmux = MagicMock()
        tmux.list_windows.return_value = ["test-session:0", "test-session:1", "test-session:2"]
        tmux.capture_pane.return_value = "idle agent content"
        tmux.kill_window.return_value = True
        return tmux

    @pytest.fixture
    def monitor(self, mock_tmux):
        """Create IdleMonitor instance."""
        return IdleMonitor(mock_tmux)

    @pytest.fixture
    def mock_logger(self):
        """Create mock logger."""
        return MagicMock(spec=logging.Logger)

    def test_team_becomes_idle_sets_timestamp(self, monitor, mock_tmux, mock_logger):
        """Test that team idle timestamp is set when all agents become idle."""
        # Setup idle agents
        agents = ["test-session:0", "test-session:1", "test-session:2"]
        monitor._idle_agents = {agent: datetime.now() for agent in agents}

        # Clear any existing notifications
        pm_notifications = {}

        # Call check team idleness
        monitor._check_team_idleness(mock_tmux, agents, mock_logger, pm_notifications)

        # Verify team idle timestamp was set
        assert "test-session" in monitor._team_idle_at
        assert monitor._team_idle_at["test-session"] is not None
        assert isinstance(monitor._team_idle_at["test-session"], datetime)

    def test_3_minute_escalation_message(self, monitor, mock_tmux, mock_logger):
        """Test 3-minute escalation message is sent."""
        # Setup
        agents = ["test-session:0", "test-session:1", "test-session:2"]
        monitor._idle_agents = {agent: datetime.now() for agent in agents}

        # Set team idle time to 3+ minutes ago
        monitor._team_idle_at = {"test-session": datetime.now() - timedelta(minutes=3, seconds=5)}

        pm_notifications = {}

        # Call check team idleness
        monitor._check_team_idleness(mock_tmux, agents, mock_logger, pm_notifications)

        # Verify escalation was logged
        mock_logger.warning.assert_called_once()
        assert "3min escalation" in mock_logger.warning.call_args[0][0]

        # Verify escalation history was recorded
        assert "test-session:0" in monitor._pm_escalation_history
        assert 3 in monitor._pm_escalation_history["test-session:0"]

    def test_5_minute_escalation_message(self, monitor, mock_tmux, mock_logger):
        """Test 5-minute escalation message is sent."""
        # Setup
        agents = ["test-session:0", "test-session:1", "test-session:2"]
        monitor._idle_agents = {agent: datetime.now() for agent in agents}

        # Set team idle time to 5+ minutes ago
        monitor._team_idle_at = {"test-session": datetime.now() - timedelta(minutes=5, seconds=5)}

        # Mark 3-min escalation as already sent
        monitor._pm_escalation_history = {"test-session:0": {3: datetime.now() - timedelta(minutes=2)}}

        pm_notifications = {}

        # Call check team idleness
        monitor._check_team_idleness(mock_tmux, agents, mock_logger, pm_notifications)

        # Verify escalation was logged
        assert any("5min escalation" in str(call) for call in mock_logger.warning.call_args_list)

        # Verify escalation history was updated
        assert 5 in monitor._pm_escalation_history["test-session:0"]

    def test_8_minute_pm_kill(self, monitor, mock_tmux, mock_logger):
        """Test PM is killed at 8 minutes."""
        # Setup
        agents = ["test-session:0", "test-session:1", "test-session:2"]
        monitor._idle_agents = {agent: datetime.now() for agent in agents}

        # Set team idle time to 8+ minutes ago
        monitor._team_idle_at = {"test-session": datetime.now() - timedelta(minutes=8, seconds=5)}

        # Mark previous escalations as sent
        monitor._pm_escalation_history = {
            "test-session:0": {3: datetime.now() - timedelta(minutes=5), 5: datetime.now() - timedelta(minutes=3)}
        }

        pm_notifications = {}

        # Call check team idleness
        monitor._check_team_idleness(mock_tmux, agents, mock_logger, pm_notifications)

        # Verify PM kill was attempted
        mock_tmux.kill_window.assert_called_once_with("test-session:0")

        # Verify critical log
        mock_logger.critical.assert_called_once()
        assert "unresponsive for 8min" in mock_logger.critical.call_args[0][0]

        # Verify escalation history was cleared after successful kill
        assert "test-session:0" not in monitor._pm_escalation_history

        # Verify team idle was reset
        assert monitor._team_idle_at["test-session"] is None

    def test_escalation_history_prevents_duplicates(self, monitor, mock_tmux, mock_logger):
        """Test that escalation history prevents duplicate messages."""
        # Setup
        agents = ["test-session:0", "test-session:1", "test-session:2"]
        monitor._idle_agents = {agent: datetime.now() for agent in agents}

        # Set team idle time to 3+ minutes ago
        monitor._team_idle_at = {"test-session": datetime.now() - timedelta(minutes=3, seconds=5)}

        # Mark 3-min escalation as already sent
        monitor._pm_escalation_history = {"test-session:0": {3: datetime.now() - timedelta(seconds=30)}}

        pm_notifications = {}

        # Clear previous calls
        mock_logger.reset_mock()

        # Call check team idleness
        monitor._check_team_idleness(mock_tmux, agents, mock_logger, pm_notifications)

        # Verify no new warning was logged (duplicate prevention)
        mock_logger.warning.assert_not_called()

    def test_team_active_resets_tracking(self, monitor, mock_tmux, mock_logger):
        """Test that team becoming active resets all tracking."""
        # Setup initial idle state
        agents = ["test-session:0", "test-session:1", "test-session:2"]
        monitor._idle_agents = {agent: datetime.now() for agent in agents}
        monitor._team_idle_at = {"test-session": datetime.now() - timedelta(minutes=2)}
        monitor._pm_escalation_history = {"test-session:0": {3: datetime.now()}}

        # Make one agent active (remove from idle list)
        monitor._idle_agents.pop("test-session:1")

        pm_notifications = {}

        # Call check team idleness
        monitor._check_team_idleness(mock_tmux, agents, mock_logger, pm_notifications)

        # Verify team idle was reset
        assert monitor._team_idle_at["test-session"] is None

        # Verify escalation history was cleared
        assert "test-session:0" not in monitor._pm_escalation_history

        # Verify log message
        mock_logger.info.assert_called()
        assert "is active again" in mock_logger.info.call_args[0][0]

    def test_multiple_sessions_tracked_independently(self, monitor, mock_tmux, mock_logger):
        """Test that multiple sessions are tracked independently."""
        # Setup agents in different sessions
        session1_agents = ["session1:0", "session1:1"]
        session2_agents = ["session2:0", "session2:1"]
        all_agents = session1_agents + session2_agents

        # Make session1 idle 5 minutes ago, session2 idle 2 minutes ago
        monitor._idle_agents = {agent: datetime.now() for agent in all_agents}
        monitor._team_idle_at = {
            "session1": datetime.now() - timedelta(minutes=5, seconds=5),
            "session2": datetime.now() - timedelta(minutes=2),
        }

        pm_notifications = {}

        # Call check team idleness
        monitor._check_team_idleness(mock_tmux, all_agents, mock_logger, pm_notifications)

        # Verify session1 got escalation (5 min threshold)
        assert "session1:0" in monitor._pm_escalation_history
        assert 5 in monitor._pm_escalation_history["session1:0"]

        # Verify session2 didn't get escalation (under 3 min threshold)
        assert "session2:0" not in monitor._pm_escalation_history

    def test_pm_not_found_uses_find_pm_agent(self, monitor, mock_tmux, mock_logger):
        """Test that _find_pm_agent is used when PM not found in team."""
        # Setup agents without obvious PM (no :0 window, no 'pm' in name)
        agents = ["test-session:1", "test-session:2", "test-session:3"]
        monitor._idle_agents = {agent: datetime.now() for agent in agents}
        monitor._team_idle_at = {"test-session": datetime.now() - timedelta(minutes=3, seconds=5)}

        # Mock _find_pm_agent to return a PM
        with patch.object(monitor, "_find_pm_agent", return_value="other-session:0") as mock_find_pm:
            pm_notifications = {}
            monitor._check_team_idleness(mock_tmux, agents, mock_logger, pm_notifications)

            # Verify _find_pm_agent was called
            mock_find_pm.assert_called_once_with(mock_tmux)

    def test_pm_kill_failure_logged(self, monitor, mock_tmux, mock_logger):
        """Test that PM kill failure is logged properly."""
        # Setup
        agents = ["test-session:0", "test-session:1"]
        monitor._idle_agents = {agent: datetime.now() for agent in agents}
        monitor._team_idle_at = {"test-session": datetime.now() - timedelta(minutes=8, seconds=5)}

        # Make kill_window fail
        mock_tmux.kill_window.side_effect = Exception("Kill failed")

        pm_notifications = {}

        # Call check team idleness
        monitor._check_team_idleness(mock_tmux, agents, mock_logger, pm_notifications)

        # Verify error was logged
        mock_logger.error.assert_called_once()
        assert "Failed to kill PM" in mock_logger.error.call_args[0][0]

        # Verify escalation was still recorded
        assert 8 in monitor._pm_escalation_history["test-session:0"]

    def test_no_agents_no_escalation(self, monitor, mock_tmux, mock_logger):
        """Test that empty agent list doesn't cause escalation."""
        agents = []
        pm_notifications = {}

        # Call check team idleness
        monitor._check_team_idleness(mock_tmux, agents, mock_logger, pm_notifications)

        # Verify no escalations were attempted
        mock_logger.warning.assert_not_called()
        mock_logger.critical.assert_not_called()
        mock_tmux.kill_window.assert_not_called()

    @pytest.mark.parametrize(
        "threshold,action,has_message",
        [
            (3, DaemonAction.MESSAGE, True),
            (5, DaemonAction.MESSAGE, True),
            (8, DaemonAction.KILL, False),
        ],
    )
    def test_escalation_configuration(self, threshold, action, has_message):
        """Test that escalation configuration matches specification."""
        assert threshold in NONRESPONSIVE_PM_ESCALATIONS_MINUTES
        escalation = NONRESPONSIVE_PM_ESCALATIONS_MINUTES[threshold]
        assert escalation[0] == action

        if has_message:
            assert escalation[1] is not None
            assert isinstance(escalation[1], str)
            assert len(escalation[1]) > 0
        else:
            assert escalation[1] is None
