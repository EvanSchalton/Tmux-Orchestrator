#!/usr/bin/env python3
"""Simple direct test of PM detection functionality."""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

from tmux_orchestrator.core.monitor import IdleMonitor


def test_pm_detection():
    """Test PM detection functionality directly."""
    print("=== PM Detection Direct Test ===")

    # Create minimal mocks
    mock_config = Mock()
    mock_config.project_root = Path("/tmp")
    mock_config.data_dir = Path("/tmp/data")

    mock_tmux = Mock()
    mock_logger = Mock()

    # Create idle monitor
    monitor = IdleMonitor(tmux=mock_tmux)

    # Test 1: Missing PM Window
    print("\n1. Testing missing PM window detection...")
    with patch.object(monitor, "_find_pm_window", return_value=None):
        crashed, target = monitor._detect_pm_crash(mock_tmux, "test_session", mock_logger)

    print(f"   Result: crashed={crashed}, target={target}")
    assert crashed, "Should detect crash when PM window missing"
    assert target is None, "Target should be None when PM window missing"
    print("   ✅ PASSED")

    # Test 2: Crash Indicators Present
    print("\n2. Testing crash indicator detection...")
    test_target = "test_session:1"
    mock_tmux.capture_pane.return_value = "bash: tmux-orc: command not found\n$ "

    with patch.object(monitor, "_find_pm_window", return_value=test_target):
        crashed, target = monitor._detect_pm_crash(mock_tmux, "test_session", mock_logger)

    print(f"   Result: crashed={crashed}, target={target}")
    assert crashed, "Should detect crash when crash indicators present"
    assert target == test_target, "Should return target when PM window exists"
    print("   ✅ PASSED")

    # Test 3: Healthy PM
    print("\n3. Testing healthy PM detection...")
    mock_tmux.capture_pane.return_value = "Claude Code (tmux-orc-pm-123)\n\nReady to help!\n\n> "

    with (
        patch.object(monitor, "_find_pm_window", return_value=test_target),
        patch("tmux_orchestrator.core.monitor.is_claude_interface_present", return_value=True),
    ):
        crashed, target = monitor._detect_pm_crash(mock_tmux, "test_session", mock_logger)

    print(f"   Result: crashed={crashed}, target={target}")
    assert not crashed, "Should not detect crash when PM is healthy"
    assert target == test_target, "Should return target when PM window exists"
    print("   ✅ PASSED")

    print("\n=== All PM Detection Tests PASSED ===")
    return True


def update_qa_findings():
    """Update the QA findings document with test results."""
    findings_path = "/workspaces/Tmux-Orchestrator/.tmux_orchestrator/planning/2025-08-15T04-15-56-pm-recovery-failure/qa-findings.md"

    # Read current content
    with open(findings_path) as f:
        content = f.read()

    # Add new test results
    new_findings = (
        """
### ✅ PM Detection Functionality Validation
- **Test**: Direct testing of `_detect_pm_crash()` method
- **Results**: All 3 scenarios PASSED
  - Missing PM window: ✅ crashed=True, target=None
  - Crash indicators present: ✅ crashed=True, target="test_session:1"
  - Healthy PM: ✅ crashed=False, target="test_session:1"
- **Status**: PM detection logic working correctly
- **Timestamp**: """
        + "19:25 UTC"
        + """

"""
    )

    # Insert before the "Pending Tests" section
    insert_pos = content.find("### ⏳ Pending Tests (Post-Fix)")
    if insert_pos != -1:
        updated_content = content[:insert_pos] + new_findings + content[insert_pos:]

        with open(findings_path, "w") as f:
            f.write(updated_content)

        print(f"✅ Updated QA findings at: {findings_path}")
    else:
        print("❌ Could not find insertion point in QA findings")


if __name__ == "__main__":
    try:
        success = test_pm_detection()
        if success:
            update_qa_findings()
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        sys.exit(1)
