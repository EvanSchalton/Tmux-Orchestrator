#!/usr/bin/env python3
"""Focused test for PM recovery functionality."""

import sys
from unittest.mock import Mock, patch

from tmux_orchestrator.core.monitor import IdleMonitor


def test_pm_recovery():
    """Test PM recovery functionality directly."""
    print("=== PM Recovery Test ===")

    # Create minimal mocks
    mock_tmux = Mock()
    mock_logger = Mock()

    # Create idle monitor
    monitor = IdleMonitor(tmux=mock_tmux)

    # Test 1: Successful Recovery
    print("\n1. Testing successful PM recovery...")

    # Mock the windows list to return empty (find index 1)
    mock_tmux.list_windows.return_value = []

    # Mock successful PM spawn
    test_target = "test_session:1"

    with (
        patch.object(monitor, "_discover_agents", return_value=[]),
        patch.object(monitor, "_spawn_pm", return_value=test_target),
        patch.object(monitor, "_check_pm_health", return_value=True),
        patch.object(monitor, "_notify_team_of_pm_recovery"),
        patch("time.sleep"),
    ):  # Skip actual sleep delays
        result = monitor._recover_crashed_pm(
            tmux=mock_tmux,
            session_name="test_session",
            crashed_pm_target=None,
            logger=mock_logger,
            max_retries=1,
            retry_delay=1,
        )

    print(f"   Result: {result}")
    assert result, "Recovery should return True when spawn succeeds and health passes"
    print("   ✅ PASSED")

    # Test 2: Recovery with Failed Health Check
    print("\n2. Testing recovery with failed health check...")

    with (
        patch.object(monitor, "_discover_agents", return_value=[]),
        patch.object(monitor, "_spawn_pm", return_value=test_target),
        patch.object(monitor, "_check_pm_health", return_value=False),
        patch("time.sleep"),
    ):  # Skip actual sleep delays
        result = monitor._recover_crashed_pm(
            tmux=mock_tmux,
            session_name="test_session",
            crashed_pm_target=None,
            logger=mock_logger,
            max_retries=1,
            retry_delay=1,
        )

    print(f"   Result: {result}")
    assert not result, "Recovery should return False when health check fails"
    print("   ✅ PASSED")

    # Test 3: Recovery with Spawn Failure
    print("\n3. Testing recovery with spawn failure...")

    with (
        patch.object(monitor, "_discover_agents", return_value=[]),
        patch.object(monitor, "_spawn_pm", return_value=None),
        patch("time.sleep"),
    ):  # Skip actual sleep delays
        result = monitor._recover_crashed_pm(
            tmux=mock_tmux,
            session_name="test_session",
            crashed_pm_target=None,
            logger=mock_logger,
            max_retries=1,
            retry_delay=1,
        )

    print(f"   Result: {result}")
    assert not result, "Recovery should return False when spawn fails"
    print("   ✅ PASSED")

    print("\n=== All PM Recovery Tests PASSED ===")
    return True


def update_qa_findings():
    """Update the QA findings document with recovery test results."""
    findings_path = "/workspaces/Tmux-Orchestrator/.tmux_orchestrator/planning/2025-08-15T04-15-56-pm-recovery-failure/qa-findings.md"

    # Read current content
    with open(findings_path) as f:
        content = f.read()

    # Add new test results
    new_findings = """
### ✅ PM Recovery Functionality Validation
- **Test**: Direct testing of `_recover_crashed_pm()` method
- **Results**: All 3 scenarios PASSED
  - Successful recovery: ✅ Returns True when spawn succeeds and health passes
  - Failed health check: ✅ Returns False when health check fails
  - Spawn failure: ✅ Returns False when spawn fails
- **Status**: PM recovery logic working correctly
- **Key Finding**: Recovery return logic appears to be functioning properly
- **Timestamp**: 19:30 UTC

"""

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
        success = test_pm_recovery()
        if success:
            update_qa_findings()
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
