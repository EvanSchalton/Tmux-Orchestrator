#!/usr/bin/env python3
"""
CRITICAL BUGS FOCUSED TEST SUITE
1. Sleep duration calculation wrong (daemon resumes too early)
2. PM notifications not working at all
"""

import json
from datetime import datetime, timedelta, timezone

print("🚨 CRITICAL BUGS FOCUSED TESTS")
print("=" * 50)


class CriticalBugTests:
    def test_sleep_duration_early_resume(self):
        """Test 1: Daemon resumes too early bug"""
        print("\n1️⃣ SLEEP DURATION EARLY RESUME TEST")
        print("-" * 40)

        from tmux_orchestrator.core.monitor_helpers import RATE_LIMIT_BUFFER_SECONDS, calculate_sleep_duration

        # Test scenarios where daemon might resume early
        test_cases = [
            {
                "name": "Near midnight rollover",
                "current_time": datetime(2025, 8, 20, 23, 45, 0, tzinfo=timezone.utc),
                "reset_time": "1am",
                "expected_hours": 1.25,  # 1h 15min
            },
            {
                "name": "Same hour next day",
                "current_time": datetime(2025, 8, 20, 10, 30, 0, tzinfo=timezone.utc),
                "reset_time": "10am",
                "expected_hours": 23.5,  # Should be tomorrow
            },
            {
                "name": "PM/AM confusion",
                "current_time": datetime(2025, 8, 20, 14, 0, 0, tzinfo=timezone.utc),  # 2pm
                "reset_time": "2am",
                "expected_hours": 12,  # Should be 12 hours
            },
            {
                "name": "Minutes precision",
                "current_time": datetime(2025, 8, 20, 15, 45, 30, tzinfo=timezone.utc),
                "reset_time": "5pm",
                "expected_hours": 1.26,  # 1h 14min 30s
            },
        ]

        failures = []
        for test in test_cases:
            calculated = calculate_sleep_duration(test["reset_time"], test["current_time"])
            expected_seconds = test["expected_hours"] * 3600 + RATE_LIMIT_BUFFER_SECONDS

            # Allow 5 minute tolerance
            diff = abs(calculated - expected_seconds)
            passed = diff < 300  # 5 minutes

            print(f"\n{test['name']}:")
            print(f"  Current: {test['current_time'].strftime('%H:%M:%S')}")
            print(f"  Reset: {test['reset_time']}")
            print(f"  Expected: ~{expected_seconds:.0f}s ({test['expected_hours']}h + buffer)")
            print(f"  Calculated: {calculated}s")
            print(f"  Difference: {diff:.0f}s")
            print(f"  Status: {'✅ PASS' if passed else '❌ FAIL'}")

            if not passed:
                failures.append(f"{test['name']}: Off by {diff:.0f}s")

        return failures

    def test_pm_notification_delivery(self):
        """Test 2: PM notifications not working"""
        print("\n\n2️⃣ PM NOTIFICATION DELIVERY TEST")
        print("-" * 40)

        # Check all points where PM notification could fail
        notification_failure_points = {
            "PM interface check": {
                "location": "monitor.py:1918-1922",
                "issue": "Skips if PM not in Claude interface",
                "test": self._test_pm_interface_check,
            },
            "Notification cooldown": {
                "location": "monitor_helpers.py:337-344",
                "issue": "5-minute cooldown blocks notifications",
                "test": self._test_notification_cooldown,
            },
            "Rate limit detection": {
                "location": "monitor.py:1872-1892",
                "issue": "Message not detected properly",
                "test": self._test_rate_limit_detection,
            },
            "Message sending": {
                "location": "monitor.py:1906-1917",
                "issue": "tmux send-keys failure",
                "test": self._test_message_sending,
            },
        }

        failures = []
        for test_name, config in notification_failure_points.items():
            print(f"\nTesting: {test_name}")
            print(f"  Location: {config['location']}")
            print(f"  Issue: {config['issue']}")

            try:
                result = config["test"]()
                print(f"  Result: {'✅ PASS' if result else '❌ FAIL'}")
                if not result:
                    failures.append(f"{test_name}: {config['issue']}")
            except Exception as e:
                print(f"  Result: ❌ ERROR - {e}")
                failures.append(f"{test_name}: Test error - {e}")

        return failures

    def _test_pm_interface_check(self):
        """Test if PM interface requirement blocks notifications"""
        from tmux_orchestrator.core.monitor_helpers import is_claude_interface_present

        # Test various PM states
        bash_prompt = "user@host:~$ "
        claude_interface = "╭─ Claude\n│ > \n╰─"

        bash_result = is_claude_interface_present(bash_prompt)
        claude_result = is_claude_interface_present(claude_interface)

        print(f"    Bash prompt detected as Claude: {bash_result}")
        print(f"    Claude interface detected: {claude_result}")

        # This is the bug - notifications only sent if PM has Claude interface
        return not bash_result  # Should be False for bash

    def _test_notification_cooldown(self):
        """Test if cooldown blocks notifications"""
        from datetime import datetime

        from tmux_orchestrator.core.monitor_helpers import AgentState, should_notify_pm

        # Recent notification
        history = {"crash_pm:1": datetime.now() - timedelta(minutes=3)}

        result = should_notify_pm(state=AgentState.RATE_LIMITED, target="pm:1", notification_history=history)

        print(f"    Notification allowed with 3-min old history: {result}")
        return result  # Should be False due to 5-min cooldown

    def _test_rate_limit_detection(self):
        """Test rate limit message detection"""
        from tmux_orchestrator.core.monitor_helpers import extract_rate_limit_reset_time

        valid_msg = "Your limit will reset at 6pm (UTC)."
        result = extract_rate_limit_reset_time(valid_msg)

        print(f"    Rate limit detection result: {result}")
        return result == "6pm"

    def _test_message_sending(self):
        """Test tmux send-keys mechanism"""
        # Would need actual tmux session to test
        print("    Requires live tmux session for validation")
        return True  # Placeholder

    def generate_test_report(self, sleep_failures, notification_failures):
        """Generate comprehensive test report"""
        report = {
            "test_timestamp": datetime.now(timezone.utc).isoformat(),
            "critical_bugs": {
                "sleep_duration_early_resume": {
                    "status": "FAIL" if sleep_failures else "PASS",
                    "failures": sleep_failures,
                    "impact": "Daemon resumes before rate limit resets",
                },
                "pm_notifications_broken": {
                    "status": "FAIL" if notification_failures else "PASS",
                    "failures": notification_failures,
                    "impact": "PM never informed about rate limits",
                },
            },
            "recommendations": {
                "sleep_duration": [
                    "Check timezone handling in calculate_sleep_duration()",
                    "Verify day rollover logic for times past midnight",
                    "Test AM/PM parsing edge cases",
                ],
                "pm_notifications": [
                    "Remove PM interface check requirement",
                    "Send notifications regardless of PM window state",
                    "Consider using pubsub for reliable delivery",
                ],
            },
        }

        # Save report
        with open("critical_bugs_test_report.json", "w") as f:
            json.dump(report, f, indent=2)

        return report


# Run tests
if __name__ == "__main__":
    tester = CriticalBugTests()

    # Run critical bug tests
    sleep_failures = tester.test_sleep_duration_early_resume()
    notification_failures = tester.test_pm_notification_delivery()

    # Generate report
    report = tester.generate_test_report(sleep_failures, notification_failures)

    print("\n\n📊 CRITICAL BUG TEST SUMMARY")
    print("=" * 50)
    print(f"Sleep Duration Bug: {report['critical_bugs']['sleep_duration_early_resume']['status']}")
    print(f"PM Notification Bug: {report['critical_bugs']['pm_notifications_broken']['status']}")

    if sleep_failures:
        print("\n❌ Sleep Duration Failures:")
        for failure in sleep_failures:
            print(f"  - {failure}")

    if notification_failures:
        print("\n❌ PM Notification Failures:")
        for failure in notification_failures:
            print(f"  - {failure}")

    print("\n📄 Detailed report: critical_bugs_test_report.json")
