#!/usr/bin/env python3
"""
Minimal test case to demonstrate sleep duration calculation bug
Expected: 3600s (1 hour) + 120s buffer = 3720s
Actual: 2564s (missing ~1156 seconds)
"""

from datetime import datetime, timedelta, timezone

from tmux_orchestrator.core.monitor_helpers import RATE_LIMIT_BUFFER_SECONDS, calculate_sleep_duration


def test_sleep_duration_calculation():
    """Test various scenarios to identify the bug"""

    print("🔍 Sleep Duration Calculation Bug Test")
    print("=" * 50)

    # Test Case 1: Exact 1 hour ahead
    now = datetime.now(timezone.utc)
    print(f"\nCurrent UTC time: {now.strftime('%Y-%m-%d %H:%M:%S')}")

    # Calculate what time is 1 hour from now
    one_hour_later = now + timedelta(hours=1)
    reset_time_str = one_hour_later.strftime("%-I%p").lower()  # e.g., "6pm"

    print("\nTest 1: Reset time 1 hour from now")
    print(f"Reset time string: {reset_time_str}")
    print(f"Expected seconds: 3600 + {RATE_LIMIT_BUFFER_SECONDS} = {3600 + RATE_LIMIT_BUFFER_SECONDS}")

    calculated = calculate_sleep_duration(reset_time_str, now)
    print(f"Calculated seconds: {calculated}")
    print(f"Difference: {calculated - (3600 + RATE_LIMIT_BUFFER_SECONDS)} seconds")

    # Test Case 2: With minutes
    two_hours_30min = now + timedelta(hours=2, minutes=30)
    reset_with_minutes = two_hours_30min.strftime("%-I:%M%p").lower()  # e.g., "6:30pm"

    print("\nTest 2: Reset time 2.5 hours from now")
    print(f"Reset time string: {reset_with_minutes}")
    print(f"Expected seconds: 9000 + {RATE_LIMIT_BUFFER_SECONDS} = {9000 + RATE_LIMIT_BUFFER_SECONDS}")

    calculated2 = calculate_sleep_duration(reset_with_minutes, now)
    print(f"Calculated seconds: {calculated2}")
    print(f"Difference: {calculated2 - (9000 + RATE_LIMIT_BUFFER_SECONDS)} seconds")

    # Test Case 3: Edge case - current hour
    current_hour = now.strftime("%-I%p").lower()
    print("\nTest 3: Reset time = current hour (should be tomorrow)")
    print(f"Reset time string: {current_hour}")
    print("Expected: ~86400 seconds (24 hours)")

    calculated3 = calculate_sleep_duration(current_hour, now)
    print(f"Calculated seconds: {calculated3}")

    # Debug the calculation step by step
    print("\n🔧 Debug Analysis:")
    print(f"Buffer seconds constant: {RATE_LIMIT_BUFFER_SECONDS}")

    # Manually calculate to compare
    hour = int(one_hour_later.strftime("%-I"))
    if "pm" in reset_time_str and hour != 12:
        hour += 12
    elif "am" in reset_time_str and hour == 12:
        hour = 0

    manual_reset = now.replace(hour=hour % 24, minute=0, second=0, microsecond=0)
    if manual_reset <= now:
        manual_reset += timedelta(days=1)

    manual_diff = (manual_reset - now).total_seconds()
    print("\nManual calculation:")
    print(f"Reset datetime: {manual_reset}")
    print(f"Difference seconds: {manual_diff}")
    print(f"With buffer: {manual_diff + RATE_LIMIT_BUFFER_SECONDS}")

    # Check if timezone is the issue
    print("\nTimezone check:")
    print(f"Now timezone: {now.tzinfo}")
    print(f"Reset timezone: {manual_reset.tzinfo}")

    # The bug appears to be in the calculation
    actual_diff = calculated - RATE_LIMIT_BUFFER_SECONDS
    print("\n❌ BUG IDENTIFIED:")
    print(f"For 1 hour wait, missing {3600 - actual_diff} seconds")
    print("This suggests the reset time calculation may be off by minutes/seconds")


if __name__ == "__main__":
    test_sleep_duration_calculation()
