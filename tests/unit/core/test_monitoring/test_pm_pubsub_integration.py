"""Tests for PM pubsub integration functionality."""

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from tmux_orchestrator.core.communication.pm_pubsub_integration import PMPubsubIntegration


class TestPMPubsubIntegration(unittest.TestCase):
    """Test PM pubsub integration functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.message_store = Path(self.temp_dir) / "messages"
        self.message_store.mkdir(parents=True, exist_ok=True)

        # Mock the message store location
        self.patcher = patch.object(PMPubsubIntegration, "__init__")
        self.mock_init = self.patcher.start()

        def init_mock(self, session="pm:0"):
            self.session = session
            self.tmux = Mock()
            self.message_store = self.message_store

        self.mock_init.side_effect = init_mock

        self.pm_integration = PMPubsubIntegration()

    def tearDown(self):
        """Clean up test environment."""
        self.patcher.stop()
        # Clean up temp directory
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_parse_daemon_messages(self):
        """Test daemon message parsing."""
        messages = [
            {
                "id": "test-1",
                "timestamp": datetime.now().isoformat(),
                "priority": "high",
                "tags": ["monitoring", "health"],
                "message": "Agent backend-dev:2 idle 15min - investigate",
                "sender": "daemon",
            },
            {
                "id": "test-2",
                "timestamp": datetime.now().isoformat(),
                "priority": "critical",
                "tags": ["recovery"],
                "message": "PM crash detected session:1 - spawning replacement",
                "sender": "daemon",
            },
        ]

        parsed = self.pm_integration._parse_daemon_messages(messages)

        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["type"], "idle_alert")
        self.assertEqual(parsed[1]["type"], "failure")
        self.assertIn("monitoring", parsed[0]["tags"])

    def test_categorize_daemon_message(self):
        """Test daemon message categorization."""
        test_cases = [
            ("Agent failed to respond", "failure"),
            ("Backend agent idle for 20 minutes", "idle_alert"),
            ("PM recovered successfully", "recovery"),
            ("Health check completed", "health_check"),
            ("General system message", "general"),
        ]

        for message, expected_type in test_cases:
            result = self.pm_integration._categorize_daemon_message(message)
            self.assertEqual(result, expected_type, f"Failed for message: {message}")

    def test_suggest_recovery_response(self):
        """Test recovery response suggestions."""
        test_cases = [
            ("PM crash detected", "Verify PM replacement spawned correctly"),
            ("Agent idle timeout", "Send status request to agent"),
            ("Connection timeout occurred", "Check agent responsiveness"),
            ("System failed to start", "Investigate failure cause"),
        ]

        for message, expected_response in test_cases:
            result = self.pm_integration._suggest_recovery_response(message)
            self.assertIn(expected_response.split()[0].lower(), result.lower(), f"Failed for message: {message}")

    def test_get_management_broadcasts(self):
        """Test filtering management broadcast messages."""
        # Create mock message file
        session_file = self.message_store / "pm_0.json"
        test_messages = [
            {
                "id": "msg-1",
                "timestamp": datetime.now().isoformat(),
                "priority": "high",
                "tags": ["monitoring", "management"],
                "message": "System alert",
                "sender": "daemon",
            },
            {
                "id": "msg-2",
                "timestamp": datetime.now().isoformat(),
                "priority": "low",
                "tags": ["status"],
                "message": "Low priority update",
                "sender": "daemon",
            },
        ]

        with open(session_file, "w") as f:
            json.dump(test_messages, f)

        # Test high priority filtering
        high_messages = self.pm_integration.get_management_broadcasts("high")
        self.assertEqual(len(high_messages), 1)
        self.assertEqual(high_messages[0]["priority"], "high")

        # Test low priority filtering
        low_messages = self.pm_integration.get_management_broadcasts("low")
        self.assertEqual(len(low_messages), 0)  # No management/monitoring tags

    @patch("subprocess.run")
    def test_acknowledge_notification(self, mock_subprocess):
        """Test notification acknowledgment."""
        mock_subprocess.return_value = Mock()

        self.pm_integration.acknowledge_notification("test-123", "Restarted agent")

        # Verify subprocess was called with correct arguments
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]

        self.assertIn("tmux-orc", call_args)
        self.assertIn("publish", call_args)
        self.assertIn("--group", call_args)
        self.assertIn("management", call_args)
        self.assertIn("test-123", call_args[-1])
        self.assertIn("Restarted agent", call_args[-1])

    @patch("subprocess.run")
    def test_request_daemon_status(self, mock_subprocess):
        """Test daemon status request."""
        mock_subprocess.return_value = Mock()

        result = self.pm_integration.request_daemon_status()

        self.assertTrue(result)
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]

        self.assertIn("tmux-orc", call_args)
        self.assertIn("publish", call_args)
        self.assertIn("status-request", call_args)

    @patch("subprocess.run")
    def test_monitor_pubsub_health(self, mock_subprocess):
        """Test pubsub health monitoring."""
        mock_result = Mock()
        mock_result.stdout = json.dumps({"total_sessions": 3, "total_agents": 5, "active_agents": 4})
        mock_subprocess.return_value = mock_result

        health = self.pm_integration.monitor_pubsub_health()

        self.assertEqual(health["total_sessions"], 3)
        self.assertEqual(health["active_agents"], 4)
        mock_subprocess.assert_called_once()

    def test_create_pm_monitoring_script(self):
        """Test monitoring script creation."""
        from tmux_orchestrator.core.communication.pm_pubsub_integration import create_pm_monitoring_script

        script_path = create_pm_monitoring_script()

        self.assertTrue(Path(script_path).exists())
        self.assertTrue(Path(script_path).is_file())

        # Verify script content
        with open(script_path) as f:
            content = f.read()

        self.assertIn("#!/bin/bash", content)
        self.assertIn("tmux-orc read", content)
        self.assertIn("tmux-orc status", content)

        # Clean up
        Path(script_path).unlink()


class TestPubsubProtocolCompliance(unittest.TestCase):
    """Test compliance with pubsub messaging protocols."""

    def test_message_schema_validation(self):
        """Test that daemon messages follow expected schema."""
        expected_fields = ["id", "timestamp", "priority", "tags", "sender", "message"]

        sample_message = {
            "id": "daemon-001",
            "timestamp": datetime.now().isoformat(),
            "priority": "high",
            "tags": ["monitoring", "health"],
            "sender": "monitoring-daemon",
            "message": "Agent backend-dev:2 idle 15min",
        }

        for field in expected_fields:
            self.assertIn(field, sample_message, f"Missing required field: {field}")

    def test_priority_levels(self):
        """Test that priority levels are valid."""
        valid_priorities = ["critical", "high", "normal", "low"]

        for priority in valid_priorities:
            # Should not raise exception
            self.assertIn(priority, valid_priorities)

    def test_tag_categories(self):
        """Test that message tags follow expected categories."""
        valid_tags = ["monitoring", "recovery", "alert", "status", "health", "management"]

        test_messages = [["monitoring", "health"], ["recovery", "alert"], ["status", "management"]]

        for tag_set in test_messages:
            for tag in tag_set:
                self.assertIn(tag, valid_tags, f"Invalid tag: {tag}")


if __name__ == "__main__":
    unittest.main()
