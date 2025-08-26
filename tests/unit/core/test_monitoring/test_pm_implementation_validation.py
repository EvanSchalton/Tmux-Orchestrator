#!/usr/bin/env python3
"""
Validation tests for the implemented PM recovery methods.
Tests the actual implementation that was just completed.
"""

import subprocess
from unittest.mock import Mock, patch

import pytest

from tmux_orchestrator.core.monitor import IdleMonitor

# TMUXManager import removed - using comprehensive_mock_tmux fixture


class TestPMImplementationValidation:
    """Test the actual PM recovery implementation."""

    def setup_method(self):
        """Setup for each test."""
        # self.tmux = comprehensive_mock_tmux  # Removed - use comprehensive_mock_tmux fixture
        self.test_sessions = []

    def teardown_method(self):
        """Cleanup after each test."""
        for session in self.test_sessions:
            try:
                subprocess.run(["tmux", "kill-session", "-t", session], capture_output=True)
            except Exception:
                pass
        self.test_sessions.clear()

    def test_pm_crash_detection_method_exists(self):
        """Test that _detect_pm_crash method exists and is callable."""
        monitor = IdleMonitor(self.tmux)

        # Test method exists
        assert hasattr(monitor, "_detect_pm_crash")

        # Test with mock inputs
        mock_logger = Mock()

        with patch.object(monitor, "_find_pm_window", return_value=None):
            crashed, target = monitor._detect_pm_crash(self.tmux, "test-session", mock_logger)

            # Should detect crash when no PM window found
            assert crashed is True
            assert target is None

    def test_pm_recovery_method_exists(self):
        """Test that _recover_crashed_pm method exists and is callable."""
        monitor = IdleMonitor(self.tmux)

        # Test method exists
        assert hasattr(monitor, "_recover_crashed_pm")

        # Test with mock inputs
        mock_logger = Mock()

        # Mock the spawn PM method to avoid actual spawning
        with patch.object(monitor, "_spawn_pm", return_value="test:1"):
            result = monitor._recover_crashed_pm(
                self.tmux,
                "test-session",
                None,  # No crashed target
                mock_logger,
            )

            # Should attempt recovery
            assert isinstance(result, bool)

    def test_pm_crash_detection_with_missing_pm(self):
        """Test crash detection when PM window is completely missing."""
        monitor = IdleMonitor(self.tmux)
        mock_logger = Mock()

        # Mock no PM window found
        with patch.object(monitor, "_find_pm_window", return_value=None):
            crashed, target = monitor._detect_pm_crash(self.tmux, "nonexistent-session", mock_logger)

            assert crashed is True, "Should detect crash when PM window missing"
            assert target is None, "Target should be None when window missing"

    def test_pm_crash_detection_with_crashed_pm(self):
        """Test crash detection when PM window exists but has crash indicators."""
        monitor = IdleMonitor(self.tmux)
        mock_logger = Mock()

        # Mock finding PM window but with crash content
        with (
            patch.object(monitor, "_find_pm_window", return_value="test:1"),
            patch.object(self.tmux, "capture_pane", return_value="bash-5.1$ command not found"),
        ):
            crashed, target = monitor._detect_pm_crash(self.tmux, "test-session", mock_logger)

            assert crashed is True, "Should detect crash with crash indicators"
            assert target == "test:1", "Should return the PM window target"

    def test_pm_crash_detection_with_healthy_pm(self):
        """Test crash detection when PM is healthy."""
        monitor = IdleMonitor(self.tmux)
        mock_logger = Mock()

        # Mock finding healthy PM window
        with (
            patch.object(monitor, "_find_pm_window", return_value="test:1"),
            patch.object(self.tmux, "capture_pane", return_value="I'm Claude, I can help you"),
            patch("tmux_orchestrator.core.monitor_helpers.is_claude_interface_present", return_value=True),
            patch.object(monitor, "_check_pm_health", return_value=True),
        ):
            crashed, target = monitor._detect_pm_crash(self.tmux, "test-session", mock_logger)

            assert crashed is False, "Should not detect crash for healthy PM"
            assert target == "test:1", "Should return the PM window target"

    def test_pm_recovery_cleanup_process(self):
        """Test PM recovery cleanup process."""
        monitor = IdleMonitor(self.tmux)
        mock_logger = Mock()

        # Mock successful cleanup and recovery
        with (
            patch.object(self.tmux, "kill_window") as mock_kill,
            patch.object(self.tmux, "list_windows", return_value=[{"index": "2"}]),
            patch.object(monitor, "_spawn_pm", return_value="test:1") as mock_spawn,
        ):
            result = monitor._recover_crashed_pm(
                self.tmux,
                "test-session",
                "test:2",  # Crashed PM target
                mock_logger,
            )

            # Should cleanup crashed PM
            mock_kill.assert_called_with("test:2")

            # Should spawn new PM
            mock_spawn.assert_called()

            assert result is True, "Recovery should succeed"

    def test_pm_recovery_retry_logic(self):
        """Test PM recovery retry logic when spawn fails initially."""
        monitor = IdleMonitor(self.tmux)
        mock_logger = Mock()

        # Mock spawn failing first time, succeeding second time
        spawn_results = [None, "test:1"]  # Fail, then succeed

        with (
            patch.object(self.tmux, "list_windows", return_value=[]),
            patch.object(monitor, "_spawn_pm", side_effect=spawn_results) as mock_spawn,
        ):
            result = monitor._recover_crashed_pm(self.tmux, "test-session", None, mock_logger, max_retries=2)

            # Should retry and eventually succeed
            assert mock_spawn.call_count == 2
            assert result is True

    def test_get_active_agents_method(self):
        """Test _get_active_agents method exists and works."""
        monitor = IdleMonitor(self.tmux)

        assert hasattr(monitor, "_get_active_agents")

        # Mock tmux session data
        with (
            patch.object(self.tmux, "list_sessions", return_value=["test-session"]),
            patch.object(
                self.tmux,
                "list_windows",
                return_value=[{"index": "1", "name": "PM"}, {"index": "2", "name": "developer"}],
            ),
        ):
            agents = monitor._get_active_agents()
            assert isinstance(agents, list)

    def test_team_notification_method(self):
        """Test team notification method exists."""
        monitor = IdleMonitor(self.tmux)

        assert hasattr(monitor, "_notify_team_of_pm_recovery")

        # Test basic call doesn't crash
        try:
            monitor._notify_team_of_pm_recovery("test-session", "test:1")
        except Exception as e:
            # Should not crash with basic inputs
            pytest.fail(f"Team notification crashed: {e}")

    def test_pm_crash_handling_method(self):
        """Test PM crash handling method exists."""
        monitor = IdleMonitor(self.tmux)

        assert hasattr(monitor, "_handle_pm_crash")

        # Test basic call
        with patch.object(monitor, "_recover_crashed_pm", return_value=True):
            try:
                monitor._handle_pm_crash("test:1")
            except Exception as e:
                pytest.fail(f"PM crash handling crashed: {e}")

    def test_spawn_replacement_pm_method(self):
        """Test spawn replacement PM method exists."""
        monitor = IdleMonitor(self.tmux)

        assert hasattr(monitor, "_spawn_replacement_pm")

        # Test with mocked spawn
        with patch.object(monitor, "_spawn_pm", return_value="test:1"):
            result = monitor._spawn_replacement_pm("test:2")
            assert isinstance(result, bool)

    def test_pane_corruption_detection(self):
        """Test pane corruption detection method."""
        monitor = IdleMonitor(self.tmux)

        assert hasattr(monitor, "_detect_pane_corruption")

        # Test with normal content
        with patch.object(self.tmux, "capture_pane", return_value="Normal text content"):
            corrupt = monitor._detect_pane_corruption("test:1")
            assert corrupt is False

        # Test with binary content
        with patch.object(self.tmux, "capture_pane", return_value="\x00\x01\xff\xfe"):
            corrupt = monitor._detect_pane_corruption("test:1")
            assert corrupt is True

    def test_terminal_reset_method(self):
        """Test terminal reset method exists."""
        monitor = IdleMonitor(self.tmux)

        assert hasattr(monitor, "_reset_terminal")

        # Test basic call
        result = monitor._reset_terminal("test:1")
        assert isinstance(result, bool)

    @pytest.mark.integration
    def test_end_to_end_crash_detection_flow(self):
        """Test end-to-end crash detection flow with mocked components."""
        monitor = IdleMonitor(self.tmux)
        mock_logger = Mock()

        # Simulate full crash detection and recovery flow
        with (
            patch.object(monitor, "_find_pm_window", return_value="test:1"),
            patch.object(self.tmux, "capture_pane", return_value="bash-5.1$ "),
            patch.object(monitor, "_spawn_pm", return_value="test:2"),
            patch.object(self.tmux, "kill_window"),
            patch.object(self.tmux, "list_windows", return_value=[]),
        ):
            # Detect crash
            crashed, target = monitor._detect_pm_crash(self.tmux, "test-session", mock_logger)
            assert crashed is True
            assert target == "test:1"

            # Recover crashed PM
            recovery_success = monitor._recover_crashed_pm(self.tmux, "test-session", target, mock_logger)
            assert recovery_success is True

    def test_all_required_methods_implemented(self):
        """Verify all required PM recovery methods are implemented."""
        monitor = IdleMonitor(self.tmux)

        required_methods = [
            "_detect_pm_crash",
            "_recover_crashed_pm",
            "_get_active_agents",
            "_notify_team_of_pm_recovery",
            "_handle_pm_crash",
            "_spawn_replacement_pm",
            "_detect_pane_corruption",
            "_reset_terminal",
        ]

        missing_methods = []
        for method in required_methods:
            if not hasattr(monitor, method):
                missing_methods.append(method)

        assert len(missing_methods) == 0, f"Missing methods: {missing_methods}"

        print("✅ All required PM recovery methods are implemented!")


