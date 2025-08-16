#!/usr/bin/env python3
"""Focused test for PM crash detection functionality."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from tmux_orchestrator.core.monitor import AgentMonitor


class TestPMDetection(unittest.TestCase):
    """Test PM crash detection functionality."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary config
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test_config.json"

        # Mock config
        self.mock_config = Mock()
        self.mock_config.project_root = Path(self.temp_dir)
        self.mock_config.data_dir = Path(self.temp_dir) / "data"
        self.mock_config.data_dir.mkdir(exist_ok=True)

        # Create mock TMUX manager
        self.mock_tmux = Mock()

        # Create agent monitor
        self.daemon = AgentMonitor(config=self.mock_config, tmux=self.mock_tmux)

    def test_missing_pm_detection(self):
        """Test detection when PM window is completely missing."""
        print("Testing missing PM detection...")

        # Mock TMUXManager
        mock_tmux = Mock()
        mock_logger = Mock()

        # Mock _find_pm_window to return None (no PM window)
        with patch.object(self.daemon, "_find_pm_window", return_value=None):
            crashed, target = self.daemon._detect_pm_crash(mock_tmux, "test_session", mock_logger)

        # Should detect crash with no target
        self.assertTrue(crashed, "Should detect crash when PM window is missing")
        self.assertIsNone(target, "Target should be None when PM window is missing")

        print(f"✅ Missing PM test: crashed={crashed}, target={target}")

    def test_crash_indicator_detection(self):
        """Test detection when PM pane shows crash indicators."""
        print("Testing crash indicator detection...")

        # Mock TMUXManager
        mock_tmux = Mock()
        mock_logger = Mock()

        # Mock _find_pm_window to return a PM window
        test_target = "test_session:1"

        # Mock capture_pane to return content with crash indicator
        mock_tmux.capture_pane.return_value = "bash: tmux-orc: command not found\n$ "

        with patch.object(self.daemon, "_find_pm_window", return_value=test_target):
            crashed, target = self.daemon._detect_pm_crash(mock_tmux, "test_session", mock_logger)

        # Should detect crash with target
        self.assertTrue(crashed, "Should detect crash when crash indicators are present")
        self.assertEqual(target, test_target, "Target should be returned when PM window exists")

        print(f"✅ Crash indicator test: crashed={crashed}, target={target}")

    def test_healthy_pm_detection(self):
        """Test detection when PM is healthy."""
        print("Testing healthy PM detection...")

        # Mock TMUXManager
        mock_tmux = Mock()
        mock_logger = Mock()

        # Mock _find_pm_window to return a PM window
        test_target = "test_session:1"

        # Mock capture_pane to return normal Claude interface content
        mock_tmux.capture_pane.return_value = "Claude Code (tmux-orc-pm-123)\n\nI'm ready to help with your project. What would you like me to work on?\n\n> "

        with (
            patch.object(self.daemon, "_find_pm_window", return_value=test_target),
            patch("tmux_orchestrator.core.monitor.is_claude_interface_present", return_value=True),
        ):
            crashed, target = self.daemon._detect_pm_crash(mock_tmux, "test_session", mock_logger)

        # Should NOT detect crash but return target
        self.assertFalse(crashed, "Should not detect crash when PM is healthy")
        self.assertEqual(target, test_target, "Target should be returned when PM window exists")

        print(f"✅ Healthy PM test: crashed={crashed}, target={target}")


def run_focused_test():
    """Run the focused PM detection test."""
    print("=== PM Detection Test ===")

    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPMDetection)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total_tests - failures - errors

    print("\n=== Test Summary ===")
    print(f"Total: {total_tests}, Passed: {passed}, Failed: {failures}, Errors: {errors}")

    if failures + errors == 0:
        print("✅ All PM detection tests PASSED")
        return True
    else:
        print("❌ Some PM detection tests FAILED")
        for failure in result.failures:
            print(f"FAILURE: {failure[0]}")
            print(f"Details: {failure[1]}")
        for error in result.errors:
            print(f"ERROR: {error[0]}")
            print(f"Details: {error[1]}")
        return False


if __name__ == "__main__":
    success = run_focused_test()
    sys.exit(0 if success else 1)
