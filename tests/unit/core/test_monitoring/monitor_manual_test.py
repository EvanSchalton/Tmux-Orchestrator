#!/usr/bin/env python3
"""Manual test for monitor auto-submit - create realistic stuck agents."""

import subprocess
import sys
from datetime import datetime


def run_command(cmd):
    """Run command and return output."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def create_stuck_agent(session_name, window_id):
    """Create a realistic stuck agent."""
    print(f"\nCreating stuck agent at {session_name}:{window_id}")

    # Send a message to be typed but not submitted
    cmd = f"tmux send-keys -t {session_name}:{window_id} 'This is a test message that simulates being stuck. The PM asked me to test the auto-submit feature.'"
    run_command(cmd)

    print(f"Message typed but not submitted in {session_name}:{window_id}")
    print("Monitor should detect and auto-submit within 10-20 seconds...")


def check_logs_realtime():
    """Monitor logs in real-time for auto-submit events."""
    print("\n=== Monitoring Logs for Auto-Submit Events ===")
    print("Press Ctrl+C to stop monitoring\n")

    log_file = "/workspaces/Tmux-Orchestrator/.tmux_orchestrator/logs/idle-monitor.log"

    # Use tail -f to follow log in real-time
    import subprocess

    try:
        process = subprocess.Popen(["tail", "-f", log_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        for line in process.stdout:
            if any(keyword in line for keyword in ["Auto-submitting", "idle with Claude", "still stuck", "attempt #"]):
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"[{timestamp}] {line.strip()}")

    except KeyboardInterrupt:
        process.terminate()
        print("\nStopped monitoring logs")


def main():
    """Run manual test."""
    print("=== Manual Monitor Auto-Submit Test ===")
    print("This will create stuck messages in existing agents")

    # Check for existing monitor-fix agents
    _, sessions_out, _ = run_command("tmux list-sessions | grep monitor-fix")

    if not sessions_out:
        print("ERROR: No monitor-fix session found")
        print("Please ensure agents are running in monitor-fix session")
        sys.exit(1)

    # Check which windows have Claude running
    print("\nChecking for Claude agents in monitor-fix session...")

    for window_id in range(1, 6):  # Check windows 1-5
        _, pane_content, _ = run_command(f"tmux capture-pane -t monitor-fix:{window_id} -p 2>/dev/null")

        if pane_content and ("│ >" in pane_content or "assistant:" in pane_content):
            print(f"Found Claude agent in window {window_id}")

            # Check if already has unsubmitted text
            if "│ >" in pane_content:
                lines = pane_content.split("\n")
                for line in lines:
                    if "│ >" in line and line.split("│ >")[1].strip():
                        print("  - Already has unsubmitted text")
                        break
                else:
                    # Create stuck message
                    response = input(f"Create stuck message in window {window_id}? [y/N]: ")
                    if response.lower() == "y":
                        create_stuck_agent("monitor-fix", window_id)

    # Monitor logs
    print("\nStarting log monitoring...")
    print("The monitor checks every 10 seconds, so please wait...")
    check_logs_realtime()


if __name__ == "__main__":
    main()
