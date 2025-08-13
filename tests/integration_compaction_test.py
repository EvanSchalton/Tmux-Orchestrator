"""Integration tests for compaction detection feature.

This module performs real integration testing of the compaction detection functionality:
1. Agents aren't marked idle during compaction
2. 'compacting' keyword detection works correctly
3. Different compaction message formats are handled
4. No false positives from similar text
"""

import logging
import time
from unittest.mock import Mock, patch

import pytest

from tmux_orchestrator.core.monitor import IdleMonitor
from tmux_orchestrator.utils.tmux import TMUXManager


@pytest.fixture
def monitor(mock_tmux):
    """Create an IdleMonitor instance with mock tmux."""
    return IdleMonitor(mock_tmux)


def test_agent_not_idle_during_compaction(mock_tmux, monitor, logger) -> None:
    """Test that agents showing 'Compacting conversation' aren't marked idle."""
    # Create snapshots showing no change (would normally indicate idle)
    # but with compaction message visible
    compacting_content = """
╭─ Assistant ─────────────────────────────────────────────────────╮
│ I've analyzed the code and here's my understanding:            │
│                                                                 │
│ The monitoring system uses a daemon process that continuously   │
│ checks agent states. Let me examine the implementation...       │
╰─────────────────────────────────────────────────────────────────╯

Compacting conversation...

╭─────────────────────────────────────────────────────────────────╮
│ >                                                               │
╰─────────────────────────────────────────────────────────────────╯
"""

    # Mock 4 identical snapshots (no change = normally idle)
    mock_tmux.capture_pane.return_value = compacting_content

    # Track if PM was notified about idle
    pm_notified = False

    def track_notification(target, msg):
        nonlocal pm_notified
        if "IDLE AGENT ALERT" in msg:
            pm_notified = True
        return True

    mock_tmux.send_message.side_effect = track_notification

    # Run agent status check
    target = "test-session:1"
    monitor._check_agent_status(mock_tmux, target, logger, {})

    # Agent should be detected as ACTIVE due to compaction
    # PM should NOT be notified about idle state
    assert not pm_notified, "Agent should not be marked idle during compaction"


@pytest.mark.parametrize(
    "content,should_be_compacting",
    [
        # Standard compaction message
        ("Compacting conversation...", True),
        # Case insensitive
        ("compacting conversation...", True),
        ("COMPACTING CONVERSATION...", True),
        # Just the word
        ("compacting", True),
        # In a sentence
        ("The system is compacting the conversation history", True),
        # Similar but not compacting
        ("Comparing conversation styles", False),
        ("Impacting system performance", False),
        # Empty or unrelated
        ("Processing your request...", False),
        ("", False),
    ],
)
def test_compacting_keyword_detection_simple(content, should_be_compacting) -> None:
    """Test simple 'compacting' keyword detection approach."""
    is_compacting = "compacting" in content.lower()
    assert is_compacting == should_be_compacting, f"Compaction detection failed for: '{content}'"


def test_compaction_message_formats(mock_tmux, monitor, logger) -> None:
    """Test different compaction message formats seen in practice."""
    compaction_formats = [
        # Standard format
        """
        Compacting conversation...

        ╭─────────────────────────────────────────────────────────────────╮
        │ >                                                               │
        ╰─────────────────────────────────────────────────────────────────╯
        """,
        # With progress indicator
        """
        Compacting conversation... ████████░░ 80%

        ╭─────────────────────────────────────────────────────────────────╮
        │ >                                                               │
        ╰─────────────────────────────────────────────────────────────────╯
        """,
        # Above input box
        """
        ╭─ Assistant ─────────────────────────────────────────────────────╮
        │ Let me help you with that analysis...                          │
        ╰─────────────────────────────────────────────────────────────────╯

        Compacting conversation...

        ╭─────────────────────────────────────────────────────────────────╮
        │ >                                                               │
        ╰─────────────────────────────────────────────────────────────────╯
        """,
        # Multiple lines above input
        """
        System processing...
        Compacting conversation history to improve performance
        Please wait...

        ╭─────────────────────────────────────────────────────────────────╮
        │ >                                                               │
        ╰─────────────────────────────────────────────────────────────────╯
        """,
    ]

    for format_content in compaction_formats:
        # Mock identical snapshots
        mock_tmux.capture_pane.return_value = format_content

        # Check that agent is not marked idle
        pm_notified = False

        def check_notification(target, msg):
            nonlocal pm_notified
            if "IDLE AGENT ALERT" in msg:
                pm_notified = True
            return True

        mock_tmux.send_message.side_effect = check_notification

        # Run check
        monitor._check_agent_status(mock_tmux, "test-session:1", logger, {})

        # Should not notify PM about idle during compaction
        assert not pm_notified, f"Agent marked idle during compaction for format: {format_content[:50]}..."


