"""Rate limit handling functionality."""

import re
from datetime import datetime, timedelta

from .constants import MAX_RATE_LIMIT_SECONDS, RATE_LIMIT_BUFFER_SECONDS


def extract_rate_limit_reset_time(content: str) -> str | None:
    """Extract the reset time from rate limit error message.

    Args:
        content: Terminal content containing rate limit message

    Returns:
        Reset time string (e.g., "4am", "4:30pm") or None if not found
    """
    # Pattern to match "Your limit will reset at 4am (UTC)." or similar
    # Handle extra whitespace with \s+
    pattern = r"Your limit will reset at\s+(\d{1,2}(?::\d{2})?(?:am|pm))\s+\(UTC\)"
    match = re.search(pattern, content, re.IGNORECASE)
    if match:
        time_str = match.group(1).strip()
        # Validate the hour is in valid range (1-12 for 12-hour format)
        hour_match = re.match(r"(\d{1,2})", time_str)
        if hour_match:
            hour = int(hour_match.group(1))
            # For 12-hour format with am/pm, hour should be 1-12
            # For 24-hour format (no am/pm), hour should be 0-23
            has_meridiem = "am" in time_str.lower() or "pm" in time_str.lower()
            if has_meridiem and (hour < 1 or hour > 12):
                return None
            elif not has_meridiem and (hour < 0 or hour > 23):
                return None
        return time_str
    return None


def calculate_sleep_duration(reset_time_str: str, now: datetime) -> int:
    """Calculate seconds until reset time plus buffer.

    Args:
        reset_time_str: Time string like "4am", "4:30pm", etc.
        now: Current datetime (should be UTC)

    Returns:
        Number of seconds to sleep (including 2 minute buffer), or 0 if > 4 hours
    """
    # Handle simple time formats
    reset_time_str = reset_time_str.strip()

    # Parse hour and optional minutes
    time_match = re.match(r"(\d{1,2})(?::(\d{2}))?([ap]m)?", reset_time_str.lower())
    if not time_match:
        raise ValueError(f"Invalid time format: {reset_time_str}")

    hour = int(time_match.group(1))
    minute = int(time_match.group(2) or 0)
    meridiem = time_match.group(3)

    # Convert to 24-hour format if needed
    if meridiem:
        if meridiem == "am" and hour == 12:
            hour = 0
        elif meridiem == "pm" and hour != 12:
            hour += 12

    # Create reset datetime for today
    reset_today = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    # If reset time has passed today, use tomorrow
    if reset_today <= now:
        reset_today += timedelta(days=1)

    # Calculate sleep duration
    sleep_duration = int((reset_today - now).total_seconds())

    # Add 2 minute buffer
    sleep_duration += RATE_LIMIT_BUFFER_SECONDS

    # Cap at 4 hours (14400 seconds) to prevent excessive delays
    if sleep_duration > MAX_RATE_LIMIT_SECONDS:
        return 0

    return max(0, sleep_duration)
