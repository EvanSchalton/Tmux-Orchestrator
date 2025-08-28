"""Daemon management functionality for the monitoring system."""

import fcntl
import logging
import os
import time
from pathlib import Path

from tmux_orchestrator.core.config import Config


class DaemonAlreadyRunningError(Exception):
    """Exception raised when trying to start a daemon that is already running."""

    def __init__(self, pid: int, pid_file: Path):
        self.pid = pid
        self.pid_file = pid_file
        super().__init__(
            f"Monitor daemon is already running with PID {pid}. "
            f"PID file: {pid_file}. "
            f"Use 'tmux-orc monitor stop' to stop the existing daemon first, "
            f"or 'tmux-orc monitor status' to check daemon status."
        )


class DaemonManager:
    """Manages daemon lifecycle operations including PID file handling and process validation."""

    def __init__(self, config: Config | None = None) -> None:
        """Initialize the daemon manager.

        Args:
            config: Optional Config instance for customization. If None, loads default.
        """
        if config is None:
            config = Config.load()
        self.config = config
        self.pid_file = config.orchestrator_base_dir / "idle-monitor.pid"
        self._startup_lock_fd: int | None = None
        self._startup_lock_file: Path | None = None

    def is_running(self) -> bool:
        """Check if monitor daemon is running with robust validation."""
        if not self.pid_file.exists():
            return False

        try:
            with open(self.pid_file) as f:
                pid_str = f.read().strip()
                if not pid_str:
                    # Empty PID file
                    self._cleanup_stale_pid_file()
                    return False

                pid = int(pid_str)

            # Use robust validation from singleton enforcement
            if self._is_valid_daemon_process(pid):
                return True
            else:
                # Clean up stale PID file
                self._cleanup_stale_pid_file()
                return False

        except (OSError, ValueError, FileNotFoundError):
            # Handle permissions errors, corrupted files, etc.
            if self.pid_file.exists():
                self._cleanup_stale_pid_file()
            return False

    def check_existing_daemon(self) -> int | None:
        """Detect existing monitoring daemon instances using PID file validation and process verification.

        Implements singleton pattern enforcement by checking for existing daemon processes
        before starting new instances. This prevents multiple monitoring daemons from
        running simultaneously, which could cause conflicts, duplicate notifications,
        and resource contention.

        Returns:
            int | None: PID of valid existing daemon, or None if no daemon running
        """
        logger = self._get_singleton_logger()
        logger.debug("[SINGLETON] Checking for existing daemon")

        # Check for PID file
        if not self.pid_file.exists():
            logger.debug("[SINGLETON] No PID file found - no existing daemon")
            return None

        # Read PID from file with error handling
        try:
            with open(self.pid_file) as f:
                pid_str = f.read().strip()
                if not pid_str:
                    logger.warning("[SINGLETON] PID file is empty - removing stale file")
                    self._cleanup_stale_pid_file()
                    return None

                pid = int(pid_str)
                logger.debug(f"[SINGLETON] Found PID file with PID {pid}")

        except (OSError, ValueError) as e:
            logger.warning(f"[SINGLETON] Could not read PID file: {e} - removing stale file")
            self._cleanup_stale_pid_file()
            return None

        # Validate the process actually exists and is our daemon
        if self._is_valid_daemon_process(pid):
            logger.info(f"[SINGLETON] Valid daemon already running with PID {pid}")
            return pid
        else:
            logger.warning(f"[SINGLETON] Stale/invalid daemon process {pid} - cleaning up stale PID file")
            # Only clean up PID file, don't kill process (might not be ours)
            self._cleanup_stale_pid_file()
            return None

    def handle_startup_race_condition(self) -> bool:
        """Handle race conditions with atomic file locking for daemon startup.

        Uses a combination of file locking and atomic PID file creation to ensure
        only one daemon can start at a time, even with concurrent startup attempts.

        Returns:
            True if this process should proceed with daemon startup, False otherwise
        """
        logger = self._get_singleton_logger()

        lock_file = self.pid_file.with_suffix(".startup.lock")
        max_retries = 3
        retry_delay = 0.1  # 100ms between retries

        for attempt in range(max_retries):
            try:
                # Ensure lock directory exists
                lock_file.parent.mkdir(parents=True, exist_ok=True)

                # Open lock file with create flag for atomic operation
                lock_fd = os.open(str(lock_file), os.O_CREAT | os.O_RDWR)

                try:
                    # Try to acquire exclusive lock (non-blocking)
                    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

                    # Write our PID to lock file for debugging
                    os.write(lock_fd, f"{os.getpid()}\n".encode())
                    os.fsync(lock_fd)  # Force write to disk

                    logger.debug(f"[SINGLETON] Acquired startup lock (attempt {attempt + 1})")

                    # CRITICAL SECTION: Check for existing daemon while holding lock
                    existing_pid = self.check_existing_daemon()
                    if existing_pid:
                        logger.info(f"[SINGLETON] Found existing daemon {existing_pid} while holding lock")
                        return False

                    # ATOMIC CHECK: Verify PID file doesn't exist before proceeding
                    if self.pid_file.exists():
                        logger.warning("[SINGLETON] PID file appeared during lock - race condition detected")
                        return False

                    # We have the lock and no existing daemon - proceed with startup
                    logger.debug("[SINGLETON] No existing daemon found - proceeding with startup")

                    # IMPORTANT: Keep the lock file and file descriptor open!
                    # Store it so it stays alive during daemon startup
                    self._startup_lock_fd = lock_fd
                    self._startup_lock_file = lock_file

                    # Don't close the FD here - it will be closed after PID file is written
                    return True

                except BlockingIOError:
                    # Another process has the lock - wait and retry
                    logger.debug(f"[SINGLETON] Startup lock held by another process (attempt {attempt + 1})")
                    os.close(lock_fd)  # Close FD since we didn't get the lock

                    if attempt < max_retries - 1:
                        # Exponential backoff for retries
                        sleep_time = retry_delay * (2**attempt)
                        logger.debug(f"[SINGLETON] Waiting {sleep_time:.2f}s before retry")
                        time.sleep(sleep_time)
                        continue
                    else:
                        # Final attempt - check if other daemon succeeded
                        logger.info("[SINGLETON] Max retries reached - checking if other daemon started")
                        time.sleep(0.5)  # Give other process time to complete

                        existing_pid = self.check_existing_daemon()
                        if existing_pid:
                            logger.info(f"[SINGLETON] Other daemon startup completed (PID {existing_pid})")
                            return False
                        else:
                            logger.warning("[SINGLETON] No daemon found after lock contention - allowing startup")
                            return True

                except Exception:
                    # Error occurred - close FD and re-raise
                    os.close(lock_fd)
                    raise

            except OSError as e:
                logger.warning(f"[SINGLETON] Lock file operation failed (attempt {attempt + 1}): {e}")

                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    # Fallback to simple check without locking
                    logger.warning("[SINGLETON] File locking failed - using fallback check")
                    existing_pid = self.check_existing_daemon()
                    return existing_pid is None

        # Should not reach here, but handle gracefully
        logger.error("[SINGLETON] Unexpected end of race condition handling")
        return False

    def write_pid_file_atomic(self, pid: int) -> bool:
        """Write PID file atomically with enhanced race condition protection.

        Uses atomic file operations and additional safety checks to ensure
        exactly one daemon can successfully write its PID file.

        Args:
            pid: Process ID to write

        Returns:
            True if successful, False otherwise
        """
        logger = self._get_singleton_logger()

        try:
            # Ensure parent directory exists and is writable
            self.pid_file.parent.mkdir(parents=True, exist_ok=True)

            # Check write permissions early
            if not os.access(self.pid_file.parent, os.W_OK):
                logger.error(f"[SINGLETON] No write permission to directory {self.pid_file.parent}")
                return False

            # Use process-specific temporary file name to avoid conflicts
            temp_file = self.pid_file.with_suffix(f".tmp.{pid}")

            try:
                # ATOMIC OPERATION 1: Write to temporary file
                with open(temp_file, "w") as f:
                    f.write(str(pid))
                    f.flush()
                    os.fsync(f.fileno())  # Force write to disk

                logger.debug(f"[SINGLETON] Wrote PID {pid} to temporary file {temp_file}")

                # ATOMIC OPERATION 2: Check for existing PID file just before move
                if self.pid_file.exists():
                    logger.warning("[SINGLETON] PID file exists just before atomic move - race condition detected")
                    # Double-check if it's a valid daemon
                    try:
                        with open(self.pid_file) as f:
                            existing_pid = int(f.read().strip())
                        if self._is_valid_daemon_process(existing_pid):
                            logger.warning(f"[SINGLETON] Valid daemon {existing_pid} already running - aborting write")
                            return False
                        else:
                            logger.warning("[SINGLETON] Stale PID file detected - proceeding with atomic move")
                    except (OSError, ValueError):
                        logger.warning("[SINGLETON] Corrupted PID file detected - proceeding with atomic move")

                # ATOMIC OPERATION 3: Atomic move (this is the critical moment)
                temp_file.rename(self.pid_file)
                logger.debug(f"[SINGLETON] Atomically moved temp file to {self.pid_file}")

                # VERIFICATION: Confirm the write was successful and not overwritten
                try:
                    with open(self.pid_file) as f:
                        written_pid_str = f.read().strip()
                        if not written_pid_str:
                            logger.error("[SINGLETON] PID file is empty after write")
                            return False

                        written_pid = int(written_pid_str)
                        if written_pid != pid:
                            logger.error(f"[SINGLETON] PID file verification failed: expected {pid}, got {written_pid}")
                            # Another process may have overwritten our file
                            return False

                    logger.debug(f"[SINGLETON] PID file verification successful: {pid}")
                    return True

                except (OSError, ValueError) as e:
                    logger.error(f"[SINGLETON] PID file verification failed: {e}")
                    return False

            finally:
                # Clean up temporary file if it still exists
                try:
                    if temp_file.exists():
                        temp_file.unlink()
                        logger.debug(f"[SINGLETON] Cleaned up temporary file {temp_file}")
                except OSError as e:
                    logger.debug(f"[SINGLETON] Could not clean up temp file: {e}")

        except PermissionError as e:
            logger.error(f"[SINGLETON] Permission denied writing PID file: {e}")
            return False
        except OSError as e:
            logger.error(f"[SINGLETON] Failed to write PID file atomically: {e}")
            return False

    def release_startup_lock(self) -> None:
        """Release the startup lock after daemon initialization."""
        if self._startup_lock_fd is not None:
            try:
                fcntl.flock(self._startup_lock_fd, fcntl.LOCK_UN)
                os.close(self._startup_lock_fd)
                if self._startup_lock_file and self._startup_lock_file.exists():
                    self._startup_lock_file.unlink()
            except Exception:
                pass
            finally:
                self._startup_lock_fd = None
                self._startup_lock_file = None

    def stop_daemon(self) -> bool:
        """Stop the running daemon.

        Returns:
            True if daemon was stopped, False if no daemon was running
        """
        if not self.pid_file.exists():
            return False

        try:
            with open(self.pid_file) as f:
                pid = int(f.read().strip())

            # Send SIGTERM to daemon
            os.kill(pid, 15)  # SIGTERM

            # Wait for daemon to stop (max 5 seconds)
            for _ in range(50):
                try:
                    os.kill(pid, 0)  # Check if process exists
                    time.sleep(0.1)
                except OSError:
                    # Process no longer exists
                    break

            # Clean up PID file
            self._cleanup_stale_pid_file()
            return True

        except (OSError, ValueError):
            self._cleanup_stale_pid_file()
            return False

    def _is_valid_daemon_process(self, pid: int) -> bool:
        """Validate that a process ID corresponds to a legitimate monitoring daemon instance.

        Args:
            pid: Process ID to validate against current system processes

        Returns:
            True if process exists and command line indicates it's a monitoring daemon,
            False if process doesn't exist or appears to be an unrelated process
        """
        logger = self._get_singleton_logger()

        try:
            # Check if process exists
            os.kill(pid, 0)
            logger.debug(f"[SINGLETON] Process {pid} exists")

            # Additional validation: check process command line to ensure it's our daemon
            try:
                with open(f"/proc/{pid}/cmdline") as f:
                    cmdline = f.read()
                    # Look for Python process running monitor-related code
                    # The cmdline is null-separated, so split it
                    cmdline_parts = cmdline.split("\0")
                    cmdline_str = " ".join(cmdline_parts)

                    # Check for monitor daemon indicators
                    monitor_indicators = [
                        "_run_monitoring_daemon",  # Direct daemon method
                        "idle-monitor",  # PID file name
                        "IdleMonitor",  # Class name
                        "monitor start",  # CLI command
                        "monitor.py",  # Module name
                    ]

                    if any(indicator in cmdline_str for indicator in monitor_indicators):
                        logger.debug(f"[SINGLETON] Process {pid} appears to be a monitor daemon: {cmdline_str}")
                        return True
                    else:
                        logger.debug(f"[SINGLETON] Process {pid} doesn't appear to be our daemon: {cmdline_str}")
                        return False
            except OSError:
                # Can't read cmdline (permissions/etc) - assume it's valid if process exists
                logger.debug(f"[SINGLETON] Cannot verify process {pid} cmdline - assuming valid")
                return True

        except OSError:
            # Process doesn't exist
            logger.debug(f"[SINGLETON] Process {pid} does not exist")
            return False

    def _cleanup_stale_pid_file(self) -> None:
        """Clean up stale PID file with proper error handling.

        Uses atomic operations to prevent race conditions.
        """
        logger = self._get_singleton_logger()

        try:
            if self.pid_file.exists():
                # Atomic removal
                self.pid_file.unlink()
                logger.debug("[SINGLETON] Removed stale PID file")
            else:
                logger.debug("[SINGLETON] No PID file to clean up")
        except OSError as e:
            logger.error(f"[SINGLETON] Could not remove stale PID file: {e}")

    def _get_singleton_logger(self) -> logging.Logger:
        """Get or create the singleton logger for daemon operations."""
        logger = logging.getLogger("idle_monitor_singleton")
        logger.setLevel(logging.DEBUG)

        # Set up handler if none exists and stderr is available
        if not logger.handlers:
            try:
                handler = logging.StreamHandler()
                formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
                handler.setFormatter(formatter)
                logger.addHandler(handler)
            except (ValueError, OSError):
                # stderr may be closed in daemon process, use file logging instead
                log_file = self.pid_file.parent / "singleton.log"
                file_handler = logging.FileHandler(log_file)
                formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)

        return logger
