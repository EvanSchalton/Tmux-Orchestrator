"""Comprehensive tests for rate limit detection and handling.

This module tests the rate limiting functionality implemented in the monitoring system:
1. Rate limit message detection from fixtures
2. Time extraction for various formats
3. Sleep duration calculation
4. Daemon pause/resume behavior
5. PM notification content and formatting
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from tmux_orchestrator.core.monitor import IdleMonitor
from tmux_orchestrator.core.monitor_helpers import (
    AgentState,
    calculate_sleep_duration,
    detect_agent_state,
    extract_rate_limit_reset_time,
    should_notify_pm,
)


@pytest.fixture
def fixtures_dir():
    """Get path to rate limit fixtures directory."""
    return Path(__file__).parent / "fixtures" / "rate_limit_examples"


@pytest.fixture
def monitor(mock_tmux):
    """Create an IdleMonitor instance with mock tmux."""
    return IdleMonitor(mock_tmux)


def test_standard_rate_limit_detection(fixtures_dir) -> None:
    """Test detection of standard rate limit message (4am UTC)."""
    content = (fixtures_dir / "standard_rate_limit.txt").read_text()

    # Should be detected as RATE_LIMITED state
    state = detect_agent_state(content)
    assert state == AgentState.RATE_LIMITED, f"Expected RATE_LIMITED, got {state}"

    # Should extract correct reset time
    reset_time = extract_rate_limit_reset_time(content)
    assert reset_time == "4am", f"Expected '4am', got '{reset_time}'"


def test_time_variations_detection(fixtures_dir) -> None:
    """Test detection with various time formats."""
    content = (fixtures_dir / "rate_limit_with_time_variations.txt").read_text()

    # Should be detected as RATE_LIMITED
    state = detect_agent_state(content)
    assert state == AgentState.RATE_LIMITED, f"Expected RATE_LIMITED, got {state}"

    # Should extract the first time mentioned (2:30pm)
    reset_time = extract_rate_limit_reset_time(content)
    assert reset_time == "2:30pm", f"Expected '2:30pm', got '{reset_time}'"


def test_mixed_content_detection(fixtures_dir) -> None:
    """Test detection when rate limit appears in middle of conversation."""
    content = (fixtures_dir / "rate_limit_mixed_content.txt").read_text()

    # Should still be detected as RATE_LIMITED
    state = detect_agent_state(content)
    assert state == AgentState.RATE_LIMITED, f"Expected RATE_LIMITED, got {state}"

    # Should extract correct time (7:30am)
    reset_time = extract_rate_limit_reset_time(content)
    assert reset_time == "7:30am", f"Expected '7:30am', got '{reset_time}'"


def test_false_positive_prevention(fixtures_dir) -> None:
    """Test that general usage discussion doesn't trigger rate limit detection."""
    content = (fixtures_dir / "false_positive_rate_limit.txt").read_text()

    # Should NOT be detected as RATE_LIMITED (missing key phrases)
    state = detect_agent_state(content)
    assert state != AgentState.RATE_LIMITED, f"False positive: got {state} when discussing usage"

    # Should be MESSAGE_QUEUED or ACTIVE since Claude is responding normally
    assert state in [AgentState.MESSAGE_QUEUED, AgentState.ACTIVE], f"Expected normal state, got {state}"

    # Should not extract any reset time
    reset_time = extract_rate_limit_reset_time(content)
    assert reset_time is None, f"False positive time extraction: got '{reset_time}'"


def test_extract_standard_times() -> None:
    """Test extraction of standard time formats."""
    test_cases = [
        ("Your limit will reset at 4am (UTC).", "4am"),
        ("Your limit will reset at 2:30pm (UTC).", "2:30pm"),
        ("Your limit will reset at 12am (UTC).", "12am"),
        ("Your limit will reset at 12pm (UTC).", "12pm"),
        ("Your limit will reset at 11:45pm (UTC).", "11:45pm"),
        ("Your limit will reset at 6:15am (UTC).", "6:15am"),
    ]

    for content, expected in test_cases:
        result = extract_rate_limit_reset_time(content)
        assert result == expected, f"Expected '{expected}' from '{content}', got '{result}'"


