#!/usr/bin/env python3
"""
Test Cases for False Positive Detection Fix Verification

This comprehensive test suite verifies that the false positive detection fix
properly distinguishes between:
1. Claude UI with error keywords (should NOT kill)
2. Actual crashes without Claude UI (SHOULD kill)

Run this after developer implements the fix to verify it works correctly.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tmux_orchestrator.core.monitor import IdleMonitor  # noqa: E402
from tmux_orchestrator.core.monitor_helpers import is_claude_interface_present  # noqa: E402


class TestFalsePositiveFix:
    """Comprehensive test suite for false positive fix verification."""

    @pytest.fixture
    def mock_tmux(self):
        """Create mock TMUXManager."""
        tmux = Mock()
        tmux.list_sessions.return_value = [{"name": "test-session"}]
        tmux.list_windows.return_value = [{"index": "1", "name": "Claude-PM"}]
        return tmux

    @pytest.fixture
    def monitor(self, mock_tmux):
        """Create IdleMonitor instance."""
        with patch("tmux_orchestrator.core.monitor.Config"):
            return IdleMonitor(mock_tmux)

    def test_comprehensive_false_positive_scenarios(self, mock_tmux, monitor):
        """Test all scenarios where PM should NOT be killed despite error keywords."""
        test_cases = [
            # Test failures
            {
                "name": "Unit test failures",
                "content": """╭─ Assistant ─────────────────────────────────────────────────────╮
│ Running tests... 5 tests failed:                               │
│ • test_auth.py::test_login failed                              │
│ • test_db.py::test_connection failed with timeout              │
│ • test_api.py::test_validation failed                          │
│ Fixing these test failures now...                              │
╰─────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────╮
│ > Analyzing test failures...                                   │
╰─────────────────────────────────────────────────────────────────╯""",
                "keywords": ["failed", "timeout"],
            },
            # Build/deployment failures
            {
                "name": "Build and deployment failures",
                "content": """╭─ Assistant ─────────────────────────────────────────────────────╮
│ Build failed with errors:                                      │
│ ERROR: TypeScript compilation failed                           │
│ FATAL: Webpack build terminated                                │
│ npm ERR! Exit status 1                                        │
│                                                                 │
│ Deployment also failed:                                        │
│ • Connection refused to server                                 │
│ • Permission denied for deploy user                            │
│ • Process killed by resource limits                            │
╰─────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────╮
│ > Fixing build configuration...                                │
╰─────────────────────────────────────────────────────────────────╯""",
                "keywords": ["failed", "error", "fatal", "terminated", "exit", "refused", "denied", "killed"],
            },
            # System errors and crashes
            {
                "name": "Analyzing system crashes",
                "content": """╭─ Assistant ─────────────────────────────────────────────────────╮
│ Found the crash logs:                                          │
│ • Segmentation fault at 0x7fff8000                            │
│ • Core dumped in /var/crash/                                  │
│ • Process terminated with signal 11                           │
│ • Kernel panic detected in dmesg                              │
│ • Thread abort() called                                       │
│                                                                 │
│ Implementing crash prevention measures...                      │
╰─────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────╮
│ > Adding signal handlers...                                    │
╰─────────────────────────────────────────────────────────────────╯""",
                "keywords": ["segmentation fault", "core dumped", "terminated", "signal", "panic", "abort"],
            },
            # Network and connection errors
            {
                "name": "Network connection issues",
                "content": """╭─ Assistant ─────────────────────────────────────────────────────╮
│ Multiple connection issues detected:                           │
│ • Connection lost to database                                  │
│ • Broken pipe when sending data                               │
│ • Connection timeout after 30s                                │
│ • No such file or directory: /tmp/socket                      │
│ • Resource temporarily unavailable                            │
│                                                                 │
│ Implementing retry logic with exponential backoff...           │
╰─────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────╮
│ > Creating connection pool...                                  │
╰─────────────────────────────────────────────────────────────────╯""",
                "keywords": ["connection lost", "broken pipe", "timeout", "no such file", "unavailable"],
            },
            # Command execution errors
            {
                "name": "Command execution errors",
                "content": """╭─ Assistant ─────────────────────────────────────────────────────╮