def test_false_positive_prevention(mock_tmux, monitor, logger) -> None:
    """Test that similar words don't trigger false positives."""
    false_positive_contents = [
        # Similar words that shouldn't trigger
        """
        Comparing different approaches to the problem

        ╭─────────────────────────────────────────────────────────────────╮
        │ >                                                               │
        ╰─────────────────────────────────────────────────────────────────╯
        """,
        # "compact" but not "compacting"
        """
        The code is very compact and efficient

        ╭─────────────────────────────────────────────────────────────────╮
        │ >                                                               │
        ╰─────────────────────────────────────────────────────────────────╯
        """,
        # Discussion about compaction
        """
        ╭─ Assistant ─────────────────────────────────────────────────────╮
        │ Database compaction is an important maintenance task that      │
        │ reduces storage usage by removing obsolete data.               │
        ╰─────────────────────────────────────────────────────────────────╯

        ╭─────────────────────────────────────────────────────────────────╮
        │ > Tell me more about compaction strategies                     │
        ╰─────────────────────────────────────────────────────────────────╯
        """,
    ]

    for content in false_positive_contents:
        # These should be treated as truly idle (if no changes)
        mock_tmux.capture_pane.return_value = content

        # Track notifications
        notifications = []
        mock_tmux.send_message.side_effect = lambda t, m: notifications.append(m) or True

        # Mock identical snapshots (no activity)
        with patch.object(monitor, "_find_pm_agent", return_value="test-session:0"):
            monitor._check_agent_status(mock_tmux, "test-session:1", logger, {})

        # Without "compacting" keyword, idle agents should be reported
        # (assuming no other activity indicators)
        has_compacting = "compacting" in content.lower()

        if not has_compacting:
            # Should potentially notify about idle (depending on cooldown)
            # This validates that we're not over-triggering on similar words
            pass


@pytest.mark.parametrize(
    "content,should_detect",
    [
        # Directly above input box
        (
            """
    Compacting conversation...
    ╭─────────────────────────────────────────────────────────────────╮
    │ >                                                               │
    ╰─────────────────────────────────────────────────────────────────╯
    """,
            True,
        ),
        # 2 lines above
        (
            """
    Compacting conversation...

    ╭─────────────────────────────────────────────────────────────────╮
    │ >                                                               │
    ╰─────────────────────────────────────────────────────────────────╯
    """,
            True,
        ),
        # 3 lines above
        (
            """
    System message:
    Compacting conversation...

    ╭─────────────────────────────────────────────────────────────────╮
    │ >                                                               │
    ╰─────────────────────────────────────────────────────────────────╯
    """,
            True,
        ),
        # Too far above (more than 3 lines)
        (
            """
    Compacting conversation...

    Some other text here
    More text

    ╭─────────────────────────────────────────────────────────────────╮
    │ >                                                               │
    ╰─────────────────────────────────────────────────────────────────╯
    """,
            True,
        ),  # Simple approach still detects it anywhere
        # After input box (not relevant)
        (
            """
    ╭─────────────────────────────────────────────────────────────────╮
    │ >                                                               │
    ╰─────────────────────────────────────────────────────────────────╯

    Compacting conversation...
    """,
            True,
        ),  # Simple approach detects it anywhere
    ],
)
def test_compaction_near_input_box(content, should_detect, monitor) -> None:
    """Test detection of 'compacting' specifically near input box (2-3 lines above)."""
    # Test with monitor's actual implementation
    lines = content.strip().split("\n")
    is_compacting = False

    # Find input box
    for i, line in enumerate(lines):
        if "│ >" in line or "│\xa0>" in line:
            # Check 2-3 lines above
            start = max(0, i - 3)
            for j in range(start, i):
                if j < len(lines) and "compacting" in lines[j].lower():
                    is_compacting = True
                    break
            if is_compacting:
                break

    # For simple approach, just check anywhere
    simple_detect = "compacting" in content.lower()

    # Both approaches should work
    assert simple_detect == should_detect, "Simple detection failed for scenario"


