"""Comprehensive tests for rate limit handling feature."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from tmux_orchestrator.core.monitor_helpers import (
    AgentState,
    calculate_sleep_duration,
    detect_agent_state,
    extract_rate_limit_reset_time,
    should_notify_pm,
)


def test_extract_rate_limit_reset_time_various_formats() -> None:
    """Test extraction of reset time from various message formats."""
    test_cases = [
        # Standard format
        ("Your limit will reset at 4am (UTC).", "4am"),
        ("Your limit will reset at 4:30pm (UTC).", "4:30pm"),
        ("Your limit will reset at 11:59pm (UTC).", "11:59pm"),
        ("Your limit will reset at 12:00am (UTC).", "12:00am"),
        ("Your limit will reset at 12pm (UTC).", "12pm"),
        # Case variations
        ("YOUR LIMIT WILL RESET AT 3PM (UTC).", "3PM"),
        ("your limit will reset at 2:15am (utc).", "2:15am"),
        # Extra whitespace
        ("Your limit will reset at  4am  (UTC).", "4am"),
        # Embedded in larger message
        (
            "Claude usage limit reached. Your limit will reset at 4:30pm (UTC). Please try again later.",
            "4:30pm",
        ),
    ]

    for message, expected in test_cases:
        result = extract_rate_limit_reset_time(message)
        assert result == expected, f"Failed for message: {message}"


def test_extract_rate_limit_reset_time_invalid() -> None:
    """Test extraction returns None for invalid messages."""
    invalid_messages = [
        "No rate limit message here",
        "Your limit will reset at 25:00 (UTC).",  # Invalid hour
        "Your limit will reset tomorrow",
        "Rate limit reached",
        "",
    ]

    for message in invalid_messages:
        result = extract_rate_limit_reset_time(message)
        assert result is None, f"Should return None for: {message}"


def test_calculate_sleep_duration_various_times() -> None:
    """Test sleep duration calculation for various reset times."""
    # Mock current time: 2:00 PM UTC
    now = datetime(2024, 12, 5, 14, 0, 0, tzinfo=timezone.utc)

    test_cases = [
        # Future times today
        ("4:30pm", 9120),  # 2.5 hours + 2 min buffer = 9120 seconds
        ("11:59pm", 36060),  # 9 hours 59 min + 2 min = 36060 seconds
        ("3pm", 3720),  # 1 hour + 2 min = 3720 seconds
        # Past times (should roll to tomorrow)
        ("1am", 39720),  # 11 hours (to tomorrow 1am) + 2 min = 39720 seconds
        ("12pm", 79320),  # 22 hours (to tomorrow noon) + 2 min = 79320 seconds
        ("2am", 43320),  # 12 hours (to tomorrow 2am) + 2 min = 43320 seconds
        # Edge cases
        ("12am", 36120),  # 10 hours (to midnight) + 2 min = 36120 seconds
        ("12:00am", 36120),  # Same as above
    ]

    for reset_time, expected in test_cases:
        result = calculate_sleep_duration(reset_time, now)
        # Allow 1 second tolerance for floating point
        assert abs(result - expected) <= 1, f"Failed for {reset_time}: got {result}, expected {expected}"


def test_calculate_sleep_duration_edge_cases() -> None:
    """Test edge cases for sleep duration calculation."""
    # Test at midnight
    midnight = datetime(2024, 12, 5, 0, 0, 0, tzinfo=timezone.utc)
    result = calculate_sleep_duration("1am", midnight)
    assert result == 3720  # 1 hour + 2 min buffer

    # Test at 11:59 PM
    almost_midnight = datetime(2024, 12, 5, 23, 59, 0, tzinfo=timezone.utc)
    result = calculate_sleep_duration("12am", almost_midnight)
    assert result == 180  # 1 minute + 2 min buffer

    # Test invalid format
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError, match="Invalid time format"):
        calculate_sleep_duration("invalid", now)


def test_detect_agent_state_rate_limited() -> None:
    """Test detection of rate limited state."""
    # Full Claude interface with rate limit message
    rate_limit_content = """
Welcome to Claude Code
╭─ Claude │ Chat with Claude 3.5 Sonnet ─────────────────────────────────────────────────╮
│ > Can you help me?                                                                      │
╰─────────────────────────────────────────────────────────────────────────────────────────╯

