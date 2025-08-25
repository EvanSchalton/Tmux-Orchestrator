#!/usr/bin/env python3
"""
Critical Test Cases: PM False Positive Detection

This test suite validates that PMs are:
1. NOT killed when outputting legitimate error/failure messages
2. ONLY killed when the Claude process actually exits/crashes

CRITICAL BUG: monitor.py line 1724 includes "failed" in crash_indicators
"""

from unittest.mock import Mock, patch

import pytest

from tmux_orchestrator.core.monitor import IdleMonitor
from tmux_orchestrator.core.monitor_helpers import AgentState, detect_agent_state, is_claude_interface_present


class TestPMFalsePositiveDetection:
    """Test suite for PM false positive detection issues."""

    @pytest.fixture
    def mock_tmux(self):
        """Create a mock TMUXManager."""
        tmux = Mock()
        tmux.list_sessions.return_value = [{"name": "test-session"}]
        tmux.list_windows.return_value = [{"index": "1", "name": "Claude-PM"}]
        return tmux

    @pytest.fixture
    def monitor(self, mock_tmux):
        """Create an IdleMonitor with mock dependencies."""
        with patch("tmux_orchestrator.core.monitor.Config"):
            return IdleMonitor(mock_tmux)

    def test_pm_not_killed_when_reporting_test_failures(self, mock_tmux, monitor):
        """PM should NOT be killed when reporting test failures."""
        # PM reporting test failures - this is NORMAL operation
        pm_content = """╭─ Assistant ─────────────────────────────────────────────────────╮
│ I ran the test suite and found several issues:                 │
│                                                                 │
│ ❌ 3 tests failed in authentication module                     │
│ ❌ Database connection test failed                             │
│ ❌ API validation tests failed with timeout                    │
│                                                                 │
│ Let me analyze these test failures and fix them...            │
╰─────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────╮
│ > Working on fixing the failed tests...                        │
╰─────────────────────────────────────────────────────────────────╯"""

        # Mock the capture_pane to return our PM content
        mock_tmux.capture_pane.return_value = pm_content

        # Check if Claude interface is detected
        assert is_claude_interface_present(pm_content) is True

        # Check agent state - should NOT be crashed
        state = detect_agent_state(pm_content)
        assert state != AgentState.CRASHED, "PM incorrectly detected as crashed when reporting test failures"

        # Verify the PM would NOT be killed
        is_crashed, target = monitor._detect_pm_crash(mock_tmux, "test-session", Mock())

        # EXPECTED: is_crashed should be False (PM is healthy)
        # ACTUAL BUG: is_crashed will be True due to "failed" in crash_indicators
        assert is_crashed is False, "CRITICAL BUG: PM would be killed for reporting test failures"

    def test_pm_not_killed_when_reporting_deployment_errors(self, mock_tmux, monitor):
        """PM should NOT be killed when reporting deployment errors."""
        pm_content = """╭─ Assistant ─────────────────────────────────────────────────────╮
│ The deployment encountered several errors:                      │
│                                                                 │
│ • Database migration failed - rolling back                     │
│ • Service startup error on port 8080                          │
│ • Health check failed after 3 retries                         │
│ • SSL certificate error detected                              │
│                                                                 │
│ I'm working on resolving these deployment errors now...        │
╰─────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────╮
│ > Checking database migration logs...                          │
╰─────────────────────────────────────────────────────────────────╯"""

        mock_tmux.capture_pane.return_value = pm_content

        # Verify Claude interface is present
        assert is_claude_interface_present(pm_content) is True

        # Check that PM is not detected as crashed
        state = detect_agent_state(pm_content)
        assert state != AgentState.CRASHED, "PM incorrectly detected as crashed when reporting deployment errors"

        # Test with actual monitor method
        is_crashed, target = monitor._detect_pm_crash(mock_tmux, "test-session", Mock())
        assert is_crashed is False, "CRITICAL BUG: PM would be killed for reporting deployment errors"

    def test_pm_not_killed_when_analyzing_errors(self, mock_tmux, monitor):
        """PM should NOT be killed when analyzing error logs."""
        pm_content = """╭─ Assistant ─────────────────────────────────────────────────────╮
│ I'm analyzing the error logs from the application:             │
│                                                                 │
│ ERROR: Connection timeout at database.connect()                │
│ ERROR: Authentication failed for user 'admin'                  │
│ CRITICAL: Memory allocation error in worker process            │
│ FATAL: Unhandled exception in main thread                      │
│                                                                 │
│ These errors indicate we need to fix the connection pool...    │
╰─────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────╮
│ > Implementing connection pool fixes...                        │
╰─────────────────────────────────────────────────────────────────╯"""

        mock_tmux.capture_pane.return_value = pm_content

        assert is_claude_interface_present(pm_content) is True

        state = detect_agent_state(pm_content)
        assert state != AgentState.CRASHED, "PM incorrectly detected as crashed when analyzing errors"

        is_crashed, target = monitor._detect_pm_crash(mock_tmux, "test-session", Mock())
        assert is_crashed is False, "CRITICAL BUG: PM would be killed for analyzing error logs"

    def test_pm_not_killed_legitimate_keywords(self, mock_tmux, monitor):
        """Test comprehensive list of legitimate keywords that should NOT kill PM."""
        # Keywords that appear in crash_indicators but are legitimate in PM output
        test_keywords = [
            "failed",
            "error",
            "exception",
            "timeout",
            "killed",
            "terminated",
            "fatal error",
            "panic:",
            "abort",
            "permission denied",
            "no such file",
            "exit code",
            "connection refused",
            "connection lost",
            "broken pipe",
        ]

        for keyword in test_keywords:
            pm_content = f"""╭─ Assistant ─────────────────────────────────────────────────────╮
│ Working on the issue where {keyword} occurred...               │
│ I'll fix this problem now.                                     │
╰─────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────╮
│ > Implementing the fix...                                      │
╰─────────────────────────────────────────────────────────────────╯"""

            mock_tmux.capture_pane.return_value = pm_content

            assert is_claude_interface_present(pm_content) is True, f"Claude UI not detected with keyword: {keyword}"

            is_crashed, target = monitor._detect_pm_crash(mock_tmux, "test-session", Mock())
            assert is_crashed is False, f"CRITICAL BUG: PM would be killed for mentioning '{keyword}'"

    def test_pm_is_killed_when_claude_process_exits(self, mock_tmux, monitor):
        """PM SHOULD be killed when Claude process actually exits."""
        # Test various actual crash scenarios
        crash_scenarios = [
            {
                "name": "Claude process terminated",
                "content": "Terminated\nuser@hostname:~/project$ ",
                "reason": "Process was terminated, only bash prompt remains",
            },
            {
                "name": "Claude command not found",
                "content": "claude: command not found\nuser@dev:~$ ",
                "reason": "Claude binary not available, process never started",
            },
            {
                "name": "Segmentation fault",
                "content": "Segmentation fault (core dumped)\nroot@container:/# ",
                "reason": "Process crashed with segfault",
            },
            {
                "name": "Just bash prompt",
                "content": "user@tmux-orc:~/workspace$ \n",
                "reason": "Only shell prompt, no Claude interface",
            },
            {
                "name": "Process killed",
                "content": "Killed\n[1]+  Killed                  claude --dangerously-skip-permissions\nuser@host:~$ ",
                "reason": "Claude process was killed",
            },
        ]

        for scenario in crash_scenarios:
            mock_tmux.capture_pane.return_value = scenario["content"]

            # Verify NO Claude interface is present
            assert (
                is_claude_interface_present(scenario["content"]) is False
            ), f"Claude UI incorrectly detected in: {scenario['name']}"

            # Verify crash IS detected
            is_crashed, target = monitor._detect_pm_crash(mock_tmux, "test-session", Mock())
            assert is_crashed is True, f"Failed to detect crash in scenario: {scenario['name']}"

    def test_pm_health_check_during_normal_operation(self, mock_tmux, monitor):
        """Test PM health check doesn't trigger false positives during normal operation."""
        # Simulate PM working normally over time
        pm_states = [
            # State 1: PM analyzing code
            """╭─ Assistant ─────────────────────────────────────────────────────╮
│ Analyzing the codebase for potential issues...                 │
╰─────────────────────────────────────────────────────────────────╯""",
            # State 2: PM finds issues
            """╭─ Assistant ─────────────────────────────────────────────────────╮
│ Found several issues that failed validation:                   │
│ - Security check failed on API endpoints                       │
│ - Unit tests failed in auth module                            │
╰─────────────────────────────────────────────────────────────────╯""",
            # State 3: PM fixing issues
            """╭─ Assistant ─────────────────────────────────────────────────────╮
│ Fixed the failed security checks and tests. All passing now!  │
╰─────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────╮
│ > Running final verification...                                │
╰─────────────────────────────────────────────────────────────────╯""",
        ]

        for i, state in enumerate(pm_states):
            mock_tmux.capture_pane.return_value = state

            # Each state should show PM as healthy
            is_crashed, target = monitor._detect_pm_crash(mock_tmux, "test-session", Mock())
            assert is_crashed is False, f"PM incorrectly detected as crashed in state {i + 1}"

    def test_pm_recovery_after_false_positive(self, mock_tmux, monitor):
        """Test that PM recovery doesn't immediately retrigger false positive."""
        # Simulate PM just recovered and reporting status
        pm_recovered_content = """╭─ Assistant ─────────────────────────────────────────────────────╮
│ I've been recovered. Let me check what failed previously...    │
│                                                                 │
│ Previous session failed due to:                                │
│ - Test suite failed with 5 errors                             │
│ - Deployment failed on staging server                         │
│                                                                 │
│ Resuming work on these issues now.                            │
╰─────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────╮
│ > Analyzing the test failures...                               │
╰─────────────────────────────────────────────────────────────────╯"""

        mock_tmux.capture_pane.return_value = pm_recovered_content

        # PM should not be immediately killed again
        is_crashed, target = monitor._detect_pm_crash(mock_tmux, "test-session", Mock())
        assert is_crashed is False, "CRITICAL BUG: Recovered PM immediately killed again due to false positive"


