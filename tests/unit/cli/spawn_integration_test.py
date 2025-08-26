#!/usr/bin/env python3
"""
Integration tests for spawn auto-increment with real tmux sessions.
These tests require tmux to be installed and will create/destroy test sessions.
"""

import subprocess
import time
import unittest

# INTEGRATION TEST - Uses real TMUXManager for legitimate integration testing
# This file should NOT be run during unit testing - only during integration testing
# TMUXManager import removed - using comprehensive_mock_tmux fixture


class TestSpawnIntegration(unittest.TestCase):
    """Integration tests with real tmux sessions"""

    TEST_SESSION_PREFIX = "tmux-orc-test-"

    @classmethod
    def setUpClass(cls):
        """Check if tmux is available"""
        try:
            subprocess.run(["tmux", "-V"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise unittest.SkipTest("tmux not available")

    def setUp(self):
        """Create test session"""
        from tests.conftest import MockTMUXManager

        self.tmux = MockTMUXManager()
        self.test_session = f"{self.TEST_SESSION_PREFIX}{int(time.time())}"
        self.cleanup_sessions()  # Clean any leftover test sessions

    def tearDown(self):
        """Clean up test sessions"""
        self.cleanup_sessions()

    def cleanup_sessions(self):
        """Remove all test sessions"""
        sessions = subprocess.run(["tmux", "list-sessions", "-F", "#{session_name}"], capture_output=True, text=True)
        if sessions.returncode == 0:
            for session in sessions.stdout.strip().split("\n"):
                if session.startswith(self.TEST_SESSION_PREFIX):
                    subprocess.run(["tmux", "kill-session", "-t", session], capture_output=True)

    def test_real_spawn_auto_increment(self):
        """Test auto-increment with real tmux session"""
        # Create test session
        self.assertTrue(self.tmux.create_session(self.test_session))

        # Create windows with gaps
        self.assertTrue(self.tmux.create_window(self.test_session, "test-0"))
        self.assertTrue(self.tmux.create_window(self.test_session, "test-1"))

        # Kill window 1 to create a gap
        subprocess.run(["tmux", "kill-window", "-t", f"{self.test_session}:1"], capture_output=True)
        time.sleep(0.1)

        # Create another window - should be index 2, not 1
        self.assertTrue(self.tmux.create_window(self.test_session, "test-new"))

        # Verify window indices
        windows = self.tmux.list_windows(self.test_session)
        indices = [w["index"] for w in windows]
        names = [w["name"] for w in windows]

        # Should have windows at 0 and 2 (not 1)
        self.assertIn(0, indices)
        self.assertIn(2, indices)
        self.assertNotIn(1, indices)
        self.assertIn("test-new", names)

    def test_concurrent_window_creation(self):
        """Test race conditions with concurrent window creation"""
        # Create test session
        self.assertTrue(self.tmux.create_session(self.test_session))

        # Spawn multiple windows rapidly
        window_names = [f"test-window-{i}" for i in range(5)]

        for name in window_names:
            self.assertTrue(self.tmux.create_window(self.test_session, name))

        # Verify all windows exist with sequential indices
        windows = self.tmux.list_windows(self.test_session)
        indices = sorted([w["index"] for w in windows])
        names = [w["name"] for w in windows]

        # Should have indices 0-4
        self.assertEqual(indices, list(range(5)))

        # All windows should be created
        for name in window_names:
            self.assertIn(name, names)

    def test_spawn_command_integration(self):
        """Test the actual spawn command with tmux"""
        # Create test session
        self.assertTrue(self.tmux.create_session(self.test_session))

        # Run spawn command
        result = subprocess.run(
            ["tmux-orc", "spawn", "agent", "test-dev", self.test_session, "--briefing", "Test developer agent"],
            capture_output=True,
            text=True,
        )

        # Command should succeed
        self.assertEqual(result.returncode, 0, f"Spawn failed: {result.stderr}")

        # Verify window was created
        windows = self.tmux.list_windows(self.test_session)
        window_names = [w["name"] for w in windows]
        self.assertIn("Claude-test-dev", window_names)

    def test_spawn_with_window_index_ignored(self):
        """Test that window index in target is properly ignored"""
        # Create test session with existing windows
        self.assertTrue(self.tmux.create_session(self.test_session))
        self.assertTrue(self.tmux.create_window(self.test_session, "existing-1"))
        self.assertTrue(self.tmux.create_window(self.test_session, "existing-2"))

        # Spawn with explicit window index (should be ignored)
        result = subprocess.run(
            ["tmux-orc", "spawn", "agent", "test-qa", f"{self.test_session}:0", "--briefing", "Test QA agent"],
            capture_output=True,
            text=True,
        )

        # Should succeed with warning
        self.assertEqual(result.returncode, 0)
        self.assertIn("will be ignored", result.stdout)

        # Verify window was added at end
        windows = self.tmux.list_windows(self.test_session)
        qa_window = next(w for w in windows if w["name"] == "Claude-test-qa")
        self.assertEqual(qa_window["index"], 3)  # Should be at end, not at 0

    def test_role_conflict_detection(self):
        """Test role-based conflict detection"""
        # Create test session
        self.assertTrue(self.tmux.create_session(self.test_session))

        # Spawn a PM
        result1 = subprocess.run(
            ["tmux-orc", "spawn", "agent", "pm", self.test_session, "--briefing", "Test PM"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result1.returncode, 0)

        # Try to spawn another PM (should fail)
        result2 = subprocess.run(
            ["tmux-orc", "spawn", "agent", "manager", self.test_session, "--briefing", "Another PM"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result2.returncode, 0)
        self.assertIn("Role conflict", result2.stdout)

    def test_empty_session_spawn(self):
        """Test spawning into a freshly created empty session"""
        # Create empty session
        self.assertTrue(self.tmux.create_session(self.test_session))

        # Remove the default window if it exists
        windows = self.tmux.list_windows(self.test_session)
        if windows:
            subprocess.run(["tmux", "kill-window", "-t", f"{self.test_session}:0"], capture_output=True)
            time.sleep(0.1)

        # Spawn agent
        result = subprocess.run(
            [
                "tmux-orc",
                "spawn",
                "agent",
                "first-agent",
                self.test_session,
                "--briefing",
                "First agent in empty session",
            ],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0)

        # Should create window 0
        windows = self.tmux.list_windows(self.test_session)
        self.assertEqual(len(windows), 1)
        self.assertEqual(windows[0]["index"], 0)
        self.assertEqual(windows[0]["name"], "Claude-first-agent")


class TestSpawnRecovery(unittest.TestCase):
    """Test recovery scenarios after failed spawns"""

    TEST_SESSION_PREFIX = "tmux-orc-recovery-"

    def setUp(self):
        """Set up test environment"""
        from tests.conftest import MockTMUXManager

        self.tmux = MockTMUXManager()
        self.test_session = f"{self.TEST_SESSION_PREFIX}{int(time.time())}"
        self.cleanup_sessions()

    def tearDown(self):
        """Clean up"""
        self.cleanup_sessions()

    def cleanup_sessions(self):
        """Remove test sessions"""
        sessions = subprocess.run(["tmux", "list-sessions", "-F", "#{session_name}"], capture_output=True, text=True)
        if sessions.returncode == 0:
            for session in sessions.stdout.strip().split("\n"):
                if session.startswith(self.TEST_SESSION_PREFIX):
                    subprocess.run(["tmux", "kill-session", "-t", session], capture_output=True)

    def test_recovery_after_interrupted_spawn(self):
        """Test recovery after spawn is interrupted"""
        # Create session
        self.assertTrue(self.tmux.create_session(self.test_session))

        # Simulate partial spawn - create window but don't start Claude
        self.assertTrue(self.tmux.create_window(self.test_session, "Claude-interrupted"))

        # Try to spawn another agent - should work
        result = subprocess.run(
            [
                "tmux-orc",
                "spawn",
                "agent",
                "recovery-agent",
                self.test_session,
                "--briefing",
                "Agent after interruption",
            ],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0)

        # Both windows should exist
        windows = self.tmux.list_windows(self.test_session)
        window_names = [w["name"] for w in windows]
        self.assertIn("Claude-interrupted", window_names)
        self.assertIn("Claude-recovery-agent", window_names)

    def test_spawn_after_session_restart(self):
        """Test spawning after session is killed and recreated"""
        # Create and kill session
        self.assertTrue(self.tmux.create_session(self.test_session))
        subprocess.run(["tmux", "kill-session", "-t", self.test_session], capture_output=True)
        time.sleep(0.1)

        # Spawn should recreate session
        result = subprocess.run(
            ["tmux-orc", "spawn", "agent", "fresh-agent", self.test_session, "--briefing", "Agent in fresh session"],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0)

        # Session should exist with agent
        self.assertTrue(self.tmux.has_session(self.test_session))
        windows = self.tmux.list_windows(self.test_session)
        self.assertGreater(len(windows), 0)


if __name__ == "__main__":
    # Run with verbose output
    unittest.main(verbosity=2)
