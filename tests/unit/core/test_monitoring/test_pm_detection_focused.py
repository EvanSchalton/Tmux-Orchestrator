#!/usr/bin/env python3
"""Focused test for PM crash detection functionality."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from tmux_orchestrator.core.monitor import IdleMonitor


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
        # Ensure logs directory exists
        (Path(self.temp_dir) / "logs").mkdir(exist_ok=True)

        # Create mock TMUX manager
        self.mock_tmux = Mock()

        # Create mock logger
        self.mock_logger = Mock()

        # Create idle monitor (which has PM crash detection)
        self.daemon = IdleMonitor(tmux=self.mock_tmux)

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
            # The detection requires 3 observations within the observation window
            # Call detection multiple times to trigger crash declaration
            crashed1, target1 = self.daemon._detect_pm_crash(mock_tmux, "test_session", mock_logger)
            crashed2, target2 = self.daemon._detect_pm_crash(mock_tmux, "test_session", mock_logger)
            crashed3, target3 = self.daemon._detect_pm_crash(mock_tmux, "test_session", mock_logger)

        # First two calls should return False (building observations)
        self.assertFalse(crashed1, "First observation should not declare crash yet")
        self.assertFalse(crashed2, "Second observation should not declare crash yet")

        # Third call should detect crash with target
        self.assertTrue(crashed3, "Should detect crash after 3 observations of crash indicators")
        self.assertEqual(target3, test_target, "Target should be returned when PM window exists")

        print(f"✅ Crash indicator test: observations 1,2,3: {crashed1},{crashed2},{crashed3}, target={target3}")

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
