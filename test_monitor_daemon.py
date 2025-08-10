#!/usr/bin/env python3
"""Test script to diagnose monitoring daemon issues."""

import os
import subprocess
import sys
import time
from pathlib import Path

# Add the project to Python path
sys.path.insert(0, str(Path(__file__).parent))

from tmux_orchestrator.core.monitor import IdleMonitor
from tmux_orchestrator.utils.tmux import TMUXManager


def test_tmux_discovery():
    """Test basic tmux discovery functionality."""
    print("Testing TMUXManager discovery...")

    tmux = TMUXManager()

    # List sessions
    print("\n1. Listing sessions:")
    sessions = tmux.list_sessions()
    for session in sessions:
        print(f"  - {session['name']} (attached: {session.get('attached', 'N/A')})")

    if not sessions:
        print("  No sessions found!")
        return

    # List windows for each session
    print("\n2. Listing windows:")
    for session in sessions:
        print(f"\n  Session: {session['name']}")
        windows = tmux.list_windows(session["name"])
        for window in windows:
            print(f"    - Window {window.get('index')}: {window.get('name')} (active: {window.get('active')})")

            # Try to capture pane content
            target = f"{session['name']}:{window.get('index')}"
            content = tmux.capture_pane(target, lines=5)
            if content:
                preview = content.strip().split("\n")[0][:50] + "..." if content else "(empty)"
                print(f"      Content preview: {preview}")


def test_agent_detection():
    """Test agent detection logic."""
    print("\n3. Testing agent detection:")

    tmux = TMUXManager()
    # monitor = IdleMonitor(tmux)  # Not used in this test

    # Create a mock monitoring daemon to test _discover_agents
    import logging

    logger = logging.getLogger("test")
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    logger.addHandler(handler)

    # We need to simulate the daemon's discovery process
    print("\n  Attempting to discover agents...")

    # Manually test discovery
    sessions = tmux.list_sessions()
    for session in sessions:
        windows = tmux.list_windows(session["name"])
        for window in windows:
            target = f"{session['name']}:{window['index']}"
            content = tmux.capture_pane(target, lines=20)

            # Check for Claude indicators
            claude_indicators = ["Claude", "│ >", "assistant:", "Human:"]
            is_claude = any(ind in content for ind in claude_indicators)

            print(f"\n  Target: {target}")
            print(f"    Window name: {window['name']}")
            print(f"    Is Claude agent: {is_claude}")
            if is_claude:
                print("    ✓ Found Claude agent!")


def test_daemon_startup():
    """Test daemon startup process."""
    print("\n4. Testing daemon startup:")

    tmux = TMUXManager()
    monitor = IdleMonitor(tmux)

    # Check if already running
    if monitor.is_running():
        print("  Monitor already running, stopping first...")
        monitor.stop()
        time.sleep(1)

    # Start the daemon
    print("  Starting daemon...")
    pid = monitor.start(interval=5)  # 5 second interval for testing
    print(f"  Daemon started with PID: {pid}")

    # Wait a bit
    time.sleep(2)

    # Check if still running
    if monitor.is_running():
        print("  ✓ Daemon is running")

        # Check log file
        log_file = Path("/tmp/tmux-orchestrator-idle-monitor.log")
        if log_file.exists():
            print("\n  Recent log entries:")
            result = subprocess.run(["tail", "-20", str(log_file)], capture_output=True, text=True)
            for line in result.stdout.strip().split("\n"):
                print(f"    {line}")
        else:
            print("  ✗ Log file not found!")
    else:
        print("  ✗ Daemon is NOT running (exited immediately)")

        # Check for error log
        error_log = Path("/tmp/monitor-daemon-error.log")
        if error_log.exists():
            print("\n  Error log found:")
            with open(error_log) as f:
                print(f.read())


def test_enhanced_monitor():
    """Test the enhanced monitor implementation."""
    print("\n5. Testing enhanced monitor:")

    # Set debug mode
    os.environ["TMUX_ORC_DEBUG"] = "true"

    from tmux_orchestrator.core.monitor_enhanced import EnhancedMonitor

    monitor = EnhancedMonitor()

    # Stop if running
    if monitor.is_running():
        print("  Stopping existing enhanced monitor...")
        with open(monitor.pid_file) as f:
            pid = int(f.read().strip())
        os.kill(pid, 15)  # SIGTERM
        time.sleep(1)

    # Start enhanced monitor
    print("  Starting enhanced monitor with 5s interval...")
    pid = monitor.start(interval=5)
    print(f"  Started with PID: {pid}")

    # Wait for some cycles
    print("  Waiting for monitoring cycles...")
    time.sleep(15)

    # Check logs
    if monitor.log_file.exists():
        print("\n  Enhanced monitor log:")
        result = subprocess.run(["tail", "-30", str(monitor.log_file)], capture_output=True, text=True)
        for line in result.stdout.strip().split("\n"):
            print(f"    {line}")


if __name__ == "__main__":
    print("=== TMux Orchestrator Monitor Diagnostics ===")
    print(f"Python: {sys.version}")
    print(f"Working directory: {os.getcwd()}")

    # Run all tests
    test_tmux_discovery()
    test_agent_detection()
    test_daemon_startup()
    test_enhanced_monitor()

    print("\n=== Diagnostics Complete ===")
    print("\nRecommendations:")
    print("1. If no agents detected, check window names contain 'Claude'")
    print("2. If daemon exits immediately, check the error log")
    print("3. Use enhanced monitor for better logging")
    print("4. Set TMUX_ORC_DEBUG=true for verbose output")
