"""Comprehensive test suite for daemon recovery fixes.

This test suite validates the critical fixes made to the monitoring daemon:
1. False positive crash detection (removed '$ ' indicator)
2. PM recovery cooldown mechanism (5-minute cooldown)
3. Team notification method signature fixes
4. Singleton enforcement verification
"""

import os
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.core.monitor import IdleMonitor
from tmux_orchestrator.core.monitoring.crash_detector import CrashDetector
from tmux_orchestrator.core.monitoring.types import AgentInfo
from tmux_orchestrator.utils.tmux import TMUXManager


class TestFalsePositiveCrashDetection:
    """Test suite for false positive crash detection fix."""

    @pytest.fixture
    def crash_detector(self):
        """Create a crash detector instance."""
        tmux = MagicMock(spec=TMUXManager)
        logger = MagicMock()
        return CrashDetector(tmux, logger)

    @pytest.fixture
    def agent_info(self):
        """Create a sample agent info."""
        return AgentInfo(
            target="test-session:1",
            session="test-session",
            window="1",
            name="Test Agent",
            type="developer",
            status="active"
        )

    def test_dollar_sign_in_conversation_not_crash(self, crash_detector, agent_info):
        """Test that discussing shell prompts in conversation doesn't trigger crash."""
        # Content with $ in normal conversation
        content = """
        Human: How do I use the shell prompt?
        
        Assistant: The shell prompt typically shows as '$ ' for regular users. 
        When you see '$ ' at the beginning of a line, it means the shell is ready.
        
        You can type commands after the $ prompt.
        """
        
        crashed, reason = crash_detector.detect_crash(agent_info, content)
        assert not crashed, "Dollar sign in conversation should not trigger crash"
        assert reason is None

    def test_actual_shell_prompt_triggers_crash(self, crash_detector, agent_info):
        """Test that actual shell prompt at end of content triggers crash."""
        # Content ending with actual shell prompt
        content = """
        Human: Please run a command
        
        Assistant: I'll run that command for you
        
        bash-5.1$ """
        
        crashed, reason = crash_detector.detect_crash(agent_info, content)
        assert crashed, "Shell prompt at end should trigger crash"
        assert "Shell prompt detected" in reason

    def test_shell_prompt_variations(self, crash_detector, agent_info):
        """Test various shell prompt patterns."""
        # Test cases: (content, should_crash, description)
        test_cases = [
            ("Some content\n$ ", True, "Bare $ at end"),
            ("Some content\nbash-5.1$ ", True, "Bash prompt at end"),
            ("Some content\nzsh: $ ", True, "Zsh prompt at end"),
            ("Some content\n[user@host]$ ", True, "Full prompt at end"),
            ("Discussing $ prompt syntax\nMore content here", False, "$ in middle of content"),
            ("The command is: echo $HOME\nOutput: /home/user", False, "$ as variable"),
            ("Cost is $50\nThank you", False, "$ as dollar sign"),
            ("Some content\n➜ ", True, "Zsh fancy prompt"),
            ("Some content\n❯ ", True, "Fish/starship prompt"),
        ]
        
        for content, should_crash, description in test_cases:
            crashed, _ = crash_detector.detect_crash(agent_info, content)
            assert crashed == should_crash, f"Failed for: {description}"

    def test_tool_output_with_dollar_sign(self, crash_detector, agent_info):
        """Test that $ in tool output doesn't trigger crash."""
        content = """
        Human: Check the price
        
        Assistant: Let me check that for you.
        
        ⎿ Tool Result:
        │ Price: $25.99
        │ Tax: $2.60
        │ Total: $28.59
        └
        
        The total cost is $28.59.
        """
        
        crashed, reason = crash_detector.detect_crash(agent_info, content)
        assert not crashed, "Dollar signs in tool output should not trigger crash"

    def test_discussion_about_crashes(self, crash_detector, agent_info):
        """Test that discussing crashes/errors doesn't trigger false positives."""
        content = """
        Human: The process was killed earlier
        
        Assistant: I see that the process was terminated. This could have happened because:
        1. The system killed it due to memory constraints
        2. Someone manually killed the process
        3. The process crashed with a segmentation fault
        
        Let me check if the process has been restarted.
        """
        
        crashed, reason = crash_detector.detect_crash(agent_info, content)
        assert not crashed, "Discussing killed processes should not trigger crash"


