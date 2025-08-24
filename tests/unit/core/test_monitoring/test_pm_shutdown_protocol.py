#!/usr/bin/env python3
"""Test PM session shutdown behavior after closeout creation.

This test verifies that PM agents properly shut down their sessions
after creating project-closeout.md files according to the mandatory protocol.
"""

import subprocess
import time
from pathlib import Path


class TestPMShutdownProtocol:
    """Test PM shutdown behavior after closeout creation."""

    def test_closeout_file_creation(self):
        """Test that PM context contains proper closeout instructions."""
        pm_context_path = Path("/workspaces/Tmux-Orchestrator/tmux_orchestrator/data/contexts/pm.md")
        assert pm_context_path.exists(), "PM context file must exist"

        content = pm_context_path.read_text()

        # Verify mandatory shutdown protocol is present
        assert "MANDATORY PROJECT COMPLETION PROTOCOL" in content
        assert "tmux kill-session -t $(tmux display-message -p '#S')" in content
        assert "project-closeout.md" in content
        assert "THIS IS NOT OPTIONAL" in content
        print("✅ PM context contains proper shutdown protocol")

    def test_session_termination_command(self):
        """Test that the session termination command works correctly."""
        # Create a test tmux session
        session_name = f"test-pm-shutdown-{int(time.time())}"

        try:
            # Create test session
            subprocess.run(["tmux", "new-session", "-d", "-s", session_name, "sleep", "60"], check=True)

            # Verify session exists
            result = subprocess.run(
                ["tmux", "list-sessions", "-F", "#{session_name}"], capture_output=True, text=True, check=True
            )
            assert session_name in result.stdout
            print(f"✅ Test session {session_name} created successfully")

            # Test direct kill command (simulating PM's final action)
            subprocess.run(["tmux", "kill-session", "-t", session_name], check=True)

            # Wait a moment for termination
            time.sleep(1)

            # Verify session is terminated
            result = subprocess.run(["tmux", "list-sessions"], capture_output=True, text=True)

            # Session should not appear in list at all
            if result.stdout:
                assert session_name not in result.stdout
            print(f"✅ Session {session_name} terminated correctly")

        except subprocess.CalledProcessError as e:
            # Clean up if test session still exists
            subprocess.run(["tmux", "kill-session", "-t", session_name], capture_output=True)
            if "can't find session" not in str(e):
                raise

    def test_closeout_template_validity(self):
        """Test that the closeout report template is valid."""
        pm_context_path = Path("/workspaces/Tmux-Orchestrator/tmux_orchestrator/data/contexts/pm.md")
        content = pm_context_path.read_text()

        # Extract the closeout template section
        lines = content.split("\n")
        in_template = False
        template_lines = []

        for line in lines:
            if 'cat > "$PLANNING_DIR/project-closeout.md"' in line:
                in_template = True
                continue
            if in_template and line.strip() == "EOF":
                break
            if in_template:
                template_lines.append(line)

        template_content = "\n".join(template_lines)

        # Verify required sections in template
        required_sections = [
            "# Project Closeout Report",
            "## Completion Status: ✅ COMPLETE",
            "### Team Members",
            "### Tasks Completed",
            "### Quality Checks",
            "### Resource Cleanup",
        ]

        for section in required_sections:
            assert section in template_content, f"Missing required section: {section}"

        print("✅ Closeout template contains all required sections")

    def test_shutdown_warning_presence(self):
        """Test that proper warnings about shutdown are present."""
        pm_context_path = Path("/workspaces/Tmux-Orchestrator/tmux_orchestrator/data/contexts/pm.md")
        content = pm_context_path.read_text()

        # Check for critical warning messages
        warnings = [
            "FAILURE TO SHUTDOWN = SYSTEM ASSUMES YOU CRASHED",
            "Session termination disconnects you from tmux entirely",
            "IF YOU DON'T TERMINATE AFTER CLOSEOUT, THE SYSTEM ASSUMES YOU CRASHED",
            "WITHOUT A CLOSEOUT REPORT, ASSUME THE TEAM CRASHED",
        ]

        for warning in warnings:
            assert warning in content, f"Missing critical warning: {warning}"

        print("✅ All critical shutdown warnings are present")

    def test_daemon_management_instructions(self):
        """Test that PM context includes proper daemon management."""
        pm_context_path = Path("/workspaces/Tmux-Orchestrator/tmux_orchestrator/data/contexts/pm.md")
        content = pm_context_path.read_text()

        # Check for daemon management instructions
        daemon_commands = ["tmux-orc monitor stop", "tmux-orc monitor start", "tmux-orc monitor status"]

        for cmd in daemon_commands:
            assert cmd in content, f"Missing daemon command: {cmd}"

        # Check for critical daemon warnings
        assert "YOU MUST START THE MONITORING DAEMON AFTER SPAWNING ALL AGENTS" in content
        assert "WITHOUT THE DAEMON, YOUR PROJECT IS DOOMED" in content

        print("✅ Daemon management instructions are comprehensive")

    def test_session_boundary_enforcement(self):
        """Test that session boundary rules are clearly stated."""
        pm_context_path = Path("/workspaces/Tmux-Orchestrator/tmux_orchestrator/data/contexts/pm.md")
        content = pm_context_path.read_text()

        boundary_rules = [
            "YOU MUST SPAWN ALL AGENTS IN YOUR CURRENT SESSION",
            "NEVER create new sessions with `tmux new-session`",
            "ALWAYS spawn agents as new windows in YOUR current session",
            "YOU ARE CONFINED TO YOUR SESSION",
        ]

        for rule in boundary_rules:
            assert rule in content, f"Missing session boundary rule: {rule}"

        print("✅ Session boundary enforcement is clearly documented")


def test_pm_quality_gates():
    """Test that quality gate enforcement is comprehensive."""
    pm_context_path = Path("/workspaces/Tmux-Orchestrator/tmux_orchestrator/data/contexts/pm.md")
    content = pm_context_path.read_text()

    # Check for zero tolerance policy
    assert "ZERO TOLERANCE POLICY" in content
    assert "IMMEDIATE TERMINATION" in content

    # Check for specific violations that trigger termination
    violations = [
        "Skip failing tests",
        "Disable tests",
        "Ignore linting errors",
        "Push broken code",
        "Remove test assertions",
    ]

    for violation in violations:
        assert violation in content, f"Missing quality violation: {violation}"

    print("✅ Quality gate enforcement is comprehensive")


if __name__ == "__main__":
    # Run the tests
    test = TestPMShutdownProtocol()

    print("🧪 Testing PM Session Shutdown Protocol...")
    print("=" * 50)

    test.test_closeout_file_creation()
    test.test_session_termination_command()
    test.test_closeout_template_validity()
    test.test_shutdown_warning_presence()
    test.test_daemon_management_instructions()
    test.test_session_boundary_enforcement()
    test_pm_quality_gates()

    print("=" * 50)
    print("✅ All PM shutdown protocol tests passed!")
