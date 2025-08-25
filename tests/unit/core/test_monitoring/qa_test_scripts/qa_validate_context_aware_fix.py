#!/usr/bin/env python3
"""
QA Validation Script for Context-Aware Crash Detection Fix

This script validates the implementation of context-aware pattern matching
based on the status report recommendations to prevent false positive PM kills.

Status Report: .tmux_orchestrator/planning/2025-08-15T22-30-00-daemon-recovery-improvements/status-report.md
"""

import re
import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent))

from tmux_orchestrator.core.monitor import IdleMonitor  # noqa: E402


class ContextAwareValidator:
    """Validates context-aware crash detection implementation."""

    def __init__(self):
        self.results = {"passed": 0, "failed": 0, "details": []}

    def validate_safe_contexts(self) -> None:
        """Validate that safe contexts don't trigger false positives."""
        print("\n🧪 Testing SAFE CONTEXTS (should NOT trigger PM kill)")
        print("=" * 70)

        safe_contexts = [
            # Test results
            ("3 tests failed in authentication module", "test results"),
            ("Unit test suite failed: 5 errors", "test suite"),
            ("Integration tests failed with timeout", "integration tests"),
            ("Test runner failed to complete", "test runner"),
            # Build outputs
            ("Build failed: TypeScript compilation error", "build error"),
            ("Docker build failed at step 5", "docker build"),
            ("npm build failed with exit code 1", "npm build"),
            ("Webpack compilation failed", "webpack"),
            # CI/CD
            ("GitHub Actions job 'test' failed", "CI job"),
            ("Jenkins pipeline failed at deploy stage", "Jenkins"),
            ("GitLab CI workflow failed", "GitLab CI"),
            ("CircleCI build failed", "CircleCI"),
            # Deployment
            ("Deployment to production failed - rolling back", "deployment rollback"),
            ("Staging deployment failed: timeout", "staging deploy"),
            ("Canary deployment failed health checks", "canary deploy"),
            ("Blue-green deployment failed", "blue-green"),
            # Status reports
            ("Previous attempt failed, retrying...", "retry context"),
            ("The last sync failed at 14:30", "sync status"),
            ("Backup job failed but will retry", "backup status"),
            ("Migration failed - investigating", "migration"),
            # Error analysis
            ("Analyzing why the deployment failed", "analysis"),
            ("The request failed due to timeout", "request analysis"),
            ("Found that authentication failed", "auth analysis"),
            ("Database connection failed earlier", "db analysis"),
            # Tool output
            ("⎿ Security scan: 3 checks failed", "tool output"),
            ("│ FAILED: SQL injection test", "tool output line"),
            ("└ Total failed: 5", "tool summary"),
        ]

        # Test each safe context
        for content, description in safe_contexts:
            result = self._test_safe_context(content, description)
            if result:
                self.results["passed"] += 1
                print(f"✅ {description}: '{content}'")
            else:
                self.results["failed"] += 1
                print(f"❌ {description}: '{content}' - WOULD KILL PM!")
                self.results["details"].append(f"False positive: {content}")

    def validate_unsafe_contexts(self) -> None:
        """Validate that real crashes are still detected."""
        print("\n🧪 Testing UNSAFE CONTEXTS (SHOULD trigger detection)")
        print("=" * 70)

        unsafe_contexts = [
            ("failed", "isolated keyword"),
            ("Killed", "process killed"),
            ("Terminated", "process terminated"),
            ("$ failed", "shell prompt error"),
            ("bash: command failed", "bash error"),
            ("Segmentation fault", "segfault"),
            ("core dumped", "core dump"),
            ("user@host:~$ ", "bare shell prompt"),
            ("[Process completed]", "process ended"),
        ]

        for content, description in unsafe_contexts:
            result = self._test_unsafe_context(content, description)
            if result:
                self.results["passed"] += 1
                print(f"✅ {description}: '{content}' - Would detect crash")
            else:
                self.results["failed"] += 1
                print(f"❌ {description}: '{content}' - MISSED CRASH!")
                self.results["details"].append(f"False negative: {content}")

    def validate_regex_patterns(self) -> None:
        """Validate the regex patterns from status report."""
        print("\n🧪 Testing REGEX PATTERNS from status report")
        print("=" * 70)

        patterns = [
            r"test.*failed",
            r"check.*failed",
            r"Tests failed:",
            r"Build failed:",
        ]

        test_cases = [
            # Should match
            ("unit test failed", True),
            ("3 tests failed", True),
            ("health check failed", True),
            ("security checks failed", True),
            ("Tests failed: 5/20", True),
            ("Build failed: missing deps", True),
            # Should not match
            ("failed", False),
            ("just failed", False),
            ("failure", False),
        ]

        for text, should_match in test_cases:
            matched = any(re.search(p, text, re.IGNORECASE) for p in patterns)
            if matched == should_match:
                self.results["passed"] += 1
                print(f"✅ '{text}' - Match: {matched} (expected)")
            else:
                self.results["failed"] += 1
                print(f"❌ '{text}' - Match: {matched} (expected: {should_match})")

    def _test_safe_context(self, content: str, description: str) -> bool:
        """Test if safe context prevents false positive."""
        # Create PM-like content with Claude UI
        pm_content = f"""╭─ Assistant ─────────────────────────────────────────────────────╮
│ {content}                                                      │
│ Let me fix this issue...                                      │
╰─────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────╮
│ > Working on solution...                                       │
╰─────────────────────────────────────────────────────────────────╯"""

        # Test with actual monitor
        mock_tmux = Mock()
        mock_tmux.capture_pane.return_value = pm_content
        mock_tmux.list_sessions.return_value = [{"name": "test"}]
        mock_tmux.list_windows.return_value = [{"index": "1", "name": "Claude-PM"}]

        with patch("tmux_orchestrator.core.monitor.Config"):
            monitor = IdleMonitor(mock_tmux)

        is_crashed, _ = monitor._detect_pm_crash(mock_tmux, "test", Mock())

        # Should NOT be crashed (return True if correctly not crashed)
        return not is_crashed

    def _test_unsafe_context(self, content: str, description: str) -> bool:
        """Test if unsafe context is properly detected."""
        # Unsafe contexts typically don't have Claude UI
        mock_tmux = Mock()
        mock_tmux.capture_pane.return_value = content
        mock_tmux.list_sessions.return_value = [{"name": "test"}]
        mock_tmux.list_windows.return_value = [{"index": "1", "name": "Claude-PM"}]

        with patch("tmux_orchestrator.core.monitor.Config"):
            monitor = IdleMonitor(mock_tmux)

        is_crashed, _ = monitor._detect_pm_crash(mock_tmux, "test", Mock())

        # Should be crashed
        return is_crashed

    def generate_report(self) -> None:
        """Generate comprehensive validation report."""
        total = self.results["passed"] + self.results["failed"]
        success_rate = (self.results["passed"] / total * 100) if total > 0 else 0

        print("\n" + "=" * 70)
        print("📊 VALIDATION SUMMARY")
        print("=" * 70)
        print(f"Total Tests: {total}")
        print(f"Passed: {self.results['passed']} ✅")
        print(f"Failed: {self.results['failed']} ❌")
        print(f"Success Rate: {success_rate:.1f}%")

        if self.results["details"]:
            print("\n🚨 ISSUES FOUND:")
            for issue in self.results["details"]:
                print(f"  - {issue}")

        print("\n📋 RECOMMENDATION:")
        if success_rate >= 95:
            print("✅ Context-aware implementation is working well!")
            print("The fix successfully prevents false positives.")
        elif success_rate >= 80:
            print("⚠️  Implementation needs minor adjustments.")
            print("Most cases work but some edge cases need attention.")
        else:
            print("❌ Implementation needs significant work.")
            print("Many false positives or false negatives detected.")

        # Provide implementation guidance
        if self.results["failed"] > 0:
            print("\n💡 IMPLEMENTATION GUIDANCE:")
            print("Ensure _should_ignore_crash_indicator() includes these patterns:")
            print(
                """
    ignore_contexts = [
        r"test.*failed",
        r"check.*failed",
        r"Tests failed:",
        r"Build failed:",
        r"[Jj]ob.*failed",
        r"[Pp]ipeline.*failed",
        r"[Dd]eployment.*failed",
        r"\\d+.*failed",  # "3 tests failed"
        r"failed.*retry",
        r"previous.*failed",
        r"⎿.*failed",  # Tool output
        r"│.*failed",  # Tool output lines
    ]
"""
            )


def main():
    """Run the validation."""
    print("🚀 Context-Aware Crash Detection Validation")
    print("Based on: .tmux_orchestrator/planning/2025-08-15T22-30-00-daemon-recovery-improvements/status-report.md")

    validator = ContextAwareValidator()

    # Run all validations
    validator.validate_safe_contexts()
    validator.validate_unsafe_contexts()
    validator.validate_regex_patterns()

    # Generate report
    validator.generate_report()

    # Return exit code
    return 0 if validator.results["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