class TestPMRecoveryCooldown:
    """Test suite for PM recovery cooldown mechanism."""

    @pytest.fixture
    def monitor(self, tmp_path):
        """Create a monitor instance with temporary directories."""
        # Set the base directory via environment variable
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = str(tmp_path)
        config = Config()
        tmux = MagicMock(spec=TMUXManager)
        monitor = IdleMonitor(tmux, config)
        return monitor

    def test_recovery_cooldown_prevents_rapid_recovery(self, monitor):
        """Test that cooldown prevents rapid PM recovery attempts."""
        session_name = "test-session"
        
        # First recovery attempt
        now = datetime.now()
        monitor._last_recovery_attempt[session_name] = now
        
        # Try to recover again immediately
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = now + timedelta(minutes=2)
            
            # Check if cooldown is active
            last_attempt = monitor._last_recovery_attempt.get(session_name)
            if last_attempt:
                time_since_last = (mock_datetime.now() - last_attempt).total_seconds() / 60
                cooldown_active = time_since_last < monitor._recovery_cooldown_minutes
                
            assert cooldown_active, "Cooldown should be active 2 minutes after recovery"

    def test_recovery_allowed_after_cooldown(self, monitor):
        """Test that recovery is allowed after cooldown period."""
        session_name = "test-session"
        
        # First recovery attempt
        now = datetime.now()
        monitor._last_recovery_attempt[session_name] = now
        
        # Try to recover after cooldown period
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = now + timedelta(minutes=6)
            
            # Check if cooldown is active
            last_attempt = monitor._last_recovery_attempt.get(session_name)
            if last_attempt:
                time_since_last = (mock_datetime.now() - last_attempt).total_seconds() / 60
                cooldown_active = time_since_last < monitor._recovery_cooldown_minutes
                
            assert not cooldown_active, "Cooldown should be inactive after 6 minutes"

    def test_pm_grace_period_after_recovery(self, monitor):
        """Test that PMs are protected by grace period after recovery."""
        session_name = "test-session"
        
        # Mark PM as recently recovered
        now = datetime.now()
        monitor._pm_recovery_timestamps[session_name] = now
        
        # Check if PM is in grace period
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = now + timedelta(minutes=2)
            
            # Check grace period
            recovery_time = monitor._pm_recovery_timestamps.get(session_name)
            if recovery_time:
                time_since_recovery = (mock_datetime.now() - recovery_time).total_seconds() / 60
                in_grace_period = time_since_recovery < monitor._grace_period_minutes
                
            assert in_grace_period, "PM should be in grace period 2 minutes after recovery"

    def test_pm_grace_period_expires(self, monitor):
        """Test that grace period expires after configured time."""
        session_name = "test-session"
        
        # Mark PM as recently recovered
        now = datetime.now()
        monitor._pm_recovery_timestamps[session_name] = now
        
        # Check after grace period expires
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = now + timedelta(minutes=4)
            
            # Check grace period
            recovery_time = monitor._pm_recovery_timestamps.get(session_name)
            if recovery_time:
                time_since_recovery = (mock_datetime.now() - recovery_time).total_seconds() / 60
                in_grace_period = time_since_recovery < monitor._grace_period_minutes
                
            assert not in_grace_period, "PM should not be in grace period after 4 minutes"


class TestTeamNotificationFixes:
    """Test suite for team notification method signature fixes."""

    @pytest.fixture
    def monitor(self, tmp_path):
        """Create a monitor instance."""
        # Set the base directory via environment variable
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = str(tmp_path)
        config = Config()
        tmux = MagicMock(spec=TMUXManager)
        monitor = IdleMonitor(tmux, config)
        return monitor

    def test_notify_team_method_exists(self, monitor):
        """Test that the correct _notify_team_of_pm_recovery method exists."""
        # Check that method exists and is callable
        assert hasattr(monitor, '_notify_team_of_pm_recovery'), "Method should exist"
        assert callable(getattr(monitor, '_notify_team_of_pm_recovery')), "Method should be callable"

    def test_notify_team_signature(self, monitor):
        """Test that _notify_team_of_pm_recovery has correct signature."""
        import inspect
        
        method = getattr(monitor, '_notify_team_of_pm_recovery')
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())
        
        # Should have session_name and pm_target parameters (self is implicit for bound methods)
        assert len(params) == 2, f"Method should have 2 parameters, got {params}"
        assert params[0] == 'session_name', "First parameter should be session_name"
        assert params[1] == 'pm_target', "Second parameter should be pm_target"

    @patch('tmux_orchestrator.core.monitor.is_claude_interface_present')
    def test_notify_team_sends_correct_message(self, mock_is_claude_present, monitor):
        """Test that team notification sends correct recovery message."""
        session_name = "test-session"
        pm_target = "test-session:1"
        
        # Mock is_claude_interface_present to return True (agents have Claude interface)
        mock_is_claude_present.return_value = True
        
        # Mock the tmux instance methods directly
        monitor.tmux.capture_pane = MagicMock(return_value="Some content")
        monitor.tmux.send_message = MagicMock(return_value=True)
        
        # Mock _discover_agents to return test agents
        monitor._discover_agents = MagicMock(return_value=[
            "test-session:1",  # PM target
            "test-session:2",  # Agent 1
            "test-session:3"   # Agent 2
        ])
        
        # Call the notification method
        monitor._notify_team_of_pm_recovery(session_name, pm_target)
        
        # Verify notifications were sent to non-PM agents
        assert monitor.tmux.send_message.call_count == 2, "Should notify 2 agents"
        
        # Check that correct message was sent
        for call in monitor.tmux.send_message.call_args_list:
            target, message = call[0]
            assert "PM RECOVERY NOTIFICATION" in message, "Notification should mention PM recovery"


