#!/usr/bin/env python3
"""Detailed debug script for calculate_sleep_duration function bug"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from tmux_orchestrator.core.monitor_helpers import (
    MAX_RATE_LIMIT_SECONDS,
    RATE_LIMIT_BUFFER_SECONDS,
    calculate_sleep_duration,
)


def debug_sleep_calculation():
    """Debug the sleep calculation logic step by step"""

    print("Debugging calculate_sleep_duration function")
    print("=" * 60)
    print(f"MAX_RATE_LIMIT_SECONDS = {MAX_RATE_LIMIT_SECONDS} ({MAX_RATE_LIMIT_SECONDS/3600:.1f} hours)")
    print(f"RATE_LIMIT_BUFFER_SECONDS = {RATE_LIMIT_BUFFER_SECONDS} ({RATE_LIMIT_BUFFER_SECONDS/60:.1f} minutes)")
    print(f"Max allowed sleep = {MAX_RATE_LIMIT_SECONDS + RATE_LIMIT_BUFFER_SECONDS} seconds")
    print("=" * 60)

    # Test Case: Current time is past the reset time
    print("\nTest Case: Reset time has already passed today")
    print("-" * 40)

    # Set current time to 9:30pm UTC
    current_time = datetime(2025, 1, 20, 21, 30, 0, tzinfo=timezone.utc)
    reset_time = "3pm"  # 3pm has already passed

    print(f"Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')} (9:30pm UTC)")
    print(f"Reset time: {reset_time}")

    # Manual calculation
    print("\nManual calculation:")
    # 3pm tomorrow = next day at 15:00
    reset_dt = current_time.replace(hour=15, minute=0, second=0, microsecond=0)
    print(f"Reset datetime (today): {reset_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    if reset_dt <= current_time:
        reset_dt += timedelta(days=1)
        print(f"Reset datetime (tomorrow): {reset_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    diff = reset_dt - current_time
    sleep_seconds = int(diff.total_seconds())
    sleep_with_buffer = sleep_seconds + RATE_LIMIT_BUFFER_SECONDS

    print(f"\nTime difference: {diff}")
    print(f"Sleep seconds (without buffer): {sleep_seconds} ({sleep_seconds/3600:.2f} hours)")
    print(f"Sleep seconds (with buffer): {sleep_with_buffer} ({sleep_with_buffer/3600:.2f} hours)")
    print(f"Exceeds max limit? {sleep_with_buffer > (MAX_RATE_LIMIT_SECONDS + RATE_LIMIT_BUFFER_SECONDS)}")

    # Actual function result
    actual_result = calculate_sleep_duration(reset_time, current_time)
    print(f"\nActual function result: {actual_result} seconds")
    print(f"BUG DETECTED: Function returns 0 instead of {sleep_with_buffer}")

    print("\n" + "=" * 60)

    # Test multiple scenarios
    print("\nTesting various time scenarios:")
    print("-" * 40)

    test_scenarios = [
        # (current_hour, reset_time, description)
        (0, "1am", "Just after midnight, reset at 1am"),
        (2, "3am", "2am, reset at 3am"),
        (14, "3pm", "2pm, reset at 3pm (same as spec)"),
        (23, "1am", "11pm, reset at 1am (same as spec)"),
        (15, "3pm", "3pm exactly, reset at 3pm"),
        (16, "3pm", "4pm, reset at 3pm (next day)"),
        (20, "6pm", "8pm, reset at 6pm (next day)"),
        (22, "12am", "10pm, reset at midnight"),
    ]

    for current_hour, reset_time, description in test_scenarios:
        current = datetime(2025, 1, 20, current_hour, 0, 0, tzinfo=timezone.utc)
        result = calculate_sleep_duration(reset_time, current)

        print(f"\n{description}")
        print(f"  Current: {current.strftime('%I:%M %p')} UTC")
        print(f"  Reset: {reset_time}")
        print(f"  Sleep duration: {result} seconds ({result/3600:.2f} hours)")

        if result == 0:
            # Calculate what it should have been
            hour_match = {"12am": 0, "1am": 1, "3am": 3, "6pm": 18, "3pm": 15}
            reset_hour = hour_match.get(reset_time, 0)
            reset_dt = current.replace(hour=reset_hour, minute=0, second=0, microsecond=0)
            if reset_dt <= current:
                reset_dt += timedelta(days=1)
            expected = int((reset_dt - current).total_seconds()) + RATE_LIMIT_BUFFER_SECONDS
            print(f"  ⚠️  BUG: Should be {expected} seconds ({expected/3600:.2f} hours)")


if __name__ == "__main__":
    debug_sleep_calculation()
