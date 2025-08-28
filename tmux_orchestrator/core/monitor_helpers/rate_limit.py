"""Rate limit detection and handling utilities."""

import re
from datetime import datetime, timedelta


def extract_rate_limit_reset_time(content: str) -> str | None:
    """Extract rate limit reset time from error message.

    Looks for various rate limit message formats and extracts
    the reset time information.

    Args:
        content: Pane content potentially containing rate limit info

    Returns:
        ISO format reset time string if found, None otherwise
    """
    if not content:
        return None

    # Common rate limit patterns
    patterns = [
        r"reset[s]? at[:\s]+([0-9T:\-Z\.]+)",
        r"retry after[:\s]+([0-9T:\-Z\.]+)",
        r"available at[:\s]+([0-9T:\-Z\.]+)",
        r"reset[s]? in[:\s]+(\d+)\s*(second|minute|hour)",
        r"retry in[:\s]+(\d+)\s*(second|minute|hour)",
        r"wait[:\s]+(\d+)\s*(second|minute|hour)",
    ]

    content_lower = content.lower()

    for pattern in patterns[:3]:  # First 3 patterns look for timestamps
        match = re.search(pattern, content_lower)
        if match:
            return match.group(1)

    # Handle relative time patterns (last 3 patterns)
    for pattern in patterns[3:]:
        match = re.search(pattern, content_lower)
        if match:
            amount = int(match.group(1))
            unit = match.group(2)

            # Calculate reset time
            now = datetime.now()
            if "second" in unit:
                reset_time = now + timedelta(seconds=amount)
            elif "minute" in unit:
                reset_time = now + timedelta(minutes=amount)
            elif "hour" in unit:
                reset_time = now + timedelta(hours=amount)
            else:
                continue

            return reset_time.isoformat()

    return None


def calculate_sleep_duration(reset_time_str: str, now: datetime) -> int:
    """Calculate how long to sleep until rate limit resets.

    Args:
        reset_time_str: ISO format reset time
        now: Current datetime

    Returns:
        Seconds to sleep (with buffer), max 4 hours
    """
    from .state_types import MAX_RATE_LIMIT_SECONDS, RATE_LIMIT_BUFFER_SECONDS

    try:
        # Parse reset time
        reset_time = datetime.fromisoformat(reset_time_str.replace("Z", "+00:00"))

        # Calculate duration
        duration = (reset_time - now).total_seconds()

        # Add buffer
        duration += RATE_LIMIT_BUFFER_SECONDS

        # Cap at maximum
        return min(int(duration), MAX_RATE_LIMIT_SECONDS)

    except (ValueError, AttributeError):
        # Default to 5 minutes if parsing fails
        return 300
