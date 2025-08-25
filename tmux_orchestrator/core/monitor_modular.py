"""
Modular IdleMonitor implementation using ComponentManager.

This is the new implementation that replaces the monolithic monitor.py
with a clean, modular architecture.
"""

import logging
import multiprocessing
import os
import signal
import time
from typing import Any

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.utils.tmux import TMUXManager

from .monitoring import ComponentManager
from .monitoring.monitor_service import MonitorService


class ModularIdleMonitor:
    """
    Modular idle monitor using ComponentManager architecture.

    This replaces the monolithic IdleMonitor with a clean, testable,
    and maintainable implementation using separated concerns.
    """

    def __init__(self, tmux: TMUXManager, config: Config | None = None):
        """Initialize the modular idle monitor."""
        self.tmux = tmux

        # Use configurable directory for storage
        if config is None:
            config = Config.load()
        self.config = config

        project_dir = config.orchestrator_base_dir
        project_dir.mkdir(parents=True, exist_ok=True)
        logs_dir = project_dir / "logs"
        logs_dir.mkdir(exist_ok=True)

        # File management
        self.pid_file = project_dir / "idle-monitor.pid"
        self.log_file = logs_dir / "idle-monitor.log"
        self.logs_dir = logs_dir
        self.graceful_stop_file = project_dir / "idle-monitor.graceful"

        # Process management
        self.daemon_process: multiprocessing.Process | None = None

        # Component manager for monitoring logic
        self.component_manager: ComponentManager | None = None
        # New monitor service facade
        self.monitor_service: MonitorService | None = None

        # Monitoring statistics
        self._cycle_count = 0
        self._total_errors = 0

    def is_running(self) -> bool:
        """Check if the daemon is running."""
        if not self.pid_file.exists():
            return False

        try:
            pid = int(self.pid_file.read_text().strip())
            # Check if process is still alive
            os.kill(pid, 0)
            return True
        except (ValueError, ProcessLookupError, OSError):
            # PID file is stale, clean it up
            self.pid_file.unlink(missing_ok=True)
            return False

    def start(self, interval: int = 10) -> bool:
        """Start the monitoring daemon."""
        if self.is_running():
            return True

        try:
            # Clear graceful stop flag
            self.graceful_stop_file.unlink(missing_ok=True)

            # Start daemon process
            self.daemon_process = multiprocessing.Process(
                target=self._run_monitoring_daemon, args=(interval,), daemon=True
            )
            self.daemon_process.start()

            # Write PID file
            if self.daemon_process.pid:
                self.pid_file.write_text(str(self.daemon_process.pid))
                return True
            else:
                return False

        except Exception as e:
            print(f"Failed to start monitoring daemon: {e}")
            return False

    def start_supervised(self, interval: int = 10) -> bool:
        """Start with supervision (legacy compatibility)."""
        return self.start(interval)

    def stop(self, allow_cleanup: bool = True) -> bool:
        """Stop the monitoring daemon."""
        if not self.is_running():
            return True

        try:
            # Signal graceful stop
            self.graceful_stop_file.touch()

            # Get PID and send termination signal
            if self.pid_file.exists():
                pid = int(self.pid_file.read_text().strip())

                # Send SIGTERM
                os.kill(pid, signal.SIGTERM)

                # Wait for graceful shutdown
                for _ in range(10):  # Wait up to 10 seconds
                    if not self.is_running():
                        break
                    time.sleep(1)

                # Force kill if still running
                if self.is_running():
                    os.kill(pid, signal.SIGKILL)
                    time.sleep(1)

            # Cleanup
            if allow_cleanup:
                self.pid_file.unlink(missing_ok=True)
                self.graceful_stop_file.unlink(missing_ok=True)

            return not self.is_running()

        except Exception as e:
            print(f"Error stopping daemon: {e}")
            return False

    def status(self) -> None:
        """Print daemon status (legacy compatibility)."""
        if self.is_running():
            print("Idle monitor daemon is running")
            if self.pid_file.exists():
                pid = self.pid_file.read_text().strip()
                print(f"PID: {pid}")
        else:
            print("Idle monitor daemon is not running")

    def is_agent_idle(self, target: str) -> bool:
        """Check if specific agent is idle (legacy compatibility)."""
        if self.monitor_service:
            health = self.monitor_service.check_health(
                target.split(":")[0], target.split(":")[1] if ":" in target else None
            )
            if isinstance(health, dict) and "is_idle" in health:
                from typing import cast

                return cast(bool, health["is_idle"])
        elif self.component_manager:
            return self.component_manager.is_agent_idle(target)
        return False

    def _run_monitoring_daemon(self, interval: int) -> None:
        """Run the monitoring daemon process."""

        # Set up signal handlers
        def signal_handler(signum: int, frame: Any) -> None:
            self._cleanup_daemon(signum, is_graceful=True)

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        # Set up logging
        logger = self._setup_daemon_logging()
        logger.info(f"Starting modular monitoring daemon (PID: {os.getpid()})")

        try:
            # Initialize monitor service (new facade)
            self.monitor_service = MonitorService(self.tmux, self.config, logger)
            self.monitor_service.set_idle_monitor(self)  # For backward compatibility

            if not self.monitor_service.start():
                logger.error("Failed to start monitor service")
                return

            # Keep component manager for backward compatibility
            self.component_manager = ComponentManager(self.tmux, self.config)
            self.component_manager.start_monitoring()

            logger.info(f"Monitoring started with {interval}s interval")

            # Startup protection: use longer intervals for first few cycles to prevent tmux server crashes
            startup_cycles = 3
            startup_interval = max(interval * 3, 30)  # 3x normal interval or 30s minimum
            current_cycle = 0

            logger.info(f"Using startup protection: {startup_interval}s interval for first {startup_cycles} cycles")

            # Main monitoring loop
            while not self.graceful_stop_file.exists():
                cycle_start = time.perf_counter()

                try:
                    # Execute monitoring cycle through service
                    self.monitor_service.run_monitoring_cycle()
                    self._cycle_count += 1

                    # Get status for logging
                    status = self.monitor_service.status()
                    cycle_duration = self.monitor_service.last_cycle_time

                    # Log cycle results
                    logger.debug(
                        f"Cycle {self._cycle_count}: {status.active_agents + status.idle_agents} agents, "
                        f"{status.idle_agents} idle, {cycle_duration:.3f}s"
                    )

                    if status.errors_detected > self._total_errors:
                        new_errors = status.errors_detected - self._total_errors
                        self._total_errors = status.errors_detected
                        logger.warning(f"Cycle {self._cycle_count} had {new_errors} new errors")

                    # Performance warning if cycle is slow
                    if cycle_duration > 0.05:  # 50ms threshold
                        logger.warning(f"Slow monitoring cycle: {cycle_duration:.3f}s (target: <0.01s)")

                except Exception as e:
                    self._total_errors += 1
                    logger.error(f"Monitoring cycle failed: {e}")

                # Calculate sleep time to maintain interval (adaptive during startup)
                cycle_end = time.perf_counter()
                cycle_duration = cycle_end - cycle_start
                current_cycle += 1

                # Use startup interval for first few cycles to prevent tmux server overload
                effective_interval = startup_interval if current_cycle <= startup_cycles else interval
                sleep_time = max(0, effective_interval - cycle_duration)

                if sleep_time > 0:
                    time.sleep(sleep_time)
                else:
                    logger.warning(
                        f"Monitoring cycle took {cycle_duration:.3f}s, longer than {effective_interval}s interval"
                    )

                # Log transition from startup to normal intervals
                if current_cycle == startup_cycles:
                    logger.info(f"Startup protection complete - switching to normal {interval}s intervals")

        except Exception as e:
            logger.error(f"Daemon error: {e}")

        finally:
            logger.info(f"Monitoring daemon stopping (cycles: {self._cycle_count}, errors: {self._total_errors})")
            self._cleanup_daemon()

    def _setup_daemon_logging(self) -> logging.Logger:
        """Set up logging for the daemon process."""
        logger = logging.getLogger("modular_idle_monitor")
        logger.setLevel(logging.INFO)

        # Remove existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # File handler
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.DEBUG)

        # Formatter
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

        return logger

    def _cleanup_daemon(self, signum: int | None = None, is_graceful: bool = False) -> None:
        """Clean up daemon resources."""
        try:
            # Stop monitor service
            if self.monitor_service:
                self.monitor_service.stop()

            # Stop component manager
            if self.component_manager:
                self.component_manager.stop_monitoring()

            # Remove PID file
            self.pid_file.unlink(missing_ok=True)

            # Remove graceful stop file
            self.graceful_stop_file.unlink(missing_ok=True)

        except Exception as e:
            # Use print since logger might not be available
            print(f"Error during daemon cleanup: {e}")

        if signum is not None:
            exit(0)

    def get_performance_stats(self) -> dict:
        """Get performance statistics."""
        if self.monitor_service:
            status = self.monitor_service.status()
            return {
                "cycle_count": status.cycle_count,
                "avg_cycle_time": status.last_cycle_time,
                "active_agents": status.active_agents,
                "idle_agents": status.idle_agents,
            }
        elif self.component_manager:
            return self.component_manager.get_performance_stats()
        return {}

    def get_status_info(self) -> dict:
        """Get detailed status information."""
        if self.monitor_service:
            status = self.monitor_service.status()
            return {
                "is_running": status.is_running,
                "active_agents": status.active_agents,
                "idle_agents": status.idle_agents,
                "cycle_count": status.cycle_count,
                "last_cycle_time": status.last_cycle_time,
                "errors_detected": status.errors_detected,
                "uptime": str(status.uptime),
            }
        elif self.component_manager:
            status = self.component_manager.get_status()
            return {
                "is_running": status.is_running,
                "active_agents": status.active_agents,
                "idle_agents": status.idle_agents,
                "cycle_count": status.cycle_count,
                "last_cycle_time": status.last_cycle_time,
                "errors_detected": status.errors_detected,
                "uptime": str(status.uptime),
            }
        return {"is_running": self.is_running()}


# Backward compatibility alias
IdleMonitorModular = ModularIdleMonitor
