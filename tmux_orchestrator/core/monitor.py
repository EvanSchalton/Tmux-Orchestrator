"""Advanced agent monitoring system with 100% accurate idle detection."""

import logging
import multiprocessing
import os
import re
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.core.daemon_supervisor import DaemonSupervisor
from tmux_orchestrator.core.monitor_helpers import (
    DAEMON_CONTROL_LOOP_COOLDOWN_SECONDS,
    NONRESPONSIVE_PM_ESCALATIONS_MINUTES,
    AgentState,
    DaemonAction,
    calculate_sleep_duration,
    detect_claude_state,
    extract_rate_limit_reset_time,
    is_claude_interface_present,
    should_notify_pm,
)
from tmux_orchestrator.utils.string_utils import efficient_change_score, levenshtein_distance
from tmux_orchestrator.utils.tmux import TMUXManager


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


class TerminalCache(BaseModel):
    """Intelligent terminal content caching for idle detection."""

    early_value: Optional[str] = None
    later_value: Optional[str] = None
    max_distance: int = 10
    use_levenshtein: bool = False  # Toggle between Levenshtein and efficient scoring

    @property
    def status(self) -> str:
        """Get the current idle status based on content changes."""
        if self.early_value is None or self.later_value is None:
            return "unknown"

        if self.match():
            return "continuously_idle"  # No significant changes
        else:
            return "newly_idle"  # Significant changes detected

    def match(self) -> bool:
        """Check if terminal content matches (minimal changes)."""
        if self.early_value is None or self.later_value is None:
            return False

        if self.use_levenshtein:
            # Use proper Levenshtein distance for precise change detection
            distance = levenshtein_distance(self.early_value, self.later_value)
            return distance <= self.max_distance
        else:
            # Use efficient change scoring optimized for terminal content
            score = efficient_change_score(self.early_value, self.later_value)
            return score <= self.max_distance

    def update(self, value: str) -> None:
        """Update cache with new terminal content."""
        self.early_value = self.later_value
        self.later_value = value


@dataclass
class AgentHealthStatus:
    """Agent health status data."""

    target: str
    last_heartbeat: datetime
    last_response: datetime
    consecutive_failures: int
    is_responsive: bool
    last_content_hash: str
    status: str  # 'healthy', 'warning', 'critical', 'unresponsive'
    is_idle: bool
    activity_changes: int


