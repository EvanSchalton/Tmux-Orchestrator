"""Test PM notification delivery system for monitoring.

This module tests PM notification features:
1. Idle agent notifications are sent immediately
2. Crash notifications work correctly
3. Notification cooldowns are respected
4. PM discovery works properly
"""

import pytest
from unittest.mock import Mock, patch, call
from datetime import datetime, timedelta
import logging

from tmux_orchestrator.core.monitor import IdleMonitor
from tmux_orchestrator.core.monitor_helpers import AgentState


class TestPMNotificationDelivery:
    """Test PM notification system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_tmux = Mock()
        self.monitor = IdleMonitor(self.mock_tmux)
        self.logger = Mock()
    
    def test_idle_agent_notification_immediate(self):
        """Test that idle agents trigger immediate PM notification."""
        target = "session:1"
        pm_target = "session:2"
        
        # Mock PM discovery
        with patch.object(self.monitor, '_find_pm_agent', return_value=pm_target):
            # Set up idle agent tracking
            self.monitor._idle_agents[target] = datetime.now()
            
            # Call notification method
            self.monitor._check_idle_notification(self.mock_tmux, target, self.logger)
        
        # Verify PM was notified
        self.mock_tmux.send_message.assert_called_once()
        call_args = self.mock_tmux.send_message.call_args
        assert call_args[0][0] == pm_target  # PM target
        assert "IDLE AGENT ALERT" in call_args[0][1]  # Message contains alert
        assert target in call_args[0][1]  # Message mentions the idle agent
    
    def test_no_self_notification_for_pm(self):
        """Test that PM doesn't get notified about their own idle state."""
        pm_target = "session:2"
        
        # Mock PM discovery to return same target
        with patch.object(self.monitor, '_find_pm_agent', return_value=pm_target):
            # PM is idle
            self.monitor._idle_agents[pm_target] = datetime.now()
            
            # Try to notify about PM's own idle state
            self.monitor._check_idle_notification(self.mock_tmux, pm_target, self.logger)
        
        # Should not send any message
        self.mock_tmux.send_message.assert_not_called()
    
    def test_crash_notification_with_cooldown(self):
        """Test crash notifications respect 5-minute cooldown."""
        target = "session:1"
        pm_target = "session:2"
        
        # Mock PM discovery
        with patch.object(self.monitor, '_find_pm_target', return_value=pm_target):
            # First notification should work
            self.monitor._notify_crash(self.mock_tmux, target, self.logger)
            
            assert self.mock_tmux.send_message.called
            first_call_count = self.mock_tmux.send_message.call_count
            
            # Reset mock
            self.mock_tmux.send_message.reset_mock()
            
            # Second notification within 5 minutes should be skipped
            self.monitor._notify_crash(self.mock_tmux, target, self.logger)
            
            assert not self.mock_tmux.send_message.called
    
    def test_pm_discovery_mechanism(self):
        """Test PM agent discovery works correctly."""
        # Set up mock sessions and windows
        sessions = [
            {"name": "monitor-fixes"},
            {"name": "backend-dev"}
        ]
        
        windows = {
            "monitor-fixes": [
                {"index": "0", "name": "orchestrator"},
                {"index": "1", "name": "qa-engineer"},
                {"index": "2", "name": "project-manager"}  # This is the PM
            ],
            "backend-dev": [
                {"index": "0", "name": "developer"},
                {"index": "1", "name": "tester"}
            ]
        }
        
        # Mock tmux methods
        self.mock_tmux.list_sessions.return_value = sessions
        self.mock_tmux.list_windows.side_effect = lambda s: windows.get(s, [])
        
        # PM window should have Claude interface
        def capture_pane_side_effect(target, lines=10):
            if target == "monitor-fixes:2":
                return "╭─ Claude Code ─╮\n│ > Ready to manage the team\n╰───────────────╯"
            return "bash$ "
        
        self.mock_tmux.capture_pane.side_effect = capture_pane_side_effect
        
        # Find PM
        pm_target = self.monitor._find_pm_agent(self.mock_tmux)
        
        assert pm_target == "monitor-fixes:2"
    
    def test_recovery_notification(self):
        """Test recovery needed notifications."""
        target = "session:1"
        pm_target = "session:2"
        
        # Mock PM discovery
        with patch.object(self.monitor, '_find_pm_agent', return_value=pm_target):
            # Send recovery notification
            self.monitor._notify_recovery_needed(self.mock_tmux, target, self.logger)
        
        # Verify notification sent
        self.mock_tmux.send_message.assert_called_once()
        call_args = self.mock_tmux.send_message.call_args
        assert call_args[0][0] == pm_target
        assert "AGENT RECOVERY NEEDED" in call_args[0][1]
        assert target in call_args[0][1]
    
    def test_notification_format(self):
        """Test notification message format and content."""
        target = "backend:3"
        pm_target = "monitor:2"
        
        # Set up idle duration
        idle_start = datetime.now() - timedelta(minutes=15)
        self.monitor._idle_agents[target] = idle_start
        
        with patch.object(self.monitor, '_find_pm_agent', return_value=pm_target):
            with patch.object(self.monitor, '_determine_agent_type', return_value="Backend Developer"):
                self.monitor._check_idle_notification(self.mock_tmux, target, self.logger)
        
        # Check message format
        call_args = self.mock_tmux.send_message.call_args
        message = call_args[0][1]
        
        assert "🚨 IDLE AGENT ALERT:" in message
        assert "backend:3 (Backend Developer)" in message
        assert "15 minutes" in message  # Idle duration
        assert "automated notification" in message
    
    def test_no_pm_found_handling(self):
        """Test graceful handling when no PM is found."""
        target = "session:1"
        
        # Mock no PM found
        with patch.object(self.monitor, '_find_pm_agent', return_value=None):
            # Should not crash, just log warning
            self.monitor._check_idle_notification(self.mock_tmux, target, self.logger)
        
        # Verify warning was logged
        self.logger.warning.assert_called()
        assert "No PM found" in self.logger.warning.call_args[0][0]
        
        # No message should be sent
        self.mock_tmux.send_message.assert_not_called()
    
    def test_notification_delivery_failure(self):
        """Test handling of notification delivery failures."""
        target = "session:1"
        pm_target = "session:2"
        
        # Mock PM discovery
        with patch.object(self.monitor, '_find_pm_agent', return_value=pm_target):
            # Mock send_message to fail
            self.mock_tmux.send_message.return_value = False
            
            # Send notification
            self.monitor._check_idle_notification(self.mock_tmux, target, self.logger)
        
        # Verify error was logged
        error_logs = [call for call in self.logger.error.call_args_list]
        assert any("Failed to notify PM" in str(call) for call in error_logs)


