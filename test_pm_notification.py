#!/usr/bin/env python3
"""Test script to verify the complete PM notification flow."""

import json
import subprocess


class TMUXManagerMock:
    """Minimal mock of TMUXManager for testing."""

    def list_windows(self, session):
        """List windows in a session."""
        cmd = ["tmux", "list-windows", "-t", session, "-F", '{"index": "#{window_index}", "name": "#{window_name}"}']
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Failed to list windows: {result.stderr}")

        windows = []
        for line in result.stdout.strip().split("\n"):
            if line:
                try:
                    windows.append(json.loads(line))
                except json.JSONDecodeError:
                    print(f"Failed to parse: {line}")
        return windows

    def capture_pane(self, target, lines=10):
        """Capture pane content."""
        cmd = ["tmux", "capture-pane", "-t", target, "-p", "-S", f"-{lines}"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Failed to capture pane: {result.stderr}")
        return result.stdout

    def send_message(self, target, message):
        """Send a message to a target - simulated."""
        print(f"\nATTEMPTING TO SEND MESSAGE TO: {target}")
        print(f"MESSAGE CONTENT:\n{message}")

        # Check if target exists
        try:
            session, window = target.split(":")
            windows = self.list_windows(session)
            found = False
            for w in windows:
                if str(w.get("index")) == str(window):
                    found = True
                    print(f"✓ Target exists: {w.get('name')} at {target}")
                    break

            if not found:
                print(f"✗ Target {target} does not exist!")
                return False

            # In real code, this would send keys to tmux
            # For testing, we just return True to indicate success
            return True

        except Exception as e:
            print(f"✗ Error sending message: {e}")
            return False


def _is_pm_agent(tmux: TMUXManagerMock, target: str) -> bool:
    """Check if target is a PM agent."""
    try:
        session, window = target.split(":")
        windows = tmux.list_windows(session)
        for w in windows:
            if w.get("index") == window:
                window_name = w.get("name", "").lower()
                return "pm" in window_name or "manager" in window_name
        return False
    except Exception:
        return False


def _find_pm_in_session(tmux: TMUXManagerMock, session: str) -> str | None:
    """Find PM agent in a specific session."""
    try:
        windows = tmux.list_windows(session)
        for window in windows:
            window_idx = str(window.get("index", ""))
            target = f"{session}:{window_idx}"
            if _is_pm_agent(tmux, target):
                return target
        return None
    except Exception:
        return None


def simulate_escalation_flow(tmux: TMUXManagerMock, failing_target: str, reason: str):
    """Simulate the complete escalation flow."""
    print(f"\n{'='*60}")
    print("SIMULATING ESCALATION FLOW")
    print(f"{'='*60}")
    print(f"Failing agent: {failing_target}")
    print(f"Reason: {reason}")

    # Step 1: Extract session from target
    session_name = failing_target.split(":")[0]
    print(f"\nStep 1: Extracted session name: '{session_name}'")

    # Step 2: Find PM in session
    pm_target = _find_pm_in_session(tmux, session_name)
    print(f"\nStep 2: _find_pm_in_session('{session_name}') = {pm_target}")

    if not pm_target:
        print("✗ No PM found in session!")
        return False

    # Step 3: Check if it's self-notification
    if pm_target == failing_target:
        print(f"\nStep 3: Skipping - PM at {failing_target} has their own issue")
        return False

    # Step 4: Get window name
    session, window = failing_target.split(":")
    windows = tmux.list_windows(session)
    window_name = "Unknown"
    for w in windows:
        if str(w.get("index")) == str(window):
            window_name = w.get("name", "Unknown")
            break

    print(f"\nStep 4: Window name for {failing_target}: '{window_name}'")

    # Step 5: Create message
    message = (
        f"🚨 AGENT FAILURE\n\n"
        f"Agent: {failing_target} ({window_name})\n"
        f"Issue: {reason}\n\n"
        f"Please restart this agent and provide the appropriate role prompt."
    )

    print("\nStep 5: Created notification message")

    # Step 6: Send message
    print("\nStep 6: Sending message...")
    success = tmux.send_message(pm_target, message)

    if success:
        print(f"\n✓ SUCCESS: Message sent to PM at {pm_target}")
    else:
        print(f"\n✗ FAILED: Could not send message to PM at {pm_target}")

    return success


def main():
    """Test the complete PM notification flow."""
    tmux = TMUXManagerMock()

    # Test scenarios
    test_cases = [
        ("critical-fixes:2", "API error (Rate Limiting)"),
        ("critical-fixes:3", "Agent crash/failure"),
        ("critical-fixes:4", "Network/Connection error"),
        ("critical-fixes:1", "PM self-notification test"),
    ]

    for failing_target, reason in test_cases:
        simulate_escalation_flow(tmux, failing_target, reason)
        print("\n")


if __name__ == "__main__":
    main()