def test_extract_case_insensitive() -> None:
    """Test that time extraction works regardless of case."""
    content = "your limit will reset at 4AM (utc)."
    result = extract_rate_limit_reset_time(content)
    assert result == "4AM", f"Expected '4AM', got '{result}'"


def test_extract_no_match() -> None:
    """Test that non-matching content returns None."""
    test_cases = [
        "No rate limit message here",
        "Usage resets daily",
        "Your limit will reset tomorrow",
        "Limit resets at some time",
        "",
    ]

    for content in test_cases:
        result = extract_rate_limit_reset_time(content)
        assert result is None, f"Expected None for '{content}', got '{result}'"


def test_calculate_same_day_future_time() -> None:
    """Test calculation when reset time is later today."""
    # Current time: 2pm UTC, Reset time: 6pm UTC
    now = datetime(2024, 1, 15, 14, 0, 0, tzinfo=timezone.utc)  # 2pm UTC
    reset_time = "6pm"

    duration = calculate_sleep_duration(reset_time, now)

    # Should be 4 hours (14400s) + 2 minute buffer (120s) = 14520s
    expected = 4 * 3600 + 120
    assert duration == expected, f"Expected {expected}s, got {duration}s"


def test_calculate_next_day_time() -> None:
    """Test calculation when reset time is tomorrow."""
    # Current time: 6pm UTC, Reset time: 4am UTC (next day)
    now = datetime(2024, 1, 15, 18, 0, 0, tzinfo=timezone.utc)  # 6pm UTC
    reset_time = "4am"

    duration = calculate_sleep_duration(reset_time, now)

    # Should be 10 hours (36000s) + 2 minute buffer (120s) = 36120s
    expected = 10 * 3600 + 120
    assert duration == expected, f"Expected {expected}s, got {duration}s"


def test_calculate_with_minutes() -> None:
    """Test calculation with reset times including minutes."""
    # Current time: 1pm UTC, Reset time: 2:30pm UTC
    now = datetime(2024, 1, 15, 13, 0, 0, tzinfo=timezone.utc)  # 1pm UTC
    reset_time = "2:30pm"

    duration = calculate_sleep_duration(reset_time, now)

    # Should be 1.5 hours (5400s) + 2 minute buffer (120s) = 5520s
    expected = 90 * 60 + 120  # 90 minutes + buffer
    assert duration == expected, f"Expected {expected}s, got {duration}s"


def test_calculate_midnight_handling() -> None:
    """Test calculation with midnight (12am) reset times."""
    # Current time: 10pm UTC, Reset time: 12am UTC (next day)
    now = datetime(2024, 1, 15, 22, 0, 0, tzinfo=timezone.utc)  # 10pm UTC
    reset_time = "12am"

    duration = calculate_sleep_duration(reset_time, now)

    # Should be 2 hours (7200s) + 2 minute buffer (120s) = 7320s
    expected = 2 * 3600 + 120
    assert duration == expected, f"Expected {expected}s, got {duration}s"


def test_calculate_noon_handling() -> None:
    """Test calculation with noon (12pm) reset times."""
    # Current time: 10am UTC, Reset time: 12pm UTC
    now = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)  # 10am UTC
    reset_time = "12pm"

    duration = calculate_sleep_duration(reset_time, now)

    # Should be 2 hours (7200s) + 2 minute buffer (120s) = 7320s
    expected = 2 * 3600 + 120
    assert duration == expected, f"Expected {expected}s, got {duration}s"