if __name__ == "__main__":
    # Run validation tests
    test = TestPMImplementationValidation()

    try:
        test.setup_method()

        print("Validating PM Recovery Implementation")
        print("=" * 50)

        # Test all methods
        test_methods = [
            "test_pm_crash_detection_method_exists",
            "test_pm_recovery_method_exists",
            "test_pm_crash_detection_with_missing_pm",
            "test_pm_crash_detection_with_crashed_pm",
            "test_pm_crash_detection_with_healthy_pm",
            "test_pm_recovery_cleanup_process",
            "test_pm_recovery_retry_logic",
            "test_get_active_agents_method",
            "test_team_notification_method",
            "test_pm_crash_handling_method",
            "test_spawn_replacement_pm_method",
            "test_pane_corruption_detection",
            "test_terminal_reset_method",
            "test_end_to_end_crash_detection_flow",
            "test_all_required_methods_implemented",
        ]

        passed = 0
        failed = 0

        for test_method in test_methods:
            print(f"\nTesting {test_method}...")

            try:
                method = getattr(test, test_method)
                method()
                print(f"✅ {test_method}: PASSED")
                passed += 1

            except Exception as e:
                print(f"❌ {test_method}: FAILED - {e}")
                failed += 1

        print("\n" + "=" * 50)
        print(f"VALIDATION RESULTS: {passed} passed, {failed} failed")

        if failed == 0:
            print("🎉 ALL TESTS PASSED - PM Recovery implementation is validated!")

    finally:
        test.teardown_method()
        print("\nValidation cleanup completed.")
