#!/usr/bin/env python3
"""Test script for monitor auto-submit functionality."""

import time
import subprocess
from pathlib import Path


def check_monitor_status():
    """Check if monitor is running."""
    result = subprocess.run(
        ["tmux-orc", "monitor", "status"],
        capture_output=True,
        text=True
    )
    print("Monitor Status:")
    print(result.stdout)
    return "is running" in result.stdout


def start_monitor():
    """Start the monitor if not running."""
    if not check_monitor_status():
        print("Starting monitor...")
        subprocess.run(["tmux-orc", "monitor", "start"])
        time.sleep(2)
        return check_monitor_status()
    return True


def check_log_file():
    """Check the monitor log for auto-submit attempts."""
    log_file = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator/logs/idle-monitor.log")
    if log_file.exists():
        print(f"\n=== Recent Monitor Log Entries ===")
        # Get last 50 lines
        with open(log_file) as f:
            lines = f.readlines()
            recent_lines = lines[-50:] if len(lines) > 50 else lines
            
            # Filter for auto-submit related messages
            auto_submit_lines = [
                line for line in recent_lines 
                if any(keyword in line for keyword in [
                    "auto-submit", "Auto-submit", "idle with Claude",
                    "still stuck", "resetting submission counter"
                ])
            ]
            
            if auto_submit_lines:
                print("Auto-submit related log entries:")
                for line in auto_submit_lines:
                    print(line.strip())
            else:
                print("No auto-submit entries found in recent logs")
    else:
        print(f"Log file not found: {log_file}")


def main():
    """Main test function."""
    print("=== Testing Monitor Auto-Submit Functionality ===\n")
    
    # 1. Check/start monitor
    if not start_monitor():
        print("ERROR: Could not start monitor")
        return
    
    print("Monitor is running successfully.\n")
    
    # 2. Check logs for auto-submit activity
    check_log_file()
    
    print("\n=== Test Summary ===")
    print("The monitor is now running with auto-submit functionality enabled.")
    print("Key improvements implemented:")
    print("1. 30-second cooldown between auto-submit attempts")
    print("2. Counter resets when agent becomes active")
    print("3. Detailed logging for each attempt")
    print("4. Proper initialization of tracking dictionaries")
    print("\nTo test the functionality:")
    print("1. Create an idle agent with a stuck Claude interface")
    print("2. Monitor the log file for auto-submit attempts")
    print("3. Verify the agent becomes active after submission")


if __name__ == "__main__":
    main()