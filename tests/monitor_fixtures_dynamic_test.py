#!/usr/bin/env python3
"""Dynamic test discovery for monitor state fixtures.

This test module automatically discovers all fixture files and validates
that the detection algorithms correctly identify their states.
"""

from pathlib import Path

import pytest

from tmux_orchestrator.core.monitor_helpers import (
    AgentState,
    detect_agent_state,
    has_unsubmitted_message,
    is_claude_interface_present,
)

# Map directory names to expected states
# Note: Some states depend on content, not just directory name
EXPECTED_STATES = {
    "active": AgentState.ACTIVE,
    "crashed": AgentState.CRASHED,
    "error": AgentState.ERROR,
    "idle": AgentState.ACTIVE,  # Single snapshot can't detect idle, defaults to ACTIVE
    "message_queued": AgentState.MESSAGE_QUEUED,
    "starting": None,  # Mixed - depends on whether Claude interface is present
    "healthy": AgentState.ACTIVE,  # Legacy naming
}

# States that require multiple snapshots for accurate detection
SNAPSHOT_DEPENDENT_STATES = {"idle"}

# States with mixed content that can't have a single expected state
MIXED_CONTENT_STATES = {"starting"}

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "monitor_states"


def discover_all_fixtures() -> dict[str, list[Path]]:
    """Discover all fixture files."""
    fixtures: dict[str, list[Path]] = {}

    # Discover all state directories
    for state_dir in FIXTURES_DIR.iterdir():
        if state_dir.is_dir() and state_dir.name in EXPECTED_STATES:
            # Find all .txt files in this state directory
            txt_files = list(state_dir.glob("*.txt"))
            if txt_files:
                fixtures[state_dir.name] = txt_files

    return fixtures


def get_all_state_fixtures() -> list[tuple[str, Path]]:
    """Generate test parameters for all state fixtures."""
    fixtures = discover_all_fixtures()
    params = []
    for state_name, fixture_files in fixtures.items():
        for fixture_path in fixture_files:
            params.append((state_name, fixture_path))
    return params


def test_all_fixtures_discovered() -> None:
    """Ensure we discovered fixtures."""
    fixtures = discover_all_fixtures()
    assert len(fixtures) > 0, "No fixture directories found"
    total_files = sum(len(files) for files in fixtures.values())
    assert total_files > 0, "No fixture files found"


@pytest.mark.parametrize("state_name,fixture_path", get_all_state_fixtures())
def test_state_detection_for_fixture(state_name, fixture_path) -> None:
    """Test that all fixtures are detected with the correct state.

    Note: IDLE state detection requires multiple snapshots over time,
    so single snapshot fixtures in idle/ will be detected as ACTIVE.
    """
    expected_state = EXPECTED_STATES[state_name]
    content = fixture_path.read_text()
    detected_state = detect_agent_state(content)

    if state_name in MIXED_CONTENT_STATES:
        # For mixed content states, detection depends on actual content
        # Starting state: ACTIVE if Claude UI present, ERROR if not
        if is_claude_interface_present(content):
            assert detected_state == AgentState.ACTIVE, f"File {fixture_path.name} with Claude UI should be ACTIVE"
        else:
            assert detected_state == AgentState.ERROR, f"File {fixture_path.name} without Claude UI should be ERROR"
    elif state_name in SNAPSHOT_DEPENDENT_STATES:
        # For snapshot-dependent states, we can't accurately detect
        # from a single fixture, so we skip strict checking
        assert detected_state in [AgentState.ACTIVE, AgentState.ERROR], (
            f"File {fixture_path.name} in {state_name}/ should be " f"ACTIVE or ERROR (single snapshot limitation)"
        )
    else:
        assert detected_state == expected_state, (
            f"File {fixture_path.name} in {state_name}/ detected as " f"{detected_state} instead of {expected_state}"
        )


def get_message_queued_fixtures() -> list[Path]:
    """Get message_queued fixtures for testing."""
    fixtures = discover_all_fixtures()
    if "message_queued" not in fixtures:
        return []
    return fixtures["message_queued"]


