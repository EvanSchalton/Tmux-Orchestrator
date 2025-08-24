#!/usr/bin/env python3
"""Test that fresh Claude instances are protected from auto-submit."""

from unittest.mock import Mock

import pytest

from tmux_orchestrator.core.monitor import IdleMonitor
from tmux_orchestrator.core.monitor_helpers import detect_claude_state

# Fresh Claude instance content
FRESH_CLAUDE_CONTENT = """Welcome to Claude Code!

I'll be working as your AI agent in this tmux session. I'm ready to help with:

• Code development and debugging
• System administration tasks
• Data analysis and processing
• Documentation and technical writing
• And much more!

Feel free to ask me anything or give me tasks to work on. I'll use the tools available to me to help accomplish your goals efficiently.

What would you like me to help you with today?
╭───────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ >                                                                                                     │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────╯
─────────────────────────────────────────────────────────────────────────────────────────────────────────
? for shortcuts ▐ ↑/↓ navigate ▐ esc/cmd+c cancel ▐ enter/cmd+enter submit ▐
"""

# Fresh Claude with placeholder text
FRESH_CLAUDE_WITH_PLACEHOLDER = """╭───────────────────────────────────────────────────╮
│ ✻ Welcome to Claude Code!                         │
│                                                   │
│   /help for help, /status for your current setup  │
│                                                   │
│   cwd: /workspaces/Tmux-Orchestrator              │
╰───────────────────────────────────────────────────╯

╭───────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ > Try "help" for more information                                                                     │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────╯
  ? for shortcuts                                                                 Bypassing Permissions"""


def test_fresh_claude_detected_correctly():
    """Test that fresh Claude instances are properly detected."""
    assert detect_claude_state(FRESH_CLAUDE_CONTENT) == "fresh"
    assert detect_claude_state(FRESH_CLAUDE_WITH_PLACEHOLDER) == "fresh"


def test_auto_submit_prevented_on_fresh():
    """Test that auto-submit is prevented on fresh Claude instances."""
    monitor = IdleMonitor(Mock())

    # Mock TMUXManager
    mock_tmux = Mock()
    mock_tmux.capture_pane.return_value = FRESH_CLAUDE_CONTENT

    # Mock logger
    mock_logger = Mock()

    # Call _try_auto_submit
    monitor._try_auto_submit(mock_tmux, "test:0", mock_logger)

    # Verify press_enter was NOT called
    mock_tmux.press_enter.assert_not_called()
    mock_tmux.press_ctrl_e.assert_not_called()
    mock_tmux.press_escape.assert_not_called()

    # Verify warning was logged
    mock_logger.warning.assert_called_with("PREVENTED auto-submit on fresh Claude instance at test:0")


def test_auto_submit_allowed_on_message_queued():
    """Test that auto-submit works on actual queued messages."""
    monitor = IdleMonitor(Mock())

    # Content with actual message
    message_content = """╭───────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ > Test message that should be submitted                                                               │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────╯"""

    # Mock TMUXManager
    mock_tmux = Mock()
    mock_tmux.capture_pane.return_value = message_content

    # Mock logger
    mock_logger = Mock()

    # Call _try_auto_submit
    monitor._try_auto_submit(mock_tmux, "test:0", mock_logger)

    # Verify press_enter WAS called
    mock_tmux.press_enter.assert_called_once_with("test:0")

    # Verify no prevention warning
    assert not any("PREVENTED" in str(call) for call in mock_logger.warning.call_args_list)


def test_message_not_mistaken_for_fresh():
    """Test that messages like 'Try fix lint errors' are not mistaken for fresh."""
    content_with_try = """╭───────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ > Try "fix lint errors"                                                                               │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────╯"""

    # Should be detected as unsubmitted, not fresh
    assert detect_claude_state(content_with_try) == "unsubmitted"

    # Test auto-submit is allowed
    monitor = IdleMonitor(Mock())
    mock_tmux = Mock()
    mock_tmux.capture_pane.return_value = content_with_try
    mock_logger = Mock()

    monitor._try_auto_submit(mock_tmux, "test:0", mock_logger)

    # Should attempt to submit
    mock_tmux.press_enter.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
