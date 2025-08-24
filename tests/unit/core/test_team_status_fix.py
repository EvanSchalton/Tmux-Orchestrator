#!/usr/bin/env python3
"""Test the team status error detection fix."""

import unittest

from tmux_orchestrator.core.team_operations.get_team_status import _determine_window_status, _is_actual_error


class MockTMUXManager:
    """Mock TMUXManager for testing."""

    def _is_idle(self, pane_content: str) -> bool:
        """Simple idle check for testing."""
        idle_patterns = ["waiting for", "ready for", "idle"]
        return any(pattern in pane_content.lower() for pattern in idle_patterns)


class TestTeamStatusFix(unittest.TestCase):
    """Test cases for the team status error detection fix."""

    def setUp(self):
        """Set up test fixtures."""
        self.tmux = MockTMUXManager()

    def test_agent_discussing_errors_not_marked_as_error(self):
        """Test that agents discussing errors aren't marked as error state."""
        test_cases = [
            "I'm working on improving the error handling in the authentication module.",
            "Let me fix the error message that appears when users input invalid data.",
            "The error checking logic needs to be more robust.",
            "I'll implement better error reporting for the API endpoints.",
            "Working on error boundaries for the React components.",
        ]

        for content in test_cases:
            status, _, health = _determine_window_status(self.tmux, content)
            self.assertNotEqual(status, "Error", f"False positive for: {content}")
            self.assertGreater(health, 0.5, f"Health too low for: {content}")

    def test_actual_errors_are_detected(self):
        """Test that actual errors are properly detected."""
        test_cases = [
            "Traceback (most recent call last):\n  File 'test.py', line 10\nNameError: name 'x' is not defined",
            "Error: Failed to connect to database",
            "Fatal error: Cannot allocate memory",
            "bash: command not found: tmux-orc",
            "Permission denied: /etc/passwd",
            "Segmentation fault (core dumped)",
            "panic: runtime error: index out of range",
            "I encountered an error while trying to read the file.",
        ]

        for content in test_cases:
            status, _, health = _determine_window_status(self.tmux, content)
            self.assertEqual(status, "Error", f"Failed to detect error in: {content}")
            self.assertLess(health, 0.5, f"Health too high for error: {content}")

    def test_idle_status_detection(self):
        """Test idle status detection."""
        test_cases = [
            "Waiting for further instructions...",
            "Ready for next task.",
            "I'm idle and awaiting your commands.",
        ]

        for content in test_cases:
            status, _, health = _determine_window_status(self.tmux, content)
            self.assertEqual(status, "Idle", f"Failed to detect idle in: {content}")
            self.assertAlmostEqual(health, 0.7, places=1)

    def test_active_status_detection(self):
        """Test active status detection."""
        test_cases = [
            "I'm implementing the new feature you requested.",
            "Working on the database schema updates.",
            "Creating unit tests for the authentication module.",
            "Updating the documentation with the new API endpoints.",
        ]

        for content in test_cases:
            status, _, health = _determine_window_status(self.tmux, content)
            self.assertEqual(status, "Active", f"Failed to detect active in: {content}")
            self.assertEqual(health, 1.0)

    def test_is_actual_error_function(self):
        """Test the _is_actual_error helper function."""
        # Should not be errors
        false_cases = [
            "Working on error handling",
            "Improving error messages",
            "The error checking is important",
            "Let me add error boundaries",
        ]

        for content in false_cases:
            self.assertFalse(_is_actual_error(content), f"False positive in _is_actual_error: {content}")

        # Should be errors
        true_cases = [
            "Traceback (most recent call last): error in module",
            "Error: Failed to initialize",
            "Fatal error occurred",
            "I encountered an error",
        ]

        for content in true_cases:
            self.assertTrue(_is_actual_error(content), f"Failed to detect error in _is_actual_error: {content}")


if __name__ == "__main__":
    unittest.main()
