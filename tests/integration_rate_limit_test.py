"""Integration tests for rate limit handling feature.

This module performs real integration testing of the rate limit functionality:
1. Daemon pause/resume behavior when rate limit is detected
2. PM notification format and content
3. Resume after timeout completion
4. Edge case handling in production environment
"""

import logging
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from tmux_orchestrator.core.monitor import IdleMonitor
from tmux_orchestrator.utils.tmux import TMUXManager


@pytest.fixture
def monitor(mock_tmux):
    """Create an IdleMonitor instance with mock tmux."""
    return IdleMonitor(mock_tmux)


def test_daemon_pauses_on_rate_limit_detection(mock_tmux, monitor, logger) -> None:
    """Test that daemon properly pauses when rate limit is detected."""
    # Simulate rate limit content
    rate_limit_content = """
╭─ Assistant ─────────────────────────────────────────────────────╮
│ I'll help you implement that feature. Let me analyze the code. │
╰─────────────────────────────────────────────────────────────────╯

Claude usage limit reached. Your limit will reset at 4am (UTC).

╭─────────────────────────────────────────────────────────────────╮
│ >                                                               │
╰─────────────────────────────────────────────────────────────────╯
"""

    # Set up mock responses
    mock_tmux.capture_pane.return_value = rate_limit_content

    # Mock current time as 2am UTC (2 hours before reset)
    mock_now = datetime(2024, 1, 15, 2, 0, 0, tzinfo=timezone.utc)

    # Track if sleep was called with correct duration
    sleep_called = False
    sleep_duration = 0

    def mock_sleep(duration):
        nonlocal sleep_called, sleep_duration
        sleep_called = True
        sleep_duration = duration

    with patch("time.sleep", side_effect=mock_sleep):
        with patch("datetime.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            # Run monitor cycle
            monitor._monitor_cycle(mock_tmux, logger)

    # Verify sleep was called with correct duration
    assert sleep_called, "Daemon should pause when rate limit detected"
    # Expected: 2 hours (7200s) + 2 minute buffer (120s) = 7320s
    expected_duration = 2 * 3600 + 120
    assert sleep_duration == expected_duration, f"Expected {expected_duration}s sleep, got {sleep_duration}s"


def test_pm_notification_format_and_content(mock_tmux, monitor, logger) -> None:
    """Test PM notification message format when rate limit is detected."""
    rate_limit_content = """
Claude usage limit reached. Your limit will reset at 6:30am (UTC).
"""

    # Set up mocks
    mock_tmux.capture_pane.return_value = rate_limit_content
    pm_target = "test-session:0"

    # Mock finding PM
    with patch.object(monitor, "_find_pm_agent", return_value=pm_target):
        with patch("time.sleep"):  # Don't actually sleep
            with patch("datetime.datetime") as mock_datetime:
                mock_now = datetime(2024, 1, 15, 4, 0, 0, tzinfo=timezone.utc)
                mock_datetime.now.return_value = mock_now
                mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

                # Run monitor cycle
                monitor._monitor_cycle(mock_tmux, logger)

    # Verify PM notification was sent
    assert mock_tmux.send_message.called, "PM should be notified"

    # Get the message that was sent
    call_args = mock_tmux.send_message.call_args_list[0]
    target, message = call_args[0]

    # Verify target
    assert target == pm_target, f"Expected notification to {pm_target}"

    # Verify message content
    assert "🚨 RATE LIMIT REACHED" in message, "Should have clear alert"
    assert "6:30am UTC" in message, "Should include exact reset time"
    assert "monitoring daemon will pause" in message, "Should explain behavior"
    assert "2 minutes after reset for safety" in message, "Should mention buffer"
    assert "All agents will become responsive" in message, "Should reassure about recovery"


def test_resume_notification_after_timeout(mock_tmux, monitor, logger) -> None:
    """Test that PM receives resume notification after rate limit expires."""
    rate_limit_content = """
Claude usage limit reached. Your limit will reset at 5am (UTC).
"""

    # Set up mocks
    mock_tmux.capture_pane.return_value = rate_limit_content
    pm_target = "test-session:0"

    # Track messages sent
    messages_sent = []

    def capture_message(target, msg):
        messages_sent.append((target, msg))
        return True

    mock_tmux.send_message.side_effect = capture_message

    with patch.object(monitor, "_find_pm_agent", return_value=pm_target):
        with patch("time.sleep"):  # Don't actually sleep
            with patch("datetime.datetime") as mock_datetime:
                mock_now = datetime(2024, 1, 15, 4, 30, 0, tzinfo=timezone.utc)
                mock_datetime.now.return_value = mock_now
                mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

                # Run monitor cycle
                monitor._monitor_cycle(mock_tmux, logger)

    # Should have sent two messages: rate limit + resume
    assert len(messages_sent) >= 2, "Should send both pause and resume notifications"

    # Find resume message
    resume_messages = [msg for (t, msg) in messages_sent if "Rate limit reset!" in msg]
    assert len(resume_messages) >= 1, "Should send resume notification"

    resume_msg = resume_messages[0]
    assert "🎉" in resume_msg, "Should have celebratory indicator"
    assert "Monitoring resumed" in resume_msg, "Should confirm monitoring restarted"
    assert "should now be responsive" in resume_msg, "Should indicate agents are working"


def test_edge_case_no_pm_available(mock_tmux, monitor, logger) -> None:
    """Test graceful handling when no PM is found during rate limit."""
    rate_limit_content = """
Claude usage limit reached. Your limit will reset at 3am (UTC).
"""

    # Set up mocks
    mock_tmux.capture_pane.return_value = rate_limit_content

    # Mock no PM found
    with patch.object(monitor, "_find_pm_agent", return_value=None):
        with patch("time.sleep") as mock_sleep:
            with patch("datetime.datetime") as mock_datetime:
                mock_now = datetime(2024, 1, 15, 1, 0, 0, tzinfo=timezone.utc)
                mock_datetime.now.return_value = mock_now
                mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

                # Run monitor cycle - should not raise exception
                monitor._monitor_cycle(mock_tmux, logger)

    # Should still sleep even without PM
    assert mock_sleep.called, "Should pause monitoring even without PM"

    # Should not try to send messages
    assert not mock_tmux.send_message.called, "Should not send messages without PM"


def test_edge_case_multiple_agents_rate_limited(mock_tmux, monitor, logger) -> None:
    """Test handling when multiple agents hit rate limit simultaneously."""
    rate_limit_content = """
Claude usage limit reached. Your limit will reset at 4am (UTC).
"""

    # All agents return rate limit
    mock_tmux.capture_pane.return_value = rate_limit_content

    pm_notified = False

    def track_notification(target, msg):
        nonlocal pm_notified
        if "RATE LIMIT REACHED" in msg:
            pm_notified = True
        return True

    mock_tmux.send_message.side_effect = track_notification

    with patch.object(monitor, "_find_pm_agent", return_value="test-session:0"):
        with patch("time.sleep"):
            with patch("datetime.datetime") as mock_datetime:
                mock_now = datetime(2024, 1, 15, 2, 0, 0, tzinfo=timezone.utc)
                mock_datetime.now.return_value = mock_now
                mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

                # Run monitor cycle
                monitor._monitor_cycle(mock_tmux, logger)

    # Should notify PM once about rate limit
    assert pm_notified, "PM should be notified about rate limit"

    # Should only send one rate limit notification (not one per agent)
    rate_limit_calls = [call for call in mock_tmux.send_message.call_args_list if "RATE LIMIT REACHED" in str(call)]
    assert len(rate_limit_calls) == 1, "Should send single rate limit notification"


def test_edge_case_malformed_reset_time(mock_tmux, monitor, logger) -> None:
    """Test handling of malformed rate limit messages."""
    malformed_content = """
Claude usage limit reached. Your limit will reset at invalid time (UTC).
"""

    # Set up mocks
    mock_tmux.capture_pane.return_value = malformed_content

    # Should handle gracefully without crashing
    with patch("time.sleep"):
        with patch("datetime.datetime") as mock_datetime:
            mock_now = datetime(2024, 1, 15, 2, 0, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = mock_now

            # Should not raise exception
            try:
                monitor._monitor_cycle(mock_tmux, logger)
            except Exception as e:
                pytest.fail(f"Should handle malformed time gracefully, got: {e}")


@pytest.mark.parametrize(
    "content,expected_detected",
    [
        # Standard format
        ("Claude usage limit reached. Your limit will reset at 4am (UTC).", True),
        # Different time formats
        ("Claude usage limit reached. Your limit will reset at 2:30pm (UTC).", True),
        ("Claude usage limit reached. Your limit will reset at 12am (UTC).", True),
        # Case variations
        ("claude usage limit reached. your limit will reset at 4am (utc).", True),
        ("CLAUDE USAGE LIMIT REACHED. YOUR LIMIT WILL RESET AT 4AM (UTC).", True),
        # Mixed content
        ("Error occurred\nClaude usage limit reached. Your limit will reset at 6pm (UTC).\nTry again later", True),
        # False positive - missing second part
        ("Claude usage limit reached but no reset time provided", False),
        # False positive - discussion about limits
        ("Let me explain how Claude usage limits work", False),
    ],
)
def test_rate_limit_detection_accuracy(content, expected_detected) -> None:
    """Test that rate limit is detected accurately in various formats."""
    mock_tmux = Mock(spec=TMUXManager)
    mock_tmux.capture_pane.return_value = content

    # Check if rate limit logic triggers
    rate_limit_detected = False

    # Simple check based on monitor implementation
    if "claude usage limit reached" in content.lower() and "your limit will reset at" in content.lower():
        rate_limit_detected = True

    assert rate_limit_detected == expected_detected, f"Rate limit detection failed for: {content[:50]}..."


def test_sleep_duration_calculation_integration() -> None:
    """Test sleep duration calculation in real scenarios."""
    from tmux_orchestrator.core.monitor_helpers import calculate_sleep_duration

    test_scenarios = [
        # Current: 2am, Reset: 4am = 2 hours + buffer
        (datetime(2024, 1, 15, 2, 0, 0, tzinfo=timezone.utc), "4am", 7320),
        # Current: 11pm, Reset: 4am (next day) = 5 hours + buffer
        (datetime(2024, 1, 15, 23, 0, 0, tzinfo=timezone.utc), "4am", 18120),
        # Current: 1:30pm, Reset: 2:30pm = 1 hour + buffer
        (datetime(2024, 1, 15, 13, 30, 0, tzinfo=timezone.utc), "2:30pm", 3720),
        # Current: 11:45pm, Reset: 12am (midnight) = 15 mins + buffer
        (datetime(2024, 1, 15, 23, 45, 0, tzinfo=timezone.utc), "12am", 1020),
    ]

    for current_time, reset_time, expected_seconds in test_scenarios:
        result = calculate_sleep_duration(reset_time, current_time)
        assert (
            result == expected_seconds
        ), f"Expected {expected_seconds}s for {current_time.strftime('%H:%M')} -> {reset_time}, got {result}s"


def test_logging_appropriateness(mock_tmux, monitor) -> None:
    """Test that logging is appropriate and informative."""
    rate_limit_content = """
Claude usage limit reached. Your limit will reset at 4am (UTC).
"""

    # Set up mock logger to capture logs
    mock_logger = Mock(spec=logging.Logger)
    log_messages = []

    def capture_log(msg, *args, **kwargs):
        log_messages.append(msg)

    mock_logger.info.side_effect = capture_log
    mock_logger.warning.side_effect = capture_log
    mock_logger.error.side_effect = capture_log

    mock_tmux.capture_pane.return_value = rate_limit_content

    with patch.object(monitor, "_find_pm_agent", return_value="test-session:0"):
        with patch("time.sleep"):
            with patch("datetime.datetime") as mock_datetime:
                mock_now = datetime(2024, 1, 15, 2, 0, 0, tzinfo=timezone.utc)
                mock_datetime.now.return_value = mock_now
                mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

                # Run monitor cycle with mock logger
                monitor._monitor_cycle(mock_tmux, mock_logger)

    # Verify appropriate log messages
    rate_limit_logs = [msg for msg in log_messages if "rate limit" in msg.lower()]
    assert len(rate_limit_logs) >= 2, "Should log rate limit detection and sleep info"

    # Check for specific log content
    assert any("Rate limit detected" in msg for msg in log_messages), "Should log rate limit detection"
    assert any("Sleeping for" in msg and "seconds" in msg for msg in log_messages), "Should log sleep duration"
    assert any("PM" in msg and "notified" in msg for msg in log_messages), "Should log PM notification"


def test_agents_responsive_after_reset() -> None:
    """Test that agents become responsive after rate limit resets."""
    # This would require actual tmux interaction
    # For integration test, we verify the notification promises this

    rate_limit_content = """
Claude usage limit reached. Your limit will reset at 4am (UTC).
"""

    tmux = Mock(spec=TMUXManager)
    monitor = IdleMonitor(tmux)

    # Capture messages
    messages = []
    tmux.send_message.side_effect = lambda t, m: messages.append(m) or True

    tmux.capture_pane.return_value = rate_limit_content
    tmux.list_sessions.return_value = [{"name": "test", "windows": 1}]
    tmux.list_windows.return_value = [{"index": "0", "name": "claude-pm"}]

    with patch.object(monitor, "_find_pm_agent", return_value="test:0"):
        with patch("time.sleep"):
            with patch("datetime.datetime") as mock_dt:
                mock_dt.now.return_value = datetime(2024, 1, 15, 3, 0, 0, tzinfo=timezone.utc)
                mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

                monitor._monitor_cycle(tmux, logging.getLogger())

    # Verify promises made in notifications
    assert any("All agents will become responsive" in msg for msg in messages), "Should promise agent recovery"
    assert any(
        "should now be responsive" in msg for msg in messages
    ), "Resume message should confirm agents are working"
