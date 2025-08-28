"""Refactored IdleMonitor using modular components for better maintainability."""

import logging
import os
import re
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.utils.tmux import TMUXManager

from .agent_discovery import AgentDiscovery
from .daemon import DaemonAlreadyRunningError, DaemonManager
from .health_checker import HealthChecker
from .idle_detector import IdleDetector
from .notifier import MonitorNotifier
from .recovery_manager import RecoveryManager
from .supervisor import SupervisorManager
from .terminal_cache import TerminalCache


class IdleMonitor:
    """Monitor with 100% accurate idle detection using native Python daemon.

    This class implements a singleton pattern to prevent multiple monitor instances
    from being created, which could lead to multiple daemons running concurrently.

    Refactored to use modular components following SOLID principles while maintaining
    backwards compatibility with the original interface.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, tmux: TMUXManager, config: Config | None = None):
        """Ensure only one instance of IdleMonitor exists (singleton pattern)."""
        if cls._instance is None:
            with cls._lock:
                # Double-check locking pattern
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, tmux: TMUXManager, config: Config | None = None) -> None:
        """Initialize the IdleMonitor with comprehensive agent tracking and daemon management.

        Sets up a singleton monitoring system that tracks agent activity, manages PM recovery,
        implements intelligent caching for terminal content analysis, and provides daemon
        lifecycle management with self-healing capabilities.

        Args:
            tmux: TMUXManager instance for TMUX session communication and agent discovery.
            config: Optional Config instance for customization. If None, loads default.
        """
        # Only initialize once
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self.tmux = tmux

        # Use configurable directory for storage
        if config is None:
            config = Config.load()
        self.config = config
        project_dir = config.orchestrator_base_dir
        project_dir.mkdir(parents=True, exist_ok=True)
        logs_dir = project_dir / "logs"
        logs_dir.mkdir(exist_ok=True)

        # Initialize file paths (maintaining original interface)
        self.pid_file = project_dir / "idle-monitor.pid"
        self.log_file = logs_dir / "idle-monitor.log"
        self.logs_dir = logs_dir
        self.graceful_stop_file = project_dir / "idle-monitor.graceful"

        # Initialize modular components
        self.daemon_manager = DaemonManager(config)
        self.health_checker = HealthChecker()
        self.idle_detector = IdleDetector()
        self.notifier = MonitorNotifier()
        self.recovery_manager = RecoveryManager()
        self.supervisor_manager = SupervisorManager(config)
        self.agent_discovery = AgentDiscovery()

        # Initialize state tracking (maintaining original behavior)
        self._pm_recovery_timestamps: dict[str, datetime] = {}
        self._last_recovery_attempt: dict[str, datetime] = {}
        self._idle_agents: dict[str, datetime] = {}
        self._idle_notifications: dict[str, datetime] = {}
        self._terminal_caches: dict[str, TerminalCache] = {}
        self._grace_period_minutes = 3
        self._recovery_cooldown_minutes = 5

        # Status tracking
        self._last_cache_cleanup = datetime.now()
        self._cache_cleanup_interval_hours = 1

        # Message queues
        self._pm_message_queues: dict[str, list[str]] = {}

    def is_running(self) -> bool:
        """Check if monitor daemon is running with robust validation."""
        return self.daemon_manager.is_running()

    def start(self, interval: int = 10) -> int:
        """Start the native Python monitor daemon with strict singleton enforcement.

        Raises:
            DaemonAlreadyRunningError: If a valid daemon is already running
            RuntimeError: If daemon startup fails for other reasons
        """
        # Handle startup race condition using daemon manager
        if not self.daemon_manager.handle_startup_race_condition():
            existing_pid = self.daemon_manager.check_existing_daemon()
            if existing_pid:
                raise DaemonAlreadyRunningError(existing_pid, self.pid_file)
            else:
                raise RuntimeError("Daemon startup failed - another process may have started concurrently")

        # Double-check no daemon exists
        existing_pid = self.daemon_manager.check_existing_daemon()
        if existing_pid:
            self.daemon_manager.release_startup_lock()
            raise DaemonAlreadyRunningError(existing_pid, self.pid_file)

        # Fork to create daemon (proper daemonization)
        pid = os.fork()
        if pid > 0:
            # Parent process - wait for child to write PID file
            for _ in range(50):  # 5 second timeout
                if self.pid_file.exists():
                    break
                time.sleep(0.1)

            # Release lock in parent after PID file is written
            self.daemon_manager.release_startup_lock()
            return pid

        # Child process - become daemon
        os.setsid()  # Create new session

        # Fork again to prevent zombie processes
        pid = os.fork()
        if pid > 0:
            os._exit(0)  # Exit first child

        # Grandchild - the actual daemon
        # Redirect file descriptors to /dev/null
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
        """Start the daemon with supervision for proper self-healing."""
        return self.supervisor_manager.start_supervised_daemon(interval)

    def stop(self, allow_cleanup: bool = True) -> bool:
        """Stop the running daemon."""
        return self.daemon_manager.stop_daemon()

    def status(self) -> None:
        """Display daemon status information."""
        if self.is_running():
            try:
                with open(self.pid_file) as f:
                    pid = int(f.read().strip())
                print(f"Monitor daemon is running (PID: {pid})")
            except (OSError, ValueError):
                print("Monitor daemon is running (PID file corrupted)")
        else:
            print("Monitor daemon is not running")

    def is_agent_idle(self, target: str) -> bool:
        """Check if agent is idle using the improved 4-snapshot method."""
        return self.idle_detector.is_agent_idle(self.tmux, target)

    def _run_monitoring_daemon(self, interval: int) -> None:
        """Run the main monitoring daemon loop."""
        # Write PID file
        current_pid = os.getpid()
        if not self.daemon_manager.write_pid_file_atomic(current_pid):
            # Failed to write PID file - another daemon may have started
            return

        # Release startup lock after successful PID file write
        self.daemon_manager.release_startup_lock()

        # Set up daemon logging
        logger = self._setup_daemon_logging()
        logger.info(f"Monitor daemon started with PID {current_pid}")

        # Set up signal handlers for graceful shutdown
        def cleanup_handler(signum, frame):
            self._cleanup_daemon(signum, is_graceful=True)

        signal.signal(signal.SIGTERM, cleanup_handler)
        signal.signal(signal.SIGINT, cleanup_handler)

        try:
            # Main monitoring loop
            while True:
                if self._check_if_paused():
                    logger.info("Monitor is paused, sleeping...")
                    time.sleep(interval)
                    continue

                # Check for graceful stop flag
                if self.graceful_stop_file.exists():
                    logger.info("Graceful stop flag detected, shutting down")
                    break

                # Run monitoring cycle
                self._monitor_cycle(self.tmux, logger)

                # Sleep until next cycle
                time.sleep(interval)

        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down gracefully")
        except Exception as e:
            logger.error(f"Daemon error: {e}")
        finally:
            self._cleanup_daemon(is_graceful=True)

    def _monitor_cycle(self, tmux: TMUXManager, logger: logging.Logger) -> None:
        """Run a single monitoring cycle."""
        try:
            # Check for duplicate daemon processes and resolve conflicts
            self._check_and_resolve_daemon_conflicts(logger)

            # Discover active agents
            agents = self.agent_discovery.discover_agents(tmux)

            if not agents:
                logger.debug("No agents found to monitor")
                return

            # Track notifications for batching
            pm_notifications: dict[str, list[str]] = {}

            # Check each agent's status
            for target in agents:
                try:
                    self.health_checker.check_agent_status(tmux, target, logger, pm_notifications)
                except Exception as e:
                    logger.error(f"Error checking agent {target}: {e}")

            # Send collected notifications
            self.notifier.send_collected_notifications(tmux, pm_notifications, logger)

            # Process queued PM messages
            self.notifier.process_pm_message_queues(tmux, logger)

            # Check for PM recovery needs
            self.recovery_manager.check_pm_recovery(tmux, agents, self.agent_discovery, logger)

            # Cleanup terminal caches periodically
            self._cleanup_terminal_caches_if_needed(logger)

        except Exception as e:
            logger.error(f"Error in monitoring cycle: {e}")

    def _cleanup_terminal_caches_if_needed(self, logger: logging.Logger) -> None:
        """Cleanup terminal caches periodically to prevent memory growth."""
        now = datetime.now()
        if (now - self._last_cache_cleanup).total_seconds() > self._cache_cleanup_interval_hours * 3600:
            logger.debug("Running terminal cache cleanup")
            # Keep only the most recent caches (limit to 100)
            if len(self._terminal_caches) > 100:
                items = list(self._terminal_caches.items())
                # Keep the last 50 caches
                self._terminal_caches = dict(items[-50:])
                logger.info(f"Cleaned terminal cache, kept {len(self._terminal_caches)} entries")

            self._last_cache_cleanup = now

    def _setup_daemon_logging(self) -> logging.Logger:
        """Set up logging for the daemon process."""
        logger = logging.getLogger("idle_monitor_daemon")
        logger.setLevel(logging.INFO)

        # Remove existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # Create file handler
        handler = logging.FileHandler(self.log_file)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def _check_if_paused(self) -> bool:
        """Check if monitoring should be paused."""
        pause_file = self.config.orchestrator_base_dir / "idle-monitor.pause"
        return pause_file.exists()

    def _cleanup_daemon(self, signum: int | None = None, is_graceful: bool = False) -> None:
        """Clean up daemon resources on shutdown."""
        logger = logging.getLogger("idle_monitor_daemon")

        if is_graceful:
            logger.info("Performing graceful daemon shutdown")
        else:
            logger.info(f"Daemon cleanup triggered by signal {signum}")

        # Remove PID file
        try:
            if self.pid_file.exists():
                self.pid_file.unlink()
                logger.info("Removed PID file")
        except OSError as e:
            logger.error(f"Failed to remove PID file: {e}")

        # Remove graceful stop flag if it exists
        try:
            if self.graceful_stop_file.exists():
                self.graceful_stop_file.unlink()
                logger.info("Removed graceful stop flag")
        except OSError:
            pass

        logger.info("Daemon cleanup completed")

        if signum is not None:
            # Exit with appropriate code
            sys.exit(0 if is_graceful else 1)

    def _check_and_resolve_daemon_conflicts(self, logger: logging.Logger) -> None:
        """Check for duplicate monitor daemons and kill conflicting ones.

        This is a "dumb" PID-based checker that doesn't use LLM evaluation.
        It finds other daemon processes writing to the same log and kills duplicates.

        Strategy: Read recent log entries to find other active PIDs, then kill
        the oldest (lowest PID) to prevent race conditions.
        Only kills one process per cycle to prevent cascading failures.
        """

        try:
            current_pid = os.getpid()

            # Check log file for other active daemon PIDs
            log_file = Path(self.config.orchestrator_base_dir) / "logs" / "idle-monitor.log"
            if not log_file.exists():
                return

            # Read recent log entries to find active PIDs
            active_pids = set()
            try:
                # Get last 200 lines to find recently active PIDs
                tail_result = subprocess.run(["tail", "-200", str(log_file)], capture_output=True, text=True, timeout=3)

                if tail_result.returncode == 0:
                    # Extract PIDs from log format "PID:12345"
                    pid_matches = re.findall(r"PID:(\d+)", tail_result.stdout)
                    for pid_str in pid_matches:
                        try:
                            pid = int(pid_str)
                            if pid != current_pid:
                                active_pids.add(pid)
                        except ValueError:
                            continue

            except Exception:
                # If tail fails, try direct file read (slower but works)
                try:
                    with open(log_file) as f:
                        # Read last 50KB to avoid loading huge files
                        f.seek(0, 2)  # Go to end
                        size = f.tell()
                        if size > 50000:
                            f.seek(size - 50000)  # Read last 50KB
                        else:
                            f.seek(0)

                        content = f.read()
                        pid_matches = re.findall(r"PID:(\d+)", content)
                        for pid_str in pid_matches:
                            try:
                                pid = int(pid_str)
                                if pid != current_pid:
                                    active_pids.add(pid)
                            except ValueError:
                                continue
                except Exception as e:
                    logger.debug(f"Could not read log file: {e}")
                    return

            # Filter to only processes that are actually running
            running_pids = []
            for pid in active_pids:
                try:
                    # Send signal 0 to check if process exists
                    os.kill(pid, 0)
                    running_pids.append(pid)
                except ProcessLookupError:
                    # Process doesn't exist anymore
                    continue
                except PermissionError:
                    # Process exists but we can't signal it
                    continue

            # If we found duplicate processes, kill the oldest (lowest PID)
            if running_pids:
                oldest_pid = min(running_pids)
                logger.warning(f"Found duplicate monitor daemon (PID: {oldest_pid}), killing it")

                try:
                    # Kill the duplicate process
                    os.kill(oldest_pid, 9)  # SIGKILL for immediate termination
                    logger.info(f"Successfully killed duplicate monitor daemon (PID: {oldest_pid})")
                except ProcessLookupError:
                    # Process already gone, ignore
                    logger.debug(f"Duplicate process {oldest_pid} already terminated")
                except PermissionError:
                    logger.error(f"Permission denied killing process {oldest_pid}")
                except Exception as e:
                    logger.error(f"Failed to kill duplicate process {oldest_pid}: {e}")

        except Exception as e:
            logger.error(f"Error checking for duplicate daemons: {e}")

    # Legacy method stubs for backwards compatibility
    def _discover_agents(self, tmux: TMUXManager) -> list[str]:
        """Legacy method - delegates to agent discovery component."""
        return self.agent_discovery.discover_agents(tmux)

    def _check_agent_status(
        self, tmux: TMUXManager, target: str, logger: logging.Logger, pm_notifications: dict[str, list[str]]
    ) -> None:
        """Legacy method - delegates to health checker component."""
        return self.health_checker.check_agent_status(tmux, target, logger, pm_notifications)