class IdleMonitor:
    """Monitor with 100% accurate idle detection using native Python daemon.

    This class implements a singleton pattern to prevent multiple monitor instances
    from being created, which could lead to multiple daemons running concurrently.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, tmux: TMUXManager, config: Optional[Config] = None):
        """Ensure only one instance of IdleMonitor exists (singleton pattern)."""
        if cls._instance is None:
            with cls._lock:
                # Double-check locking pattern
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, tmux: TMUXManager, config: Optional[Config] = None):
        # Only initialize once
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self.tmux = tmux
        # Use configurable directory for storage
        if config is None:
            config = Config.load()
        project_dir = config.orchestrator_base_dir
        project_dir.mkdir(parents=True, exist_ok=True)
        logs_dir = project_dir / "logs"
        logs_dir.mkdir(exist_ok=True)

        self.pid_file = project_dir / "idle-monitor.pid"
        self.log_file = logs_dir / "idle-monitor.log"
        self.logs_dir = logs_dir  # Store for multi-log system
        self.graceful_stop_file = project_dir / "idle-monitor.graceful"  # File-based flag for graceful stop
        self.daemon_process: multiprocessing.Process | None = None

        # PM recovery grace period tracking
        self._pm_recovery_timestamps: dict[str, datetime] = {}  # Track when PMs were recovered
        self._grace_period_minutes = config.get(
            "monitoring.pm_recovery_grace_period_minutes", 3
        )  # Configurable grace period

        # Recovery cooldown to prevent rapid recovery loops
        self._recovery_cooldown_minutes = config.get("monitoring.pm_recovery_cooldown_minutes", 5)
        self._last_recovery_attempt: dict[str, datetime] = {}  # Track last recovery attempt per session

        # PM crash observation tracking for pre-kill confirmation
        self._pm_crash_observations: dict[str, list[datetime]] = {}  # Track crash observations
        self._crash_observation_window = 30  # 30-second observation period before killing PM
        self._crash_notifications: dict[str, datetime] = {}
        self._idle_notifications: dict[str, datetime] = {}
        self._idle_agents: dict[str, datetime] = {}
        self._submission_attempts: dict[str, int] = {}
        self._last_submission_time: dict[str, float] = {}
        self._session_agents: dict[
            str, dict[str, dict[str, str]]
        ] = {}  # Track agents with names: {session: {target: {name, type}}}
        # Track when agents were first identified as missing
        self._missing_agent_grace: dict[str, datetime] = {}
        # Track when we last notified about missing agents
        self._missing_agent_notifications: dict[str, datetime] = {}
        # Track when entire team becomes idle per session
        self._team_idle_at: dict[str, datetime | None] = {}
        # Track escalation history per PM
        self._pm_escalation_history: dict[str, dict[int, datetime]] = {}
        # Cache session-specific loggers
        self._session_loggers: dict[str, logging.Logger] = {}

        # Activity tracking for intelligent idle detection
        # Terminal content caches per agent with resource limits
        self._terminal_caches: dict[str, TerminalCache] = {}
        self._cache_access_times: dict[str, float] = {}  # Track last access time for LRU cleanup
        self._max_cache_entries = config.get("monitoring.max_cache_entries", 100)  # Max agents to track
        self._max_cache_age_hours = config.get("monitoring.max_cache_age_hours", 24)  # Max cache age
        self._cache_cleanup_interval = 3600  # Clean up caches every hour
        self._last_cache_cleanup = time.time()

        # Self-healing daemon flag - only set True by tmux-orc stop command
        self.__allow_cleanup = False

        # Initialize daemon supervisor for proper self-healing
        self.supervisor = DaemonSupervisor("idle-monitor")

    # COMMENTED OUT: __del__ method causing multiple daemon spawning issues
    # The file-based graceful stop mechanism is sufficient for daemon management
    # This destructor was being called by every Python process that imports IdleMonitor,
    # including test processes, causing multiple daemon instances to spawn
    #
    # def __del__(self) -> None:
    #     """Destructor that implements self-healing daemon behavior.
    #
    #     If the daemon is killed by any method other than tmux-orc stop,
    #     it will automatically respawn itself to ensure continuous monitoring.
    #     """
    #     # Implementation commented out to prevent multiple daemon spawning

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

    def _check_existing_daemon(self) -> int | None:
        """Check for existing daemon without killing it.

        Returns:
            PID of existing valid daemon, None if no valid daemon exists
        """
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

    def _is_valid_daemon_process(self, pid: int) -> bool:
        """Check if PID corresponds to a valid monitor daemon process.

        Args:
            pid: Process ID to validate

        Returns:
            True if process exists and appears to be our daemon
        """
        logger = logging.getLogger("idle_monitor_singleton")

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
        logger = logging.getLogger("idle_monitor_singleton")

        try:
            if self.pid_file.exists():
                # Atomic removal
                self.pid_file.unlink()
                logger.debug("[SINGLETON] Removed stale PID file")
            else:
                logger.debug("[SINGLETON] No PID file to clean up")
        except OSError as e:
            logger.error(f"[SINGLETON] Could not remove stale PID file: {e}")

    def _write_pid_file_atomic(self, pid: int) -> bool:
        """Write PID file atomically with enhanced race condition protection.

        Uses atomic file operations and additional safety checks to ensure
        exactly one daemon can successfully write its PID file.

        Args:
            pid: Process ID to write

        Returns:
            True if successful, False otherwise
        """
        logger = logging.getLogger("idle_monitor_singleton")

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

    def _handle_startup_race_condition(self) -> bool:
        """Handle race conditions with atomic file locking for daemon startup.

        Uses a combination of file locking and atomic PID file creation to ensure
        only one daemon can start at a time, even with concurrent startup attempts.

        Returns:
            True if this process should proceed with daemon startup, False otherwise
        """
        logger = logging.getLogger("idle_monitor_singleton")

        # Use file locking with atomic operations to prevent race conditions
        import fcntl
        import time

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
                    existing_pid = self._check_existing_daemon()
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

                        existing_pid = self._check_existing_daemon()
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
                    existing_pid = self._check_existing_daemon()
                    return existing_pid is None

        # Should not reach here, but handle gracefully
        logger.error("[SINGLETON] Unexpected end of race condition handling")
        return False

    def start(self, interval: int = 10) -> int:
        """Start the native Python monitor daemon with strict singleton enforcement.

        Raises:
            DaemonAlreadyRunningError: If a valid daemon is already running
            RuntimeError: If daemon startup fails for other reasons
        """
        # CRITICAL: Acquire startup lock BEFORE any checks or forking
        # This ensures atomic singleton enforcement
        if not self._handle_startup_race_condition():
            # Another process is starting or daemon already exists
            existing_pid = self._check_existing_daemon()
            if existing_pid:
                raise DaemonAlreadyRunningError(existing_pid, self.pid_file)
            else:
                # Race condition - another process won the lock
                raise RuntimeError("Daemon startup failed - another process may have started concurrently")

        # We have the lock - double-check no daemon exists
        existing_pid = self._check_existing_daemon()
        if existing_pid:
            # Release lock before raising exception
            if hasattr(self, "_startup_lock_fd"):
                try:
                    import fcntl

                    fcntl.flock(self._startup_lock_fd, fcntl.LOCK_UN)
                    os.close(self._startup_lock_fd)
                except Exception:
                    pass
            raise DaemonAlreadyRunningError(existing_pid, self.pid_file)

        # Fork to create daemon (proper daemonization to prevent early exit)
        pid = os.fork()
        if pid > 0:
            # Parent process - keep lock until child writes PID file
            # Wait briefly for child to write PID file
            for _ in range(50):  # 5 second timeout
                if self.pid_file.exists():
                    break
                time.sleep(0.1)

            # Release lock in parent after PID file is written
            if hasattr(self, "_startup_lock_fd"):
                try:
                    import fcntl

                    fcntl.flock(self._startup_lock_fd, fcntl.LOCK_UN)
                    os.close(self._startup_lock_fd)
                    if hasattr(self, "_startup_lock_file") and self._startup_lock_file.exists():
                        self._startup_lock_file.unlink()
                except Exception:
                    pass

            return pid

        # Child process - become daemon
        os.setsid()  # Create new session

        # Fork again to prevent zombie processes
        pid = os.fork()
        if pid > 0:
            os._exit(0)  # Exit first child

        # Grandchild - the actual daemon
        # Redirect file descriptors to /dev/null instead of closing them
        # This prevents issues with logging in the daemon process
        dev_null = os.open("/dev/null", os.O_RDWR)
        os.dup2(dev_null, 0)  # stdin
        os.dup2(dev_null, 1)  # stdout
        os.dup2(dev_null, 2)  # stderr
        if dev_null > 2:
            os.close(dev_null)

        # Run the monitoring daemon
        self._run_monitoring_daemon(interval)
        os._exit(0)  # Should never reach here

    def start_supervised(self, interval: int = 10) -> bool:
        """Start the daemon with supervision for proper self-healing.

        This method starts the daemon under supervision which provides:
        - Automatic restart on unexpected failure
        - Exponential backoff to prevent restart storms
        - Heartbeat-based health monitoring
        - Proper cleanup on graceful shutdown

        Args:
            interval: Monitoring interval in seconds

        Returns:
            bool: True if supervision started successfully

        Raises:
            DaemonAlreadyRunningError: If a daemon is already running
        """
        # Prepare daemon command that supervisor will manage
        daemon_command = [
            sys.executable,
            "-c",
            f"""import sys
sys.path.insert(0, '/workspaces/Tmux-Orchestrator')
from tmux_orchestrator.core.monitor import IdleMonitor
from tmux_orchestrator.utils.tmux import TMUXManager

tmux = TMUXManager()
monitor = IdleMonitor(tmux)
monitor._run_monitoring_daemon({interval})
""",
        ]

        # Let supervisor handle all the locking and checking
        success = self.supervisor.start_daemon(daemon_command)
        if not success:
            raise RuntimeError("Failed to start daemon under supervision")

        return success

    def _check_claude_interface(self, target: str, content: str) -> bool:
        """Check if Claude interface is present in pane content.

        Args:
            target: Window target
            content: Pane content

        Returns:
            bool: True if Claude interface is present
        """
        # Import crash detector for interface checking
        from tmux_orchestrator.core.monitoring.crash_detector import CrashDetector

        detector = CrashDetector(self.tmux, self.logger)
        return detector._is_claude_interface_present(content)

    def _log_error(self, message: str) -> None:
        """Log an error message.

        Args:
            message: Error message to log
        """
        self.logger.error(message)

    def _resume_incomplete_recoveries(self) -> None:
        """Resume incomplete PM recoveries after daemon restart."""
        # This would check for incomplete recoveries and resume them
        # For now, just a placeholder
        self.logger.info("Checking for incomplete PM recoveries")

    def _handle_corrupted_pm(self, target: str) -> None:
        """Handle corrupted PM terminal.

        Args:
            target: PM target
        """
        self.logger.warning(f"Handling corrupted PM at {target}")
        self._reset_terminal(target)

    def _get_team_agents(self, session: str) -> list[dict]:
        """Get team agents in a session.

        Args:
            session: Session name

        Returns:
            List of agent info dicts
        """
        agents = []
        try:
            windows = self.tmux.list_windows(session)
            for window in windows:
                window_name = window.get("name", "").lower()
                window_idx = window.get("index", "0")

                # Skip PM windows
                if "pm" in window_name or "manager" in window_name:
                    continue

                agents.append(
                    {
                        "target": f"{session}:{window_idx}",
                        "name": window_name,
                        "type": self._determine_agent_type(window_name),
                    }
                )
        except Exception as e:
            self.logger.error(f"Error getting team agents: {e}")

        return agents

    def _determine_agent_type(self, window_name: str) -> str:
        """Determine agent type from window name.

        Args:
            window_name: Window name

        Returns:
            Agent type string
        """
        name_lower = window_name.lower()
        if "dev" in name_lower:
            return "developer"
        elif "qa" in name_lower or "test" in name_lower:
            return "qa"
        elif "devops" in name_lower or "ops" in name_lower:
            return "devops"
        elif "review" in name_lower:
            return "reviewer"
        else:
            return "agent"

    def _notify_agent(self, target: str, message: str) -> None:
        """Send notification to an agent.

        Args:
            target: Agent target
            message: Message to send
        """
        try:
            self.tmux.send_keys(target, message, literal=True)
            self.tmux.send_keys(target, "Enter")
        except Exception as e:
            self.logger.error(f"Failed to notify agent {target}: {e}")

    def _detect_pane_corruption(self, target: str) -> bool:
        """Detect if pane content is corrupted.

        Args:
            target: Window target

        Returns:
            bool: True if corrupted
        """
        try:
            content = self.tmux.capture_pane(target)
            # Check for binary/control characters
            non_printable_count = sum(1 for c in content if ord(c) < 32 and c not in "\n\r\t")
            return non_printable_count > len(content) * 0.1  # More than 10% non-printable
        except Exception:
            return False

    def _reset_terminal(self, target: str) -> bool:
        """Reset terminal in target window.

        Args:
            target: Window target

        Returns:
            bool: True if successful
        """
        try:
            self.tmux.send_keys(target, "C-c")  # Cancel
            time.sleep(0.5)
            self.tmux.send_keys(target, "reset", literal=True)
            self.tmux.send_keys(target, "Enter")
            return True
        except Exception as e:
            self.logger.error(f"Failed to reset terminal {target}: {e}")
            return False

    def _check_recovery_state(self, state_file: Path) -> None:
        """Check recovery state file and resume incomplete recoveries.

        Args:
            state_file: Path to state file
        """
        if state_file.exists():
            try:
                import json

                with open(state_file) as f:
                    state = json.load(f)
                if state.get("recovering"):
                    self._resume_incomplete_recoveries()
            except Exception as e:
                self.logger.error(f"Error checking recovery state: {e}")

    def stop(self, allow_cleanup: bool = True) -> bool:
        """Stop the idle monitor daemon.

        Args:
            allow_cleanup: If True, allows the daemon to be permanently stopped.
                          Only the tmux-orc CLI should set this to True.
        """
        logger = logging.getLogger("idle_monitor_stop")

        # Try supervisor-based stop first
        if self.supervisor.is_daemon_running():
            logger.info("[STOP] Stopping supervised daemon")
            return self.supervisor.stop_daemon(graceful=allow_cleanup)

        # Fallback to direct process stop for legacy daemons
        if not self.is_running():
            logger.debug("[STOP] Daemon not running - nothing to stop")
            return False

        try:
            with open(self.pid_file) as f:
                pid = int(f.read().strip())

            logger.info(f"[STOP] Stopping daemon PID {pid} (allow_cleanup={allow_cleanup})")

            # Set the cleanup flag if this is an authorized stop
            if allow_cleanup:
                # Create graceful stop file to signal daemon this is an authorized stop
                self.graceful_stop_file.touch()
                logger.debug("[STOP] Created graceful stop file for authorized stop")

            # Send SIGTERM for graceful shutdown
            os.kill(pid, signal.SIGTERM)
            logger.debug(f"[STOP] Sent SIGTERM to PID {pid}")

            # Don't wait for process to stop - return immediately for CLI responsiveness
            # The daemon will handle cleanup gracefully in the background

            # Clean up PID file with proper error handling
            if self.pid_file.exists():
                try:
                    self.pid_file.unlink()
                    logger.debug("[STOP] PID file removed")
                except OSError as e:
                    logger.warning(f"[STOP] Failed to remove PID file: {e}")

            logger.info("[STOP] Daemon stopped successfully")
            return True
        except (OSError, ValueError, FileNotFoundError) as e:
            logger.error(f"[STOP] Failed to stop daemon: {e}")
            return False

    def status(self) -> None:
        """Display monitor status."""
        from rich.console import Console
        from rich.panel import Panel

        console = Console()

        if self.is_running():
            try:
                with open(self.pid_file) as f:
                    pid = int(f.read().strip())
            except (OSError, ValueError) as e:
                console.print(Panel(f"❌ Monitor daemon PID file corrupted: {e}", title="Daemon Status"))
                return

            # Get log info if available
            log_info = ""
            if self.log_file.exists():
                try:
                    stat = self.log_file.stat()
                    log_info = f"\nLog size: {stat.st_size} bytes\nLog file: {self.log_file}"
                except OSError:
                    log_info = f"\nLog file: {self.log_file}"

            # List all session-specific logs
            session_logs = list(self.logs_dir.glob("idle-monitor-*.log"))
            if session_logs:
                log_info += "\n\nSession logs:"
                for log in sorted(session_logs):
                    try:
                        size = log.stat().st_size
                        log_info += f"\n  {log.name}: {size} bytes"
                    except OSError:
                        log_info += f"\n  {log.name}: (unavailable)"

            console.print(
                Panel(
                    f"✓ Monitor is running (PID: {pid})\nNative Python daemon with bulletproof detection{log_info}",
                    title="Monitoring Status",
                    style="green",
                )
            )
        else:
            console.print(
                Panel(
                    "✗ Monitor is not running\nUse 'tmux-orc monitor start' to begin monitoring",
                    title="Monitoring Status",
                    style="red",
                )
            )

    def _run_monitoring_daemon(self, interval: int) -> None:
        """Run the monitoring daemon in a separate process."""
        # Set up logging first so we can use it immediately
        logger = self._setup_daemon_logging()
        logger.info(
            f"[DAEMON START] Native Python monitoring daemon starting (PID: {os.getpid()}, interval: {interval}s)"
        )
        logger.debug(f"[DAEMON START] Log file: {self.log_file}")
        logger.debug(f"[DAEMON START] PID file: {self.pid_file}")

        # CRITICAL: Check for existing daemon BEFORE writing PID file
        # This prevents race condition where multiple daemons write PID files
        existing_pid = self._check_existing_daemon()
        if existing_pid:
            logger.error(f"[DAEMON START] Another daemon already running with PID {existing_pid} - exiting")
            os._exit(1)

        # Acquire startup lock to ensure atomic PID file creation
        if not self._handle_startup_race_condition():
            logger.error("[DAEMON START] Failed to acquire startup lock - another daemon may be starting")
            os._exit(1)

        # Set up signal handlers for graceful shutdown
        def signal_handler(signum: int, frame: Any) -> None:
            logger.debug(f"[SIGNAL] Received signal {signum} in PID {os.getpid()}")
            # Check if this is a graceful stop by looking for the graceful stop file
            is_graceful = self.graceful_stop_file.exists()
            if is_graceful:
                logger.info("[SIGNAL] Graceful stop detected - daemon will not respawn")
                # Clean up the graceful stop file
                try:
                    self.graceful_stop_file.unlink()
                except Exception:
                    pass
            else:
                logger.warning("[SIGNAL] Unexpected termination - daemon may respawn if self-healing is enabled")
            self._cleanup_daemon(signum=signum, is_graceful=is_graceful)
            logger.debug(f"[SIGNAL] Exiting after signal {signum}")
            exit(0)

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        logger.debug(f"[SIGNAL] Signal handlers installed for PID {os.getpid()}")

        # Write PID file atomically
        current_pid = os.getpid()
        if not self._write_pid_file_atomic(current_pid):
            logger.error("[DAEMON START] Failed to write PID file atomically - daemon may not start properly")
            # Release the lock before exiting
            if hasattr(self, "_startup_lock_fd"):
                try:
                    import fcntl

                    fcntl.flock(self._startup_lock_fd, fcntl.LOCK_UN)
                    os.close(self._startup_lock_fd)
                except Exception:
                    pass
            os._exit(1)
        else:
            logger.debug(f"[DAEMON START] PID file written atomically: {self.pid_file}")

        # Release the startup lock now that PID file is written
        if hasattr(self, "_startup_lock_fd"):
            try:
                import fcntl

                fcntl.flock(self._startup_lock_fd, fcntl.LOCK_UN)
                os.close(self._startup_lock_fd)
                logger.debug("[DAEMON START] Released startup lock")

                # Clean up lock file
                if hasattr(self, "_startup_lock_file") and self._startup_lock_file.exists():
                    try:
                        self._startup_lock_file.unlink()
                        logger.debug("[DAEMON START] Cleaned up startup lock file")
                    except OSError as e:
                        logger.debug(f"[DAEMON START] Could not clean up lock file: {e}")
            except Exception as e:
                logger.warning(f"[DAEMON START] Error releasing startup lock: {e}")

        # Initialize restart attempts tracking for the daemon process
        self._restart_attempts: dict[str, datetime] = {}
        # Initialize notification tracking for the daemon process (fixes notification spam)
        # These are intentionally separate from parent process attributes
        self._idle_notifications: dict[str, datetime] = {}  # type: ignore[no-redef]
        self._crash_notifications: dict[str, datetime] = {}  # type: ignore[no-redef]

        # Create TMUXManager instance for this process
        tmux = TMUXManager()

        # Initialize heartbeat for supervisor monitoring
        heartbeat_file = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator/idle-monitor.heartbeat")

        def update_heartbeat():
            """Update heartbeat file to signal daemon is alive."""
            try:
                heartbeat_file.touch()
            except Exception as e:
                logger.warning(f"[HEARTBEAT] Failed to update heartbeat: {e}")

        # Main monitoring loop
        cycle_count = 0
        try:
            while True:
                cycle_count += 1
                start_time = time.time()

                # Update heartbeat for supervisor
                update_heartbeat()

                # Log cycle start with timestamp
                logger.debug(
                    f"[CYCLE {cycle_count}] Starting monitoring cycle at {datetime.now().strftime('%H:%M:%S')}"
                )

                # Discover and monitor agents
                self._monitor_cycle(tmux, logger)

                # Periodic cache cleanup to prevent unbounded growth
                if time.time() - self._last_cache_cleanup > self._cache_cleanup_interval:
                    self._cleanup_terminal_caches(logger)
                    self._last_cache_cleanup = time.time()

                # Calculate sleep time to maintain interval
                elapsed = time.time() - start_time
                sleep_time = max(0, interval - elapsed)

                logger.debug(f"[CYCLE {cycle_count}] Completed in {elapsed:.2f}s, sleeping for {sleep_time:.2f}s")

                if sleep_time > 0:
                    time.sleep(sleep_time)

        except KeyboardInterrupt:
            logger.info("[DAEMON STOP] Monitoring daemon interrupted by KeyboardInterrupt")
        except Exception as e:
            logger.error(f"[DAEMON ERROR] Monitoring daemon error: {e}", exc_info=True)
            # Try to write error to a debug file
            try:
                error_log = self.log_file.parent / "monitor-daemon-error.log"
                with open(error_log, "a") as f:
                    f.write(f"{datetime.now()}: {type(e).__name__}: {e}\n")
                    import traceback

                    traceback.print_exc(file=f)
            except Exception:
                pass
        finally:
            logger.info(f"[DAEMON STOP] Daemon shutting down (PID: {os.getpid()})")
            self._cleanup_daemon()

    def _setup_daemon_logging(self) -> logging.Logger:
        """Set up logging for the daemon process."""
        logger = logging.getLogger("idle_monitor_daemon")
        logger.setLevel(logging.DEBUG)  # Changed to DEBUG for troubleshooting

        # Clear existing handlers
        logger.handlers.clear()

        # File handler for general log (keeping for backward compatibility)
        handler = logging.FileHandler(self.log_file)
        # Include PID in log format for better debugging
        formatter = logging.Formatter(f"%(asctime)s - PID:{os.getpid()} - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Also create general logger for non-session-specific logs
        general_log = self.logs_dir / "idle-monitor-general.log"
        general_handler = logging.FileHandler(general_log)
        general_handler.setFormatter(formatter)

        general_logger = logging.getLogger("idle_monitor_general")
        # Changed to DEBUG for troubleshooting
        general_logger.setLevel(logging.DEBUG)
        general_logger.handlers.clear()
        general_logger.addHandler(general_handler)

        return logger

    def _get_session_logger(self, session_name: str) -> logging.Logger:
        """Get or create a session-specific logger.

        Args:
            session_name: Name of the session

        Returns:
            Logger instance for the session
        """
        # Return cached logger if available
        if session_name in self._session_loggers:
            return self._session_loggers[session_name]

        # Create new session logger
        logger_name = f"idle_monitor_{session_name}"
        session_logger = logging.getLogger(logger_name)
        session_logger.setLevel(logging.INFO)

        # Clear any existing handlers
        session_logger.handlers.clear()

        # Create session-specific log file
        log_file = self.logs_dir / f"idle-monitor-{session_name}.log"
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter(f"%(asctime)s - PID:{os.getpid()} - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        session_logger.addHandler(handler)

        # Cache the logger
        self._session_loggers[session_name] = session_logger

        return session_logger

    def _cleanup_daemon(self, signum: Optional[int] = None, is_graceful: bool = False) -> None:
        """Clean up daemon resources.

        Args:
            signum: Signal number if called from signal handler
            is_graceful: Whether this is a graceful stop (from tmux-orc monitor stop)
        """
        try:
            # Get logger for cleanup logging
            logger = logging.getLogger("idle_monitor_daemon")
            logger.debug(
                f"[CLEANUP] Starting daemon cleanup for PID {os.getpid()}, signal={signum}, graceful={is_graceful}"
            )

            if self.pid_file.exists():
                logger.debug(f"[CLEANUP] Removing PID file: {self.pid_file}")
                try:
                    self.pid_file.unlink()
                    logger.debug("[CLEANUP] PID file removed successfully")
                except OSError as e:
                    logger.error(f"[CLEANUP] Failed to remove PID file: {e}")
            else:
                logger.debug("[CLEANUP] No PID file to remove")

            # Clean up graceful stop file if it exists
            if self.graceful_stop_file.exists():
                try:
                    self.graceful_stop_file.unlink()
                    logger.debug("[CLEANUP] Graceful stop file removed")
                except Exception:
                    pass

            # Log cleanup reason
            if signum == signal.SIGTERM:
                if is_graceful:
                    logger.info("[CLEANUP] Daemon terminated by SIGTERM (graceful stop from tmux-orc)")
                else:
                    logger.warning("[CLEANUP] Daemon terminated by SIGTERM (unexpected termination)")
            elif signum == signal.SIGINT:
                logger.info("[CLEANUP] Daemon terminated by SIGINT (interrupt)")
            elif signum == signal.SIGKILL:
                logger.warning("[CLEANUP] Daemon terminated by SIGKILL (force kill)")
            else:
                logger.info(f"[CLEANUP] Daemon cleanup called (signal={signum})")

            # Self-healing is disabled to prevent multiple daemon spawning issues
            if not is_graceful and signum is not None:
                logger.warning("[CLEANUP] Daemon was terminated unexpectedly - self-healing is disabled")

            logger.debug("[CLEANUP] Daemon cleanup completed")
        except Exception as e:
            # Try to log even if logger fails
            try:
                print(f"[CLEANUP ERROR] Exception during cleanup: {e}")
            except Exception:
                pass

    def _monitor_cycle(self, tmux: TMUXManager, logger: logging.Logger) -> None:
        """Perform one monitoring cycle."""
        try:
            # Use general logger for system-wide events
            general_logger = logging.getLogger("idle_monitor_general")

            # Discover active agents
            agents = self._discover_agents(tmux)

            general_logger.debug(f"Agent discovery complete: found {len(agents)} agents")

            if not agents:
                general_logger.warning("No agents found to monitor")
                # Log available sessions for debugging
                try:
                    sessions = tmux.list_sessions()
                    general_logger.debug(f"Available sessions: {[s['name'] for s in sessions]}")
                except Exception as e:
                    general_logger.error(f"Could not list sessions: {e}")
                return

            general_logger.debug(f"Monitoring agents: {agents}")

            # Initialize notification collection structure for this cycle
            pm_notifications: dict[str, list[str]] = {}

            # First, check all agents for rate limiting
            for target in agents:
                try:
                    content = tmux.capture_pane(target, lines=50)

                    # Check for rate limit message
                    if (
                        "claude usage limit reached" in content.lower()
                        and "your limit will reset at" in content.lower()
                    ):
                        reset_time = extract_rate_limit_reset_time(content)
                        if reset_time:
                            # Calculate sleep duration
                            now = datetime.now(timezone.utc)
                            sleep_seconds = calculate_sleep_duration(reset_time, now)

                            # If sleep_seconds is 0, it means the rate limit is stale/invalid (>4 hours away)
                            if sleep_seconds == 0:
                                logger.warning(
                                    f"Rate limit message appears stale (reset time {reset_time} is >4 hours away). "
                                    f"Ignoring and continuing normal monitoring."
                                )
                                continue

                            # Calculate resume time
                            resume_time = now + timedelta(seconds=sleep_seconds)

                            logger.warning(f"Rate limit detected on agent {target}. Reset time: {reset_time} UTC")

                            # Try to notify PM (may also be rate limited)
                            pm_target = self._find_pm_agent(tmux)
                            if pm_target:
                                # Check if PM has active Claude interface before sending message
                                pm_content = tmux.capture_pane(pm_target, lines=10)
                                if is_claude_interface_present(pm_content):
                                    message = (
                                        f"🚨 RATE LIMIT REACHED: All Claude agents are rate limited.\n"
                                        f"Will reset at {reset_time} UTC.\n\n"
                                        f"The monitoring daemon will pause and resume at {resume_time.strftime('%H:%M')} UTC "
                                        f"(2 minutes after reset for safety).\n"
                                        f"All agents will become responsive after the rate limit resets."
                                    )
                                    try:
                                        tmux.send_message(pm_target, message)
                                        logger.info(f"PM {pm_target} notified about rate limit")
                                    except Exception:
                                        logger.warning("Could not notify PM - may also be rate limited")
                                else:
                                    logger.debug(
                                        f"PM {pm_target} does not have active Claude interface - skipping rate limit notification"
                                    )

                            # Log and sleep
                            logger.debug(
                                f"Rate limit detected. Sleeping for {sleep_seconds} seconds until {reset_time} UTC"
                            )
                            time.sleep(sleep_seconds)

                            # After waking up, notify that monitoring has resumed
                            logger.info("Rate limit period ended, resuming monitoring")
                            if pm_target:
                                # Check if PM has active Claude interface before sending resume message
                                pm_content = tmux.capture_pane(pm_target, lines=10)
                                if is_claude_interface_present(pm_content):
                                    try:
                                        tmux.send_message(
                                            pm_target,
                                            "🎉 Rate limit reset! Monitoring resumed. All agents should now be responsive.",
                                        )
                                    except Exception:
                                        pass
                                else:
                                    logger.debug(
                                        f"PM {pm_target} does not have active Claude interface - skipping resume notification"
                                    )

                            # Return to restart the monitoring cycle
                            return

                except Exception as e:
                    logger.error(f"Error checking rate limit for {target}: {e}")

            # Check for PM recovery need before monitoring agents
            self._check_pm_recovery(tmux, agents, logger)

            # Check for missing agents (track high-water mark per session)
            self._check_missing_agents(tmux, agents, logger, pm_notifications)

            # Monitor each agent normally if no rate limit detected
            for target in agents:
                try:
                    self._check_agent_status(tmux, target, logger, pm_notifications)
                except Exception as e:
                    logger.error(f"Error checking agent {target}: {e}")

            # Check for team-wide idleness and handle PM escalations
            self._check_team_idleness(tmux, agents, logger, pm_notifications)

            # Send all collected notifications at the end of the cycle
            pm_notified = False
            if pm_notifications:
                logger.info(f"Sending collected notifications to {len(pm_notifications)} PMs")
                self._send_collected_notifications(pm_notifications, tmux, logger)
                pm_notified = True

            # If any PM was notified, apply cooldown period
            if pm_notified:
                logger.info(f"PM notification sent - applying {DAEMON_CONTROL_LOOP_COOLDOWN_SECONDS}s cooldown")
                time.sleep(DAEMON_CONTROL_LOOP_COOLDOWN_SECONDS)

        except Exception as e:
            logger.error(f"Error in monitoring cycle: {e}")

    def _discover_agents(self, tmux: TMUXManager) -> list[str]:
        """Discover active agents to monitor."""
        agents = []

        try:
            # Get all tmux sessions
            sessions = tmux.list_sessions()

            for session_info in sessions:
                session_name = session_info["name"]

                # Get windows for this session
                try:
                    windows = tmux.list_windows(session_name)
                    for window_info in windows:
                        # Fix: use 'index' not 'id' - window_info contains index/name/active
                        window_idx = window_info.get("index", "0")
                        target = f"{session_name}:{window_idx}"

                        # Check if window contains an active agent
                        if self._is_agent_window(tmux, target):
                            agents.append(target)

                except Exception:
                    # Skip this session if we can't list windows
                    continue

        except Exception:
            # Return empty list if we can't discover agents
            pass

        return agents

    def _is_agent_window(self, tmux: TMUXManager, target: str) -> bool:
        """Check if a window should be monitored as an agent window.

        This checks window NAME patterns, not content, so we can track
        crashed agents that need recovery.
        """
        try:
            session_name, window_idx = target.split(":")
            windows = tmux.list_windows(session_name)

            # Find the window info for this index
            for window in windows:
                if str(window.get("index", "")) == str(window_idx):
                    window_name = window.get("name", "").lower()

                    # Check if this is an agent window by name pattern
                    # Claude agent windows are named "Claude-{role}"
                    if window_name.startswith("claude-"):
                        return True

                    # Also check for common agent indicators in window name
                    agent_indicators = ["pm", "developer", "qa", "engineer", "devops", "backend", "frontend"]
                    if any(indicator in window_name for indicator in agent_indicators):
                        return True

            return False

        except Exception:
            return False

    def _check_agent_status(
        self, tmux: TMUXManager, target: str, logger: logging.Logger, pm_notifications: dict[str, list[str]]
    ) -> None:
        """Check agent status using improved detection algorithm."""
        try:
            # Get session-specific logger
            session_name = target.split(":")[0]
            session_logger = self._get_session_logger(session_name)

            session_logger.debug(f"Checking status for agent {target}")

            # Step 1: Use polling-based active detection (NEW METHOD)
            snapshots = []
            poll_interval = 0.3  # 300ms
            poll_count = 4  # 1.2s total

            # Take snapshots for change detection
            for i in range(poll_count):
                content = tmux.capture_pane(target, lines=50)
                snapshots.append(content)
                if i < poll_count - 1:
                    time.sleep(poll_interval)

            # Use last snapshot for state detection
            content = snapshots[-1]

            # Step 2: Detect if terminal is actively changing
            is_active = False
            for i in range(1, len(snapshots)):
                # Simple change detection - if content changed significantly, it's active
                if snapshots[i - 1] != snapshots[i]:
                    # Check if change is meaningful (not just cursor blink)
                    changes = sum(1 for a, b in zip(snapshots[i - 1], snapshots[i]) if a != b)
                    session_logger.debug(f"Agent {target} snapshot {i} has {changes} character changes")
                    if changes > 1:
                        is_active = True
                        break

            if not is_active:
                session_logger.debug(f"Agent {target} determined to be idle - no significant changes")

            # Simple activity detection (minimal coupling to Claude Code implementation)
            if not is_active:
                content_lower = content.lower()

                # Check for compaction (robust across Claude Code versions)
                if "compacting conversation" in content_lower:
                    session_logger.debug(f"Agent {target} is compacting conversation")
                    session_logger.debug(f"Agent {target} found thinking indicator: 'Compacting conversation'")
                    session_logger.info(f"Agent {target} appears idle but is compacting - will not mark as idle")
                    is_active = True

                # Check for active processing (ellipsis indicates ongoing work)
                elif "…" in content and any(
                    word in content_lower for word in ["thinking", "pondering", "divining", "musing", "elucidating"]
                ):
                    session_logger.debug(f"Agent {target} is actively processing")
                    is_active = True

            # Step 3: Detect base state from content
            if not is_claude_interface_present(content):
                # No Claude interface - check if crashed
                lines = content.strip().split("\n")
                last_few_lines = [line for line in lines[-5:] if line.strip()]

                # Check for bash prompt
                for line in last_few_lines:
                    if line.strip().endswith(("$", "#", ">", "%")):
                        state = AgentState.CRASHED
                        session_logger.error(f"Agent {target} has crashed - attempting auto-restart")
                        success = self._attempt_agent_restart(tmux, target, session_logger)
                        if not success:
                            session_logger.error(f"Auto-restart failed for {target} - notifying PM")
                            self._notify_crash(tmux, target, logger, pm_notifications)
                        return

                # Otherwise it's an error state
                state = AgentState.ERROR
                session_logger.error(f"Agent {target} in error state - needs recovery")
                self._notify_recovery_needed(tmux, target, session_logger)
                return

            # Step 4: Check Claude state (fresh vs unsubmitted vs active)
            claude_state = detect_claude_state(content)

            if claude_state == "fresh":
                state = AgentState.FRESH
                session_logger.info(f"Agent {target} is FRESH - needs context/briefing")
                # Check if should notify PM about fresh agent
                if should_notify_pm(state, target, self._idle_notifications):
                    self._notify_fresh_agent(tmux, target, session_logger, pm_notifications)
                    # Track notification time with fresh prefix
                    self._idle_notifications[f"fresh_{target}"] = datetime.now()
                return
            elif claude_state == "unsubmitted":
                state = AgentState.MESSAGE_QUEUED
                session_logger.info(f"Agent {target} has unsubmitted message - attempting auto-submit")
                self._try_auto_submit(tmux, target, session_logger)
                return

            # Step 5: Determine if idle or active
            if is_active:
                state = AgentState.ACTIVE
                session_logger.info(f"Agent {target} is ACTIVE")
                # Reset tracking for active agents
                self._reset_agent_tracking(target)
            else:
                state = AgentState.IDLE

                # Intelligent idle detection: newly idle vs continuously idle
                idle_type = self._detect_idle_type(target, content, session_logger)

                if idle_type == "newly_idle":
                    session_logger.info(f"Agent {target} is NEWLY IDLE (just completed work) - notifying PM")
                    # Always notify PM about newly idle agents (they just finished work)
                    self._check_idle_notification(tmux, target, session_logger, pm_notifications)
                    self._idle_notifications[target] = datetime.now()
                elif idle_type == "continuously_idle":
                    session_logger.debug(f"Agent {target} is CONTINUOUSLY IDLE (no recent activity)")
                    # Use cooldown logic for continuously idle agents to prevent spam
                    from tmux_orchestrator.core.monitor_helpers import should_notify_continuously_idle

                    if should_notify_continuously_idle(target, self._idle_notifications):
                        session_logger.info(f"Agent {target} continuously idle - notifying PM (with 5min cooldown)")
                        self._check_idle_notification(tmux, target, session_logger, pm_notifications)
                        self._idle_notifications[target] = datetime.now()
                    else:
                        session_logger.debug(f"Agent {target} continuously idle - notification in cooldown")
                else:  # "unknown" fallback
                    session_logger.info(f"Agent {target} is IDLE (type unknown) - notifying PM")
                    self._check_idle_notification(tmux, target, session_logger, pm_notifications)
                    self._idle_notifications[target] = datetime.now()

        except Exception as e:
            # Use the main logger if session logger is not available
            try:
                session_logger.error(f"Failed to check agent {target}: {e}")
            except NameError:
                logger.error(f"Failed to check agent {target}: {e}")

    def _capture_snapshots(self, tmux: TMUXManager, target: str, count: int, interval: float) -> list[str]:
        """Capture multiple snapshots of terminal content."""
        snapshots = []
        for i in range(count):
            content = tmux.capture_pane(target, lines=50)
            snapshots.append(content)
            if i < count - 1:
                time.sleep(interval)
        return snapshots

    def _reset_agent_tracking(self, target: str) -> None:
        """Reset tracking for active agents."""
        if target in self._idle_agents:
            del self._idle_agents[target]
        if target in self._submission_attempts:
            self._submission_attempts[target] = 0
        if target in self._last_submission_time:
            del self._last_submission_time[target]
        # Reset terminal cache when agent becomes active (fresh start)
        if target in self._terminal_caches:
            del self._terminal_caches[target]

    def _detect_idle_type(self, target: str, current_content: str, logger: logging.Logger) -> str:
        """Detect if agent is newly idle (just finished work) or continuously idle.

        Uses TerminalCache class for efficient change detection to distinguish between:
        - newly_idle: Agent just completed work and became idle (notify immediately)
        - continuously_idle: Agent has been idle with no activity (use cooldown)

        Args:
            target: Agent target identifier
            current_content: Current terminal content
            logger: Logger instance

        Returns:
            "newly_idle", "continuously_idle", or "unknown"
        """
        try:
            # Performance optimization: configurable line count for terminal sampling
            terminal_sample_lines = 10  # Reduced from 100 for better performance

            # Get last N lines for efficiency (terminal activity usually at the end)
            current_lines = current_content.strip().split("\n")
            current_sample = (
                "\n".join(current_lines[-terminal_sample_lines:])
                if len(current_lines) >= terminal_sample_lines
                else current_content
            )

            # Get or create terminal cache for this agent
            if target not in self._terminal_caches:
                self._terminal_caches[target] = TerminalCache()
                logger.debug(f"Created new terminal cache for {target}")

            cache = self._terminal_caches[target]

            # Update cache with current content
            cache.update(current_sample)

            # Get intelligent status from cache
            status = cache.status
            logger.debug(f"Terminal cache status for {target}: {status}")

            return status

        except Exception as e:
            logger.error(f"Error in idle type detection for {target}: {e}")
            # Fallback to unknown on error
            return "unknown"

    def _try_auto_submit(self, tmux: TMUXManager, target: str, logger: logging.Logger) -> None:
        """Try auto-submitting stuck messages with cooldown.

        CRITICAL: Never auto-submit on fresh Claude instances to prevent breaking them.
        """
        current_time = time.time()
        last_attempt = self._last_submission_time.get(target, 0)

        # Check if we've already tried too many times
        attempts = self._submission_attempts.get(target, 0)
        if attempts >= 5:
            logger.debug(f"Skipping auto-submit for {target} - already tried {attempts} times")
            return

        if current_time - last_attempt >= 10:  # 10 second cooldown
            # SAFETY CHECK: Verify this isn't a fresh Claude instance before submitting
            content = tmux.capture_pane(target, lines=50)
            claude_state = detect_claude_state(content)

            if claude_state == "fresh":
                logger.warning(f"PREVENTED auto-submit on fresh Claude instance at {target}")
                return

            logger.info(f"Auto-submitting stuck message for {target} (attempt #{attempts + 1})")

            # Try different submission methods
            if attempts == 0:
                # First try: Just Enter (Claude Code submits with Enter, not Ctrl+Enter)
                tmux.press_enter(target)
            elif attempts == 1:
                # Second try: Move to end of line then Enter
                tmux.press_ctrl_e(target)
                time.sleep(0.1)
                tmux.press_enter(target)
            elif attempts == 2:
                # Third try: Escape (to exit any mode) then Enter
                tmux.press_escape(target)
                time.sleep(0.1)
                tmux.press_enter(target)
            else:
                # Later attempts: Just Enter
                tmux.press_enter(target)

            self._submission_attempts[target] = attempts + 1
            self._last_submission_time[target] = current_time

    def _attempt_agent_restart(self, tmux: TMUXManager, target: str, logger: logging.Logger) -> bool:
        """Detect agent failure and notify PM with one-command restart solution."""
        try:
            # Get restart cooldown tracking
            restart_key = f"restart_{target}"
            now = datetime.now()

            # Check cooldown (5 minutes between notifications)
            if hasattr(self, "_restart_attempts"):
                last_restart = self._restart_attempts.get(restart_key)
                if last_restart and (now - last_restart) < timedelta(minutes=5):
                    logger.debug(f"Restart notification for {target} in cooldown")
                    return False
            else:
                self._restart_attempts = {}

            # Step 1: Detect API error patterns and failure type
            current_content = tmux.capture_pane(target, lines=50)
            api_error_detected = self._detect_api_error_patterns(current_content)

            if api_error_detected:
                error_type = self._identify_error_type(current_content)
                logger.info(f"API error detected for {target}: {error_type}. Notifying PM with one-command fix.")
                failure_reason = f"API error ({error_type})"
            else:
                logger.info(f"Agent failure detected for {target}. Notifying PM with one-command fix.")
                failure_reason = "Agent crash/failure"

            # Step 2: Kill the crashed window to clean up resources
            try:
                logger.info(f"Killing crashed window {target} before notifying PM")
                tmux.kill_window(target)
                logger.info(f"Successfully killed crashed window {target}")
            except Exception as kill_error:
                logger.error(f"Failed to kill crashed window {target}: {kill_error}")
                # Continue with notification even if kill fails

            # Step 3: Send PM notification with ready-to-copy-paste command
            self._send_simple_restart_notification(tmux, target, failure_reason, logger)

            # Track notification time
            self._restart_attempts[restart_key] = now

            return True

        except Exception as e:
            logger.error(f"Exception during restart notification for {target}: {e}")
            return False

    def _detect_api_error_patterns(self, content: str) -> bool:
        """Detect API error patterns in terminal content."""
        content_lower = content.lower()

        # Common API error patterns
        api_error_patterns = [
            # Network and connection errors
            "network error occurred",
            "connection error",
            "connection timed out",
            "connection refused",
            "network timeout",
            "request timeout",
            "socket timeout",
            # API-specific errors
            "api error",
            "rate limit",
            "rate limited",
            "quota exceeded",
            "authentication failed",
            "unauthorized",
            "forbidden",
            "service unavailable",
            "internal server error",
            "bad gateway",
            "gateway timeout",
            # Claude-specific patterns
            "claude api error",
            "anthropic api",
            "model overloaded",
            "server overloaded",
            # Red text indicators (ANSI escape codes for red)
            "\033[31m",  # Red text
            "\033[91m",  # Bright red
            "\u001b[31m",  # Alternative red encoding
        ]

        return any(pattern in content_lower for pattern in api_error_patterns)

    def _identify_error_type(self, content: str) -> str:
        """Identify the specific type of API error for better reporting."""
        content_lower = content.lower()

        if any(pattern in content_lower for pattern in ["network error", "connection", "timeout"]):
            return "Network/Connection"
        elif any(pattern in content_lower for pattern in ["rate limit", "quota"]):
            return "Rate Limiting"
        elif any(pattern in content_lower for pattern in ["authentication", "unauthorized"]):
            return "Authentication"
        elif any(pattern in content_lower for pattern in ["server", "gateway", "service unavailable"]):
            return "Server Error"
        elif any(pattern in content_lower for pattern in ["overloaded", "capacity"]):
            return "Capacity"
        elif "\033[31m" in content or "\033[91m" in content:
            return "Error Output"
        else:
            return "API Error"

    def _send_simple_restart_notification(
        self, tmux: TMUXManager, target: str, reason: str, logger: logging.Logger
    ) -> None:
        """Send simple PM notification about agent failure."""
        try:
            # Find PM target IN THE SAME SESSION
            session_name = target.split(":")[0]
            pm_target = self._find_pm_in_session(tmux, session_name)
            if not pm_target:
                logger.debug(f"No PM found in session {session_name} to notify about agent failure")
                return

            # Don't notify PM about their own issues
            if pm_target == target:
                logger.debug(f"Skipping notification - PM at {target} has their own issue")
                return

            # Get window name from target
            session, window = target.split(":")
            window_name = self._get_window_name(tmux, session, window)

            # Send simple notification
            message = (
                f"🚨 AGENT FAILURE\n\n"
                f"Agent: {target} ({window_name})\n"
                f"Issue: {reason}\n\n"
                f"Please restart this agent and provide the appropriate role prompt."
            )

            # Check if PM has active Claude interface before sending message
            pm_content = tmux.capture_pane(pm_target, lines=10)
            if not is_claude_interface_present(pm_content):
                logger.debug(f"PM {pm_target} does not have active Claude interface - skipping restart notification")
                return

            # Send notification
            success_sent = tmux.send_message(pm_target, message)

            if success_sent:
                logger.info(f"Sent restart notification to PM at {pm_target} for {target}")
            else:
                logger.warning(f"Failed to send restart notification to PM at {pm_target}")

        except Exception as e:
            logger.error(f"Failed to send restart notification: {e}")

    def _notify_recovery_needed(self, tmux: TMUXManager, target: str, logger: logging.Logger) -> None:
        """Notify PM that agent needs recovery."""
        logger.warning(f"Notifying PM that {target} needs recovery")
        session_name = target.split(":")[0]
        pm_target = self._find_pm_in_session(tmux, session_name)
        if pm_target:
            # Check if PM has active Claude interface before sending message
            pm_content = tmux.capture_pane(pm_target, lines=10)
            if not is_claude_interface_present(pm_content):
                logger.debug(f"PM {pm_target} does not have active Claude interface - skipping recovery notification")
                return

            message = f"🔴 AGENT RECOVERY MAY BE NEEDED: {target} is idle and Claude interface is not responding. Please restart this agent if it wasn't intentionally released from duty."
            try:
                tmux.send_message(pm_target, message)
                logger.info(f"Sent recovery notification to PM at {pm_target}")
            except Exception as e:
                logger.error(f"Failed to notify PM: {e}")
        else:
            logger.warning(f"No PM agent found in session {session_name} to notify about recovery")

    def _find_pm_agent(self, tmux: TMUXManager) -> str | None:
        """Find a PM agent to send notifications to."""
        try:
            sessions = tmux.list_sessions()
            for session in sessions:
                windows = tmux.list_windows(session["name"])
                for window in windows:
                    window_name = window.get("name", "").lower()
                    target = f"{session['name']}:{window['index']}"

                    # Check if this looks like a PM window
                    if any(pm_indicator in window_name for pm_indicator in ["pm", "manager", "project"]):
                        # Verify it has Claude interface
                        content = tmux.capture_pane(target, lines=10)
                        if is_claude_interface_present(content):
                            return target
            return None
        except Exception:
            return None

    def _find_pm_window(self, tmux: TMUXManager, session_name: Optional[str] = None) -> Optional[str]:
        """Find PM window by name pattern, regardless of Claude interface status.

        This is used for recovery detection - finds ANY PM window, healthy or crashed.

        Args:
            tmux: TMUXManager instance
            session_name: Optional session to search in. If None, searches all sessions.

        Returns:
            Target string (session:window) if PM window found, None otherwise
        """
        try:
            if session_name:
                # Search specific session
                sessions = [{"name": session_name}]
            else:
                # Search all sessions
                sessions = tmux.list_sessions()

            for session in sessions:
                windows = tmux.list_windows(session["name"])
                for window in windows:
                    window_name = window.get("name", "").lower()

                    # Check for PM window patterns
                    # Claude-pm, Claude-PM, pm, project-manager, etc.
                    pm_patterns = ["claude-pm", "pm", "manager", "project-manager"]
                    if any(pattern in window_name for pattern in pm_patterns):
                        target = f"{session['name']}:{window['index']}"
                        return target

            return None
        except Exception as e:
            logger = self._get_session_logger(session_name or "general")
            logger.error(f"Error finding PM window: {e}")
            return None

    def _should_ignore_crash_indicator(self, indicator: str, content: str, content_lower: str) -> bool:
        """Determine if a crash indicator should be ignored based on context.

        This prevents false positives when PMs are discussing failures/errors
        in normal conversation or reporting status.

        Args:
            indicator: The crash indicator that was found
            content: Full terminal content (original case)
            content_lower: Lowercase version of content

        Returns:
            True if the indicator should be ignored (false positive)
        """
        # Regex patterns that indicate normal PM output, not crashes
        # As recommended in status report lines 99-104
        regex_ignore_contexts = [
            r"test.*failed",
            r"tests?\s+failed",
            r"check.*failed",
            r"Tests failed:",
            r"Build failed:",
            r"unit\s+test.*failed",
            r"integration\s+test.*failed",
            r"test\s+suite.*failed",
            r"failing\s+test",
            r"deployment.*failed",
            r"pipeline.*failed",
            r"job.*failed",
            r"Task failed:",
            r"Failed:",
            r"FAILED:",
            r"\d+\s+tests?\s+failed",  # "3 tests failed"
            r"failed\s+\d+\s+tests?",  # "failed 3 tests"
        ]

        # Check regex patterns for more flexible matching
        for pattern in regex_ignore_contexts:
            if re.search(pattern, content, re.IGNORECASE):
                return True

        # Additional substring patterns for non-regex matches
        safe_contexts = [
            # PM analyzing or reporting errors
            "error occurred",
            "error was",
            "error has been",
            "previous error",
            "fixed the error",
            "resolving error",
            "error in the",
            # Status reports and discussions
            "reported killed",
            "was killed by",
            "process was terminated",
            "has been terminated",
            "connection was lost",
            # Historical references
            "previously failed",
            "had failed",
            "which failed",
            "that failed",
            # Tool output patterns
            "⎿",  # Tool output boundary
            "│",  # Tool output formatting
            "└",  # Tool output formatting
            "├",  # Tool output formatting
        ]

        # Check if indicator appears in a safe context
        for safe_context in safe_contexts:
            if safe_context.lower() in content_lower:
                # Found in safe context - this is likely normal PM output
                return True

        # Additional checks for specific indicators
        if indicator == "killed":
            # Check if it's discussing a killed process vs being killed itself
            kill_contexts = ["process killed", "killed the", "killed by", "was killed", "been killed"]
            for context in kill_contexts:
                if context in content_lower:
                    return True

        if indicator == "terminated":
            # Check if discussing termination vs being terminated
            term_contexts = ["was terminated", "been terminated", "process terminated", "terminated the"]
            for context in term_contexts:
                if context in content_lower:
                    return True

        # FIRST: Check for shell prompts at the very end of content (indicates actual crash)
        # This takes precedence over other patterns
        lines = content.strip().split("\n")
        if lines:
            last_line = lines[-1].strip()
            # Shell prompts that indicate actual crashes
            shell_prompt_patterns = [
                ("bash-", True),  # bash-5.1$ format
                ("zsh:", True),  # zsh: format
                ("$", False),  # Generic $ prompt (check if standalone)
                ("%", False),  # Generic % prompt
                ("#", False),  # Root prompt
            ]

            for pattern, prefix_check in shell_prompt_patterns:
                if prefix_check:
                    # Check if line starts with this pattern (e.g., "bash-5.1$")
                    if last_line.startswith(pattern) and last_line.endswith("$"):
                        return False  # This is a crash
                else:
                    # Check if it's just the prompt character
                    if last_line == pattern:
                        return False  # This is a crash

            # Also check if the specific crash indicator is in a crash line
            if indicator in ["bash-", "$ "] and last_line.startswith("bash-") and "$" in last_line:
                return False  # bash prompt after crash

        # Check if content has active Claude interface markers
        claude_active_patterns = [
            "Human:",
            "Assistant:",
            "You:",
            "I'll",
            "I will",
            "Let me",
            "I can",
            "I understand",
            "tmux-orc",  # PM using tmux-orc commands
            "Checking",  # PM actively checking something
            "Running",  # PM running commands
            "Executing",  # PM executing tasks
        ]

        # If we see active conversation patterns, it's likely not crashed
        for pattern in claude_active_patterns:
            if pattern in content:
                return True

        # Default: don't ignore the indicator
        return False

    def _detect_pm_crash(self, tmux: TMUXManager, session_name: str, logger: logging.Logger) -> tuple[bool, str | None]:
        """Detect if PM has crashed in the given session.

        Returns:
            Tuple of (crashed: bool, pm_target: Optional[str])
            - crashed: True if PM crashed or is unhealthy
            - pm_target: The target string if PM window exists (crashed or healthy)
        """
        try:
            logger.debug(f"Detecting PM crash in session {session_name}")

            # First, check if there's any PM window
            pm_window = self._find_pm_window(tmux, session_name)

            if not pm_window:
                logger.info(f"No PM window found in session {session_name}")
                return (True, None)  # PM is missing entirely

            logger.debug(f"Found PM window at {pm_window}, checking health...")

            # Check if PM has Claude interface
            content = tmux.capture_pane(pm_window, lines=20)

            # Focused crash indicators - only actual process crashes, not tool output
            crash_indicators = [
                "claude: command not found",  # Claude binary missing
                "segmentation fault",  # Process crash
                "core dumped",  # Process crash
                "killed",  # Process killed
                "terminated",  # Process terminated
                "panic:",  # System panic
                "bash-",  # Shell prompt (Claude gone)
                "zsh:",  # Shell prompt (Claude gone)
                "$ ",  # Generic shell prompt (Claude gone)
                "traceback (most recent call last)",  # Python crash
                "modulenotfounderror",  # Import failure
                "process finished with exit code",  # Process died
                "[process completed]",  # Process ended
                "process does not exist",  # Process killed
                "no process found",  # Process terminated
                "broken pipe",  # Communication failure
                "connection lost",  # Connection failure (not tool output)
            ]

            content_lower = content.lower()
            crash_indicator_found = False
            found_indicator = None

            for indicator in crash_indicators:
                if indicator in content_lower:
                    # Context-aware check to prevent false positives
                    if self._should_ignore_crash_indicator(indicator, content, content_lower):
                        logger.debug(f"Ignoring crash indicator '{indicator}' - appears to be normal output")
                        continue
                    logger.warning(f"PM crash indicator found: '{indicator}' in {pm_window}")
                    crash_indicator_found = True
                    found_indicator = indicator
                    break

            # Implement observation period before declaring crash
            if crash_indicator_found:
                current_time = datetime.now()

                # Initialize observation list if needed
                if pm_window not in self._pm_crash_observations:
                    self._pm_crash_observations[pm_window] = []

                # Clean up old observations outside the window
                self._pm_crash_observations[pm_window] = [
                    obs
                    for obs in self._pm_crash_observations[pm_window]
                    if current_time - obs < timedelta(seconds=self._crash_observation_window)
                ]

                # Add current observation
                self._pm_crash_observations[pm_window].append(current_time)

                # Check if we have multiple observations within the window
                observation_count = len(self._pm_crash_observations[pm_window])

                if observation_count < 3:  # Require 3 observations before declaring crash
                    logger.info(
                        f"PM crash indicator '{found_indicator}' observed ({observation_count}/3) "
                        f"in {pm_window} - monitoring for {self._crash_observation_window}s"
                    )
                    return (False, pm_window)  # Don't declare crash yet
                else:
                    logger.error(
                        f"PM crash confirmed after {observation_count} observations "
                        f"within {self._crash_observation_window}s window"
                    )
                    # Clear observations for this PM
                    del self._pm_crash_observations[pm_window]
                    return (True, pm_window)

            # Check if Claude interface is present
            if not is_claude_interface_present(content):
                logger.warning(f"PM at {pm_window} missing Claude interface - likely crashed")
                return (True, pm_window)

            # Enhanced health checks with retry mechanism for reliability
            health_check_attempts = 0
            max_health_attempts = 2

            while health_check_attempts < max_health_attempts:
                if self._check_pm_health(tmux, pm_window, logger):
                    logger.debug(f"PM at {pm_window} passed health check")
                    break

                health_check_attempts += 1
                if health_check_attempts < max_health_attempts:
                    logger.debug("PM health check failed, retrying in 1 second...")
                    time.sleep(1)
            else:
                logger.warning(f"PM at {pm_window} failed {max_health_attempts} health checks")
                return (True, pm_window)

            logger.debug(f"PM at {pm_window} appears healthy")
            return (False, pm_window)

        except Exception as e:
            logger.error(f"Error detecting PM crash: {e}")
            return (True, None)  # Assume crash on error

    def _check_pm_health(
        self, tmux: TMUXManager, pm_target: str, logger: logging.Logger, retry_for_new_pm: bool = False
    ) -> bool:
        """Check if PM is responsive and healthy.

        Args:
            tmux: TMUXManager instance
            pm_target: Target PM window to check
            logger: Logger instance
            retry_for_new_pm: If True, retry with delays for newly spawned PMs
        """
        max_retries = 5 if retry_for_new_pm else 1  # Increased retries for new PMs
        retry_delay = 4 if retry_for_new_pm else 0  # Increased delay for startup time

        for attempt in range(max_retries):
            try:
                # Capture more content to get better view of terminal state
                content = tmux.capture_pane(pm_target, lines=30)
                content_lower = content.lower()

                # Enhanced Claude interface detection - check both strict and lenient patterns
                has_claude_interface = is_claude_interface_present(content)

                # For new PMs, also check for broader indicators of Claude presence
                if retry_for_new_pm and not has_claude_interface:
                    # Additional patterns that indicate Claude is present but starting up
                    claude_startup_patterns = [
                        "loading",
                        "initializing",
                        "starting",
                        "claude --dangerously-skip-permissions",
                        "bypassing permissions",
                        "connecting",
                        "human:",  # Conversation indicators
                        "assistant:",  # Response indicators
                        "claude code",  # Product name
                        "anthropic",  # Company name
                    ]

                    # Check if any startup patterns are present
                    has_startup_indicators = any(pattern in content_lower for pattern in claude_startup_patterns)

                    # If we see startup indicators, treat as potentially healthy and continue retrying
                    if has_startup_indicators and attempt < max_retries - 1:
                        logger.info(
                            f"PM {pm_target} shows Claude startup indicators, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(retry_delay)
                        continue
                    elif has_startup_indicators:
                        # On the last attempt, if we see startup indicators, consider it healthy
                        logger.info(f"PM {pm_target} has Claude startup indicators - considering healthy")
                        has_claude_interface = True

                # Check if Claude interface is present
                if not has_claude_interface:
                    if retry_for_new_pm and attempt < max_retries - 1:
                        logger.info(
                            f"PM {pm_target} Claude interface not ready yet, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(retry_delay)
                        continue
                    else:
                        logger.warning(f"PM {pm_target} missing Claude interface after {attempt + 1} attempts")
                        return False

                # Differentiate error checking based on PM state
                if retry_for_new_pm:
                    # For new PMs, only fail on critical errors during startup
                    critical_errors = [
                        "authentication failed",
                        "network error",
                        "connection refused",
                        "command not found",
                        "permission denied",
                    ]

                    if any(error in content_lower for error in critical_errors):
                        logger.error(f"PM {pm_target} has critical startup error")
                        return False
                else:
                    # Standard error checking for established PMs
                    error_indicators = [
                        "connection lost",
                        "session expired",
                        "rate limited",
                        "authentication failed",
                        "network error",
                        "timeout",
                    ]

                    if any(indicator in content_lower for indicator in error_indicators):
                        logger.warning(f"PM {pm_target} showing error indicators")
                        return False

                logger.debug(f"PM {pm_target} health check passed on attempt {attempt + 1}")
                return True

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Health check attempt {attempt + 1} failed for {pm_target}: {e}, retrying...")
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.error(f"Failed to check PM health for {pm_target} after {max_retries} attempts: {e}")
                    return False

        return False

    def _cleanup_terminal_caches(self, logger: logging.Logger) -> None:
        """Clean up old or excessive terminal caches to prevent memory growth.

        Args:
            logger: Logger instance for diagnostics
        """
        try:
            _current_time = datetime.now()

            # Remove caches older than max age
            aged_targets = []
            for target in list(self._terminal_caches.keys()):
                # Check if cache is stale (no recent updates)
                cache = self._terminal_caches[target]
                if cache.early_value is None and cache.later_value is None:
                    aged_targets.append(target)

            for target in aged_targets:
                del self._terminal_caches[target]
                self._cache_access_times.pop(target, None)

            if aged_targets:
                logger.info(f"Cleaned up {len(aged_targets)} stale terminal caches")

            # If still over limit, remove least recently used entries
            if len(self._terminal_caches) > self._max_cache_entries:
                # Sort by access time (least recently used first)
                sorted_targets = sorted(self._terminal_caches.keys(), key=lambda t: self._cache_access_times.get(t, 0))
                excess_count = len(self._terminal_caches) - self._max_cache_entries

                for i in range(excess_count):
                    target = sorted_targets[i]
                    del self._terminal_caches[target]
                    self._cache_access_times.pop(target, None)

                logger.info(
                    f"Removed {excess_count} least recently used terminal caches (limit: {self._max_cache_entries})"
                )

        except Exception as e:
            logger.error(f"Error during terminal cache cleanup: {e}")

    def is_agent_idle(self, target: str) -> bool:
        """Check if agent is idle using the improved 4-snapshot method."""
        try:
            session, window = target.split(":")

            # Take 4 snapshots of the last line at 300ms intervals
            snapshots = []
            for _ in range(4):
                content = self.tmux.capture_pane(target, lines=1)
                last_line = content.strip().split("\n")[-1] if content else ""
                snapshots.append(last_line)
                time.sleep(0.3)

            # If all snapshots are identical, agent is idle
            return all(line == snapshots[0] for line in snapshots)

        except Exception:
            return False  # If we can't check, assume active

    def _auto_submit_message(self, tmux: TMUXManager, target: str, logger: logging.Logger) -> None:
        """Auto-submit unsubmitted message in Claude prompt."""
        try:
            logger.info(f"Auto-submitting unsubmitted message for {target}")

            # Simply send Enter key to submit the message
            # Claude Code submits with Enter, not complex key sequences
            tmux.press_enter(target)

            logger.info(f"Message submitted for {target}")

        except Exception as e:
            logger.error(f"Failed to auto-submit message for {target}: {e}")

    def _notify_crash(
        self, tmux: TMUXManager, target: str, logger: logging.Logger, pm_notifications: dict[str, list[str]]
    ) -> None:
        """Notify PM about crashed Claude agent."""
        try:
            # Find PM target IN THE SAME SESSION
            session_name = target.split(":")[0]
            session_logger = self._get_session_logger(session_name)
            pm_target = self._find_pm_in_session(tmux, session_name)
            if not pm_target:
                session_logger.warning(f"No PM found in session {session_name} to notify about crash")
                return

            # Get current time for cooldown check
            now = datetime.now()
            crash_key = f"crash_{target}"

            # Check cooldown (5 minutes between crash notifications)
            last_notified = self._crash_notifications.get(crash_key)
            if last_notified and (now - last_notified) < timedelta(minutes=5):
                session_logger.debug(f"Crash notification for {target} in cooldown")
                return

            # Format crash message
            message = (
                f"🚨 AGENT CRASH ALERT:\n\n"
                f"Claude Code has crashed for agent at {target}\n\n"
                f"**RECOVERY ACTIONS NEEDED**:\n"
                f"1. Restart Claude Code in the crashed window\n"
                f"2. Provide system prompt from agent-prompts.yaml\n"
                f"3. Re-assign current tasks\n"
                f"4. Verify agent is responsive\n\n"
                f"Use this command:\n"
                f"• tmux send-keys -t {target} 'claude --dangerously-skip-permissions' Enter"
            )

            # Collect notification instead of sending directly
            self._collect_notification(pm_notifications, session_name, message, tmux)
            session_logger.info(f"Collected crash notification for {target}")
            self._crash_notifications[crash_key] = now

        except Exception as e:
            session_logger.error(f"Failed to collect crash notification: {e}")

    def _notify_fresh_agent(
        self, tmux: TMUXManager, target: str, logger: logging.Logger, pm_notifications: dict[str, list[str]]
    ) -> None:
        """Notify PM about fresh agent that needs context/briefing."""
        try:
            session_name = target.split(":")[0]
            session_logger = self._get_session_logger(session_name)

            session_logger.debug(f"_notify_fresh_agent called for {target}")

            # Find PM target IN THE SAME SESSION
            pm_target = self._find_pm_in_session(tmux, session_name)
            if not pm_target:
                logger.warning(f"No PM found in session {session_name} to notify about fresh agent {target}")
                return

            # Don't notify PM about themselves being fresh
            if pm_target == target:
                logger.debug(f"Skipping self-notification - PM at {pm_target} is the fresh agent")
                return

            # Get window name from target
            session, window = target.split(":")
            window_name = self._get_window_name(tmux, session, window)

            # Send fresh agent notification
            message = (
                f"🆕 FRESH AGENT ALERT:\n\n"
                f"Agent {target} ({window_name}) is a fresh Claude instance that needs context and direction.\n\n"
                f"**ACTIONS NEEDED**:\n"
                f"1. Provide agent role context/briefing\n"
                f"2. Assign initial tasks\n"
                f"3. Verify agent understands their role\n\n"
                f"This agent is ready to work but needs proper initialization."
            )

            # Collect notification instead of sending directly
            self._collect_notification(pm_notifications, session_name, message, tmux)
            logger.info(f"Collected fresh agent notification for {target}")

        except Exception as e:
            logger.error(f"Failed to collect fresh agent notification: {e}")

    def _check_idle_notification(
        self, tmux: TMUXManager, target: str, logger: logging.Logger, pm_notifications: dict[str, list[str]]
    ) -> None:
        """Check if PM should be notified about idle agent."""
        try:
            session_name = target.split(":")[0]
            session_logger = self._get_session_logger(session_name)

            session_logger.debug(f"_check_idle_notification called for {target}")
            # Already initialized in __init__

            now = datetime.now()

            # Track idle state for notification purposes
            if target not in self._idle_agents:
                self._idle_agents[target] = now
                session_logger.debug(f"Started tracking idle state for {target}")
                # Don't return here - continue to check if we should notify immediately

            # No minimum wait time - if agent is idle, PM should know immediately

            # No cooldown needed - if agent is idle, PM should be notified
            # PM will communicate with agent, and if agent becomes active, notifications stop naturally

            # Find PM target IN THE SAME SESSION
            logger.info(f"Looking for PM to notify about idle agent {target}")
            session_name = target.split(":")[0]
            pm_target = self._find_pm_in_session(tmux, session_name)
            if not pm_target:
                logger.warning(f"No PM found in session {session_name} to notify about idle agent {target}")
                return
            logger.info(f"Found PM at {pm_target} to notify about idle agent {target}")

            # Don't notify PM about themselves being idle - only skip self-notifications
            if pm_target == target:
                logger.debug(
                    f"Skipping self-notification - PM at {pm_target} would be notified about their own idle status"
                )
                return

            # Get window name from target
            session, window = target.split(":")
            window_name = self._get_window_name(tmux, session, window)

            # Send idle notification
            message = (
                f"🚨 IDLE AGENT(S) ALERT:\n\n"
                f"Agent {target} ({window_name}) is currently idle and available for work.\n\n"
                f"Please review their status and assign tasks as needed.\n\n"
                f"This is an automated notification from the monitoring system."
            )

            # Collect notification instead of sending directly
            self._collect_notification(pm_notifications, session_name, message, tmux)
            logger.info(f"Collected idle notification for {target}")

        except Exception as e:
            logger.error(f"Failed to collect idle notification: {e}")

    def _is_agent_fresh_or_idle(self, tmux: TMUXManager, target: str) -> bool:
        """Check if agent is fresh (needs context) or idle (not actively working).

        This is used for team idleness detection to determine if escalation is needed.
        """
        try:
            content = tmux.capture_pane(target, lines=50)
            claude_state = detect_claude_state(content)

            # Fresh and idle agents count as "not working" for escalation purposes
            return claude_state in ["fresh", "idle"]
        except Exception:
            # If we can't check, assume they're active
            return False

    def _find_pm_target(self, tmux: TMUXManager) -> str | None:
        """Find PM session dynamically - just use the better implementation."""
        return self._find_pm_agent(tmux)

    def _spawn_pm(
        self,
        tmux: TMUXManager,
        target_session: str,
        window_index: int,
        logger: logging.Logger,
        recovery_context: str = "",
    ) -> str | None:
        """Spawn a PM agent at the specified location.

        Args:
            tmux: TMUXManager instance
            target_session: Session to spawn PM in
            window_index: Window index to use
            logger: Logger instance
            recovery_context: Additional context for recovery scenarios

        Returns:
            PM target string if successful, None if failed
        """
        pm_target = f"{target_session}:{window_index}"

        try:
            # CRITICAL: Kill ALL existing PM windows before spawning new PM
            try:
                windows = tmux.list_windows(target_session)
                pm_windows_killed = 0
                for window in windows:
                    window_name = window.get("name", "").lower()
                    window_idx = window.get("index", "")
                    window_target = f"{target_session}:{window_idx}"

                    # Kill any window that could be a PM (by name pattern or is the target index)
                    if "pm" in window_name or "manager" in window_name or str(window_idx) == str(window_index):
                        logger.info(
                            f"Killing existing PM/target window {window_target} ({window.get('name', 'Unknown')}) before spawning new PM"
                        )
                        tmux.kill_window(window_target)
                        pm_windows_killed += 1

                if pm_windows_killed > 0:
                    logger.info(f"Killed {pm_windows_killed} existing PM windows before spawning new PM")

            except Exception as kill_error:
                logger.warning(f"Error killing existing PM windows: {kill_error}")
                # Continue anyway - we'll try to create the new PM

            # Create new window for PM using subprocess
            import subprocess

            subprocess.run(
                ["tmux", "new-window", "-t", f"{target_session}:{window_index}", "-n", "Claude-pm"], check=True
            )
            logger.info(f"Created PM window at {pm_target}")

            # Start Claude with PM context
            tmux.send_keys(pm_target, "claude --dangerously-skip-permissions", literal=True)
            tmux.send_keys(pm_target, "Enter")

            # Wait for Claude to initialize
            import time

            time.sleep(8)

            # Send PM instruction message
            message = (
                "You're the PM for our team, please run 'tmux-orc context show pm' for more information about your role"
            )

            # Add recovery context if provided
            if recovery_context:
                message += f"\n\n## Recovery Context\n\n{recovery_context}"

            # Wait a moment for Claude to fully initialize before checking interface
            time.sleep(2)
            pm_content = tmux.capture_pane(pm_target, lines=10)
            if is_claude_interface_present(pm_content):
                success = tmux.send_message(pm_target, message)
                if success:
                    logger.info(f"Successfully spawned PM at {pm_target} with instruction")
                    return pm_target
                else:
                    logger.error(f"Failed to send instruction to PM at {pm_target}")
            else:
                logger.warning(f"PM at {pm_target} does not have active Claude interface after spawning")

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create PM window: {e}")
            logger.error(f"Command returncode: {e.returncode}")
            logger.error(f"Command stderr: {e.stderr if hasattr(e, 'stderr') else 'N/A'}")
        except Exception as e:
            logger.error(f"Failed to spawn PM: {e}")
            import traceback

            logger.debug(f"PM spawn traceback: {traceback.format_exc()}")

        return None

    def _check_pm_recovery(self, tmux: TMUXManager, agents: list[str], logger: logging.Logger) -> None:
        """Check if PM needs to be auto-spawned when other agents exist but PM is missing or unhealthy."""
        try:
            # Skip if no agents exist
            if not agents:
                return

            # Group agents by session to focus recovery
            session_counts: dict[str, int] = {}
            for agent in agents:
                session_name = agent.split(":")[0]
                session_counts[session_name] = session_counts.get(session_name, 0) + 1

            # Check each session with agents for PM health
            for session_name, agent_count in session_counts.items():
                session_logger = self._get_session_logger(session_name)
                session_logger.debug(f"🔍 Checking PM health in session {session_name} with {agent_count} agents")

                # Check if any PM in this session is in grace period
                pm_in_grace_period = False
                for pm_target_key, recovery_time in list(self._pm_recovery_timestamps.items()):
                    if pm_target_key.startswith(session_name + ":"):
                        time_since_recovery = datetime.now() - recovery_time
                        if time_since_recovery < timedelta(minutes=self._grace_period_minutes):
                            session_logger.debug(
                                f"PM {pm_target_key} in grace period ({time_since_recovery.total_seconds():.0f}s since recovery)"
                            )
                            pm_in_grace_period = True
                            break
                        else:
                            # Grace period expired, remove from tracking
                            del self._pm_recovery_timestamps[pm_target_key]
                            session_logger.debug(f"Grace period expired for PM {pm_target_key}")

                # Skip health checks if PM is in grace period
                if pm_in_grace_period:
                    session_logger.debug(f"Skipping PM health check for session {session_name} - in grace period")
                    continue

                # Use the new crash detection method
                crashed, pm_target = self._detect_pm_crash(tmux, session_name, session_logger)

                if not crashed:
                    session_logger.debug(f"✅ PM in session {session_name} is healthy, no recovery needed")
                    continue

                # PM has crashed or is missing - trigger recovery
                session_logger.warning(f"🚨 PM crash detected in session {session_name}")

                # Log detailed recovery context with timestamps
                session_logger.info("🔧 Initiating PM recovery process:")
                session_logger.info(f"   - Crashed PM target: {pm_target or 'Missing entirely'}")
                session_logger.info(f"   - Active agents requiring coordination: {agent_count}")
                session_logger.info("   - Recovery mode: Automatic with enhanced retry logic")
                session_logger.info(f"   - Recovery initiated at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f"Session has {agent_count} agents that need a PM")

                # Check recovery cooldown to prevent rapid recovery loops
                if session_name in self._last_recovery_attempt:
                    time_since_last_attempt = datetime.now() - self._last_recovery_attempt[session_name]
                    cooldown_period = timedelta(minutes=self._recovery_cooldown_minutes)

                    if time_since_last_attempt < cooldown_period:
                        remaining_cooldown = cooldown_period - time_since_last_attempt
                        logger.warning(
                            f"Recovery cooldown active for session {session_name}. "
                            f"Waiting {remaining_cooldown.total_seconds():.0f}s before next attempt."
                        )
                        return

                # Record this recovery attempt
                self._last_recovery_attempt[session_name] = datetime.now()

                # Use the new recovery orchestration method
                recovery_success = self._recover_crashed_pm(
                    tmux=tmux,
                    session_name=session_name,
                    crashed_pm_target=pm_target,
                    logger=session_logger,
                    max_retries=3,
                    retry_delay=2,
                )

                if recovery_success:
                    session_logger.info(f"🎉 Successfully recovered PM for session {session_name}")
                    session_logger.info("📈 Recovery metrics:")
                    session_logger.info(f"   - Session agents preserved: {agent_count}")
                    session_logger.info("   - Recovery process completed successfully")
                    session_logger.info("   - PM is healthy and ready for coordination")
                else:
                    logger.error(f"Failed to recover PM for session {session_name} - manual intervention required")

        except Exception as e:
            logger.error(f"Failed to auto-spawn PM: {e}")

    def _recover_crashed_pm(
        self,
        tmux: TMUXManager,
        session_name: str,
        crashed_pm_target: Optional[str],
        logger: logging.Logger,
        max_retries: int = 3,
        retry_delay: int = 2,
    ) -> bool:
        """Orchestrate PM recovery with retries and comprehensive error handling.

        Args:
            tmux: TMUXManager instance
            session_name: Session where PM crashed
            crashed_pm_target: Target of crashed PM window (if exists)
            logger: Logger instance
            max_retries: Maximum recovery attempts
            retry_delay: Delay between retries in seconds

        Returns:
            bool: True if recovery successful, False otherwise
        """
        logger.info(f"Starting PM recovery for session {session_name}")
        logger.info(f"Crashed PM target: {crashed_pm_target or 'None (missing entirely)'}")

        # Step 1: Clean up crashed PM if it exists
        if crashed_pm_target:
            logger.info(f"Cleaning up crashed PM at {crashed_pm_target}")
            try:
                tmux.kill_window(crashed_pm_target)
                logger.info(f"Successfully killed crashed PM window {crashed_pm_target}")
                time.sleep(1)  # Allow cleanup to complete
            except Exception as e:
                logger.error(f"Failed to kill crashed PM: {e}")
                # Continue with recovery attempt anyway

        # Step 2: Find suitable window index for new PM
        try:
            windows = tmux.list_windows(session_name)
            used_indices = {int(w["index"]) for w in windows}
            new_window_index = 1
            while new_window_index in used_indices:
                new_window_index += 1
            logger.info(f"Selected window index {new_window_index} for new PM")
        except Exception as e:
            logger.error(f"Failed to find suitable window index: {e}")
            return False

        # Step 3: Attempt recovery with enhanced retry logic and progressive delays
        progressive_delays = [2, 5, 10]  # Progressive backoff

        for attempt in range(1, max_retries + 1):
            logger.info(f"PM recovery attempt {attempt}/{max_retries}")

            try:
                # Get active agents for context with enhanced session analysis
                agents = self._discover_agents(tmux)
                session_agents = [a for a in agents if a.startswith(f"{session_name}:")]

                # Enhanced recovery context with more detail
                recovery_context = f"""🔄 PM RECOVERY NOTIFICATION:
You are being spawned as the Project Manager after a PM failure was detected and resolved.

📊 SESSION STATUS:
- Session: {session_name}
- Active agents in session: {len(session_agents)}
- Agent targets: {', '.join(session_agents) if session_agents else 'None'}
- Recovery attempt: {attempt}/{max_retries}

🎯 YOUR MISSION:
1. Verify the status of all active agents in this session
2. Check for any pending tasks or blockers
3. Resume project coordination and maintain team momentum
4. Report any issues that need immediate attention

The monitoring daemon has automatically handled the technical recovery.
Please focus on project continuity and team coordination."""

                # Spawn new PM with better error handling
                pm_target = self._spawn_pm(tmux, session_name, new_window_index, logger, recovery_context)

                if pm_target:
                    logger.info(f"PM spawned at {pm_target}, verifying health...")

                    # Give PM extra time to fully initialize before health checks
                    init_wait = min(5 + (attempt - 1) * 2, 12)  # 5s to 12s based on attempt
                    logger.info(f"Waiting {init_wait}s for PM initialization...")
                    time.sleep(init_wait)

                    # Single health check with internal retry logic (more efficient)
                    health_verified = self._check_pm_health(tmux, pm_target, logger, retry_for_new_pm=True)

                    if health_verified:
                        logger.info(f"✅ PM recovery SUCCESSFUL at {pm_target} after {attempt} attempts")

                        # Record recovery timestamp for grace period
                        self._pm_recovery_timestamps[pm_target] = datetime.now()
                        logger.info(f"PM {pm_target} entered {self._grace_period_minutes}-minute grace period")

                        # Enhanced team notification
                        try:
                            self._notify_team_of_pm_recovery(session_name, pm_target)
                            logger.info(f"Team notification sent for recovered PM at {pm_target}")
                        except Exception as notify_error:
                            logger.warning(f"Team notification failed: {notify_error}")

                        # Additional validation: verify PM can receive messages
                        try:
                            test_message = "🔄 PM recovery complete. You are now active."
                            tmux.send_message(pm_target, test_message)
                            logger.debug("Successfully sent test message to recovered PM")
                        except Exception as msg_error:
                            logger.warning(f"Failed to send test message to PM: {msg_error}")

                        return True
                    else:
                        logger.warning(f"❌ Spawned PM at {pm_target} failed all health checks")
                        # Try to clean up failed PM attempt
                        try:
                            tmux.kill_window(pm_target)
                            logger.debug(f"Cleaned up failed PM attempt at {pm_target}")
                        except Exception:
                            pass
                else:
                    logger.error(f"❌ Failed to spawn PM on attempt {attempt}")

            except Exception as e:
                logger.error(f"Recovery attempt {attempt} failed with error: {e}")
                import traceback

                logger.debug(f"Recovery attempt traceback: {traceback.format_exc()}")

            # Progressive retry delay (except on last attempt)
            if attempt < max_retries:
                delay = progressive_delays[min(attempt - 1, len(progressive_delays) - 1)]
                logger.info(f"Waiting {delay} seconds before retry (progressive backoff)...")
                time.sleep(delay)

        logger.error(f"PM recovery FAILED after {max_retries} attempts for session {session_name}")
        return False

    def _notify_team_of_pm_recovery(self, session_name: str, pm_target: str) -> None:
        """Notify team agents about PM recovery.

        Args:
            session_name: Session where recovery occurred
            pm_target: Target of new PM
        """
        logger = self._get_session_logger(session_name)
        try:
            # Get all agents in session
            agents = self._discover_agents(self.tmux)
            team_agents = [a for a in agents if a.startswith(f"{session_name}:") and a != pm_target]

            if not team_agents:
                logger.debug("No team agents to notify about PM recovery")
                return

            logger.info(f"Notifying {len(team_agents)} team agents about PM recovery")

            notification = f"""🔄 PM RECOVERY NOTIFICATION:
The Project Manager has been automatically recovered and is now active at {pm_target}.

📋 RECOVERY STATUS:
- PM failure was detected and resolved by the monitoring daemon
- New PM has been spawned and verified as healthy
- All session agents have been preserved during recovery

🎯 NEXT STEPS:
- Continue with your current tasks
- Report any blockers or status updates to the PM
- No action required from you regarding the recovery

The recovery process is complete and project coordination has resumed."""

            successful_notifications = 0
            failed_notifications = 0
            skipped_notifications = 0

            for agent in team_agents:
                try:
                    # Check if agent has Claude interface before notifying
                    content = self.tmux.capture_pane(agent, lines=10)
                    if is_claude_interface_present(content):
                        result = self.tmux.send_message(agent, notification)
                        if result:
                            logger.debug(f"✅ Notified {agent} about PM recovery")
                            successful_notifications += 1
                        else:
                            logger.warning(f"❌ Failed to send message to {agent} (no result)")
                            failed_notifications += 1
                    else:
                        logger.debug(f"⏭️  Skipped {agent} - no Claude interface")
                        skipped_notifications += 1
                except Exception as e:
                    logger.warning(f"❌ Failed to notify {agent}: {e}")
                    failed_notifications += 1

            # Log comprehensive summary of notification results
            logger.info("📤 Team notification summary:")
            logger.info(f"   - Successfully notified: {successful_notifications} agents")
            logger.info(f"   - Failed notifications: {failed_notifications} agents")
            logger.info(f"   - Skipped (no Claude interface): {skipped_notifications} agents")

            if failed_notifications > 0:
                logger.warning(f"⚠️  {failed_notifications} agents did not receive PM recovery notification")

        except Exception as e:
            logger.error(f"Failed to notify team of PM recovery: {e}")
            import traceback

            logger.debug(f"Team notification traceback: {traceback.format_exc()}")

    def _handle_pm_crash(self, pm_target: str) -> None:
        """Handle detected PM crash.

        Args:
            pm_target: Target of crashed PM
        """
        session_name = pm_target.split(":")[0]
        logger = self._get_session_logger(session_name)

        logger.warning(f"Handling PM crash at {pm_target}")

        # Use the full recovery process
        crashed, _ = self._detect_pm_crash(self.tmux, session_name, logger)
        if crashed:
            self._recover_crashed_pm(
                tmux=self.tmux, session_name=session_name, crashed_pm_target=pm_target, logger=logger
            )

    def _spawn_replacement_pm(self, crashed_target: str, max_retries: int = 3) -> bool:
        """Spawn replacement PM for crashed PM.

        Args:
            crashed_target: Target of crashed PM
            max_retries: Maximum spawn attempts

        Returns:
            bool: True if successful, False otherwise
        """
        session_name = crashed_target.split(":")[0]
        logger = self._get_session_logger(session_name)

        return self._recover_crashed_pm(
            tmux=self.tmux,
            session_name=session_name,
            crashed_pm_target=crashed_target,
            logger=logger,
            max_retries=max_retries,
        )

    def _detect_pane_corruption(self, target: str) -> bool:
        """Detect if pane content is corrupted.

        Args:
            target: Target pane to check

        Returns:
            bool: True if corruption detected
        """
        try:
            content = self.tmux.capture_pane(target, lines=50)

            # Check for binary content or corruption indicators
            corruption_indicators = [
                "\x00",  # Null bytes
                "\xff\xfe",  # BOM markers
                "\x01\x02",  # Control characters
                "\\x",  # Escaped hex in output
            ]

            for indicator in corruption_indicators:
                if indicator in content:
                    return True

            # Check for excessive binary characters
            binary_chars = sum(1 for c in content if ord(c) < 32 and c not in "\n\t\r")
            if len(content) > 0 and binary_chars / len(content) > 0.1:  # >10% binary
                return True

            return False

        except Exception:
            return True  # Assume corruption on error

    def _reset_terminal(self, target: str) -> bool:
        """Reset corrupted terminal.

        Args:
            target: Target pane to reset

        Returns:
            bool: True if reset successful
        """
        try:
            logger = self._get_session_logger(target.split(":")[0])
            logger.info(f"Resetting corrupted terminal at {target}")

            # Send terminal reset sequence
            self.tmux.send_keys(target, "C-c")  # Cancel any running command
            time.sleep(0.5)
            self.tmux.send_keys(target, "reset", literal=True)
            self.tmux.send_keys(target, "Enter")
            time.sleep(2)

            # Check if reset worked
            if not self._detect_pane_corruption(target):
                logger.info(f"Terminal reset successful for {target}")
                return True
            else:
                logger.warning(f"Terminal reset failed for {target}")
                return False

        except Exception as e:
            logger = self._get_session_logger(target.split(":")[0] if ":" in target else "general")
            logger.error(f"Failed to reset terminal {target}: {e}")
            return False

    def _get_active_agents(self) -> list[dict[str, str]]:
        """Get list of active agents for tests.

        Returns:
            List of agent dictionaries with type, session, etc.
        """
        try:
            agents = self._discover_agents(self.tmux)
            result = []

            for agent in agents:
                session_name, window_idx = agent.split(":")
                windows = self.tmux.list_windows(session_name)

                for window in windows:
                    if str(window.get("index", "")) == window_idx:
                        window_name = window.get("name", "").lower()

                        # Determine agent type from window name
                        agent_type = "unknown"
                        if "pm" in window_name or "manager" in window_name:
                            agent_type = "pm"
                        elif "dev" in window_name:
                            agent_type = "developer"
                        elif "qa" in window_name:
                            agent_type = "qa"
                        elif "devops" in window_name:
                            agent_type = "devops"

                        result.append(
                            {
                                "target": agent,
                                "session": session_name,
                                "window": window_idx,
                                "name": window_name,
                                "type": agent_type,
                            }
                        )
                        break

            return result

        except Exception:
            return []

    def _check_missing_agents(
        self,
        tmux: TMUXManager,
        current_agents: list[str],
        logger: logging.Logger,
        pm_notifications: dict[str, list[str]],
    ) -> None:
        """Track agents per session and notify PM when non-PM agents disappear."""
        try:
            # Import the constant here to avoid circular imports
            from tmux_orchestrator.core.monitor_helpers import MISSING_AGENT_GRACE_MINUTES

            # Group current agents by session and cache their info
            current_by_session: dict[str, dict[str, dict[str, str]]] = {}
            for agent in current_agents:
                session_name = agent.split(":")[0]
                if session_name not in current_by_session:
                    current_by_session[session_name] = {}

                # Get agent info and determine if it's a PM
                window_name = self._get_window_name(tmux, session_name, agent.split(":")[1])
                is_pm = self._is_pm_agent(tmux, agent)

                # Only track non-PM agents to avoid false positives
                if not is_pm:
                    current_by_session[session_name][agent] = {
                        "name": window_name,
                        "type": "worker",  # Non-PM agents are workers
                    }

            # Check each session for missing agents
            for session_name, current_agents_dict in current_by_session.items():
                # Initialize session tracking if needed
                if session_name not in self._session_agents:
                    self._session_agents[session_name] = {}

                # Cache new agent info (preserves names even after windows are deleted)
                for agent, info in current_agents_dict.items():
                    if agent not in self._session_agents[session_name]:
                        self._session_agents[session_name][agent] = info
                        logger.info(f"Tracking new agent {agent} ({info['name']}) in session {session_name}")

                # Check for missing agents (only non-PM agents)
                previous_agents = set(self._session_agents[session_name].keys())
                current_agents_set = set(current_agents_dict.keys())
                missing_agents = previous_agents - current_agents_set

                # Check for missing agents (set subtraction)
                missing_agents = previous_agents - current_agents_set

                # Clean up agents that have come back
                for agent in current_agents_set:
                    if agent in self._missing_agent_grace:
                        del self._missing_agent_grace[agent]
                        logger.info(f"Agent {agent} has recovered - removing from grace period tracking")

                if missing_agents:
                    now = datetime.now()

                    # Check grace period for each missing agent
                    agents_to_notify = []
                    for agent in missing_agents:
                        if agent not in self._missing_agent_grace:
                            # First time seeing this agent as missing
                            self._missing_agent_grace[agent] = now
                            logger.info(
                                f"Agent {agent} detected as missing - starting {MISSING_AGENT_GRACE_MINUTES} minute grace period"
                            )
                        else:
                            # Check if grace period has expired
                            time_missing = now - self._missing_agent_grace[agent]
                            if time_missing >= timedelta(minutes=MISSING_AGENT_GRACE_MINUTES):
                                agents_to_notify.append(agent)
                            else:
                                remaining = timedelta(minutes=MISSING_AGENT_GRACE_MINUTES) - time_missing
                                logger.debug(
                                    f"Agent {agent} still in grace period - {remaining.seconds} seconds remaining"
                                )

                    # Only notify if we have agents past their grace period
                    if agents_to_notify:
                        # Find PM in this session to notify
                        pm_target = None
                        for agent in current_agents_set:
                            if self._is_pm_agent(tmux, agent):
                                pm_target = agent
                                break

                        if pm_target:
                            # Import cooldown constant
                            from tmux_orchestrator.core.monitor_helpers import (
                                MISSING_AGENT_NOTIFICATION_COOLDOWN_MINUTES,
                            )

                            # Check cooldown for these specific missing agents
                            notification_key = f"{session_name}:{','.join(sorted(agents_to_notify))}"
                            last_notified = self._missing_agent_notifications.get(notification_key)

                            if last_notified:
                                time_since_notification = now - last_notified
                                if time_since_notification < timedelta(
                                    minutes=MISSING_AGENT_NOTIFICATION_COOLDOWN_MINUTES
                                ):
                                    cooldown_remaining = (
                                        timedelta(minutes=MISSING_AGENT_NOTIFICATION_COOLDOWN_MINUTES)
                                        - time_since_notification
                                    )
                                    logger.debug(
                                        f"Missing agents notification in cooldown - {cooldown_remaining.seconds} seconds remaining"
                                    )
                                    continue

                            # Get display names for missing and current agents
                            missing_display = []
                            for agent in agents_to_notify:
                                display_name = self._get_agent_display_name(tmux, agent)
                                missing_display.append(display_name)

                            current_display = []
                            for agent in current_agents_set:
                                display_name = self._get_agent_display_name(tmux, agent)
                                current_display.append(display_name)

                            missing_list = "\n".join(sorted(missing_display))
                            current_list = "\n".join(sorted(current_display))

                            message = f"""🚨 TEAM MEMBER ALERT:

Missing agents detected in session {session_name}:
{missing_list}

Current team members:
{current_list}

Please review your team plan to determine if these agents are still needed.
If they are needed, restart them with their appropriate briefing.
If they are no longer needed, no action is required.

Use 'tmux list-windows -t {session_name}' to check window status."""

                            try:
                                # Collect notification instead of sending directly
                                self._collect_notification(pm_notifications, session_name, message, tmux)
                                logger.warning(
                                    f"Collected missing agents notification for session {session_name}: {missing_list}"
                                )
                                # Track notification time
                                self._missing_agent_notifications[notification_key] = now
                            except Exception as e:
                                logger.error(f"Error collecting missing agents notification: {e}")
                        else:
                            logger.warning(
                                f"Missing agents {agents_to_notify} in session {session_name} but no PM found to notify"
                            )

        except Exception as e:
            logger.error(f"Error checking missing agents: {e}")

    def _get_agent_display_name(self, tmux: TMUXManager, target: str) -> str:
        """Get a display name for an agent that includes window name and location."""
        try:
            session_name, window_idx = target.split(":")
            windows = tmux.list_windows(session_name)

            for window in windows:
                if str(window.get("index", "")) == str(window_idx):
                    window_name = window.get("name", "Unknown")
                    # Format: "WindowName[session:idx]"
                    return f"{window_name}[{target}]"

            return f"Unknown[{target}]"
        except Exception:
            return target

    def _get_window_name(self, tmux: TMUXManager, session: str, window: str) -> str:
        """Get just the window name for an agent."""
        try:
            windows = tmux.list_windows(session)
            for w in windows:
                if str(w.get("index", "")) == str(window):
                    return w.get("name", "Unknown")
            return "Unknown"
        except Exception:
            return "Unknown"

    def _find_pm_in_session(self, tmux: TMUXManager, session: str) -> str | None:
        """Find healthy PM agent in a specific session."""
        try:
            # First try to find any PM window in the session
            pm_window = self._find_pm_window(tmux, session)
            if not pm_window:
                return None

            # Check if it has active Claude interface
            content = tmux.capture_pane(pm_window, lines=10)
            if is_claude_interface_present(content):
                return pm_window

            # PM window exists but no Claude interface
            logger = self._get_session_logger(session)
            logger.debug(f"PM window {pm_window} exists but has no active Claude interface")
            return None
        except Exception:
            return None

    def _is_pm_agent(self, tmux: TMUXManager, target: str) -> bool:
        """Check if target is a PM agent."""
        try:
            # Simple check: window name contains 'pm' or is identified as PM
            session, window = target.split(":")
            windows = tmux.list_windows(session)
            for w in windows:
                if w.get("index") == window:
                    window_name = w.get("name", "").lower()
                    return "pm" in window_name or "manager" in window_name
            return False
        except Exception:
            return False

    def _collect_notification(
        self, pm_notifications: dict[str, list[str]], session: str, message: str, tmux: TMUXManager
    ) -> None:
        """Collect notification for batching instead of sending immediately.

        Args:
            pm_notifications: Collection dict mapping PM targets to messages
            session: Session name to find PM in
            message: Notification message to collect
            tmux: TMUXManager instance
        """
        # Find PM in the session
        pm_target = self._find_pm_in_session(tmux, session)
        if not pm_target:
            # No PM to notify, discard message
            return

        # Initialize list if needed
        if pm_target not in pm_notifications:
            pm_notifications[pm_target] = []

        # Add message to collection
        pm_notifications[pm_target].append(message)

    def _check_team_idleness(
        self, tmux: TMUXManager, agents: list[str], logger: logging.Logger, pm_notifications: dict[str, list[str]]
    ) -> None:
        """Check if entire team is idle and handle PM escalations."""
        # Group agents by session to track team idleness per session
        session_agents: dict[str, list[str]] = {}
        for agent in agents:
            session = agent.split(":")[0]
            if session not in session_agents:
                session_agents[session] = []
            session_agents[session].append(agent)

        # Check each session/team
        for session, team_agents in session_agents.items():
            # Check if ALL agents in this session are idle or fresh (not actively working)
            # Fresh agents count as "not working" for escalation purposes
            all_idle = all(
                agent in self._idle_agents or self._is_agent_fresh_or_idle(tmux, agent) for agent in team_agents
            )

            if all_idle and team_agents:  # Ensure we have agents to check
                # Find PM for this session - MUST be in the same session!
                pm_target = self._find_pm_in_session(tmux, session)

                # Only if no PM found in session, check if agent is PM by window name
                if not pm_target:
                    for agent in team_agents:
                        if self._is_pm_agent(tmux, agent):
                            pm_target = agent
                            break

                if pm_target:
                    now = datetime.now()

                    # Initialize team idle tracking for this session
                    if session not in self._team_idle_at or self._team_idle_at[session] is None:
                        self._team_idle_at[session] = now
                        logger.info(f"Team in session {session} became idle at {now}")

                    # Calculate elapsed time
                    team_idle_time = self._team_idle_at[session]
                    assert team_idle_time is not None  # Already checked above
                    elapsed = now - team_idle_time
                    elapsed_minutes = int(elapsed.total_seconds() / 60)

                    # Check for escalations
                    for threshold_minutes, (action, message) in sorted(NONRESPONSIVE_PM_ESCALATIONS_MINUTES.items()):
                        if elapsed_minutes >= threshold_minutes:
                            # Check if we've already sent this escalation
                            if pm_target not in self._pm_escalation_history:
                                self._pm_escalation_history[pm_target] = {}

                            if threshold_minutes not in self._pm_escalation_history[pm_target]:
                                # Send escalation
                                if action == DaemonAction.MESSAGE and message:
                                    logger.warning(f"Sending {threshold_minutes}min escalation to PM {pm_target}")
                                    self._collect_notification(pm_notifications, session, message, tmux)
                                    self._pm_escalation_history[pm_target][threshold_minutes] = now

                                elif action == DaemonAction.KILL:
                                    logger.critical(
                                        f"PM {pm_target} unresponsive for {threshold_minutes}min - killing PM"
                                    )
                                    try:
                                        # Kill the PM window
                                        tmux.kill_window(pm_target)
                                        logger.info(f"Killed unresponsive PM {pm_target}")

                                        # Clear escalation history for this PM
                                        if pm_target in self._pm_escalation_history:
                                            del self._pm_escalation_history[pm_target]

                                        # Reset team idle tracking for this session
                                        self._team_idle_at[session] = None

                                        # The daemon's PM recovery will automatically spawn a new PM
                                    except Exception as e:
                                        logger.error(f"Failed to kill PM {pm_target}: {e}")
                                        # Only record this in history if kill failed
                                        if pm_target not in self._pm_escalation_history:
                                            self._pm_escalation_history[pm_target] = {}
                                        self._pm_escalation_history[pm_target][threshold_minutes] = now
            else:
                # Team is not all idle - reset tracking for this session
                if session in self._team_idle_at and self._team_idle_at[session] is not None:
                    logger.info(f"Team in session {session} is active again")
                    self._team_idle_at[session] = None

                    # Clear escalation history for PMs in this session
                    for agent in team_agents:
                        if agent in self._pm_escalation_history:
                            del self._pm_escalation_history[agent]

    def _send_collected_notifications(
        self, pm_notifications: dict[str, list[str]], tmux: TMUXManager, logger: logging.Logger
    ) -> None:
        """Send all collected notifications as consolidated reports to PMs.

        Args:
            pm_notifications: Collection dict mapping PM targets to messages
            tmux: TMUXManager instance
            logger: Logger instance
        """
        for pm_target, messages in pm_notifications.items():
            if not messages:
                continue

            # Build consolidated report
            timestamp = datetime.now().strftime("%H:%M:%S UTC")
            report_header = f"🔔 MONITORING REPORT - {timestamp}\n"

            # Group messages by type
            crashed_agents = []
            fresh_agents = []
            idle_agents = []
            missing_agents = []
            other_messages = []

            for msg in messages:
                if "CRASH" in msg or "FAILURE" in msg:
                    crashed_agents.append(msg)
                elif "FRESH AGENT ALERT" in msg:
                    fresh_agents.append(msg)
                elif "IDLE" in msg:
                    idle_agents.append(msg)
                elif "MISSING" in msg or "TEAM MEMBER ALERT" in msg:
                    missing_agents.append(msg)
                else:
                    other_messages.append(msg)

            # Build consolidated message
            report_parts = [report_header]

            if crashed_agents:
                report_parts.append("\n🚨 CRASHED AGENTS:")
                for msg in crashed_agents:
                    # Extract agent info from message
                    if "Agent: " in msg:
                        agent_line = [line for line in msg.split("\n") if line.startswith("Agent: ")][0]
                        report_parts.append(f"- {agent_line}")
                    elif "agent at " in msg:
                        import re

                        match = re.search(r"agent at ([^\s]+)", msg)
                        if match:
                            report_parts.append(f"- {match.group(1)}")

            if fresh_agents:
                report_parts.append("\n🆕 FRESH AGENTS (Need Context):")
                for msg in fresh_agents:
                    # Extract agent info
                    if "Agent " in msg and " (" in msg:
                        import re

                        match = re.search(r"Agent ([^\s]+) \(([^)]+)\)", msg)
                        if match:
                            report_parts.append(f"- {match.group(1)} ({match.group(2)})")

            if idle_agents:
                report_parts.append("\n⚠️ IDLE AGENTS:")
                for msg in idle_agents:
                    # Extract agent info
                    if "Agent " in msg and " (" in msg:
                        import re

                        match = re.search(r"Agent ([^\s]+) \(([^)]+)\)", msg)
                        if match:
                            report_parts.append(f"- {match.group(1)} ({match.group(2)})")

            if missing_agents:
                report_parts.append("\n📍 MISSING AGENTS:")
                for msg in missing_agents:
                    # Extract missing agents list
                    if "Missing agents detected" in msg:
                        lines = msg.split("\n")
                        for i, line in enumerate(lines):
                            if "Missing agents detected" in line and i + 1 < len(lines):
                                report_parts.append(f"- {lines[i + 1]}")
                                break

            if other_messages:
                report_parts.append("\n📋 OTHER NOTIFICATIONS:")
                for msg in other_messages:
                    # Get first meaningful line
                    first_line = msg.strip().split("\n")[0]
                    if first_line:
                        report_parts.append(f"- {first_line}")

            report_parts.append("\nAs the PM, please review and take appropriate action.")

            # Check if PM has active Claude interface before sending consolidated report
            pm_content = tmux.capture_pane(pm_target, lines=10)
            if not is_claude_interface_present(pm_content):
                logger.debug(f"PM {pm_target} does not have active Claude interface - skipping consolidated report")
                continue

            # Send consolidated report
            consolidated_message = "\n".join(report_parts)
            try:
                success = tmux.send_message(pm_target, consolidated_message)
                if success:
                    logger.info(f"Sent consolidated report to PM at {pm_target} with {len(messages)} notifications")
                else:
                    logger.error(f"Failed to send consolidated report to PM at {pm_target}")
            except Exception as e:
                logger.error(f"Error sending consolidated report to {pm_target}: {e}")

    def _check_claude_interface(self, target: str, content: str) -> bool:
        """Check if Claude interface is present in pane content.

        Args:
            target: Window target
            content: Pane content

        Returns:
            bool: True if Claude interface is present
        """
        # Import crash detector for interface checking
        from tmux_orchestrator.core.monitoring.crash_detector import CrashDetector

        detector = CrashDetector(self.tmux, self.logger)
        return detector._is_claude_interface_present(content)

    def _log_error(self, message: str) -> None:
        """Log an error message.

        Args:
            message: Error message to log
        """
        self.logger.error(message)

    def _resume_incomplete_recoveries(self) -> None:
        """Resume incomplete PM recoveries after daemon restart."""
        # This would check for incomplete recoveries and resume them
        # For now, just a placeholder
        self.logger.info("Checking for incomplete PM recoveries")

    def _handle_corrupted_pm(self, target: str) -> None:
        """Handle corrupted PM terminal.

        Args:
            target: PM target
        """
        self.logger.warning(f"Handling corrupted PM at {target}")
        self._reset_terminal(target)

    def _get_team_agents(self, session: str) -> list[dict]:
        """Get team agents in a session.

        Args:
            session: Session name

        Returns:
            List of agent info dicts
        """
        agents = []
        try:
            windows = self.tmux.list_windows(session)
            for window in windows:
                window_name = window.get("name", "").lower()
                window_idx = window.get("index", "0")

                # Skip PM windows
                if "pm" in window_name or "manager" in window_name:
                    continue

                agents.append(
                    {
                        "target": f"{session}:{window_idx}",
                        "name": window_name,
                        "type": self._determine_agent_type(window_name),
                    }
                )
        except Exception as e:
            self.logger.error(f"Error getting team agents: {e}")

        return agents

    def _determine_agent_type(self, window_name: str) -> str:
        """Determine agent type from window name.

        Args:
            window_name: Window name

        Returns:
            Agent type string
        """
        name_lower = window_name.lower()
        if "dev" in name_lower:
            return "developer"
        elif "qa" in name_lower or "test" in name_lower:
            return "qa"
        elif "devops" in name_lower or "ops" in name_lower:
            return "devops"
        elif "review" in name_lower:
            return "reviewer"
        else:
            return "agent"

    def _notify_agent(self, target: str, message: str) -> None:
        """Send notification to an agent.

        Args:
            target: Agent target
            message: Message to send
        """
        try:
            self.tmux.send_keys(target, message, literal=True)
            self.tmux.send_keys(target, "Enter")
        except Exception as e:
            self.logger.error(f"Failed to notify agent {target}: {e}")

    def _detect_pane_corruption(self, target: str) -> bool:
        """Detect if pane content is corrupted.

        Args:
            target: Window target

        Returns:
            bool: True if corrupted
        """
        try:
            content = self.tmux.capture_pane(target)
            # Check for binary/control characters
            non_printable_count = sum(1 for c in content if ord(c) < 32 and c not in "\n\r\t")
            return non_printable_count > len(content) * 0.1  # More than 10% non-printable
        except Exception:
            return False

    def _reset_terminal(self, target: str) -> bool:
        """Reset terminal in target window.

        Args:
            target: Window target

        Returns:
            bool: True if successful
        """
        try:
            self.tmux.send_keys(target, "C-c")  # Cancel
            time.sleep(0.5)
            self.tmux.send_keys(target, "reset", literal=True)
            self.tmux.send_keys(target, "Enter")
            return True
        except Exception as e:
            self.logger.error(f"Failed to reset terminal {target}: {e}")
            return False

    def _check_recovery_state(self, state_file: Path) -> None:
        """Check recovery state file and resume incomplete recoveries.

        Args:
            state_file: Path to state file
        """
        if state_file.exists():
            try:
                import json

                with open(state_file) as f:
                    state = json.load(f)
                if state.get("recovering"):
                    self._resume_incomplete_recoveries()
            except Exception as e:
                self.logger.error(f"Error checking recovery state: {e}")


class AgentMonitor:
    """Enhanced agent monitor with bulletproof idle detection and recovery."""

    def __init__(self, config: Config, tmux: TMUXManager):
        self.config = config
        self.tmux = tmux
        self.idle_monitor = IdleMonitor(tmux)

        # Set up log file path
        project_dir = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator")
        project_dir.mkdir(exist_ok=True)
        logs_dir = project_dir / "logs"
        logs_dir.mkdir(exist_ok=True)
        self.log_file = logs_dir / "agent-monitor.log"

        self.logger = self._setup_logging()
        self.agent_status: dict[str, AgentHealthStatus] = {}

        # Health check configuration
        self.heartbeat_interval = config.get("monitoring.heartbeat_interval", 30)
        self.response_timeout = config.get("monitoring.response_timeout", 60)
        self.max_failures = config.get("monitoring.max_failures", 3)
        self.recovery_cooldown = config.get("monitoring.recovery_cooldown", 300)

        # Track recent recovery attempts
        self.recent_recoveries: dict[str, datetime] = {}

    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the monitor."""
        logger = logging.getLogger("agent_monitor")
        logger.setLevel(logging.INFO)

        # Clear existing handlers
        logger.handlers.clear()

        # Log to file
        log_file = self.log_file
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter(f"%(asctime)s - PID:{os.getpid()} - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def register_agent(self, target: str) -> None:
        """Register an agent for monitoring."""
        now = datetime.now()
        self.agent_status[target] = AgentHealthStatus(
            target=target,
            last_heartbeat=now,
            last_response=now,
            consecutive_failures=0,
            is_responsive=True,
            last_content_hash="",
            status="healthy",
            is_idle=False,
            activity_changes=0,
        )
        self.logger.info(f"Registered agent for monitoring: {target}")

    def unregister_agent(self, target: str) -> None:
        """Remove agent from monitoring."""
        if target in self.agent_status:
            del self.agent_status[target]
            self.logger.info(f"Unregistered agent from monitoring: {target}")

    def check_agent_health(self, target: str) -> AgentHealthStatus:
        """Check agent health using improved idle detection."""
        if target not in self.agent_status:
            self.register_agent(target)

        status = self.agent_status[target]
        now = datetime.now()

        try:
            # Use the bulletproof idle detection
            is_idle = self.idle_monitor.is_agent_idle(target)
            status.is_idle = is_idle

            # Capture current content for change detection
            content = self.tmux.capture_pane(target, lines=50)
            content_hash = str(hash(content))

            # Track activity changes
            if content_hash != status.last_content_hash:
                status.last_heartbeat = now
                status.last_content_hash = content_hash
                status.activity_changes += 1

            # Enhanced responsiveness check
            is_responsive = self._check_agent_responsiveness(target, content, is_idle)

            if is_responsive:
                status.last_response = now
                status.consecutive_failures = 0
                status.is_responsive = True
                status.status = "healthy"
            else:
                status.consecutive_failures += 1
                status.is_responsive = False

                # Determine status based on failure patterns
                time_since_response = now - status.last_response
                if self._has_critical_errors(content):
                    status.status = "critical"
                elif time_since_response > timedelta(seconds=self.response_timeout * 2):
                    status.status = "critical"
                elif time_since_response > timedelta(seconds=self.response_timeout):
                    status.status = "warning"
                elif status.consecutive_failures >= self.max_failures:
                    status.status = "unresponsive"
                else:
                    status.status = "warning"

            self.agent_status[target] = status

        except Exception as e:
            self.logger.error(f"Error checking health for {target}: {e}")
            status.consecutive_failures += 1
            status.status = "critical"

        return status

    def _check_agent_responsiveness(self, target: str, content: str, is_idle: bool) -> bool:
        """Enhanced responsiveness check."""
        # If agent is actively working, it's responsive
        if not is_idle:
            return True

        # Check for normal Claude interface elements
        if self._has_normal_claude_interface(content):
            return True

        # Check for error conditions
        if self._has_critical_errors(content):
            return False

        # If idle but with normal interface, it's responsive
        return True

    def _has_normal_claude_interface(self, content: str) -> bool:
        """Check if content shows normal Claude interface."""
        # Use the helper function from monitor_helpers
        return is_claude_interface_present(content)

    def _has_critical_errors(self, content: str) -> bool:
        """Check for critical error states."""
        # Use the helper functions from monitor_helpers
        from tmux_orchestrator.core.monitor_helpers import _has_crash_indicators, _has_error_indicators

        return _has_crash_indicators(content) or _has_error_indicators(content)

    def should_attempt_recovery(self, target: str, status: AgentHealthStatus) -> bool:
        """Determine if recovery should be attempted."""
        # Don't recover if recently recovered
        if target in self.recent_recoveries:
            time_since_recovery = datetime.now() - self.recent_recoveries[target]
            if time_since_recovery < timedelta(seconds=self.recovery_cooldown):
                return False

        # Recover if critical with multiple failures
        if status.status == "critical" and status.consecutive_failures >= self.max_failures:
            return True

        # Recover if unresponsive for too long
        time_since_response = datetime.now() - status.last_response
        if time_since_response > timedelta(seconds=self.response_timeout * 3):
            return True

        return False

    def attempt_recovery(self, target: str) -> bool:
        """Attempt to recover an unresponsive agent."""
        self.logger.warning(f"Attempting recovery for agent: {target}")

        try:
            # Use the CLI restart command
            _result = subprocess.run(
                ["tmux-orchestrator", "agent", "restart", target],
                capture_output=True,
                text=True,
                check=True,
            )

            # Mark recovery attempt
            self.recent_recoveries[target] = datetime.now()

            # Reset agent status after successful restart
            if target in self.agent_status:
                now = datetime.now()
                self.agent_status[target].last_response = now
                self.agent_status[target].last_heartbeat = now
                self.agent_status[target].consecutive_failures = 0
                self.agent_status[target].status = "healthy"
                self.agent_status[target].is_responsive = True
                self.agent_status[target].activity_changes = 0

            self.logger.info(f"Successfully recovered agent: {target}")
            return True

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to recover agent {target}: {e.stderr}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error recovering agent {target}: {e}")
            return False

    def monitor_all_agents(self) -> dict[str, AgentHealthStatus]:
        """Monitor all registered agents and return their status."""
        results = {}

        for target in list(self.agent_status.keys()):
            try:
                status = self.check_agent_health(target)
                results[target] = status

                # Attempt recovery if needed
                if self.should_attempt_recovery(target, status):
                    recovery_success = self.attempt_recovery(target)
                    if recovery_success:
                        # Re-check status after recovery
                        status = self.check_agent_health(target)
                        results[target] = status

            except Exception as e:
                self.logger.error(f"Error monitoring agent {target}: {e}")

        return results

    def get_unhealthy_agents(self) -> list[tuple[str, AgentHealthStatus]]:
        """Get list of agents that are not healthy."""
        unhealthy = []
        for target, status in self.agent_status.items():
            if status.status != "healthy":
                unhealthy.append((target, status))
        return unhealthy

    def get_monitoring_summary(self) -> dict[str, int]:
        """Get a summary of monitoring status."""
        total_agents = len(self.agent_status)
        healthy = sum(1 for s in self.agent_status.values() if s.status == "healthy")
        warning = sum(1 for s in self.agent_status.values() if s.status == "warning")
        critical = sum(1 for s in self.agent_status.values() if s.status == "critical")
        unresponsive = sum(1 for s in self.agent_status.values() if s.status == "unresponsive")
        idle = sum(1 for s in self.agent_status.values() if s.is_idle)

        return {
            "total_agents": total_agents,
            "healthy": healthy,
            "warning": warning,
            "critical": critical,
            "unresponsive": unresponsive,
            "idle": idle,
            "recent_recoveries": len(self.recent_recoveries),
        }