│ Several commands failed:                                       │
│ • bash: command not found: node                               │
│ • zsh: killed     python script.py                            │
│ • $: syntax error near unexpected token                       │
│ • traceback (most recent call last):                          │
│   File "test.py", line 42                                    │
│   SyntaxError: invalid syntax                                 │
│                                                                 │
│ Installing missing dependencies...                             │
╰─────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────╮
│ > Running npm install...                                       │
╰─────────────────────────────────────────────────────────────────╯""",
                "keywords": ["command not found", "killed", "$", "traceback", "error"],
            },
        ]

        for test_case in test_cases:
            mock_tmux.capture_pane.return_value = test_case["content"]

            # Verify Claude UI is present
            assert is_claude_interface_present(test_case["content"]), f"Claude UI not detected in: {test_case['name']}"

            # Test crash detection - should NOT detect as crashed
            is_crashed, target = monitor._detect_pm_crash(mock_tmux, "test-session", Mock())

            assert not is_crashed, (
                f"FALSE POSITIVE: {test_case['name']} - PM would be killed despite having Claude UI\n"
                f"Keywords present: {', '.join(test_case['keywords'])}"
            )

    def test_actual_crashes_still_detected(self, mock_tmux, monitor):
        """Verify that actual crashes are still properly detected."""
        crash_scenarios = [
            {"name": "Clean bash prompt", "content": "user@hostname:~/project$ ", "reason": "No Claude UI, just shell"},
            {
                "name": "Claude not found",
                "content": "bash: claude: command not found\nuser@host:~$ ",
                "reason": "Claude binary missing",
            },
            {
                "name": "Process terminated cleanly",
                "content": "[Process completed - press Enter to close]\nuser@host:~$ ",
                "reason": "Claude exited normally",
            },
            {
                "name": "Killed process",
                "content": "Killed\n[1]+  Killed                  claude --dangerously-skip-permissions\n$ ",
                "reason": "Claude was killed",
            },
            {
                "name": "Segfault without UI",
                "content": "Segmentation fault (core dumped)\n$ ",
                "reason": "Claude crashed",
            },
            {"name": "Empty terminal", "content": "\n\n", "reason": "No content at all"},
            {
                "name": "System message only",
                "content": "System is going down for reboot NOW!\n",
                "reason": "System shutdown",
            },
        ]

        for scenario in crash_scenarios:
            mock_tmux.capture_pane.return_value = scenario["content"]

            # Verify NO Claude UI
            assert not is_claude_interface_present(
                scenario["content"]
            ), f"Claude UI incorrectly detected in crash scenario: {scenario['name']}"

            # Test crash detection - SHOULD detect as crashed
            is_crashed, target = monitor._detect_pm_crash(mock_tmux, "test-session", Mock())

            assert (
                is_crashed
            ), f"FALSE NEGATIVE: Failed to detect crash in '{scenario['name']}'\nReason: {scenario['reason']}"

    def test_edge_cases(self, mock_tmux, monitor):
        """Test edge cases for crash detection."""
        edge_cases = [
            {
                "name": "Partial Claude UI with errors",
                "content": """╭─ Assistant ─────
│ Working on failed tests...
[ERROR] Connection lost""",
                "should_crash": False,  # Has partial Claude UI
                "reason": "Partial UI indicates Claude is still running",
            },
            {
                "name": "Claude startup with previous errors",
                "content": """user@host:~$ claude
Previous session failed
Starting Claude...

╭─ Assistant ─────────────────────────────────────────────────────╮
│ Hello! How can I help you today?                              │
╰─────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────╮
│ > _                                                            │
╰─────────────────────────────────────────────────────────────────╯""",
                "should_crash": False,
                "reason": "Claude successfully started despite previous errors",
            },
            {
                "name": "Error keywords in user input",
                "content": """╭─ Human ─────────────────────────────────────────────────────────╮
│ My deployment failed and the process was killed. Can you help? │
╰─────────────────────────────────────────────────────────────────╯

╭─ Assistant ─────────────────────────────────────────────────────╮
│ I'll help you debug the failed deployment...                   │
╰─────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────╮
│ > Let me check the logs...                                     │
╰─────────────────────────────────────────────────────────────────╯""",
                "should_crash": False,
                "reason": "Error keywords in conversation, not actual errors",
            },
        ]

        for case in edge_cases:
            mock_tmux.capture_pane.return_value = case["content"]

            is_crashed, target = monitor._detect_pm_crash(mock_tmux, "test-session", Mock())

            if case["should_crash"]:
                assert is_crashed, f"Edge case '{case['name']}' should detect crash: {case['reason']}"
            else:
                assert not is_crashed, f"Edge case '{case['name']}' should NOT detect crash: {case['reason']}"

    def test_recovery_scenarios(self, mock_tmux, monitor):
        """Test PM recovery scenarios to prevent death loops."""
        # Simulate PM just recovered and immediately talks about previous failure
        recovery_content = """╭─ Assistant ─────────────────────────────────────────────────────╮
│ I've been recovered after the previous session failed.         │
│ The error was: connection terminated unexpectedly              │
│ Let me continue where we left off...                          │
╰─────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────╮
│ > Resuming task...                                             │
╰─────────────────────────────────────────────────────────────────╯"""

        mock_tmux.capture_pane.return_value = recovery_content

        is_crashed, target = monitor._detect_pm_crash(mock_tmux, "test-session", Mock())

        assert not is_crashed, "CRITICAL: Recovered PM would be immediately killed again, creating death loop"


def run_verification_tests():
    """Run all verification tests and report results."""
    print("🧪 Running False Positive Fix Verification Tests")
    print("=" * 70)

    # Run pytest programmatically
    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"], capture_output=True, text=True
    )

    print(result.stdout)
    if result.stderr:
        print("Errors:", result.stderr)

    if result.returncode == 0:
        print("\n✅ ALL TESTS PASSED - False positive fix is working correctly!")
        print("The developer's fix properly distinguishes between:")
        print("  • Claude UI with error keywords → NOT killed ✓")
        print("  • Actual crashes without UI → Properly killed ✓")
    else:
        print("\n❌ TESTS FAILED - False positive fix needs more work")
        print("Check the test output above for specific failures")

    return result.returncode


if __name__ == "__main__":
    sys.exit(run_verification_tests())