@pytest.mark.parametrize(
    "error_keyword,context",
    [
        ("failed", "Build failed with exit code 1"),
        ("error", "TypeError: undefined is not a function"),
        ("exception", "Unhandled exception in async handler"),
        ("timeout", "Request timeout after 30 seconds"),
        ("killed", "Previous process was killed"),
        ("fatal", "Fatal error in database connection"),
        ("panic", "Panic: runtime error"),
        ("abort", "Operation aborted by user"),
        ("denied", "Permission denied accessing /root"),
        ("refused", "Connection refused to localhost:5432"),
    ],
)
def test_parametrized_false_positives(mock_tmux, error_keyword, context):
    """Parametrized test for various error keywords in legitimate PM output."""
    monitor = IdleMonitor(mock_tmux)

    pm_content = f"""╭─ Assistant ─────────────────────────────────────────────────────╮
│ I found an issue: {context}                                    │
│ Let me fix this problem.                                       │
╰─────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────╮
│ > Working on the solution...                                   │
╰─────────────────────────────────────────────────────────────────╯"""

    mock_tmux.capture_pane.return_value = pm_content

    is_crashed, target = monitor._detect_pm_crash(mock_tmux, "test-session", Mock())
    assert is_crashed is False, f"PM killed for legitimate use of '{error_keyword}' in: {context}"


def test_edge_case_pm_compiling_with_errors():
    """Test PM showing compilation errors should not be killed."""
    pm_content = """╭─ Assistant ─────────────────────────────────────────────────────╮
│ Compilation failed with errors:                                │
│                                                                 │
│ main.c:42: error: 'undefined_var' undeclared                  │
│ main.c:43: error: expected ';' before '}' token               │
│ main.c:45: fatal error: missing.h: No such file or directory  │
│                                                                 │
│ Fixing these compilation errors now...                         │
╰─────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────╮
│ > Adding missing header file...                                │
╰─────────────────────────────────────────────────────────────────╯"""

    assert is_claude_interface_present(pm_content) is True
    state = detect_agent_state(pm_content)
    assert state != AgentState.CRASHED, "PM showing compilation errors detected as crashed"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
