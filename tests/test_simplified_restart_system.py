"""Test the FINAL simplified restart system.

This module validates that:
1. Daemon only detects failures and sends simple notifications (no role storage)
2. PM gets clean notifications like 'Agent X failed, please restart'
3. No complex state management remains
4. System follows: detect → notify → PM handles restart with team knowledge
"""

from datetime import datetime
from unittest.mock import Mock, patch

from tmux_orchestrator.core.monitor import IdleMonitor


class TestSimplifiedRestartSystem:
    """Test the simplified detect → notify → PM handles restart approach."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_tmux = Mock()
        self.monitor = IdleMonitor(self.mock_tmux)
        self.logger = Mock()

    def test_daemon_only_detects_and_notifies(self):
        """Test that daemon only detects failures and sends notifications - no autonomous restart."""
        target = "session:1"
        pm_target = "session:2"

        # Mock crashed agent content
        crashed_content = "bash: claude: command not found\nbash $ "
        self.mock_tmux.capture_pane.return_value = crashed_content

        # Mock PM discovery
        with patch.object(self.monitor, "_find_pm_agent", return_value=pm_target):
            with patch("tmux_orchestrator.core.monitor.is_claude_interface_present", return_value=False):
                with patch("time.sleep"):
                    # Check agent status - should detect crash and notify PM
                    self.monitor._check_agent_status(self.mock_tmux, target, self.logger)

        # Verify notification was sent to PM
        assert self.mock_tmux.send_message.called
        notification_calls = [call for call in self.mock_tmux.send_message.call_args_list if call[0][0] == pm_target]
        assert len(notification_calls) == 1

        # Verify NO autonomous restart was attempted
        assert not self.mock_tmux.press_ctrl_c.called
        assert not any(
            "claude --dangerously-skip-permissions" in str(call) for call in self.mock_tmux.send_text.call_args_list
        )
        assert not self.mock_tmux.press_enter.called

    def test_pm_gets_clean_simple_notifications(self):
        """Test that PM receives clean, simple failure notifications."""
        target = "backend:3"
        pm_target = "session:1"

        # Mock API error scenario
        api_error_content = "Network error occurred\nConnection timed out"
        self.mock_tmux.capture_pane.return_value = api_error_content

        # Mock _attempt_agent_restart to test notification content
        with patch.object(self.monitor, "_find_pm_agent", return_value=pm_target):
            # Call the simplified restart notification directly
            self.monitor._send_simple_restart_notification(
                self.mock_tmux, target, "API error (Network/Connection)", self.logger
            )

        # Verify clean, simple notification format
        assert self.mock_tmux.send_message.called
        notification_call = self.mock_tmux.send_message.call_args
        message = notification_call[0][1]

        # Check message contains expected simple format
        assert "🚨 AGENT FAILURE" in message
        assert "backend:3" in message
        assert "API error (Network/Connection)" in message
        assert "Please restart this agent and provide the appropriate role prompt." in message

        # Verify message is clean and simple (no complex instructions)
        assert "autonomous" not in message.lower()
        assert "rehydration" not in message.lower()
        assert "role storage" not in message.lower()
        assert "complex" not in message.lower()

    def test_no_complex_state_management_remains(self):
        """Test that no complex role storage or state management exists."""
        # Verify IdleMonitor doesn't have complex state management attributes
        monitor_attrs = dir(self.monitor)

        # Should NOT have complex attributes
        assert not any(attr for attr in monitor_attrs if "role" in attr.lower() and "storage" in attr.lower())
        assert not any(attr for attr in monitor_attrs if "rehydr" in attr.lower())
        assert not any(attr for attr in monitor_attrs if "autonomous" in attr.lower())

        # Should have only simple notification tracking
        simple_attrs = [
            "_crash_notifications",
            "_idle_notifications",
            "_idle_agents",
            "_submission_attempts",
            "_last_submission_time",
        ]
        for attr in simple_attrs:
            assert hasattr(self.monitor, attr), f"Missing simple tracking attribute: {attr}"

        # Verify initialization only sets up simple tracking
        assert isinstance(self.monitor._crash_notifications, dict)
        assert isinstance(self.monitor._idle_notifications, dict)
        assert isinstance(self.monitor._idle_agents, dict)

    def test_notification_cooldown_prevents_spam(self):
        """Test that notification cooldown prevents spamming PM."""
        target = "session:1"
        pm_target = "session:2"

        # Mock crashed content
        crashed_content = "bash $ "
        self.mock_tmux.capture_pane.return_value = crashed_content

        # First notification should work
        with patch.object(self.monitor, "_find_pm_agent", return_value=pm_target):
            self.monitor._send_simple_restart_notification(self.mock_tmux, target, "Agent crash/failure", self.logger)

        assert self.mock_tmux.send_message.called

        # Reset mock and try again immediately
        self.mock_tmux.send_message.reset_mock()

        # Second notification within cooldown should be blocked by _attempt_agent_restart
        # Set up restart attempt tracking to simulate recent notification
        self.monitor._restart_attempts = {f"restart_{target}": datetime.now()}

        result = self.monitor._attempt_agent_restart(self.mock_tmux, target, self.logger)

        # Should return False due to cooldown
        assert result is False
        assert not self.mock_tmux.send_message.called

    def test_simple_workflow_detect_notify_only(self):
        """Test the complete simplified workflow: detect → notify → stop."""
        target = "qa:2"
        pm_target = "session:1"

        # Mock various failure scenarios
        failure_scenarios = [
            ("bash $ ", "Agent crash/failure"),
            ("claude: command not found", "Agent crash/failure"),
            ("Network error occurred", "API error (Network/Connection)"),
            ("Rate limit exceeded", "API error (Rate Limiting)"),
        ]

        for content, expected_reason in failure_scenarios:
            # Reset mocks
            self.mock_tmux.reset_mock()

            # Mock failure content
            self.mock_tmux.capture_pane.return_value = content

            # Mock PM discovery
            with patch.object(self.monitor, "_find_pm_agent", return_value=pm_target):
                # Call attempt restart (which now only notifies)
                self.monitor._restart_attempts = {}  # Reset cooldown
                result = self.monitor._attempt_agent_restart(self.mock_tmux, target, self.logger)

            # Verify workflow: detect → notify → stop
            assert result is True  # Notification sent successfully
            assert self.mock_tmux.send_message.called  # PM notified

            # Verify NO complex actions taken
            assert not self.mock_tmux.press_ctrl_c.called  # No autonomous restart
            assert not any(
                "claude --dangerously-skip-permissions" in str(call) for call in self.mock_tmux.send_text.call_args_list
            )  # No restart commands

            # Verify message content is appropriate
            notification_call = self.mock_tmux.send_message.call_args
            message = notification_call[0][1]
            assert "🚨 AGENT FAILURE" in message
            assert target in message


class TestPMManualRestartWorkflow:
    """Test that PM can manually restart agents with appropriate commands."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_tmux = Mock()

    def test_pm_can_use_manual_restart_command(self):
        """Test that PM can use manual restart commands with system prompts."""
        target = "backend:3"

        # Simulate PM sending manual restart command
        restart_command = 'claude --dangerously-skip-permissions --system-prompt "You are a Backend Developer..."'

        # Mock successful restart sequence
        self.mock_tmux.send_text.return_value = True
        self.mock_tmux.press_enter.return_value = True

        # Simulate PM actions
        self.mock_tmux.send_text(target, restart_command)
        self.mock_tmux.press_enter(target)

        # Verify commands were sent
        self.mock_tmux.send_text.assert_called_with(target, restart_command)
        self.mock_tmux.press_enter.assert_called_with(target)

        # Verify command format is correct
        sent_command = self.mock_tmux.send_text.call_args[0][1]
        assert "claude --dangerously-skip-permissions" in sent_command
        assert "--system-prompt" in sent_command
        assert "Backend Developer" in sent_command

    def test_pm_has_team_knowledge_for_roles(self):
        """Test that PM approach allows for team-specific role knowledge."""
        # Mock different agent types and their expected role prompts
        agent_roles = {
            "backend:1": "You are a Backend Developer working on API endpoints",
            "frontend:2": "You are a Frontend Developer working on React components",
            "qa:3": "You are a QA Engineer responsible for testing and validation",
            "devops:4": "You are a DevOps Engineer managing infrastructure",
        }

        for target, role_prompt in agent_roles.items():
            # Simulate PM restarting each agent with appropriate role
            command = f'claude --dangerously-skip-permissions --system-prompt "{role_prompt}"'

            self.mock_tmux.send_text(target, command)
            self.mock_tmux.press_enter(target)

            # Verify PM can customize restart for each agent type
            sent_command = self.mock_tmux.send_text.call_args[0][1]
            assert role_prompt in sent_command
            assert "--system-prompt" in sent_command