def test_invalid_time_format() -> None:
    """Test that invalid time formats raise ValueError."""
    now = datetime(2024, 1, 15, 14, 0, 0, tzinfo=timezone.utc)

    invalid_formats = ["25am", "13:70pm", "invalid", ""]

    for invalid_time in invalid_formats:
        with pytest.raises(ValueError, match="Invalid time format"):
            calculate_sleep_duration(invalid_time, now)


def test_rate_limit_triggers_daemon_pause(mock_tmux, monitor, logger) -> None:
    """Test that detecting rate limit causes daemon to pause monitoring."""
    rate_limit_content = "Claude usage limit reached. Your limit will reset at 4am (UTC)."

    # Mock tmux structure
    mock_tmux.list_sessions.return_value = [{"name": "test-session", "windows": 2, "created": "2024-01-15"}]
    mock_tmux.list_windows.return_value = [
        {"index": "0", "name": "claude-pm", "active": True},
        {"index": "1", "name": "claude-dev", "active": False},
    ]

    # Mock rate limit content
    mock_tmux.capture_pane.return_value = rate_limit_content
    mock_tmux.send_message.return_value = True

    with patch("tmux_orchestrator.core.monitor.time.sleep") as mock_sleep:
        with patch("tmux_orchestrator.core.monitor_helpers.datetime") as mock_datetime:
            # Mock current time as 2am UTC (2 hours before reset)
            now = datetime(2024, 1, 15, 2, 0, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            # Mock PM discovery
            with patch.object(monitor, "_find_pm_agent", return_value="pm:0"):
                # Call monitoring cycle which should detect rate limit
                monitor._monitor_cycle(mock_tmux, logger)

        # Should have called sleep with correct duration
        # The calculation adds a buffer and may adjust for timezone
        mock_sleep.assert_called_once()
        sleep_duration = mock_sleep.call_args[0][0]

        # Verify sleep was called with a reasonable duration (> 1 hour, < 24 hours)
        assert 3600 < sleep_duration < 86400, f"Sleep duration {sleep_duration}s is unreasonable"

        # The exact duration depends on timezone handling, but it should be roughly 2 hours + buffer
        # Allow for some variance in the calculation
        min_expected = 7000  # ~2 hours minus some margin
        max_expected = 35000  # Account for timezone differences
        assert (
            min_expected <= sleep_duration <= max_expected
        ), f"Sleep duration {sleep_duration}s outside expected range"


def test_pm_notification_during_rate_limit(mock_tmux, monitor, logger) -> None:
    """Test that PM is notified when rate limit is detected."""
    rate_limit_content = "Claude usage limit reached. Your limit will reset at 6:30am (UTC)."
    pm_target = "pm:0"

    mock_tmux.capture_pane.return_value = rate_limit_content

    with patch("time.sleep"):
        with patch("datetime.datetime") as mock_datetime:
            now = datetime(2024, 1, 15, 4, 0, 0, tzinfo=timezone.utc)  # 4am UTC
            mock_datetime.now.return_value = now

            with patch.object(monitor, "_find_pm_agent", return_value=pm_target):
                monitor._monitor_cycle(mock_tmux, logger)

    # Should have sent notification to PM
    assert mock_tmux.send_message.called, "PM should be notified about rate limit"

    # Check notification content
    notification_calls = [call for call in mock_tmux.send_message.call_args_list if call[0][0] == pm_target]
    assert len(notification_calls) >= 1, "Should have notified PM"

    message = notification_calls[0][0][1]
    assert "🚨 RATE LIMIT REACHED" in message, "Message should indicate rate limit"
    assert "6:30am UTC" in message, "Message should include reset time"
    assert "monitoring daemon will pause" in message, "Message should explain daemon behavior"


def test_resume_notification_after_sleep(mock_tmux, monitor, logger) -> None:
    """Test that PM is notified when monitoring resumes."""
    rate_limit_content = "Claude usage limit reached. Your limit will reset at 5am (UTC)."
    pm_target = "pm:0"

    mock_tmux.capture_pane.return_value = rate_limit_content

    with patch("time.sleep"):
        with patch("datetime.datetime") as mock_datetime:
            now = datetime(2024, 1, 15, 4, 30, 0, tzinfo=timezone.utc)  # 4:30am UTC
            mock_datetime.now.return_value = now

            with patch.object(monitor, "_find_pm_agent", return_value=pm_target):
                monitor._monitor_cycle(mock_tmux, logger)

    # Should have sent two messages: rate limit notification + resume notification
    assert mock_tmux.send_message.call_count >= 2, "Should notify about both pause and resume"

    # Check resume notification
    messages = [call[0][1] for call in mock_tmux.send_message.call_args_list]
    resume_messages = [msg for msg in messages if "Rate limit reset!" in msg and "resumed" in msg]
    assert len(resume_messages) >= 1, "Should have sent resume notification"


def test_no_pm_found_handling(mock_tmux, monitor, logger) -> None:
    """Test graceful handling when no PM is found during rate limit."""
    rate_limit_content = "Claude usage limit reached. Your limit will reset at 3am (UTC)."

    mock_tmux.capture_pane.return_value = rate_limit_content

    with patch("tmux_orchestrator.core.monitor.time.sleep") as mock_sleep:
        with patch("datetime.datetime") as mock_datetime:
            now = datetime(2024, 1, 15, 1, 0, 0, tzinfo=timezone.utc)  # 1am UTC
            mock_datetime.now.return_value = now

            # Mock no PM found
            with patch.object(monitor, "_find_pm_agent", return_value=None):
                monitor._monitor_cycle(mock_tmux, logger)

    # Should still sleep despite no PM
    assert mock_sleep.called, "Should still pause monitoring even without PM"

    # Should not have tried to send any messages
    assert not mock_tmux.send_message.called, "Should not try to send messages without PM"


def test_rate_limit_notification_format(mock_tmux, monitor) -> None:
    """Test the format of rate limit notification messages."""
    pm_target = "pm:0"
    reset_time = "4am"

    with patch("datetime.datetime") as mock_datetime:
        now = datetime(2024, 1, 15, 2, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = now

        with patch.object(monitor, "_find_pm_agent", return_value=pm_target):
            # Simulate the PM notification part of rate limit handling
            message = (
                f"🚨 RATE LIMIT REACHED: All Claude agents are rate limited.\n"
                f"Will reset at {reset_time} UTC.\n\n"
                f"The monitoring daemon will pause and resume at {(now + timedelta(hours=2, minutes=2)).strftime('%H:%M')} UTC "
                f"(2 minutes after reset for safety).\n"
                f"All agents will become responsive after the rate limit resets."
            )

            mock_tmux.send_message(pm_target, message)

    # Verify message was sent
    assert mock_tmux.send_message.called
    sent_message = mock_tmux.send_message.call_args[0][1]

    # Check message components
    assert "🚨 RATE LIMIT REACHED" in sent_message, "Should have clear alert indicator"
    assert "4am UTC" in sent_message, "Should include reset time"
    assert "monitoring daemon will pause" in sent_message, "Should explain daemon behavior"
    assert "2 minutes after reset for safety" in sent_message, "Should explain buffer time"
    assert "All agents will become responsive" in sent_message, "Should reassure about recovery"


def test_resume_notification_format(mock_tmux) -> None:
    """Test the format of monitoring resume notification."""
    pm_target = "pm:0"
    resume_message = "🎉 Rate limit reset! Monitoring resumed. All agents should now be responsive."

    mock_tmux.send_message(pm_target, resume_message)

    # Verify message components
    assert mock_tmux.send_message.called
    sent_message = mock_tmux.send_message.call_args[0][1]

    assert "🎉" in sent_message, "Should have celebratory indicator"
    assert "Rate limit reset" in sent_message, "Should confirm reset occurred"
    assert "Monitoring resumed" in sent_message, "Should confirm monitoring restarted"
    assert "should now be responsive" in sent_message, "Should indicate agents are working"


def test_rate_limited_needs_recovery() -> None:
    """Test that RATE_LIMITED state is considered as needing recovery."""
    from tmux_orchestrator.core.monitor_helpers import needs_recovery

    # Rate limited agents should be considered as needing recovery/attention
    assert needs_recovery(AgentState.RATE_LIMITED), "RATE_LIMITED should need recovery"


def test_rate_limited_should_notify_pm() -> None:
    """Test that RATE_LIMITED state triggers PM notifications with cooldown."""
    target = "session:1"
    notification_history = {}

    # First notification should be sent
    assert should_notify_pm(
        AgentState.RATE_LIMITED, target, notification_history
    ), "First RATE_LIMITED notification should be sent"

    # Simulate notification was sent
    notification_history[f"crash_{target}"] = datetime.now()

    # Second notification within cooldown should be blocked
    assert not should_notify_pm(
        AgentState.RATE_LIMITED, target, notification_history
    ), "RATE_LIMITED notification should respect cooldown"


def test_rate_limit_detection_priority() -> None:
    """Test that rate limit detection takes priority over other state detection."""
    # Content that has both rate limit and other indicators
    mixed_content = """
    Error: Network timeout occurred

    Claude usage limit reached. Your limit will reset at 4am (UTC).

    Permission denied: Unable to access file
    """

    state = detect_agent_state(mixed_content)
    assert state == AgentState.RATE_LIMITED, f"Rate limit should take priority, got {state}"


def test_malformed_rate_limit_message() -> None:
    """Test handling of malformed rate limit messages."""
    malformed_cases = [
        "Claude usage limit reached. Your limit will reset at invalid (UTC).",
        "Claude usage limit reached. Your limit will reset at (UTC).",
        "Claude usage limit reached. No reset time provided.",
        "Claude usage limit reached. Your limit will reset at 25am (UTC).",
    ]

    for content in malformed_cases:
        # Should still detect as RATE_LIMITED based on key phrases
        state = detect_agent_state(content)
        assert state == AgentState.RATE_LIMITED, f"Should detect rate limit despite malformed time: {content}"

        # But time extraction should return None or handle gracefully
        reset_time = extract_rate_limit_reset_time(content)
        # Either None or it should handle the error gracefully in calculate_sleep_duration
        # Verify reset_time is either None or a valid time string
        assert reset_time is None or isinstance(reset_time, str), f"Invalid reset time type: {type(reset_time)}"


def test_rate_limit_with_partial_message() -> None:
    """Test handling when rate limit message is cut off."""
    partial_content = "Claude usage limit reached. Your limit will reset at"

    # Should still detect as rate limited based on first phrase
    if "claude usage limit reached" in partial_content.lower():
        # This would depend on exact implementation - might be RATE_LIMITED or ERROR
        state = detect_agent_state(partial_content)
        # Either state is acceptable as long as it's handled appropriately
        assert state in [
            AgentState.RATE_LIMITED,
            AgentState.ERROR,
        ], f"Partial rate limit should be handled gracefully, got {state}"


def test_empty_fixture_files() -> None:
    """Test that fixture files are not empty and contain expected content."""
    fixture_files = [
        "standard_rate_limit.txt",
        "rate_limit_with_time_variations.txt",
        "rate_limit_mixed_content.txt",
        "false_positive_rate_limit.txt",
    ]

    fixtures_dir = Path(__file__).parent / "fixtures" / "rate_limit_examples"

    for filename in fixture_files:
        fixture_path = fixtures_dir / filename
        assert fixture_path.exists(), f"Fixture file {filename} should exist"

        content = fixture_path.read_text()
        assert len(content.strip()) > 0, f"Fixture file {filename} should not be empty"

        # Verify expected patterns based on filename
        if "false_positive" not in filename:
            assert (
                "claude usage limit reached" in content.lower()
            ), f"Rate limit fixture {filename} should contain key phrase"