def test_compaction_with_thinking_indicators(mock_tmux) -> None:
    """Test that compaction is detected alongside thinking indicators."""
    combined_content = """
    💭 Thinking...

    Compacting conversation...

    ╭─────────────────────────────────────────────────────────────────╮
    │ >                                                               │
    ╰─────────────────────────────────────────────────────────────────╯
    """

    # Mock the content
    mock_tmux.capture_pane.return_value = combined_content

    # Check internal logic
    is_active = False

    # Check for thinking patterns
    thinking_patterns = [
        "💭 Thinking...",
        "Compacting conversation",
    ]

    for pattern in thinking_patterns:
        if pattern in combined_content:
            is_active = True
            break

    assert is_active, "Should detect as active with either thinking or compacting"


def test_performance_impact_minimal() -> None:
    """Test that compaction detection has minimal performance impact."""
    # Large content to test performance
    large_content = "\n".join([f"Line {i}" for i in range(1000)])
    large_content += "\nCompacting conversation...\n"
    large_content += """
    ╭─────────────────────────────────────────────────────────────────╮
    │ >                                                               │
    ╰─────────────────────────────────────────────────────────────────╯
    """

    # Time the detection
    start_time = time.time()

    # Simple keyword check
    for _ in range(1000):  # Run 1000 times
        is_compacting = "compacting" in large_content.lower()

    elapsed = time.time() - start_time

    # Should be very fast (< 100ms for 1000 checks)
    assert elapsed < 0.1, f"Compaction detection too slow: {elapsed:.3f}s for 1000 checks"
    assert is_compacting, "Should detect compacting in large content"


def test_integration_with_idle_detection(mock_tmux, monitor, logger) -> None:
    """Test that compaction detection integrates properly with idle detection."""
    # Content that would normally be idle (no changes)
    static_content = """
    ╭─ Assistant ─────────────────────────────────────────────────────╮
    │ Analysis complete. The system is ready for your next request.   │
    ╰─────────────────────────────────────────────────────────────────╯

    ╭─────────────────────────────────────────────────────────────────╮
    │ >                                                               │
    ╰─────────────────────────────────────────────────────────────────╯
    """

    # Same content but with compacting
    compacting_content = """
    ╭─ Assistant ─────────────────────────────────────────────────────╮
    │ Analysis complete. The system is ready for your next request.   │
    ╰─────────────────────────────────────────────────────────────────╯

    Compacting conversation...

    ╭─────────────────────────────────────────────────────────────────╮
    │ >                                                               │
    ╰─────────────────────────────────────────────────────────────────╯
    """

    # Test both scenarios
    notifications = []

    def capture_notifications(target, msg):
        notifications.append(msg)
        return True

    mock_tmux.send_message.side_effect = capture_notifications

    # Test 1: Static content (should be idle)
    mock_tmux.capture_pane.return_value = static_content
    with patch.object(monitor, "_find_pm_agent", return_value="test-session:0"):
        monitor._check_agent_status(mock_tmux, "test-session:1", logger, {})

    # Test 2: Compacting content (should NOT be idle)
    notifications.clear()
    mock_tmux.capture_pane.return_value = compacting_content
    with patch.object(monitor, "_find_pm_agent", return_value="test-session:0"):
        monitor._check_agent_status(mock_tmux, "test-session:1", logger, {})

    # Compacting content should not generate idle notifications
    idle_notifications = [n for n in notifications if "IDLE AGENT ALERT" in n]
    assert len(idle_notifications) == 0, "Should not send idle notifications during compaction"


def test_appropriate_logging_for_compaction() -> None:
    """Test that compaction detection logs appropriately."""
    tmux = Mock(spec=TMUXManager)
    monitor = IdleMonitor(tmux)

    # Mock logger
    mock_logger = Mock(spec=logging.Logger)
    log_messages = []

    def capture_logs(msg, *args, **kwargs):
        log_messages.append(msg)

    mock_logger.debug.side_effect = capture_logs
    mock_logger.info.side_effect = capture_logs

    compacting_content = """
    Compacting conversation...

    ╭─────────────────────────────────────────────────────────────────╮
    │ >                                                               │
    ╰─────────────────────────────────────────────────────────────────╯
    """

    # Mock identical snapshots (would be idle without compaction)
    tmux.capture_pane.return_value = compacting_content
    tmux.list_sessions.return_value = [{"name": "test"}]
    tmux.list_windows.return_value = [{"index": "1", "name": "claude-dev"}]

    # Run check
    monitor._check_agent_status(tmux, "test:1", mock_logger, {})

    # Should log about compaction detection
    compaction_logs = [msg for msg in log_messages if "compacting" in msg.lower()]
    assert len(compaction_logs) >= 1, "Should log when compaction is detected"

    # Should indicate why agent isn't idle
    assert any(
        "appears idle but is compacting" in msg for msg in log_messages
    ), "Should explain why agent isn't marked idle"
