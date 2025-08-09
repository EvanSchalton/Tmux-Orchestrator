"""Recovery daemon with bulletproof idle detection integration."""

import logging
import os
import signal
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from ..utils.tmux import TMUXManager
from .config import Config
from .recovery import (
    check_agent_health,
    discover_agents,
    restart_agent,
    restore_context,
)
from .recovery.check_agent_health import AgentHealthStatus


class RecoveryDaemon:
    """
    Recovery daemon with bulletproof idle detection and automatic recovery.

    Orchestrates the recovery system by coordinating single-function modules
    following SOLID principles and proper separation of concerns.
    """

    def __init__(self, config_file: Optional[str] = None) -> None:
        """Initialize recovery daemon with configuration."""
        self.config: Config = Config.load(Path(config_file) if config_file else None)
        self.tmux: TMUXManager = TMUXManager()
        self.logger: logging.Logger = self._setup_logging()
        self.running: bool = False

        # Daemon configuration
        self.check_interval: int = self.config.get("daemon.check_interval", 30)
        self.auto_discover: bool = self.config.get("daemon.auto_discover", True)
        self.pid_file: Path = Path("/tmp/tmux-orchestrator-recovery.pid")
        self.log_file: Path = Path("/tmp/tmux-orchestrator-recovery.log")

        # Agent tracking
        self.known_agents: set[str] = set()
        self.agent_health: dict[str, AgentHealthStatus] = {}
        self.recent_recoveries: dict[str, datetime] = {}
        self.recovery_cooldown: int = self.config.get("daemon.recovery_cooldown", 300)

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _setup_logging(self) -> logging.Logger:
        """Set up daemon logging."""
        logger: logging.Logger = logging.getLogger("recovery_daemon")
        logger.setLevel(logging.INFO)

        # Clear existing handlers
        logger.handlers.clear()

        # File handler
        handler: logging.FileHandler = logging.FileHandler(self.log_file)
        formatter: logging.Formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)

    def _write_pid_file(self) -> None:
        """Write daemon PID to file."""
        with open(self.pid_file, "w") as f:
            f.write(str(os.getpid()))

    def _remove_pid_file(self) -> None:
        """Remove daemon PID file."""
        if self.pid_file.exists():
            self.pid_file.unlink()

    def _should_attempt_recovery(self, target: str, health_status: AgentHealthStatus) -> bool:
        """
        Determine if recovery should be attempted for an agent.

        Args:
            target: Target agent identifier
            health_status: Current health status

        Returns:
            True if recovery should be attempted
        """
        # Don't recover if recently recovered
        if target in self.recent_recoveries:
            time_since_recovery: timedelta = datetime.now() - self.recent_recoveries[target]
            if time_since_recovery < timedelta(seconds=self.recovery_cooldown):
                return False

        # Only recover unhealthy agents
        if health_status.is_healthy:
            return False

        # Check failure patterns that warrant recovery
        critical_failures: set[str] = {
            "critical_error_detected",
            "max_consecutive_failures_reached",
            "extended_unresponsiveness",
            "abnormal_interface_state",
        }

        return health_status.failure_reason in critical_failures

    def _update_agent_tracking(self, current_agents: set[str]) -> None:
        """
        Update agent tracking with discovered agents.

        Args:
            current_agents: Currently discovered agents
        """
        # Remove stale agents
        stale_agents: set[str] = self.known_agents - current_agents
        for stale_agent in stale_agents:
            if stale_agent in self.agent_health:
                del self.agent_health[stale_agent]
            self.known_agents.remove(stale_agent)
            self.logger.info(f"Removed stale agent: {stale_agent}")

        # Add new agents
        new_agents: set[str] = current_agents - self.known_agents
        for new_agent in new_agents:
            self.known_agents.add(new_agent)
            self.logger.info(f"Added new agent: {new_agent}")

    def start(self) -> bool:
        """Start the recovery daemon."""
        if self.is_running():
            self.logger.error("Daemon is already running")
            return False

        self.logger.info("Starting recovery daemon with bulletproof detection...")
        self._write_pid_file()
        self.running = True

        try:
            self._run_daemon_loop()
        except KeyboardInterrupt:
            self.logger.info("Daemon interrupted by user")
        except Exception as e:
            self.logger.error(f"Daemon error: {e}")
        finally:
            self.stop()

        return True

    def stop(self) -> None:
        """Stop the recovery daemon."""
        if self.running:
            self.logger.info("Stopping recovery daemon...")
            self.running = False
            self._remove_pid_file()

    def is_running(self) -> bool:
        """Check if daemon is already running."""
        if not self.pid_file.exists():
            return False

        try:
            with open(self.pid_file) as f:
                pid: int = int(f.read().strip())

            os.kill(pid, 0)  # Check if process exists
            return True
        except (OSError, ValueError):
            self._remove_pid_file()
            return False

    def _run_daemon_loop(self) -> None:
        """Main daemon loop with enhanced monitoring."""
        self.logger.info(f"Daemon loop started (interval: {self.check_interval}s)")

        while self.running:
            try:
                loop_start: datetime = datetime.now()

                # Discover agents if auto-discovery enabled
                if self.auto_discover:
                    current_agents: set[str] = discover_agents(self.tmux, self.logger)
                    self._update_agent_tracking(current_agents)

                # Monitor all known agents
                self._monitor_agents()

                # Log summary
                self._log_monitoring_summary()

                # Calculate sleep time
                elapsed: float = (datetime.now() - loop_start).total_seconds()
                sleep_time: float = max(0, self.check_interval - elapsed)

                if self.running:
                    time.sleep(sleep_time)

            except Exception as e:
                self.logger.error(f"Error in daemon loop: {e}")
                if self.running:
                    time.sleep(self.check_interval)

    def _monitor_agents(self) -> None:
        """Monitor all known agents for health issues."""
        for target in list(self.known_agents):
            try:
                # Get previous health status
                previous_health: Optional[AgentHealthStatus] = self.agent_health.get(target)

                # Determine last response time
                last_response: datetime = previous_health.last_check if previous_health else datetime.now()

                # Check agent health
                health_status: AgentHealthStatus = check_agent_health(
                    self.tmux,
                    target,
                    last_response,
                    previous_health.consecutive_failures if previous_health else 0,
                )

                # Update health tracking
                self.agent_health[target] = health_status

                # Attempt recovery if needed
                if self._should_attempt_recovery(target, health_status):
                    self._attempt_agent_recovery(target)

            except Exception as e:
                self.logger.error(f"Error monitoring agent {target}: {e}")

    def _attempt_agent_recovery(self, target: str) -> None:
        """
        Attempt to recover a failed agent.

        Args:
            target: Target agent identifier
        """
        self.logger.warning(f"Attempting recovery for: {target}")

        try:
            # Restart the agent
            success, message = restart_agent(target, self.logger)

            if success:
                # Mark recovery attempt
                self.recent_recoveries[target] = datetime.now()

                # Restore context
                context_success: bool = restore_context(self.tmux, target, self.logger)

                if context_success:
                    self.logger.info(f"Successfully recovered agent: {target}")
                else:
                    self.logger.warning(f"Agent restarted but context restore failed: {target}")

                # Reset health status
                if target in self.agent_health:
                    # Create new healthy status
                    self.agent_health[target] = AgentHealthStatus(
                        target=target,
                        is_healthy=True,
                        is_idle=False,
                        failure_reason="healthy",
                        last_check=datetime.now(),
                        consecutive_failures=0,
                    )
            else:
                self.logger.error(f"Failed to restart agent {target}: {message}")

        except Exception as e:
            self.logger.error(f"Recovery attempt failed for {target}: {e}")

    def _log_monitoring_summary(self) -> None:
        """Log monitoring summary with health statistics."""
        total_agents: int = len(self.known_agents)

        if total_agents == 0:
            return

        healthy_count: int = sum(1 for h in self.agent_health.values() if h.is_healthy)
        unhealthy_count: int = total_agents - healthy_count
        idle_count: int = sum(1 for h in self.agent_health.values() if h.is_idle)
        recent_recoveries: int = len(self.recent_recoveries)

        self.logger.info(
            f"Monitoring summary: {total_agents} agents total, "
            f"{healthy_count} healthy, {unhealthy_count} unhealthy, "
            f"{idle_count} idle, {recent_recoveries} recent recoveries"
        )

        # Log unhealthy agents
        for target, health in self.agent_health.items():
            if not health.is_healthy:
                self.logger.warning(
                    f"Unhealthy agent {target}: {health.failure_reason} " f"(failures: {health.consecutive_failures})"
                )

    def get_status(self) -> dict[str, Any]:
        """Get daemon status information."""
        is_running: bool = self.is_running()
        pid: Optional[int] = None

        if is_running and self.pid_file.exists():
            with open(self.pid_file) as f:
                pid = int(f.read().strip())

        return {
            "running": is_running,
            "pid": pid,
            "config_file": getattr(self.config, "config_file", None),
            "check_interval": self.check_interval,
            "auto_discover": self.auto_discover,
            "log_file": str(self.log_file),
            "pid_file": str(self.pid_file),
            "enhanced_detection": True,
            "known_agents": len(self.known_agents),
            "healthy_agents": sum(1 for h in self.agent_health.values() if h.is_healthy),
            "recent_recoveries": len(self.recent_recoveries),
        }
