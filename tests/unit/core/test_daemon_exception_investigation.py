#!/usr/bin/env python3
"""Investigation test to understand why DaemonAlreadyRunningError is not preventing multiple instances."""

import subprocess
import sys
import threading
import time
from pathlib import Path

# Add project to path
sys.path.insert(0, "/workspaces/Tmux-Orchestrator")

from tmux_orchestrator.core.monitor import DaemonAlreadyRunningError, IdleMonitor  # noqa: E402

# TMUXManager import removed - using comprehensive_mock_tmux fixture  # noqa: E402


def test_exception_flow():
    """Test the exception flow in different scenarios."""
    print("\n=== Testing DaemonAlreadyRunningError Exception Flow ===\n")

    # Clean up first
    cleanup_daemons()

    # Test 1: Direct start() method
    print("Test 1: Direct start() method")
    from tests.conftest import MockTMUXManager

    tmux = MockTMUXManager()
    monitor1 = IdleMonitor(tmux)

    try:
        pid1 = monitor1.start(interval=10)
        print(f"✅ First daemon started successfully with PID: {pid1}")
    except DaemonAlreadyRunningError as e:
        print(f"❌ First start raised exception: {e}")
    except Exception as e:
        print(f"❌ First start raised unexpected exception: {type(e).__name__}: {e}")

    time.sleep(2)  # Let daemon stabilize

    # Test 2: Second direct start() should raise exception
    print("\nTest 2: Second direct start() attempt")
    from tests.conftest import MockTMUXManager

    tmux2 = MockTMUXManager()
    monitor2 = IdleMonitor(tmux2)

    try:
        pid2 = monitor2.start(interval=10)
        print(f"❌ CRITICAL: Second daemon started without exception! PID: {pid2}")
    except DaemonAlreadyRunningError as e:
        print(f"✅ Second start correctly raised DaemonAlreadyRunningError: {e}")
    except Exception as e:
        print(f"❌ Second start raised unexpected exception: {type(e).__name__}: {e}")

    # Test 3: Supervised start
    print("\nTest 3: First supervised start")
    monitor3 = IdleMonitor(tmux)

    try:
        success3 = monitor3.start_supervised(interval=10)
        print(f"✅ First supervised start returned: {success3}")
    except DaemonAlreadyRunningError as e:
        print(f"❌ First supervised start raised exception: {e}")
    except Exception as e:
        print(f"❌ First supervised start raised unexpected exception: {type(e).__name__}: {e}")

    time.sleep(2)

    # Test 4: Second supervised start
    print("\nTest 4: Second supervised start attempt")
    monitor4 = IdleMonitor(tmux)

    try:
        success4 = monitor4.start_supervised(interval=10)
        print(f"❌ CRITICAL: Second supervised start returned: {success4} (should raise exception)")
    except DaemonAlreadyRunningError as e:
        print(f"✅ Second supervised start correctly raised DaemonAlreadyRunningError: {e}")
    except Exception as e:
        print(f"❌ Second supervised start raised unexpected exception: {type(e).__name__}: {e}")

    # Check actual daemon count
    print("\nDaemon Count Check:")
    count = count_daemons()
    print(f"Total daemon processes running: {count}")

    if count > 1:
        print("❌ CRITICAL: Multiple daemons are running!")
    else:
        print("✅ Only one daemon is running")

    # Cleanup
    cleanup_daemons()


