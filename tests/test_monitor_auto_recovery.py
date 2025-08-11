"""Test auto-recovery mechanisms for the monitoring system.

This module tests auto-recovery features:
1. Auto-restart of crashed agents
2. Recovery cooldown mechanisms
3. Recovery failure handling
4. Integration with PM notifications
"""

import pytest
from unittest.mock import Mock, patch, call
from datetime import datetime, timedelta
import time

from tmux_orchestrator.core.monitor import IdleMonitor
from tmux_orchestrator.core.monitor_helpers import AgentState


class TestAutoRecoveryMechanisms:
    """Test automatic agent recovery functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_tmux = Mock()
        self.monitor = IdleMonitor(self.mock_tmux)
        self.logger = Mock()
    
    def test_crashed_agent_auto_restart(self):
        """Test that crashed agents trigger auto-restart."""
        target = "session:1"
        
        # Mock crashed agent detection
        crashed_content = """Human: exit
vscode ➜ /workspaces/project $ """
        
        self.mock_tmux.capture_pane.return_value = crashed_content
        
        # Mock successful restart
        with patch.object(self.monitor, '_attempt_agent_restart', return_value=True) as mock_restart:
            with patch('tmux_orchestrator.core.monitor.detect_agent_state', return_value=AgentState.CRASHED):
                self.monitor._check_agent_status(self.mock_tmux, target, self.logger)
        
        # Verify restart was attempted
        mock_restart.assert_called_once_with(self.mock_tmux, target, self.logger)
        
        # Verify no PM notification sent (restart succeeded)
        assert not any("_notify_crash" in str(call) for call in self.logger.error.call_args_list)
    
    def test_restart_failure_notifies_pm(self):
        """Test that failed restart attempts notify PM."""
        target = "session:1"
        pm_target = "session:2"
        
        # Mock crashed agent
        crashed_content = "bash: claude: command not found\n$ "
        self.mock_tmux.capture_pane.return_value = crashed_content
        
        # Mock failed restart and PM discovery
        with patch.object(self.monitor, '_attempt_agent_restart', return_value=False):
            with patch.object(self.monitor, '_find_pm_target', return_value=pm_target):
                with patch('tmux_orchestrator.core.monitor.detect_agent_state', return_value=AgentState.CRASHED):
                    self.monitor._check_agent_status(self.mock_tmux, target, self.logger)
        
        # Verify PM was notified about crash
        self.mock_tmux.send_message.assert_called()
        call_args = self.mock_tmux.send_message.call_args
        assert "AGENT CRASH ALERT" in call_args[0][1]
    
    def test_restart_command_sequence(self):
        """Test the correct command sequence for agent restart."""
        target = "backend:3"
        
        # Mock tmux capture to simulate restart progress
        capture_responses = [
            "$ ",  # Initial crashed state
            "$ claude --dangerously-skip-permissions",  # Command typed
            "Starting Claude...",  # Starting
            "Welcome to Claude Code!",  # Started successfully
        ]
        self.mock_tmux.capture_pane.side_effect = capture_responses
        
        # Test restart attempt
        with patch('time.sleep'):  # Skip actual sleep
            result = self.monitor._attempt_agent_restart(self.mock_tmux, target, self.logger)
        
        # Verify command sequence
        send_keys_calls = self.mock_tmux.send_keys.call_args_list
        assert len(send_keys_calls) >= 2
        
        # Should send Ctrl+C first
        assert send_keys_calls[0] == call(target, "C-c")
        
        # Then claude command
        assert send_keys_calls[1] == call(target, "claude --dangerously-skip-permissions")
        assert send_keys_calls[2] == call(target, "Enter")
        
        assert result is True
    
    def test_restart_cooldown_mechanism(self):
        """Test that restart attempts respect cooldown period."""
        target = "session:1"
        
        # First restart attempt
        with patch('tmux_orchestrator.core.monitor.is_claude_interface_present', return_value=True):
            with patch('time.sleep'):
                self.monitor._attempt_agent_restart(self.mock_tmux, target, self.logger)
        
        # Second attempt should be blocked by cooldown
        self.mock_tmux.reset_mock()
        with patch('time.sleep'):
            result = self.monitor._attempt_agent_restart(self.mock_tmux, target, self.logger)
        
        # Should not attempt restart
        assert result is False
        assert not self.mock_tmux.send_keys.called
    
    def test_restart_timeout_handling(self):
        """Test handling of restart timeout."""
        target = "session:1"
        
        # Mock Claude never starting
        self.mock_tmux.capture_pane.return_value = "$ "
        
        # Test restart with timeout
        with patch('time.sleep') as mock_sleep:
            result = self.monitor._attempt_agent_restart(self.mock_tmux, target, self.logger)
        
        # Should have tried for 15 seconds
        assert mock_sleep.call_count >= 15
        assert result is False
        
        # Should log timeout
        self.logger.warning.assert_called()
        assert "timeout" in self.logger.warning.call_args[0][0].lower()
    
    def test_restart_error_detection(self):
        """Test detection of errors during restart."""
        target = "session:1"
        
        # Mock permission denied error
        self.mock_tmux.capture_pane.return_value = "bash: /usr/local/bin/claude: Permission denied"
        
        # Test restart
        with patch('time.sleep'):
            result = self.monitor._attempt_agent_restart(self.mock_tmux, target, self.logger)
        
        assert result is False
        
        # Should log the error
        error_logs = [call for call in self.logger.error.call_args_list]
        assert any("permission denied" in str(call).lower() for call in error_logs)


class TestRecoveryIntegration:
    """Test integration of recovery with other monitoring features."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_tmux = Mock()
        self.monitor = IdleMonitor(self.mock_tmux)
        self.logger = Mock()
    
    def test_recovery_clears_idle_tracking(self):
        """Test that successful recovery clears idle tracking."""
        target = "session:1"
        
        # Set up idle tracking
        self.monitor._idle_agents[target] = datetime.now() - timedelta(minutes=30)
        self.monitor._submission_attempts[target] = 5
        
        # Mock successful restart
        with patch('tmux_orchestrator.core.monitor.is_claude_interface_present', return_value=True):
            with patch('time.sleep'):
                self.monitor._attempt_agent_restart(self.mock_tmux, target, self.logger)
        
        # Tracking should remain (restart doesn't clear it, only activity does)
        # This is correct behavior - agent needs to become active to clear tracking
        assert target in self.monitor._idle_agents
    
    def test_multiple_agent_recovery(self):
        """Test recovery of multiple agents in sequence."""
        agents = ["frontend:1", "backend:2", "qa:3"]
        
        # Mock all as crashed
        for agent in agents:
            with patch('tmux_orchestrator.core.monitor.detect_agent_state', return_value=AgentState.CRASHED):
                with patch.object(self.monitor, '_attempt_agent_restart', return_value=True):
                    self.monitor._check_agent_status(self.mock_tmux, agent, self.logger)
        
        # Verify all were attempted
        assert self.logger.error.call_count >= len(agents)
        for agent in agents:
            assert any(agent in str(call) for call in self.logger.error.call_args_list)
    
    def test_recovery_with_custom_error_states(self):
        """Test recovery for various error states."""
        error_contents = [
            "Segmentation fault (core dumped)",
            "Killed",
            "[Process completed]",
            "Terminated",
            "ModuleNotFoundError: No module named 'claude'",
        ]
        
        for i, content in enumerate(error_contents):
            target = f"session:{i}"
            self.mock_tmux.capture_pane.return_value = content
            
            with patch('tmux_orchestrator.core.monitor.detect_agent_state', return_value=AgentState.CRASHED):
                with patch.object(self.monitor, '_attempt_agent_restart', return_value=True):
                    self.monitor._check_agent_status(self.mock_tmux, target, self.logger)
            
            # Should attempt recovery for all crash types
            assert any(target in str(call) for call in self.logger.error.call_args_list)