@pytest.mark.parametrize("fixture_path", get_message_queued_fixtures())
def test_message_queued_fixtures_have_unsubmitted_messages(fixture_path) -> None:
    """Test that all message_queued fixtures have unsubmitted messages."""
    if not fixture_path:  # Skip if no fixtures
        pytest.skip("No message_queued fixtures found")
    content = fixture_path.read_text()
    assert has_unsubmitted_message(content), f"File {fixture_path.name} should have unsubmitted message"


def get_idle_fixtures() -> list[Path]:
    """Get idle fixtures for testing."""
    fixtures = discover_all_fixtures()
    if "idle" not in fixtures:
        return []
    return fixtures["idle"]


@pytest.mark.parametrize("fixture_path", get_idle_fixtures())
def test_idle_fixtures_have_no_unsubmitted_messages(fixture_path) -> None:
    """Test that idle fixtures don't have unsubmitted messages."""
    if not fixture_path:  # Skip if no fixtures
        pytest.skip("No idle fixtures found")
    content = fixture_path.read_text()
    assert not has_unsubmitted_message(content), f"File {fixture_path.name} should not have unsubmitted message"


def get_crashed_fixtures() -> list[Path]:
    """Get crashed fixtures for testing."""
    fixtures = discover_all_fixtures()
    if "crashed" not in fixtures:
        return []
    return fixtures["crashed"]


@pytest.mark.parametrize("fixture_path", get_crashed_fixtures())
def test_crashed_fixtures_have_no_claude_interface(fixture_path) -> None:
    """Test that crashed fixtures don't have Claude interface."""
    if not fixture_path:  # Skip if no fixtures
        pytest.skip("No crashed fixtures found")
    content = fixture_path.read_text()
    assert not is_claude_interface_present(content), f"File {fixture_path.name} should not have Claude interface"


def get_active_interface_fixtures() -> list[tuple[str, Path]]:
    """Get fixtures that should have Claude interface."""
    fixtures = discover_all_fixtures()
    params = []
    for state_name in ["active", "healthy", "idle", "message_queued"]:
        if state_name in fixtures:
            for fixture_path in fixtures[state_name]:
                params.append((state_name, fixture_path))
    return params


@pytest.mark.parametrize("state_name,fixture_path", get_active_interface_fixtures())
def test_active_fixtures_have_claude_interface(state_name, fixture_path) -> None:
    """Test that active/healthy fixtures have Claude interface."""
    content = fixture_path.read_text()
    assert is_claude_interface_present(
        content
    ), f"File {fixture_path.name} in {state_name}/ should have Claude interface"


@pytest.mark.parametrize("state_name,fixture_path", get_all_state_fixtures())
def test_fixture_naming_conventions(state_name, fixture_path) -> None:
    """Test that fixture names follow conventions."""
    # Basic naming checks
    assert fixture_path.name.endswith(".txt"), f"Fixture {fixture_path.name} should end with .txt"
    # Ensure no temporary or backup files
    assert ".bak" not in fixture_path.name, f"Backup file {fixture_path.name} should not be in fixtures"
    assert ".tmp" not in fixture_path.name, f"Temporary file {fixture_path.name} should not be in fixtures"
    assert ".corrupted" not in fixture_path.name, f"Corrupted file {fixture_path.name} should not be in fixtures"


def print_fixture_summary():
    """Print a summary of discovered fixtures (for debugging)."""
    print("\nFixture Discovery Summary:")
    print("-" * 50)

    for state_dir in sorted(FIXTURES_DIR.iterdir()):
        if state_dir.is_dir():
            txt_files = list(state_dir.glob("*.txt"))
            if txt_files:
                print(f"\n{state_dir.name}/: {len(txt_files)} fixtures")
                for f in sorted(txt_files):
                    print(f"  - {f.name}")


if __name__ == "__main__":
    # Print summary when run directly
    print_fixture_summary()
    # Run pytest when executed directly
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
