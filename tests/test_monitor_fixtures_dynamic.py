#!/usr/bin/env python3
"""Dynamic test discovery for monitor state fixtures.

This test module automatically discovers all fixture files and validates
that the detection algorithms correctly identify their states.
"""

import unittest
from pathlib import Path
from typing import Dict, List

from tmux_orchestrator.core.monitor_helpers import (
    detect_agent_state,
    has_unsubmitted_message,
    is_claude_interface_present,
    AgentState
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


class TestMonitorFixturesDynamic(unittest.TestCase):
    """Dynamically test all monitor state fixtures."""
    
    @classmethod
    def setUpClass(cls):
        """Discover all fixture files."""
        cls.fixtures: Dict[str, List[Path]] = {}
        
        # Discover all state directories
        for state_dir in FIXTURES_DIR.iterdir():
            if state_dir.is_dir() and state_dir.name in EXPECTED_STATES:
                # Find all .txt files in this state directory
                txt_files = list(state_dir.glob("*.txt"))
                if txt_files:
                    cls.fixtures[state_dir.name] = txt_files
    
    def test_all_fixtures_discovered(self):
        """Ensure we discovered fixtures."""
        self.assertGreater(len(self.fixtures), 0, "No fixture directories found")
        total_files = sum(len(files) for files in self.fixtures.values())
        self.assertGreater(total_files, 0, "No fixture files found")
    
    def test_state_detection_for_all_fixtures(self):
        """Test that all fixtures are detected with the correct state.
        
        Note: IDLE state detection requires multiple snapshots over time,
        so single snapshot fixtures in idle/ will be detected as ACTIVE.
        """
        for state_name, fixture_files in self.fixtures.items():
            expected_state = EXPECTED_STATES[state_name]
            
            for fixture_path in fixture_files:
                with self.subTest(state=state_name, fixture=fixture_path.name):
                    content = fixture_path.read_text()
                    detected_state = detect_agent_state(content)
                    
                    if state_name in MIXED_CONTENT_STATES:
                        # For mixed content states, detection depends on actual content
                        # Starting state: ACTIVE if Claude UI present, ERROR if not
                        if is_claude_interface_present(content):
                            self.assertEqual(detected_state, AgentState.ACTIVE,
                                f"File {fixture_path.name} with Claude UI should be ACTIVE")
                        else:
                            self.assertEqual(detected_state, AgentState.ERROR,
                                f"File {fixture_path.name} without Claude UI should be ERROR")
                    elif state_name in SNAPSHOT_DEPENDENT_STATES:
                        # For snapshot-dependent states, we can't accurately detect
                        # from a single fixture, so we skip strict checking
                        self.assertIn(
                            detected_state, 
                            [AgentState.ACTIVE, AgentState.ERROR],
                            f"File {fixture_path.name} in {state_name}/ should be "
                            f"ACTIVE or ERROR (single snapshot limitation)"
                        )
                    else:
                        self.assertEqual(
                            detected_state, expected_state,
                            f"File {fixture_path.name} in {state_name}/ detected as "
                            f"{detected_state} instead of {expected_state}"
                        )
    
    def test_message_queued_fixtures_have_unsubmitted_messages(self):
        """Test that all message_queued fixtures have unsubmitted messages."""
        if "message_queued" not in self.fixtures:
            self.skipTest("No message_queued fixtures found")
        
        for fixture_path in self.fixtures["message_queued"]:
            with self.subTest(fixture=fixture_path.name):
                content = fixture_path.read_text()
                self.assertTrue(
                    has_unsubmitted_message(content),
                    f"File {fixture_path.name} should have unsubmitted message"
                )
    
    def test_idle_fixtures_have_no_unsubmitted_messages(self):
        """Test that idle fixtures don't have unsubmitted messages."""
        if "idle" not in self.fixtures:
            self.skipTest("No idle fixtures found")
        
        for fixture_path in self.fixtures["idle"]:
            with self.subTest(fixture=fixture_path.name):
                content = fixture_path.read_text()
                self.assertFalse(
                    has_unsubmitted_message(content),
                    f"File {fixture_path.name} should not have unsubmitted message"
                )
    
    def test_crashed_fixtures_have_no_claude_interface(self):
        """Test that crashed fixtures don't have Claude interface."""
        if "crashed" not in self.fixtures:
            self.skipTest("No crashed fixtures found")
        
        for fixture_path in self.fixtures["crashed"]:
            with self.subTest(fixture=fixture_path.name):
                content = fixture_path.read_text()
                self.assertFalse(
                    is_claude_interface_present(content),
                    f"File {fixture_path.name} should not have Claude interface"
                )
    
    def test_active_fixtures_have_claude_interface(self):
        """Test that active/healthy fixtures have Claude interface."""
        for state_name in ["active", "healthy", "idle", "message_queued"]:
            if state_name not in self.fixtures:
                continue
            
            for fixture_path in self.fixtures[state_name]:
                with self.subTest(state=state_name, fixture=fixture_path.name):
                    content = fixture_path.read_text()
                    self.assertTrue(
                        is_claude_interface_present(content),
                        f"File {fixture_path.name} in {state_name}/ should have Claude interface"
                    )
    
    def test_fixture_naming_conventions(self):
        """Test that fixture names follow conventions."""
        for state_name, fixture_files in self.fixtures.items():
            for fixture_path in fixture_files:
                with self.subTest(state=state_name, fixture=fixture_path.name):
                    # Basic naming checks
                    self.assertTrue(
                        fixture_path.name.endswith(".txt"),
                        f"Fixture {fixture_path.name} should end with .txt"
                    )
                    # Ensure no temporary or backup files
                    self.assertNotIn(
                        ".bak", fixture_path.name,
                        f"Backup file {fixture_path.name} should not be in fixtures"
                    )
                    self.assertNotIn(
                        ".tmp", fixture_path.name,
                        f"Temporary file {fixture_path.name} should not be in fixtures"
                    )
                    self.assertNotIn(
                        ".corrupted", fixture_path.name,
                        f"Corrupted file {fixture_path.name} should not be in fixtures"
                    )


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
    unittest.main(verbosity=2)