Claude usage limit reached. Your limit will reset at 4:30pm (UTC).
Please try again after that time.
"""
    state = detect_agent_state(rate_limit_content)
    assert state == AgentState.RATE_LIMITED

    # Rate limit without full interface should still be detected as rate limited
    minimal_content = "Claude usage limit reached. Your limit will reset at 4am (UTC)."
    state = detect_agent_state(minimal_content)
    assert state == AgentState.RATE_LIMITED  # Rate limit is checked first


def test_should_notify_pm_for_rate_limited() -> None:
    """Test PM notification logic for rate limited state."""
    # Fresh notification
    result = should_notify_pm(AgentState.RATE_LIMITED, "test-session:1", {})
    assert result is True

    # With recent notification (should have cooldown)
    recent_time = datetime.now() - timedelta(minutes=2)
    notification_history = {"crash_test-session:1": recent_time}
    result = should_notify_pm(AgentState.RATE_LIMITED, "test-session:1", notification_history)
    assert result is False  # Within 5 minute cooldown

    # After cooldown period
    old_time = datetime.now() - timedelta(minutes=10)
    notification_history = {"crash_test-session:1": old_time}
    result = should_notify_pm(AgentState.RATE_LIMITED, "test-session:1", notification_history)
    assert result is True


@patch("tmux_orchestrator.core.monitor.TMUXManager")
@patch("tmux_orchestrator.core.monitor.time.sleep")
def test_monitor_detects_and_handles_rate_limit(mock_sleep, mock_tmux_manager) -> None:
    """Test that monitor detects rate limit and pauses appropriately."""
    from tmux_orchestrator.core.monitor import IdleMonitor

    # Setup
    tmux = mock_tmux_manager.return_value
    monitor = IdleMonitor(tmux)

    # Mock agent discovery
    tmux.list_sessions.return_value = [{"name": "test-session"}]
    tmux.list_windows.return_value = [{"index": "1", "name": "claude-dev"}]

    # Mock rate limit content
    rate_limit_content = """
Welcome to Claude Code
Claude usage limit reached. Your limit will reset at 4:30pm (UTC).
"""
    tmux.capture_pane.return_value = rate_limit_content

    # Mock logger
    with patch("tmux_orchestrator.core.monitor.logging.getLogger") as mock_logger:
        logger = MagicMock()
        mock_logger.return_value = logger

        # Run one monitor cycle
        monitor._monitor_cycle(tmux, logger)

        # Verify rate limit was detected
        logger.warning.assert_called()
        warning_calls = [call.args[0] for call in logger.warning.call_args_list]
        assert any("Rate limit detected" in msg for msg in warning_calls)

        # Verify sleep was called with appropriate duration
        mock_sleep.assert_called()
        sleep_duration = mock_sleep.call_args[0][0]
        # Should be positive and reasonable (between 1 minute and 24 hours)
        assert 60 <= sleep_duration <= 86400


def test_rate_limit_time_extraction_comprehensive() -> None:
    """Test comprehensive time extraction scenarios."""
    # Test with various Claude response formats
    test_messages = [
        # Standard Claude responses
        """
Error: Claude usage limit reached. Your limit will reset at 4am (UTC).

Please try again after that time. You can check your usage at:
https://console.anthropic.com
""",
        # With additional context
        """
I apologize, but I've reached my usage limit.

Claude usage limit reached. Your limit will reset at 11:30pm (UTC).

This is a temporary restriction that will be lifted at the specified time.
""",
        # Inline with other text
        "Sorry! Claude usage limit reached. Your limit will reset at 2:15pm (UTC). Come back later!",
    ]

    expected_times = ["4am", "11:30pm", "2:15pm"]

    for message, expected in zip(test_messages, expected_times):
        result = extract_rate_limit_reset_time(message)
        assert result == expected


def test_sleep_duration_timezone_handling() -> None:
    """Test that sleep duration correctly handles UTC timezone."""
    # Test from different timezones (but calculation should always use UTC)
    utc_now = datetime(2024, 12, 5, 14, 0, 0, tzinfo=timezone.utc)

    # Reset at 4pm UTC (2 hours from now)
    result = calculate_sleep_duration("4pm", utc_now)
    assert result == 7320  # 2 hours + 2 min buffer

    # Verify the calculation is consistent
    # Even if we mistakenly pass a naive datetime, it should work
    naive_now = datetime(2024, 12, 5, 14, 0, 0)
    result2 = calculate_sleep_duration("4pm", naive_now)
    assert result2 == 7320  # Should be the same


@pytest.mark.parametrize(
    "current_time,reset_time,expected_hours",
    [
        # Normal cases
        ("14:00", "16:00", 2.033),  # 2 hours + 2 min buffer
        ("23:00", "01:00", 2.033),  # Crosses midnight
        ("00:30", "00:45", 0.283),  # Very short duration
        # Edge cases
        ("23:59", "00:01", 0.067),  # Just across midnight (2 min + 2 min buffer)
        ("12:00", "12:00", 24.033),  # Same time (next day)
    ],
)
def test_sleep_calculation_parametrized(current_time, reset_time, expected_hours) -> None:
    """Parametrized test for various time combinations."""
    # Parse current time
    hour, minute = map(int, current_time.split(":"))
    now = datetime(2024, 12, 5, hour, minute, 0, tzinfo=timezone.utc)

    # Convert reset time to am/pm format
    reset_hour, reset_minute = map(int, reset_time.split(":"))
    if reset_hour == 0:
        reset_str = f"12:{reset_minute:02d}am"
    elif reset_hour < 12:
        reset_str = f"{reset_hour}:{reset_minute:02d}am" if reset_minute else f"{reset_hour}am"
    elif reset_hour == 12:
        reset_str = f"12:{reset_minute:02d}pm" if reset_minute else "12pm"
    else:
        reset_str = f"{reset_hour - 12}:{reset_minute:02d}pm" if reset_minute else f"{reset_hour - 12}pm"

    result_seconds = calculate_sleep_duration(reset_str, now)
    result_hours = result_seconds / 3600

    assert abs(result_hours - expected_hours) < 0.01, (
        f"Failed for {current_time} -> {reset_time} ({reset_str}): "
        f"got {result_hours:.3f} hours, expected {expected_hours:.3f}"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
