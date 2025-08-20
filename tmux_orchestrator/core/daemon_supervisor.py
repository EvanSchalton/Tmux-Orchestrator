"""Daemon supervisor for reliable self-healing process management.

This module provides a proper self-healing mechanism to replace the flawed
__del__ method approach that was causing multiple daemon spawning issues.
"""

import logging
import os
import signal
import subprocess
import time
from datetime import datetime
from pathlib import Path

from tmux_orchestrator.core.config import Config


class DaemonSupervisor:
    """Reliable daemon supervision with proper self-healing capabilities."""

    def __init__(self, daemon_name: str = "idle-monitor"):
        self.daemon_name = daemon_name

        # Use configurable directory for all supervision files
        config = Config.load()
        project_dir = config.orchestrator_base_dir
        project_dir.mkdir(parents=True, exist_ok=True)

        self.pid_file = project_dir / f"{daemon_name}.pid"
        self.heartbeat_file = project_dir / f"{daemon_name}.heartbeat"
        self.supervisor_pid_file = project_dir / f"{daemon_name}-supervisor.pid"
        self.graceful_stop_file = project_dir / f"{daemon_name}.graceful"

        # Restart attempt tracking with exponential backoff
        self.restart_attempts = 0
        self.max_restart_attempts = 5
        self.base_backoff_seconds = 1
        self.max_backoff_seconds = 60
        self.last_restart_time = datetime.min

        # Health check configuration
        self.heartbeat_timeout = 30  # Seconds without heartbeat before restart
        self.check_interval = 10  # Seconds between health checks

        self.logger = self._setup_logging()

    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the supervisor."""
        logger = logging.getLogger(f"daemon_supervisor_{self.daemon_name}")
        logger.setLevel(logging.INFO)

        # Clear existing handlers
        logger.handlers.clear()

        # Create logs directory
        logs_dir = Path.cwd() / ".tmux_orchestrator" / "logs"
        logs_dir.mkdir(exist_ok=True)

        # File handler
        log_file = logs_dir / f"{self.daemon_name}-supervisor.log"
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter(f"%(asctime)s - PID:{os.getpid()} - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def is_daemon_running(self) -> bool:
        """Check if the daemon process is actually running."""
        if not self.pid_file.exists():
            return False

        try:
            with open(self.pid_file) as f:
                pid = int(f.read().strip())
            # Use kill(0) to check if process exists without sending signal
            os.kill(pid, 0)
            return True
        except (OSError, ValueError, FileNotFoundError):
            # Clean up stale PID file
            if self.pid_file.exists():
                try:
                    self.pid_file.unlink()
                except OSError:
                    pass
            return False

    def is_daemon_healthy(self) -> bool:
        """Check if daemon is running and responsive via heartbeat."""
        if not self.is_daemon_running():
            return False

        if not self.heartbeat_file.exists():
            self.logger.warning("Daemon running but no heartbeat file found")
            return False

        try:
            # Check heartbeat freshness
            heartbeat_age = time.time() - self.heartbeat_file.stat().st_mtime
            if heartbeat_age > self.heartbeat_timeout:
                self.logger.warning(f"Daemon heartbeat stale ({heartbeat_age:.1f}s old)")
                return False

            return True
        except OSError:
            self.logger.warning("Failed to read heartbeat file")
            return False

    def start_daemon(self, daemon_command: list[str]) -> bool:
        """Start the daemon process with proper supervision setup and file locking."""
        import fcntl

        # First check if daemon is already running before acquiring lock
        if self.is_daemon_running():
            self.logger.info("Daemon already running")
            from tmux_orchestrator.core.monitor import DaemonAlreadyRunningError

            existing_pid = None
            if self.pid_file.exists():
                try:
                    with open(self.pid_file) as f:
                        existing_pid = int(f.read().strip())
                except Exception:
                    pass
            raise DaemonAlreadyRunningError(existing_pid or 0, self.pid_file)

        # Use a lock file to prevent concurrent starts
        lock_file_path = self.pid_file.parent / f"{self.daemon_name}.start.lock"

        try:
            # Create/open lock file
            lock_fd = os.open(str(lock_file_path), os.O_CREAT | os.O_RDWR)

            try:
                # Try to acquire exclusive lock (non-blocking)
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

                # Double-check if daemon is running while holding the lock
                if self.is_daemon_running():
                    self.logger.info("Daemon already running (checked under lock)")
                    from tmux_orchestrator.core.monitor import DaemonAlreadyRunningError

                    existing_pid = None
                    if self.pid_file.exists():
                        try:
                            with open(self.pid_file) as f:
                                existing_pid = int(f.read().strip())
                        except Exception:
                            pass
                    raise DaemonAlreadyRunningError(existing_pid or 0, self.pid_file)

                self.logger.info(f"Starting daemon: {' '.join(daemon_command)}")

                # Start daemon process
                subprocess.Popen(
                    daemon_command,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                )

                # Wait briefly for daemon to initialize and write PID file
                for _ in range(50):  # 5 second timeout
                    if self.pid_file.exists():
                        break
                    time.sleep(0.1)
                else:
                    self.logger.error("Daemon failed to create PID file within timeout")
                    return False

                # Verify daemon started successfully
                if self.is_daemon_running():
                    self.logger.info("Daemon started successfully with PID from file")
                    self.restart_attempts = 0  # Reset on successful start
                    return True
                else:
                    self.logger.error("Daemon process failed to start properly")
                    return False

            finally:
                # Always release the lock
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                os.close(lock_fd)

        except BlockingIOError:
            # Another process has the lock
            self.logger.info("Another process is starting the daemon, waiting...")

            # Wait for the other process to finish, then raise exception since daemon already exists
            for _ in range(50):  # 5 second timeout
                if self.is_daemon_running():
                    self.logger.info("Daemon started by another process")
                    # Import and raise the exception to indicate daemon already exists
                    from tmux_orchestrator.core.monitor import DaemonAlreadyRunningError

                    existing_pid = None
                    if self.pid_file.exists():
                        try:
                            with open(self.pid_file) as f:
                                existing_pid = int(f.read().strip())
                        except Exception:
                            pass
                    raise DaemonAlreadyRunningError(existing_pid or 0, self.pid_file)
                time.sleep(0.1)

            self.logger.error("Timeout waiting for daemon to start by another process")
            return False

        except Exception as e:
            self.logger.error(f"Failed to start daemon: {e}")
            if "lock_fd" in locals():
                try:
                    os.close(lock_fd)
                except Exception:
                    pass
            return False

    def stop_daemon(self, graceful: bool = True) -> bool:
        """Stop the daemon process with proper cleanup."""
        if not self.is_daemon_running():
            self.logger.info("Daemon not running")
            return True

        try:
            with open(self.pid_file) as f:
                pid = int(f.read().strip())

            if graceful:
                # Create graceful stop flag
                self.graceful_stop_file.touch()
                self.logger.info(f"Created graceful stop flag for daemon PID {pid}")

            # Send SIGTERM for graceful shutdown
            os.kill(pid, signal.SIGTERM)
            self.logger.info(f"Sent SIGTERM to daemon PID {pid}")

            # Wait for graceful shutdown with timeout
            for i in range(30):  # 3 second timeout
                if not self.is_daemon_running():
                    self.logger.info(f"Daemon stopped gracefully after {i * 0.1:.1f}s")
                    break
                time.sleep(0.1)
            else:
                # Force kill if still running
                self.logger.warning("Daemon did not stop gracefully, sending SIGKILL")
                try:
                    os.kill(pid, signal.SIGKILL)
                    time.sleep(0.5)  # Give it time to die
                except OSError:
                    pass

            # Clean up files
            self._cleanup_daemon_files()
            return True

        except Exception as e:
            self.logger.error(f"Failed to stop daemon: {e}")
            return False

    def _cleanup_daemon_files(self):
        """Clean up daemon-related files."""
        for file_path in [self.pid_file, self.heartbeat_file, self.graceful_stop_file]:
            if file_path.exists():
                try:
                    file_path.unlink()
                    self.logger.debug(f"Cleaned up {file_path}")
                except OSError as e:
                    self.logger.warning(f"Failed to clean up {file_path}: {e}")

    def restart_daemon_with_backoff(self, daemon_command: list[str]) -> bool:
        """Restart daemon with exponential backoff to prevent restart storms."""
        now = datetime.now()

        # Check if we've exceeded max restart attempts
        if self.restart_attempts >= self.max_restart_attempts:
            time_since_last = (now - self.last_restart_time).total_seconds()
            if time_since_last < 300:  # 5 minutes cooling off period
                self.logger.error(
                    f"Max restart attempts ({self.max_restart_attempts}) exceeded. " f"Waiting for cooling off period."
                )
                return False
            else:
                # Reset attempts after cooling off
                self.restart_attempts = 0
                self.logger.info("Restart cooling off period completed, resetting attempts")

        # Calculate backoff delay
        backoff_delay = min(self.base_backoff_seconds * (2**self.restart_attempts), self.max_backoff_seconds)

        self.logger.warning(
            f"Restarting daemon (attempt {self.restart_attempts + 1}/{self.max_restart_attempts}) "
            f"after {backoff_delay}s backoff"
        )

        # Apply backoff delay
        time.sleep(backoff_delay)

        # Attempt restart
        self.restart_attempts += 1
        self.last_restart_time = now

        # Stop existing daemon if running
        self.stop_daemon(graceful=False)

        # Start daemon
        success = self.start_daemon(daemon_command)

        if success:
            self.logger.info(f"Daemon restarted successfully on attempt {self.restart_attempts}")
        else:
            self.logger.error(f"Daemon restart failed on attempt {self.restart_attempts}")

        return success

    def supervise_daemon(self, daemon_command: list[str]) -> None:
        """Main supervision loop - monitors daemon health and restarts as needed."""
        self.logger.info(f"Starting daemon supervision for: {' '.join(daemon_command)}")

        # Write supervisor PID file
        with open(self.supervisor_pid_file, "w") as f:
            f.write(str(os.getpid()))

        try:
            while True:
                try:
                    # Check if graceful stop was requested
                    if self.graceful_stop_file.exists():
                        self.logger.info("Graceful stop requested for supervision")
                        break

                    # Check daemon health
                    if not self.is_daemon_healthy():
                        self.logger.warning("Daemon unhealthy, attempting restart")

                        if not self.restart_daemon_with_backoff(daemon_command):
                            self.logger.error("Failed to restart daemon, will retry next cycle")
                    else:
                        # Daemon is healthy
                        self.logger.debug("Daemon health check passed")

                    # Sleep until next check
                    time.sleep(self.check_interval)

                except KeyboardInterrupt:
                    self.logger.info("Supervision interrupted by KeyboardInterrupt")
                    break
                except Exception as e:
                    self.logger.error(f"Error in supervision loop: {e}", exc_info=True)
                    time.sleep(self.check_interval)

        finally:
            self.logger.info("Daemon supervision ending")
            # Clean up supervisor PID file
            if self.supervisor_pid_file.exists():
                try:
                    self.supervisor_pid_file.unlink()
                except OSError:
                    pass

    def get_status(self) -> dict:
        """Get current supervision status."""
        return {
            "daemon_running": self.is_daemon_running(),
            "daemon_healthy": self.is_daemon_healthy(),
            "restart_attempts": self.restart_attempts,
            "max_restart_attempts": self.max_restart_attempts,
            "supervisor_pid": os.getpid() if self.supervisor_pid_file.exists() else None,
        }
