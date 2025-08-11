#!/usr/bin/env python3
"""Test monitor message detection for cases that were missed."""

import unittest
from pathlib import Path

from tmux_orchestrator.core.monitor_helpers import (
    detect_agent_state,
    has_unsubmitted_message,
    AgentState
)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "monitor_states"


class TestMessageDetection(unittest.TestCase):
    """Test message detection improvements."""
    
    def test_agent_test_message_not_submitted(self):
        """Test detection of 'Another test message' that wasn't auto-submitted."""
        fixture_path = FIXTURES_DIR / "message_queued" / "agent_test_message_not_submitted.txt"
        content = fixture_path.read_text()
        
        # Should detect unsubmitted message
        self.assertTrue(has_unsubmitted_message(content), 
                       "Failed to detect 'Another test message' as unsubmitted")
        
        # Should detect state as MESSAGE_QUEUED
        state = detect_agent_state(content)
        self.assertEqual(state, AgentState.MESSAGE_QUEUED,
                        f"Expected MESSAGE_QUEUED but got {state}")
    
    def test_all_message_queued_fixtures(self):
        """Test all message_queued fixtures are detected correctly."""
        message_queued_dir = FIXTURES_DIR / "message_queued"
        
        for fixture_file in message_queued_dir.glob("*.txt"):
            with self.subTest(fixture=fixture_file.name):
                content = fixture_file.read_text()
                
                # Should detect unsubmitted message
                has_msg = has_unsubmitted_message(content)
                self.assertTrue(has_msg, 
                               f"{fixture_file.name}: Failed to detect unsubmitted message")
                
                # Should detect state as MESSAGE_QUEUED
                state = detect_agent_state(content)
                self.assertEqual(state, AgentState.MESSAGE_QUEUED,
                                f"{fixture_file.name}: Expected MESSAGE_QUEUED but got {state}")


if __name__ == "__main__":
    unittest.main()