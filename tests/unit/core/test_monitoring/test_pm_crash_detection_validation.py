#!/usr/bin/env python3
"""
PM Crash Detection Validation Harness

This script provides rapid validation of PM crash detection logic,
specifically testing the false positive bug and verifying proper crash detection.

Usage:
    python test_pm_crash_detection_validation.py [--quick] [--verbose]
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tmux_orchestrator.core.monitor import IdleMonitor  # noqa: E402
from tmux_orchestrator.utils.tmux import TMUXManager  # noqa: E402

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class CrashDetectionValidator:
    """Validates PM crash detection logic."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results = {"false_positives": [], "true_positives": [], "false_negatives": [], "true_negatives": []}

    def log(self, message: str, level: str = "info"):
        """Log message with optional verbose output."""
        if level == "error":
            logger.error(message)
        elif level == "warning":
            logger.warning(message)
        elif self.verbose:
            logger.info(message)

    def create_test_scenarios(self) -> dict[str, list[dict[str, Any]]]:
        """Create comprehensive test scenarios."""
        return {
            "should_not_crash": [
                {
                    "name": "PM reporting test failures",
                    "content": """╭─ Assistant ─────────────────────────────────────────────────────╮
│ Test results: 3 tests failed                                   │
│ - auth_test.py failed with assertion error                     │
│ - db_test.py failed due to connection timeout                  │
│ Working on fixes...                                            │
╰─────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────╮
│ > Fixing the failed tests...                                   │
╰─────────────────────────────────────────────────────────────────╯""",
                    "keywords": ["failed", "error", "timeout"],
                },
                {
                    "name": "PM handling deployment errors",
                    "content": """╭─ Assistant ─────────────────────────────────────────────────────╮
│ Deployment failed: Connection refused to production server     │
│ Error: Permission denied for deployment user                   │
│ Fatal: Cannot push to protected branch                         │
│ I'll resolve these deployment issues...                        │
╰─────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────╮
│ > Updating deployment configuration...                         │
╰─────────────────────────────────────────────────────────────────╯""",
                    "keywords": ["failed", "refused", "denied", "fatal", "error"],
                },
                {
                    "name": "PM debugging application errors",
                    "content": """╭─ Assistant ─────────────────────────────────────────────────────╮
│ Found the root cause of the crashes:                           │
│ - Segmentation fault in memory allocation                      │
│ - Process terminated due to OOM killer                         │
│ - Signal 9 (SIGKILL) sent to worker process                   │
│ Implementing memory optimizations now...                       │
╰─────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────╮
│ > Optimizing memory usage...                                   │
╰─────────────────────────────────────────────────────────────────╯""",
                    "keywords": ["segmentation fault", "terminated", "killed", "signal"],
                },
                {
                    "name": "PM with build failures",
                    "content": """╭─ Assistant ─────────────────────────────────────────────────────╮
│ Build failed with multiple errors:                             │
│ ERROR: Package not found - @types/node                        │
│ FATAL: TypeScript compilation failed                           │
│ npm ERR! Exit status 1                                        │
│ Fixing package dependencies...                                 │
╰─────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────╮
│ > Installing missing packages...                               │
╰─────────────────────────────────────────────────────────────────╯""",
                    "keywords": ["failed", "error", "fatal", "exit"],
                },
                {
                    "name": "PM analyzing crash logs",
                    "content": """╭─ Assistant ─────────────────────────────────────────────────────╮
│ Analyzing the crash dump:                                      │
│ - Core dumped at 0x7fff8934                                   │
│ - Abort() called from thread 42                               │
│ - Panic: index out of bounds                                  │
│ - Process killed by watchdog timeout                          │
│ Creating a patch to prevent future crashes...                  │
╰─────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────╮
│ > Implementing crash prevention measures...                    │
╰─────────────────────────────────────────────────────────────────╯""",
                    "keywords": ["dumped", "abort", "panic", "killed", "timeout"],
                },
            ],
            "should_crash": [
                {
                    "name": "No Claude interface - just bash",
                    "content": "user@hostname:~/project$ ",
                    "reason": "Only shell prompt, no Claude UI",
                },
                {
                    "name": "Claude command not found",
                    "content": "bash: claude: command not found\nuser@host:~$ ",
                    "reason": "Claude binary missing",
                },
                {
                    "name": "Process terminated",
                    "content": "Terminated\n[1]+  Terminated              claude\nuser@host:~$ ",
                    "reason": "Claude process was terminated",
                },
                {
                    "name": "Segfault with no UI",
                    "content": "Segmentation fault (core dumped)\nroot@container:/# ",
                    "reason": "Process crashed, only shell remains",
                },
                {"name": "Empty terminal", "content": "\n\n", "reason": "No content in terminal"},
            ],
        }

    def test_crash_detection(self, content: str, should_crash: bool) -> tuple[bool, str]:
        """Test if crash detection works correctly for given content."""
        try:
            # Create mock TMUXManager
            mock_tmux = Mock(spec=TMUXManager)
            mock_tmux.capture_pane.return_value = content
            mock_tmux.list_sessions.return_value = [{"name": "test"}]
            mock_tmux.list_windows.return_value = [{"index": "1", "name": "Claude-PM"}]

            # Create monitor instance
            with patch("tmux_orchestrator.core.monitor.Config"):
                monitor = IdleMonitor(mock_tmux)

            # Test crash detection
            mock_logger = Mock()
            is_crashed, target = monitor._detect_pm_crash(mock_tmux, "test", mock_logger)

            # Determine result
            if should_crash and is_crashed:
                return True, "Correctly detected as crashed"
            elif not should_crash and not is_crashed:
                return True, "Correctly detected as healthy"
            elif not should_crash and is_crashed:
                return False, "FALSE POSITIVE: Healthy PM detected as crashed"
            else:  # should_crash and not is_crashed
                return False, "FALSE NEGATIVE: Crashed PM not detected"

        except Exception as e:
            return False, f"ERROR: {str(e)}"

    def run_validation(self, quick: bool = False) -> dict[str, Any]:
        """Run comprehensive validation tests."""
        logger.info("🚀 Starting PM Crash Detection Validation")
        logger.info("=" * 70)

        scenarios = self.create_test_scenarios()
        total_tests = 0
        passed_tests = 0

        # Test scenarios that should NOT trigger crash detection
        logger.info("\n📋 Testing scenarios that should NOT kill PM...")
        for scenario in scenarios["should_not_crash"]:
            if quick and total_tests >= 2:  # Quick mode: only test first 2
                break

            total_tests += 1
            self.log(f"\nTesting: {scenario['name']}")
            self.log(f"Keywords present: {', '.join(scenario['keywords'])}")

            success, message = self.test_crash_detection(scenario["content"], should_crash=False)

            if success:
                passed_tests += 1
                logger.info(f"✅ PASS: {scenario['name']}")
                self.results["true_negatives"].append(scenario["name"])
            else:
                logger.error(f"❌ FAIL: {scenario['name']} - {message}")
                self.results["false_positives"].append(
                    {"name": scenario["name"], "keywords": scenario["keywords"], "reason": message}
                )

        # Test scenarios that SHOULD trigger crash detection
        logger.info("\n📋 Testing scenarios that SHOULD kill PM...")
        for scenario in scenarios["should_crash"]:
            if quick and total_tests >= 4:  # Quick mode: test 2 of each type
                break

            total_tests += 1
            self.log(f"\nTesting: {scenario['name']}")
            self.log(f"Reason: {scenario['reason']}")

            success, message = self.test_crash_detection(scenario["content"], should_crash=True)

            if success:
                passed_tests += 1
                logger.info(f"✅ PASS: {scenario['name']}")
                self.results["true_positives"].append(scenario["name"])
            else:
                logger.error(f"❌ FAIL: {scenario['name']} - {message}")
                self.results["false_negatives"].append(
                    {"name": scenario["name"], "reason": scenario["reason"], "error": message}
                )

        # Generate summary
        logger.info("\n" + "=" * 70)
        logger.info("📊 VALIDATION SUMMARY")
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {total_tests - passed_tests}")
        logger.info(f"Success Rate: {(passed_tests / total_tests) * 100:.1f}%")

        if self.results["false_positives"]:
            logger.error(f"\n🚨 FALSE POSITIVES DETECTED: {len(self.results['false_positives'])}")
            for fp in self.results["false_positives"]:
                logger.error(f"   - {fp['name']}")
                logger.error(f"     Keywords: {', '.join(fp['keywords'])}")

        if self.results["false_negatives"]:
            logger.error(f"\n⚠️  FALSE NEGATIVES DETECTED: {len(self.results['false_negatives'])}")
            for fn in self.results["false_negatives"]:
                logger.error(f"   - {fn['name']}: {fn['reason']}")

        # Final verdict
        logger.info("\n" + "=" * 70)
        if not self.results["false_positives"] and not self.results["false_negatives"]:
            logger.info("✅ ALL TESTS PASSED - Crash detection working correctly!")
            verdict = "PASS"
        else:
            logger.error("❌ VALIDATION FAILED - Crash detection has issues!")
            if self.results["false_positives"]:
                logger.error("   Primary issue: FALSE POSITIVES (healthy PMs being killed)")
            verdict = "FAIL"

        return {
            "verdict": verdict,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "false_positives": len(self.results["false_positives"]),
            "false_negatives": len(self.results["false_negatives"]),
            "details": self.results,
        }


def main():
    """Run the validation harness."""
    parser = argparse.ArgumentParser(description="Validate PM crash detection logic")
    parser.add_argument("--quick", action="store_true", help="Run quick validation (subset of tests)")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    args = parser.parse_args()

    validator = CrashDetectionValidator(verbose=args.verbose)
    results = validator.run_validation(quick=args.quick)

    # Return appropriate exit code
    return 0 if results["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
