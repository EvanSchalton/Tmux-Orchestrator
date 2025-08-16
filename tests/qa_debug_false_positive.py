#!/usr/bin/env python3
"""Debug script to identify which crash indicators are causing false positives"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from unittest.mock import Mock, patch

from tmux_orchestrator.core.monitor import IdleMonitor
from tmux_orchestrator.core.monitor_helpers import is_claude_interface_present

# Test content that's failing
test_content = """╭─ Assistant ─────────────────────────────────────────────────────╮
│ Running tests... 5 tests failed:                               │
│ • test_auth.py::test_login failed                              │
│ • test_db.py::test_connection failed with timeout              │
│ • test_api.py::test_validation failed                          │
│ Fixing these test failures now...                              │
╰─────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────╮
│ > Analyzing test failures...                                   │
╰─────────────────────────────────────────────────────────────────╯"""

# Create mock objects
mock_tmux = Mock()
mock_tmux.capture_pane.return_value = test_content
mock_tmux.list_sessions.return_value = [{"name": "test"}]
mock_tmux.list_windows.return_value = [{"index": "1", "name": "Claude-PM"}]

with patch("tmux_orchestrator.core.monitor.Config"):
    monitor = IdleMonitor(mock_tmux)

# Check crash indicators
crash_indicators = [
    "claude: command not found",
    "segmentation fault",
    "core dumped",
    "killed",
    "terminated",
    "panic:",
    "bash-",
    "zsh:",
    "$ ",
    "traceback (most recent call last)",
    "modulenotfounderror",
    "process finished with exit code",
    "[process completed]",
    "process does not exist",
    "no process found",
    "broken pipe",
    "connection lost",
]

content_lower = test_content.lower()

print("Checking which indicators match the test content:")
print("=" * 70)

for indicator in crash_indicators:
    if indicator in content_lower:
        # Check if it would be ignored
        ignored = monitor._should_ignore_crash_indicator(indicator, test_content, content_lower)

        print(f"✓ Found '{indicator}' - Ignored: {ignored}")
        if not ignored:
            print("  ❌ This indicator is causing false positive!")

print("\nChecking Claude UI presence:")
print(f"Claude UI detected: {is_claude_interface_present(test_content)}")

# Test the actual crash detection
is_crashed, target = monitor._detect_pm_crash(mock_tmux, "test", Mock())
print(f"\nCrash detected: {is_crashed}")
