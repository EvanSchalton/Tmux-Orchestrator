#!/usr/bin/env python3
"""Debug sleep duration calculation issue."""

from datetime import datetime, timedelta, timezone

from tmux_orchestrator.core.monitor_helpers import calculate_sleep_duration

# Test case: If we're 1 hour away from reset time, should get 3600s + 120s buffer = 3720s
# But we're getting 2564s instead

# Simulate current time
now = datetime(2024, 1, 15, 14, 0, 0, tzinfo=timezone.utc)  # 2:00 PM UTC
print(f"Current time: {now}")

# Test various reset times
test_cases = [
    ("3pm", 3600),  # 1 hour ahead
    ("3:00pm", 3600),  # Same with minutes
    ("4pm", 7200),  # 2 hours ahead
    ("1pm", -3600),  # 1 hour behind (should go to tomorrow)
]

for reset_time, expected_base in test_cases:
    sleep_seconds = calculate_sleep_duration(reset_time, now)
    expected_with_buffer = expected_base + 120 if expected_base > 0 else 86400 - 3600 + 120

    print(f"\nReset time: {reset_time}")
    print(f"Sleep seconds: {sleep_seconds}")
    print(f"Expected (with 120s buffer): {expected_with_buffer}")
    print(f"Difference: {sleep_seconds - expected_with_buffer}")

    # Check intermediate calculations
    hour = int(reset_time.split(":")[0].replace("am", "").replace("pm", ""))
    if "pm" in reset_time and hour != 12:
        hour += 12

    reset_dt = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if reset_dt <= now:
        reset_dt += timedelta(days=1)

    diff = reset_dt - now
    print(f"Reset datetime: {reset_dt}")
    print(f"Time difference: {diff}")
    print(f"Seconds: {diff.total_seconds()}")
