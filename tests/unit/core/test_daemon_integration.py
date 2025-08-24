#!/usr/bin/env python3
"""Integration tests for the new daemon supervisor functionality."""

import os
import sys
import time
from pathlib import Path

# Add project path for imports
sys.path.insert(0, "/workspaces/Tmux-Orchestrator")

from tmux_orchestrator.core.daemon_supervisor import DaemonSupervisor  # noqa: E402
from tmux_orchestrator.core.monitor import IdleMonitor  # noqa: E402
from tmux_orchestrator.utils.tmux import TMUXManager  # noqa: E402


def test_basic_supervisor_functionality():
    """Test basic supervisor start/stop functionality."""
    print("🧪 Testing basic supervisor functionality...")

    supervisor = DaemonSupervisor("test-daemon")

    # Test that daemon is not running initially
    assert not supervisor.is_daemon_running(), "Daemon should not be running initially"

    # Test command that will start and write a PID
    test_command = [
        sys.executable,
        "-c",
        """
import os
import time
from pathlib import Path

# Write PID file
pid_file = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator/test-daemon.pid")
with open(pid_file, 'w') as f:
    f.write(str(os.getpid()))

# Keep alive for a bit
for i in range(50):
    time.sleep(0.1)
""",
    ]

    # Start daemon
    assert supervisor.start_daemon(test_command), "Failed to start test daemon"

    # Verify it's running
    assert supervisor.is_daemon_running(), "Daemon should be running after start"

    # Stop daemon
    assert supervisor.stop_daemon(), "Failed to stop test daemon"

    # Verify it's stopped
    assert not supervisor.is_daemon_running(), "Daemon should be stopped"

    print("✅ Basic supervisor functionality works")


def test_heartbeat_monitoring():
    """Test heartbeat-based health monitoring."""
    print("🧪 Testing heartbeat monitoring...")

    supervisor = DaemonSupervisor("test-heartbeat")

    # Test command that writes heartbeat
    test_command = [
        sys.executable,
        "-c",
        """
import os
import time
from pathlib import Path

# Write PID file
pid_file = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator/test-heartbeat.pid")
with open(pid_file, 'w') as f:
    f.write(str(os.getpid()))

# Write heartbeat file
heartbeat_file = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator/test-heartbeat.heartbeat")

# Keep updating heartbeat
for i in range(30):
    heartbeat_file.touch()
    time.sleep(0.1)
""",
    ]

    # Start daemon
    assert supervisor.start_daemon(test_command), "Failed to start heartbeat test daemon"

    # Give it time to write heartbeat
    time.sleep(0.5)

    # Check health
    assert supervisor.is_daemon_healthy(), "Daemon should be healthy with fresh heartbeat"

    # Stop daemon
    supervisor.stop_daemon()

    print("✅ Heartbeat monitoring works")


def test_monitor_integration():
    """Test integration with IdleMonitor."""
    print("🧪 Testing IdleMonitor integration...")

    tmux = TMUXManager()
    monitor = IdleMonitor(tmux)

    # Test that supervisor is initialized
    assert monitor.supervisor is not None, "Monitor should have supervisor initialized"

    # Test that supervisor uses correct daemon name
    assert monitor.supervisor.daemon_name == "idle-monitor", "Supervisor should use correct daemon name"

    print("✅ IdleMonitor integration works")


def test_process_isolation():
    """Test that supervisor properly isolates processes."""
    print("🧪 Testing process isolation...")

    supervisor = DaemonSupervisor("test-isolation")

    # Test command that forks
    test_command = [
        sys.executable,
        "-c",
        """
import os
import time
from pathlib import Path

# Write PID file
pid_file = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator/test-isolation.pid")
with open(pid_file, 'w') as f:
    f.write(str(os.getpid()))

# Test that we're in a new session
print(f"Started daemon with PID {os.getpid()}, session {os.getsid(0)}")

# Keep alive briefly
time.sleep(2)
""",
    ]

    # Start daemon
    assert supervisor.start_daemon(test_command), "Failed to start isolation test daemon"

    # Get daemon PID
    pid_file = supervisor.pid_file
    with open(pid_file) as f:
        daemon_pid = int(f.read().strip())

    # Verify daemon is in different session than current process
    current_session = os.getsid(0)
    daemon_session = os.getsid(daemon_pid)

    assert current_session != daemon_session, "Daemon should be in different session for isolation"

    # Clean up
    supervisor.stop_daemon()

    print("✅ Process isolation works")


def main():
    """Run all integration tests."""
    print("🚀 Starting daemon supervisor integration tests...\n")

    # Ensure test directory exists
    test_dir = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator")
    test_dir.mkdir(exist_ok=True)

    try:
        test_basic_supervisor_functionality()
        test_heartbeat_monitoring()
        test_monitor_integration()
        test_process_isolation()

        print("\n🎉 All daemon supervisor integration tests passed!")
        print("✅ Self-healing mechanism is ready for production use")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)

    finally:
        # Cleanup any test files
        cleanup_patterns = ["test-daemon.*", "test-heartbeat.*", "test-isolation.*"]

        for pattern in cleanup_patterns:
            for file_path in test_dir.glob(pattern):
                try:
                    file_path.unlink()
                except OSError:
                    pass


if __name__ == "__main__":
    main()
