#!/usr/bin/env python3
"""Debug real-world sleep duration issue where we get 2564s instead of 3600s."""

from datetime import datetime, timedelta, timezone

from tmux_orchestrator.core.monitor_helpers import calculate_sleep_duration

# Real-world case: expecting 3600s, getting 2564s
# Difference is 1036s = 17 minutes 16 seconds

# Let's test if the issue is with minute calculation
# If current time has minutes/seconds, and we're calculating to next hour...

# Test with non-zero minutes
test_times = [
    # (current_time_minutes, reset_time, description)
    (0, "3pm", "Clean hour to hour"),
    (17, "3pm", "17 minutes past to next hour"),  # 17:16 = 1036s!
    (30, "3pm", "Half past to next hour"),
    (17, "3:00pm", "17 minutes past to 3:00pm"),
]

for minutes, reset_time, desc in test_times:
    now = datetime(2024, 1, 15, 14, minutes, 16, tzinfo=timezone.utc)
    sleep_seconds = calculate_sleep_duration(reset_time, now)

    # Calculate expected
    hour = 15  # 3pm
    reset_dt = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if reset_dt <= now:
        reset_dt += timedelta(days=1)

    expected = int((reset_dt - now).total_seconds()) + 120

    print(f"\n{desc}")
    print(f"Current: {now.strftime('%H:%M:%S')} UTC")
    print(f"Reset time: {reset_time}")
    print(f"Sleep seconds: {sleep_seconds}")
    print(f"Expected: {expected}")
    print(f"Difference: {sleep_seconds - expected}")

# Found it! If test is at 14:17:16 and reset at 15:00:00,
# the difference is 42:44 = 2564s, not 3600s!
