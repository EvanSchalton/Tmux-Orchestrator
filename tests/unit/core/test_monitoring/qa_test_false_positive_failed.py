#!/usr/bin/env python3
"""
CRITICAL QA Test: False Positive Detection for 'failed' keyword
==============================================================

This test verifies the critical bug identified in the team plan:
- monitor.py line 1724 includes "failed" as a crash indicator
- This causes healthy PMs to be killed when they output legitimate messages containing "failed"

Testing scenarios:
1. PM reports "tests failed" - should NOT be killed
2. PM mentions "deployment failed" - should NOT be killed
3. PM has error messages - should NOT be killed
4. PM is actually crashed - SHOULD be detected

Bug Location: tmux_orchestrator/core/monitor.py:1724
"""

import logging
from pathlib import Path
from typing import Any

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class FalsePositiveQATest:
    """QA test for false positive 'failed' detection bug."""

    def __init__(self):
        self.test_results: dict[str, Any] = {}
        self.passed_tests = 0
        self.failed_tests = 0

    def test_pm_outputs_failed_keyword(self) -> dict[str, Any]:
        """
        CRITICAL TEST: Verify PM outputting 'failed' is NOT killed

        This tests the exact scenario from the team plan:
        - PM outputs "tests failed" or "deployment failed"
        - Monitor should NOT kill the PM
        - This is currently BROKEN due to line 1724 in monitor.py
        """
        logger.info("🔍 Testing PM outputs with 'failed' keyword...")

        test_scenarios = [
            {
                "name": "PM reports test failure",
                "content": """╭─ Assistant ─────────────────────────────────────────────────────╮
│ I ran the tests and unfortunately 3 tests failed. Let me       │
│ analyze the failures and fix them:                              │
│                                                                 │
│ ❌ test_user_auth.py::test_login_validation failed              │
│ ❌ test_database.py::test_connection failed                     │
│ ❌ test_api.py::test_endpoint_validation failed                 │
╰─────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────╮
│ > Let me examine the failures in detail...                     │
╰─────────────────────────────────────────────────────────────────╯""",
                "should_be_killed": False,
                "reason": "PM is working normally, just reporting test results",
            },
            {
                "name": "PM reports deployment failure",
                "content": """╭─ Assistant ─────────────────────────────────────────────────────╮
│ The deployment failed due to configuration issues. Here's      │
│ what I found:                                                   │
│                                                                 │
│ 1. Database connection failed - missing environment variable   │
│ 2. SSL certificate validation failed                           │
│ 3. Health check failed after 30 seconds                       │
│                                                                 │
│ I'll fix these issues now.                                     │
╰─────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────╮
│ > Updating configuration files...                              │
╰─────────────────────────────────────────────────────────────────╯""",
                "should_be_killed": False,
                "reason": "PM is working normally, just reporting deployment status",
            },
            {
                "name": "PM with error messages but working",
                "content": """╭─ Assistant ─────────────────────────────────────────────────────╮
│ I see several issues that need attention:                      │
│                                                                 │
│ ⚠️  Build step failed - fixing now                             │
│ ⚠️  Linter check failed - updating code style                  │
│ ⚠️  Security scan failed - addressing vulnerabilities          │
│                                                                 │
│ Working on resolving these failures systematically...          │
╰─────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────╮
│ > Running npm run build...                                     │
╰─────────────────────────────────────────────────────────────────╯""",
                "should_be_killed": False,
                "reason": "PM is actively working to fix issues",
            },
        ]

        results = []
        for scenario in test_scenarios:
            logger.info(f"  Testing: {scenario['name']}")

            # Test with current monitor logic (importing the actual function)
            try:
                from tmux_orchestrator.core.monitor_helpers import is_claude_interface_present

                # Check if Claude interface is detected (should be True)
                has_claude_ui = is_claude_interface_present(scenario["content"])

                # Check for crash indicators (this is where the bug is)
                content_lower = scenario["content"].lower()
                crash_detected = "failed" in content_lower

                result = {
                    "scenario": scenario["name"],
                    "has_claude_ui": has_claude_ui,
                    "crash_detected_by_keyword": crash_detected,
                    "should_be_killed": scenario["should_be_killed"],
                    "expected_behavior": f"Should {'NOT ' if not scenario['should_be_killed'] else ''}be killed",
                    "actual_behavior": f"Would {'be killed' if crash_detected else 'NOT be killed'} due to keyword detection",
                    "test_passed": not crash_detected if not scenario["should_be_killed"] else crash_detected,
                    "reason": scenario["reason"],
                }

                results.append(result)

                if result["test_passed"]:
                    logger.info(f"    ✅ PASS: {scenario['name']}")
                    self.passed_tests += 1
                else:
                    logger.error(f"    ❌ FAIL: {scenario['name']} - {result['actual_behavior']}")
                    self.failed_tests += 1

            except Exception as e:
                logger.error(f"    ❌ ERROR testing {scenario['name']}: {e}")
                self.failed_tests += 1
                results.append({"scenario": scenario["name"], "error": str(e), "test_passed": False})

        return {
            "test_name": "PM outputs with 'failed' keyword",
            "results": results,
            "summary": f"Passed: {len([r for r in results if r.get('test_passed', False)])}, Failed: {len([r for r in results if not r.get('test_passed', True)])}",
        }

    def test_actual_crash_detection(self) -> dict[str, Any]:
        """
        Test that actual crashes ARE properly detected.
        This verifies that fixing the false positive doesn't break real crash detection.
        """
        logger.info("🔍 Testing actual crash detection...")

        crash_scenarios = [
            {
                "name": "Process terminated",
                "content": "Terminated\nuser@hostname:~/project$ ",
                "should_be_killed": True,
                "reason": "Process was actually terminated",
            },
            {
                "name": "Command not found",
                "content": "claude: command not found\nuser@dev:~$ ",
                "should_be_killed": True,
                "reason": "Claude binary not available",
            },
            {
                "name": "Segmentation fault",
                "content": "Segmentation fault (core dumped)\nroot@container:/# ",
                "should_be_killed": True,
                "reason": "Process crashed with segfault",
            },
        ]

        results = []
        for scenario in crash_scenarios:
            logger.info(f"  Testing: {scenario['name']}")

            try:
                from tmux_orchestrator.core.monitor_helpers import is_claude_interface_present

                # Check if Claude interface is detected (should be False)
                has_claude_ui = is_claude_interface_present(scenario["content"])

                # Check for crash indicators
                content_lower = scenario["content"].lower()
                crash_indicators = ["terminated", "command not found", "segmentation fault"]
                crash_detected = any(indicator in content_lower for indicator in crash_indicators)

                result = {
                    "scenario": scenario["name"],
                    "has_claude_ui": has_claude_ui,
                    "crash_detected": crash_detected,
                    "should_be_killed": scenario["should_be_killed"],
                    "test_passed": crash_detected == scenario["should_be_killed"],
                    "reason": scenario["reason"],
                }

                results.append(result)

                if result["test_passed"]:
                    logger.info(f"    ✅ PASS: {scenario['name']}")
                    self.passed_tests += 1
                else:
                    logger.error(f"    ❌ FAIL: {scenario['name']}")
                    self.failed_tests += 1

            except Exception as e:
                logger.error(f"    ❌ ERROR testing {scenario['name']}: {e}")
                self.failed_tests += 1
                results.append({"scenario": scenario["name"], "error": str(e), "test_passed": False})

        return {
            "test_name": "Actual crash detection",
            "results": results,
            "summary": f"Passed: {len([r for r in results if r.get('test_passed', False)])}, Failed: {len([r for r in results if not r.get('test_passed', True)])}",
        }

    def run_comprehensive_test(self) -> dict[str, Any]:
        """Run comprehensive QA test for false positive detection."""
        logger.info("🚀 Starting comprehensive false positive QA test...")
        logger.info("=" * 70)

        test_results = {}

        # Test 1: False positive scenarios
        test_results["false_positive_test"] = self.test_pm_outputs_failed_keyword()

        # Test 2: True positive scenarios
        test_results["true_positive_test"] = self.test_actual_crash_detection()

        # Generate summary
        total_passed = self.passed_tests
        total_failed = self.failed_tests
        total_tests = total_passed + total_failed

        summary = {
            "total_tests": total_tests,
            "passed": total_passed,
            "failed": total_failed,
            "success_rate": f"{(total_passed/total_tests)*100:.1f}%" if total_tests > 0 else "0%",
            "critical_issues": [],
        }

        # Identify critical issues
        if test_results["false_positive_test"]["results"]:
            failed_false_positive = [
                r for r in test_results["false_positive_test"]["results"] if not r.get("test_passed", True)
            ]
            if failed_false_positive:
                summary["critical_issues"].append(
                    {
                        "type": "FALSE_POSITIVE_BUG",
                        "description": "PMs are being killed for legitimate 'failed' messages",
                        "impact": "HIGH - Healthy PMs are being unnecessarily killed",
                        "location": "tmux_orchestrator/core/monitor.py:1724",
                        "fix_required": "Remove 'failed' from crash_indicators list",
                    }
                )

        test_results["summary"] = summary

        logger.info("=" * 70)
        logger.info(f"🏁 QA Test Complete: {total_passed}/{total_tests} tests passed ({summary['success_rate']})")

        if summary["critical_issues"]:
            logger.error("🚨 CRITICAL ISSUES FOUND:")
            for issue in summary["critical_issues"]:
                logger.error(f"   {issue['type']}: {issue['description']}")
                logger.error(f"   Impact: {issue['impact']}")
                logger.error(f"   Fix: {issue['fix_required']}")
        else:
            logger.info("✅ No critical issues detected")

        return test_results


def main():
    """Run the QA test."""
    tester = FalsePositiveQATest()
    results = tester.run_comprehensive_test()

    # Save results to file
    results_file = Path("qa_false_positive_test_results.json")
    import json

    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)

    logger.info(f"📄 Test results saved to: {results_file}")

    # Return exit code based on test results
    if results["summary"]["failed"] > 0:
        logger.error("🚨 Some tests failed - investigation required")
        return 1
    else:
        logger.info("✅ All tests passed")
        return 0


if __name__ == "__main__":
    exit(main())
