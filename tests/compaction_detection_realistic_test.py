"""Test compaction detection with realistic monitor logic flow."""

from unittest.mock import MagicMock, patch

import pytest

from tmux_orchestrator.core.monitor import IdleMonitor


def test_compaction_state_detection() -> None:
    """Test that compaction is properly detected as ACTIVE state."""
    tmux = MagicMock()
    monitor = IdleMonitor(tmux)

    # Realistic Claude UI during compaction
    compacting_content = """╭─ Claude Code ──────────────────────────────────────────────────────────────╮
│                                                                             │
│ Human: Please analyze this codebase                                         │
│                                                                             │
│ Assistant: I'll analyze the codebase for you.                              │
│                                                                             │
│ [Compacting conversation...]                                                │
│                                                                             │
│ >                                                                           │
│                                                                             │
╰─────────────────────────────────────────────────────────────────────────────╯"""

    # Mock to return same content 4 times (appears idle but is compacting)
    tmux.capture_pane.return_value = compacting_content

    with patch("tmux_orchestrator.core.monitor.logging.getLogger") as mock_logger:
        logger = MagicMock()
        mock_logger.return_value = logger

        # No PM needed for this test
        monitor._find_pm_agent = MagicMock(return_value=None)

        # Run check
        monitor._check_agent_status(tmux, "test:1", logger, {})

        # Check logs to verify detection
        debug_logs = [call.args[0] for call in logger.debug.call_args_list]
        info_logs = [call.args[0] for call in logger.info.call_args_list]

        # Should be detected as ACTIVE due to "Compacting conversation" in thinking patterns
        assert any("found thinking indicator: 'Compacting conversation'" in log for log in debug_logs)
        assert any("is ACTIVE" in log for log in info_logs)


def test_idle_without_compacting() -> None:
    """Test that truly idle agent (no compacting) gets PM notification."""
    tmux = MagicMock()
    monitor = IdleMonitor(tmux)

    # Idle Claude UI without compacting
    idle_content = """╭─ Claude Code ──────────────────────────────────────────────────────────────╮
│                                                                             │
│ Human: What can you help me with?                                           │
│                                                                             │
│ Assistant: I can help you with various programming tasks including:         │
│ - Code analysis and debugging                                               │
│ - Writing new features                                                      │
│ - Refactoring existing code                                                 │
│                                                                             │
│ >                                                                           │
│                                                                             │
╰─────────────────────────────────────────────────────────────────────────────╯"""

    # Mock to return same content 4 times (truly idle)
    tmux.capture_pane.side_effect = [idle_content] * 4

    with patch("tmux_orchestrator.core.monitor.logging.getLogger") as mock_logger:
        logger = MagicMock()
        mock_logger.return_value = logger

        # Mock PM exists
        monitor._find_pm_agent = MagicMock(return_value="pm:0")

        # Mock that we should notify PM (no cooldown)
        with patch("tmux_orchestrator.core.monitor.should_notify_pm", return_value=True):
            # Run check
            monitor._check_agent_status(tmux, "test:1", logger, {})

        # Check logs
        info_logs = [call.args[0] for call in logger.info.call_args_list]

        # Should be IDLE
        assert any("is IDLE" in log for log in info_logs)

        # PM should be notified since truly idle
        assert any("notifying PM" in log for log in info_logs)


def test_compaction_near_input_detection() -> None:
    """Test the simplified compaction detection logic for near-input compacting."""
    # The simpler approach looks for 'compacting' 2-4 lines above input box
    content = """╭─ Claude Code ──────────────────────────────────────────────────────────────╮
│ Previous conversation...                                                    │
│                                                                             │
│ [Compacting conversation...]                                                │
│                                                                             │
│ >                                                                           │
│                                                                             │
╰─────────────────────────────────────────────────────────────────────────────╯"""

    lines = content.strip().split("\n")
    is_compacting = False

    # Find input box and check 2-4 lines above
    for i, line in enumerate(lines):
        if "│ >" in line:
            start = max(0, i - 4)
            for j in range(start, i):
                if "compacting" in lines[j].lower():
                    is_compacting = True
                    break
            break

    assert is_compacting is True


def test_compaction_detection_edge_cases() -> None:
    """Test various compaction message formats."""
    test_cases = [
        ("Compacting conversation...", True),
        ("compacting the conversation", True),
        ("COMPACTING CONVERSATION", True),
        ("[Compacting old messages...]", True),
        ("Compact mode enabled", False),  # Not "compacting"
        ("Compression complete", False),  # Not "compacting"
    ]

    for message, should_detect in test_cases:
        content = f"""╭─ Claude Code ──────────────────────────────────────────────────────────────╮
│                                                                             │
│ {message}                                                                   │
│                                                                             │
│ >                                                                           │
│                                                                             │
╰─────────────────────────────────────────────────────────────────────────────╯"""

        lines = content.strip().split("\n")
        is_compacting = False

        for i, line in enumerate(lines):
            if "│ >" in line:
                start = max(0, i - 4)
                for j in range(start, i):
                    if "compacting" in lines[j].lower():
                        is_compacting = True
                        break
                break

        assert is_compacting == should_detect, f"Failed for: {message}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