class TestNotificationCooldowns:
    """Test notification cooldown mechanisms."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_tmux = Mock()
        self.monitor = IdleMonitor(self.mock_tmux)
        self.logger = Mock()
    
    def test_idle_notification_cooldown_from_helper(self):
        """Test that idle notifications use cooldown from helper function."""
        from tmux_orchestrator.core.monitor_helpers import should_notify_pm
        
        target = "session:1"
        notification_history = {}
        
        # First notification should be allowed
        assert should_notify_pm(AgentState.IDLE, target, notification_history) is True
        
        # Add to history
        notification_history[target] = datetime.now()
        
        # Immediate second notification should be blocked
        assert should_notify_pm(AgentState.IDLE, target, notification_history) is False
        
        # After 10 minutes, should be allowed
        notification_history[target] = datetime.now() - timedelta(minutes=11)
        assert should_notify_pm(AgentState.IDLE, target, notification_history) is True
    
    def test_crash_notification_cooldown_from_helper(self):
        """Test that crash notifications use cooldown from helper function."""
        from tmux_orchestrator.core.monitor_helpers import should_notify_pm
        
        target = "session:1"
        notification_history = {}
        
        # First crash notification should be allowed
        assert should_notify_pm(AgentState.CRASHED, target, notification_history) is True
        
        # Add to history with crash prefix
        notification_history[f"crash_{target}"] = datetime.now()
        
        # Immediate second notification should be blocked
        assert should_notify_pm(AgentState.CRASHED, target, notification_history) is False
        
        # After 5 minutes, should be allowed
        notification_history[f"crash_{target}"] = datetime.now() - timedelta(minutes=6)
        assert should_notify_pm(AgentState.CRASHED, target, notification_history) is True


class TestIntegratedNotificationFlow:
    """Test complete notification flow integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_tmux = Mock()
        self.monitor = IdleMonitor(self.mock_tmux)
        self.logger = Mock()
    
    def test_full_idle_detection_to_notification_flow(self):
        """Test complete flow from idle detection to PM notification."""
        agent_target = "backend:1"
        pm_target = "monitor:2"
        
        # Set up agent content (idle with Claude interface, no message)
        idle_content = """╭─ Claude Code ─────────────────────────────────────────────────╮
│ Task completed successfully!                                     │
╰─────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────╮
│ > _                                                             │
╰─────────────────────────────────────────────────────────────╯"""
        
        # Mock tmux methods
        self.mock_tmux.capture_pane.return_value = idle_content
        
        # Mock PM discovery
        with patch.object(self.monitor, '_find_pm_agent', return_value=pm_target):
            # Mock helper functions
            with patch('tmux_orchestrator.core.monitor.detect_agent_state', return_value=AgentState.HEALTHY):
                with patch('tmux_orchestrator.core.monitor.is_terminal_idle', return_value=True):
                    with patch('tmux_orchestrator.core.monitor.is_claude_interface_present', return_value=True):
                        with patch('tmux_orchestrator.core.monitor.has_unsubmitted_message', return_value=False):
                            with patch('tmux_orchestrator.core.monitor.should_notify_pm', return_value=True):
                                # Run status check
                                self.monitor._check_agent_status(self.mock_tmux, agent_target, self.logger)
        
        # Verify notification was sent
        self.mock_tmux.send_message.assert_called()
        call_args = self.mock_tmux.send_message.call_args
        assert call_args[0][0] == pm_target
        assert "IDLE AGENT ALERT" in call_args[0][1]
        assert agent_target in call_args[0][1]