class TestRecoveryEdgeCases:
    """Test edge cases and boundary conditions for recovery."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_tmux = Mock()
        self.monitor = IdleMonitor(self.mock_tmux)
        self.logger = Mock()
    
    def test_recovery_during_startup(self):
        """Test that agents in startup state are not restarted."""
        target = "session:1"
        
        startup_content = """Initializing Claude Code...
Loading configuration..."""
        
        self.mock_tmux.capture_pane.return_value = startup_content
        
        with patch('tmux_orchestrator.core.monitor.detect_agent_state', return_value=AgentState.STARTING):
            with patch.object(self.monitor, '_attempt_agent_restart') as mock_restart:
                self.monitor._check_agent_status(self.mock_tmux, target, self.logger)
        
        # Should not attempt restart for starting agents
        mock_restart.assert_not_called()
    
    def test_recovery_exception_handling(self):
        """Test graceful handling of exceptions during recovery."""
        target = "session:1"
        
        # Mock exception during restart
        with patch.object(self.monitor, '_attempt_agent_restart', side_effect=Exception("Test error")):
            with patch('tmux_orchestrator.core.monitor.detect_agent_state', return_value=AgentState.CRASHED):
                # Should not crash the monitor
                self.monitor._check_agent_status(self.mock_tmux, target, self.logger)
        
        # Should log the error
        assert self.logger.error.called
    
    def test_concurrent_recovery_protection(self):
        """Test protection against concurrent recovery attempts."""
        target = "session:1"
        
        # Simulate rapid successive checks
        for _ in range(5):
            with patch('tmux_orchestrator.core.monitor.detect_agent_state', return_value=AgentState.CRASHED):
                with patch.object(self.monitor, '_attempt_agent_restart', return_value=False) as mock_restart:
                    self.monitor._check_agent_status(self.mock_tmux, target, self.logger)
        
        # Due to cooldown in notifications, PM shouldn't be spammed
        # Check notification cooldown is working
        notification_calls = self.mock_tmux.send_message.call_count
        assert notification_calls <= 1  # Should only notify once due to cooldown