def test_concurrent_starts():
    """Test concurrent start attempts."""
    print("\n=== Testing Concurrent Start Attempts ===\n")

    cleanup_daemons()

    results = []
    threads = []

    def start_daemon(idx):
        """Start daemon in thread."""
        from tests.conftest import MockTMUXManager

        tmux = MockTMUXManager()
        monitor = IdleMonitor(tmux)

        try:
            success = monitor.start_supervised(interval=10)
            results.append((idx, "SUCCESS", success))
        except DaemonAlreadyRunningError as e:
            results.append((idx, "EXCEPTION", str(e)))
        except Exception as e:
            results.append((idx, "ERROR", f"{type(e).__name__}: {e}"))

    # Start 5 threads simultaneously
    for i in range(5):
        thread = threading.Thread(target=start_daemon, args=(i,))
        threads.append(thread)
        thread.start()

    # Wait for all threads
    for thread in threads:
        thread.join()

    # Analyze results
    print("Thread Results:")
    success_count = 0
    exception_count = 0

    for idx, status, detail in results:
        print(f"  Thread {idx}: {status} - {detail}")
        if status == "SUCCESS":
            success_count += 1
        elif status == "EXCEPTION":
            exception_count += 1

    print(f"\nSummary: {success_count} successes, {exception_count} exceptions")

    # Check actual daemon count
    time.sleep(2)
    count = count_daemons()
    print(f"Total daemon processes running: {count}")

    if count > 1:
        print("❌ CRITICAL: Race condition still exists - multiple daemons created!")
    elif count == 1 and success_count > 1:
        print("❌ CRITICAL: Multiple threads reported success but only one daemon exists!")
    elif count == 0:
        print("❌ ERROR: No daemons running despite success reports!")
    else:
        print("✅ Singleton enforcement working correctly")

    cleanup_daemons()


def test_cli_behavior():
    """Test CLI behavior with exceptions."""
    print("\n=== Testing CLI Behavior ===\n")

    cleanup_daemons()

    # First start via CLI
    print("Test 1: First CLI start")
    result1 = subprocess.run(["tmux-orc", "monitor", "start", "--supervised"], capture_output=True, text=True)
    print(f"Exit code: {result1.returncode}")
    print(f"Output:\n{result1.stdout}")
    if result1.stderr:
        print(f"Error:\n{result1.stderr}")

    time.sleep(2)

    # Second start via CLI
    print("\nTest 2: Second CLI start (should show exception)")
    result2 = subprocess.run(["tmux-orc", "monitor", "start", "--supervised"], capture_output=True, text=True)
    print(f"Exit code: {result2.returncode}")
    print(f"Output:\n{result2.stdout}")
    if result2.stderr:
        print(f"Error:\n{result2.stderr}")

    # Check if exception message appears
    if "already running" in result2.stdout.lower():
        print("✅ CLI properly shows 'already running' message")
    else:
        print("❌ CLI does not show proper exception message")

    # Check daemon count
    count = count_daemons()
    print(f"\nTotal daemon processes: {count}")

    cleanup_daemons()


def count_daemons():
    """Count running daemon processes."""
    result = subprocess.run(["pgrep", "-f", "python.*_run_monitoring_daemon"], capture_output=True, text=True)

    if result.returncode == 0 and result.stdout:
        pids = result.stdout.strip().split("\n")
        return len([pid for pid in pids if pid])
    return 0


def cleanup_daemons():
    """Clean up all daemon processes and files."""
    # Stop via CLI
    subprocess.run(["tmux-orc", "monitor", "stop"], capture_output=True)
    time.sleep(1)

    # Force kill any remaining
    subprocess.run(["pkill", "-f", "python.*_run_monitoring_daemon"], capture_output=True)
    time.sleep(1)

    # Clean up files
    pid_files = [
        "/workspaces/Tmux-Orchestrator/.tmux_orchestrator/idle-monitor.pid",
        "/workspaces/Tmux-Orchestrator/.tmux_orchestrator/idle-monitor-supervisor.pid",
        "/workspaces/Tmux-Orchestrator/.tmux_orchestrator/idle-monitor.start.lock",
    ]

    for pid_file in pid_files:
        if Path(pid_file).exists():
            try:
                Path(pid_file).unlink()
            except Exception:
                pass


if __name__ == "__main__":
    print("=" * 60)
    print("DaemonAlreadyRunningError Investigation")
    print("=" * 60)

    # Run all tests
    test_exception_flow()
    test_concurrent_starts()
    test_cli_behavior()

    print("\n" + "=" * 60)
    print("Investigation Complete")
    print("=" * 60)