class TestSingletonEnforcement:
    """Test suite for singleton pattern enforcement."""

    def test_singleton_creates_single_instance(self, tmp_path):
        """Test that only one instance of IdleMonitor is created."""
        # Set the base directory via environment variable
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = str(tmp_path)
        config = Config()
        tmux = MagicMock(spec=TMUXManager)
        
        # Create first instance
        monitor1 = IdleMonitor(tmux, config)
        
        # Create second instance
        monitor2 = IdleMonitor(tmux, config)
        
        # They should be the same object
        assert monitor1 is monitor2, "Singleton should return same instance"

    def test_singleton_thread_safe(self, tmp_path):
        """Test that singleton is thread-safe."""
        import threading
        
        # Set the base directory via environment variable
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = str(tmp_path)
        config = Config()
        tmux = MagicMock(spec=TMUXManager)
        instances = []
        
        def create_instance():
            instance = IdleMonitor(tmux, config)
            instances.append(instance)
        
        # Create multiple threads trying to create instances
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=create_instance)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # All instances should be the same
        assert len(set(id(inst) for inst in instances)) == 1, "All instances should be identical"

    def test_pid_file_locking(self, tmp_path):
        """Test that PID file prevents multiple daemons."""
        # Set the base directory via environment variable
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = str(tmp_path)
        config = Config()
        tmux = MagicMock(spec=TMUXManager)
        monitor = IdleMonitor(tmux, config)
        
        # Write a PID file
        pid_file = tmp_path / "idle-monitor.pid"
        pid_file.write_text("12345")
        
        # Mock process validation to say it's running
        with patch.object(monitor, '_is_valid_daemon_process', return_value=True):
            existing_pid = monitor._check_existing_daemon()
            assert existing_pid == 12345, "Should detect existing daemon"


class TestIntegrationScenarios:
    """Integration tests for overall daemon stability."""

    @pytest.fixture
    def full_monitor(self, tmp_path):
        """Create a fully configured monitor with mocked TMux."""
        # Set the base directory via environment variable
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = str(tmp_path)
        config = Config()
        tmux = MagicMock(spec=TMUXManager)
        
        # Mock TMux responses
        tmux.list_sessions.return_value = ["test-session"]
        tmux.list_windows.return_value = [
            {"index": "1", "name": "pm"},
            {"index": "2", "name": "backend-dev"},
            {"index": "3", "name": "qa-engineer"}
        ]
        tmux.capture_pane.return_value = "Human: Hello\n\nAssistant: Ready to help!"
        
        monitor = IdleMonitor(tmux, config)
        return monitor

    def test_pm_recovery_with_grace_period_scenario(self, full_monitor):
        """Test complete PM recovery scenario with grace period."""
        session_name = "test-session"
        
        # Simulate PM crash detection
        full_monitor.tmux.capture_pane.return_value = "bash-5.1$ "
        
        # First recovery
        now = datetime.now()
        full_monitor._last_recovery_attempt[session_name] = now
        full_monitor._pm_recovery_timestamps[session_name] = now
        
        # Immediate second crash (within cooldown)
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = now + timedelta(minutes=2)
            
            # Should not allow recovery due to cooldown
            last_attempt = full_monitor._last_recovery_attempt.get(session_name)
            time_since_last = (mock_datetime.now() - last_attempt).total_seconds() / 60
            allow_recovery = time_since_last >= full_monitor._recovery_cooldown_minutes
            
            assert not allow_recovery, "Should not allow recovery within cooldown"

    def test_false_positive_prevention_scenario(self, full_monitor):
        """Test that false positives are prevented in real scenarios."""
        crash_detector = CrashDetector(full_monitor.tmux, MagicMock())
        
        # Simulate various agent conversations
        test_scenarios = [
            {
                "content": "PM: The previous test failed with error: $ command not found",
                "should_crash": False,
                "scenario": "PM discussing test failure"
            },
            {
                "content": "Dev: I fixed the bug where the process was killed unexpectedly",
                "should_crash": False,
                "scenario": "Developer discussing fix"
            },
            {
                "content": "QA: All tests passed\n\nPM: Great work!\n\nbash-5.1$ ",
                "should_crash": True,
                "scenario": "Actual crash with shell prompt"
            },
            {
                "content": "Agent: The cost is $50 per month\n\nHuman: That's reasonable",
                "should_crash": False,
                "scenario": "Dollar amount in conversation"
            }
        ]
        
        agent = AgentInfo(
            target="test-session:1",
            session="test-session", 
            window="1",
            name="Test Agent",
            type="pm",
            status="active"
        )
        
        for scenario in test_scenarios:
            crashed, _ = crash_detector.detect_crash(agent, scenario["content"])
            assert crashed == scenario["should_crash"], f"Failed: {scenario['scenario']}"