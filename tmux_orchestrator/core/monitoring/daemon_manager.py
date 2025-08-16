"""
Daemon lifecycle management.

This module handles daemon process management, including starting, stopping,
and monitoring daemon processes. Extracted from monitor.py for better separation of concerns.
"""

import fcntl
import logging
import os
import signal
import time
from pathlib import Path
from typing import Any, Callable, Optional

from tmux_orchestrator.core.config import Config

from .interfaces import DaemonManagerInterface


class DaemonManager(DaemonManagerInterface):
    """Manages daemon process lifecycle with proper locking and cleanup."""

    def __init__(self, config: Config, logger: logging.Logger):
        """Initialize the daemon manager.

        Args:
            config: Configuration instance
            logger: Logger instance
        """
        self.config = config
        self.logger = logger
        self.pid_file = Path(config.RUNTIME_DIR) / "tmux-orchestrator.pid"
        self.lock_file = Path(config.RUNTIME_DIR) / "tmux-orchestrator.lock"
        self._shutdown_requested = False
        self._lock_fd: Optional[int] = None

        # Ensure runtime directory exists
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)

    def is_running(self) -> bool:
        """Check if daemon is running.

        Returns:
            True if daemon is running
        """
        pid = self.get_pid()
        if not pid:
            return False

        try:
            # Check if process exists
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            # Process doesn't exist, clean up stale file
            self.logger.info(f"Daemon PID {pid} not found, cleaning up stale files")
            self.cleanup_stale_files()
            return False
        except PermissionError:
            # Process exists but we can't signal it (different user?)
            return True
        except Exception as e:
            self.logger.error(f"Error checking daemon status: {e}")
            return False

    def get_pid(self) -> Optional[int]:
        """Get daemon PID from file.

        Returns:
            PID if found, None otherwise
        """
        if not self.pid_file.exists():
            return None

        try:
            with open(self.pid_file) as f:
                return int(f.read().strip())
        except (OSError, ValueError) as e:
            self.logger.error(f"Error reading PID file: {e}")
            return None

    def start_daemon(self, target_func: Callable, args: tuple = ()) -> int:
        """Start the daemon process.

        Args:
            target_func: Function to run as daemon
            args: Arguments for target function

        Returns:
            PID of started daemon

        Raises:
            RuntimeError: If daemon already running or lock acquisition fails
        """
        if self.is_running():
            raise RuntimeError("Daemon is already running")

        # Try to acquire exclusive lock
        if not self._acquire_lock():
            raise RuntimeError("Failed to acquire daemon lock - another instance may be starting")

        try:
            # Fork first child
            pid = os.fork()
            if pid > 0:
                # Parent process - wait for child and return its PID
                os.waitpid(pid, 0)
                # Read the daemon PID that the grandchild wrote
                time.sleep(0.5)  # Give grandchild time to write PID
                daemon_pid = self.get_pid()
                if daemon_pid:
                    self.logger.info(f"Daemon started with PID {daemon_pid}")
                    return daemon_pid
                else:
                    raise RuntimeError("Daemon process started but PID not found")

            # First child - create new session and fork again
            os.setsid()

            # Fork second child (daemon)
            pid = os.fork()
            if pid > 0:
                # First child exits
                os._exit(0)

            # Second child (daemon process)
            # Redirect standard file descriptors
            with open("/dev/null") as devnull:
                os.dup2(devnull.fileno(), 0)  # stdin

            # Set up logging to file for daemon
            log_file = Path(self.config.RUNTIME_DIR) / "daemon.log"
            with open(log_file, "a") as log_fd:
                os.dup2(log_fd.fileno(), 1)  # stdout
                os.dup2(log_fd.fileno(), 2)  # stderr

            # Write PID file
            daemon_pid = os.getpid()
            with open(self.pid_file, "w") as f:
                f.write(str(daemon_pid))

            # Set up signal handlers
            signal.signal(signal.SIGTERM, self._handle_signal)
            signal.signal(signal.SIGINT, self._handle_signal)
            signal.signal(signal.SIGHUP, signal.SIG_IGN)

            # Run the target function
            try:
                target_func(*args)
            except Exception as e:
                self.logger.error(f"Daemon crashed: {e}")
            finally:
                self.cleanup_stale_files()
                os._exit(0)

        finally:
            self._release_lock()

    def stop_daemon(self, timeout: int = 10) -> bool:
        """Stop the daemon gracefully.

        Args:
            timeout: Maximum seconds to wait for shutdown

        Returns:
            True if stopped successfully
        """
        pid = self.get_pid()
        if not pid:
            self.logger.info("No daemon PID found")
            return True

        try:
            # Send SIGTERM for graceful shutdown
            self.logger.info(f"Sending SIGTERM to daemon PID {pid}")
            os.kill(pid, signal.SIGTERM)

            # Wait for process to terminate
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    os.kill(pid, 0)  # Check if still running
                    time.sleep(0.1)
                except ProcessLookupError:
                    # Process terminated
                    self.logger.info(f"Daemon PID {pid} stopped successfully")
                    self.cleanup_stale_files()
                    return True

            # Timeout - force kill
            self.logger.warning(f"Daemon PID {pid} didn't stop gracefully, sending SIGKILL")
            os.kill(pid, signal.SIGKILL)
            time.sleep(0.5)
            self.cleanup_stale_files()
            return True

        except ProcessLookupError:
            # Already dead
            self.logger.info(f"Daemon PID {pid} already stopped")
            self.cleanup_stale_files()
            return True
        except Exception as e:
            self.logger.error(f"Error stopping daemon: {e}")
            return False

    def restart_daemon(self, target_func: Callable, args: tuple = ()) -> int:
        """Restart the daemon process.

        Args:
            target_func: Function to run as daemon
            args: Arguments for target function

        Returns:
            PID of restarted daemon
        """
        self.logger.info("Restarting daemon")

        # Stop existing daemon if running
        if self.is_running():
            if not self.stop_daemon():
                raise RuntimeError("Failed to stop existing daemon")

        # Small delay to ensure cleanup
        time.sleep(1)

        # Start new daemon
        return self.start_daemon(target_func, args)

    def cleanup_stale_files(self) -> None:
        """Clean up stale PID and lock files."""
        if self.pid_file.exists():
            try:
                self.pid_file.unlink()
                self.logger.debug("Removed PID file")
            except Exception as e:
                self.logger.error(f"Error removing PID file: {e}")

        if self.lock_file.exists() and not self._lock_fd:
            try:
                self.lock_file.unlink()
                self.logger.debug("Removed lock file")
            except Exception as e:
                self.logger.error(f"Error removing lock file: {e}")

    def should_shutdown(self) -> bool:
        """Check if daemon should shutdown.

        Returns:
            True if shutdown requested
        """
        return self._shutdown_requested

    def get_daemon_info(self) -> dict:
        """Get daemon information.

        Returns:
            Dictionary with daemon details
        """
        pid = self.get_pid()
        is_running = self.is_running()

        info = {
            "pid": pid,
            "is_running": is_running,
            "pid_file": str(self.pid_file),
            "lock_file": str(self.lock_file),
            "shutdown_requested": self._shutdown_requested,
        }

        if is_running and pid:
            try:
                # Get process info from /proc
                with open(f"/proc/{pid}/stat") as f:
                    stat_line = f.read().strip()
                    # Parse basic info from stat line
                    parts = stat_line.split(")")
                    if len(parts) >= 2:
                        # State is first char after closing paren
                        state_info = parts[1].strip().split()
                        if state_info:
                            state_map = {
                                "R": "running",
                                "S": "sleeping",
                                "D": "disk sleep",
                                "Z": "zombie",
                                "T": "stopped",
                            }
                            info["state"] = state_map.get(state_info[0], "unknown")

                # Get process uptime
                with open(f"/proc/{pid}/stat") as f:
                    stat_parts = f.read().strip().split()
                    if len(stat_parts) > 21:
                        start_time = int(stat_parts[21])
                        clock_ticks = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
                        uptime_seconds = time.time() - (start_time / clock_ticks)
                        info["uptime_seconds"] = int(uptime_seconds)

            except Exception as e:
                self.logger.debug(f"Could not get additional process info: {e}")

        return info

    def _acquire_lock(self) -> bool:
        """Acquire exclusive lock for daemon.

        Returns:
            True if lock acquired successfully
        """
        try:
            self._lock_fd = os.open(str(self.lock_file), os.O_CREAT | os.O_WRONLY, 0o600)
            fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except OSError as e:
            self.logger.error(f"Failed to acquire lock: {e}")
            if self._lock_fd:
                os.close(self._lock_fd)
                self._lock_fd = None
            return False

    def _release_lock(self) -> None:
        """Release daemon lock."""
        if self._lock_fd:
            try:
                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
                os.close(self._lock_fd)
                self._lock_fd = None
            except Exception as e:
                self.logger.error(f"Error releasing lock: {e}")

    def _handle_signal(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        self.logger.info(f"Received signal {signum}, requesting shutdown")
        self._shutdown_requested = True