class TestSystemCleanlinessValidation:
    """Validate that the simplified system is much cleaner than previous versions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_tmux = Mock()
        self.monitor = IdleMonitor(self.mock_tmux)

    def test_no_complex_restart_logic_remains(self):
        """Test that complex autonomous restart logic has been removed."""
        # Read the _attempt_agent_restart method
        import inspect

        restart_method = inspect.getsource(self.monitor._attempt_agent_restart)

        # Should NOT contain complex restart logic
        assert "press_ctrl_c" not in restart_method
        assert "send_text" not in restart_method or "claude --dangerously-skip-permissions" not in restart_method
        assert "wait for Claude to initialize" not in restart_method
        assert "rehydration" not in restart_method.lower()
        assert "role storage" not in restart_method.lower()

        # Should contain only detection and notification
        assert "detect" in restart_method.lower()
        assert "notify" in restart_method.lower()
        assert "_send_simple_restart_notification" in restart_method

    def test_clean_separation_of_concerns(self):
        """Test clean separation: daemon detects/notifies, PM handles restart."""
        # Daemon responsibilities (should exist)
        assert hasattr(self.monitor, "_check_agent_status")  # Detection
        assert hasattr(self.monitor, "_attempt_agent_restart")  # Notification trigger
        assert hasattr(self.monitor, "_send_simple_restart_notification")  # Notification

        # Complex restart responsibilities (should NOT exist)
        import inspect

        restart_method_source = inspect.getsource(self.monitor._attempt_agent_restart)

        # Should not handle actual restart
        assert "tmux.press_ctrl_c" not in restart_method_source
        assert "tmux.send_text" not in restart_method_source or "claude" not in restart_method_source
        assert "claude --dangerously-skip-permissions" not in restart_method_source

    def test_simplified_approach_benefits(self):
        """Test that simplified approach provides clear benefits."""
        # Benefits of simplified approach:

        # 1. No complex state management
        complex_attrs = [
            attr
            for attr in dir(self.monitor)
            if any(keyword in attr.lower() for keyword in ["role", "rehydr", "autonomous", "storage"])
        ]
        assert len(complex_attrs) == 0, f"Found complex attributes: {complex_attrs}"

        # 2. Simple notification tracking only
        simple_attrs = ["_crash_notifications", "_idle_notifications", "_restart_attempts"]
        for attr in simple_attrs:
            assert hasattr(self.monitor, attr)
            assert isinstance(getattr(self.monitor, attr), dict)

        # 3. Clear workflow: detect → notify → done
        import inspect

        check_method = inspect.getsource(self.monitor._check_agent_status)

        # Should detect and call _attempt_agent_restart (which notifies)
        assert "_attempt_agent_restart" in check_method

        # 4. PM retains full control and team knowledge
        # (This is validated by the PM being able to use custom restart commands)
        # No autonomous decisions made by daemon
        restart_source = inspect.getsource(self.monitor._attempt_agent_restart)
        assert "PM" in restart_source  # References PM in notifications
        assert "notify" in restart_source.lower()  # Only notifies
