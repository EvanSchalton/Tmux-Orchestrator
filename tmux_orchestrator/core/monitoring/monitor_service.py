"""MonitorService facade for coordinating all monitoring components."""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.core.monitoring.agent_monitor import AgentMonitor
from tmux_orchestrator.core.monitoring.daemon_manager import DaemonManager
from tmux_orchestrator.core.monitoring.health_checker import HealthChecker
from tmux_orchestrator.core.monitoring.notification_manager import NotificationManager
from tmux_orchestrator.core.monitoring.pm_recovery_manager import PMRecoveryManager
from tmux_orchestrator.core.monitoring.state_tracker import StateTracker
from tmux_orchestrator.core.monitoring.types import AgentInfo, MonitorStatus
from tmux_orchestrator.utils.tmux import TMUXManager


class MonitorService:
    """Facade for the monitoring system.

    This provides a simple interface for starting, stopping, and interacting
    with the monitoring system while delegating to specialized components.
    """

    def __init__(self, tmux: TMUXManager, config: Config, logger: logging.Logger | None = None):
        """Initialize the monitor service.

        Args:
            tmux: TMUX manager instance
            config: Configuration object
            logger: Optional logger instance
        """
        self.tmux = tmux
        self.config = config
        self.logger = logger or logging.getLogger(__name__)

        # Initialize components
        self.daemon_manager = DaemonManager(config, self.logger)  # type: ignore[abstract]
        self.health_checker = HealthChecker(tmux, config, self.logger)
        self.agent_monitor = AgentMonitor(tmux, config, self.logger)
        self.notification_manager = NotificationManager(tmux, config, self.logger)
        self.state_tracker = StateTracker(tmux, config, self.logger)
        self.pm_recovery_manager = PMRecoveryManager(tmux, config, self.logger)  # type: ignore[abstract]

        # Runtime state
        self.is_running = False
        self.start_time: datetime | None = None
        self.cycle_count = 0
        self.last_cycle_time = 0.0
        self.errors_detected = 0

        # Monitoring configuration
        self.check_interval = getattr(config, "check_interval", 30)
        self.idle_monitor = None  # Will be set when available

    def initialize(self) -> bool:
        """Initialize all components.

        Returns:
            True if initialization successful
        """
        try:
            # Initialize each component
            components = [
                self.daemon_manager,
                self.health_checker,
                self.agent_monitor,
                self.notification_manager,
                self.state_tracker,
                self.pm_recovery_manager,
            ]

            for component in components:
                if hasattr(component, "initialize") and not component.initialize():
                    self.logger.error(f"Failed to initialize {component.__class__.__name__}")
                    return False

            self.logger.info("MonitorService initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Error initializing MonitorService: {e}")
            return False

    def cleanup(self) -> None:
        """Clean up all components."""
        components = [
            self.pm_recovery_manager,
            self.state_tracker,
            self.notification_manager,
            self.agent_monitor,
            self.health_checker,
            self.daemon_manager,
        ]

        for component in components:
            try:
                if hasattr(component, "cleanup"):
                    component.cleanup()
            except Exception as e:
                self.logger.error(f"Error cleaning up {component.__class__.__name__}: {e}")

    def set_idle_monitor(self, idle_monitor) -> None:
        """Set the idle monitor instance.

        Args:
            idle_monitor: Idle monitor instance
        """
        self.idle_monitor = idle_monitor
        self.health_checker.set_idle_monitor(idle_monitor)

    def start(self) -> bool:
        """Start the monitoring service.

        Returns:
            True if started successfully
        """
        if self.is_running:
            self.logger.warning("MonitorService is already running")
            return True

        if not self.initialize():
            return False

        # Start the daemon if needed
        if not self.daemon_manager.is_running():
            if not self.daemon_manager.start():
                self.logger.error("Failed to start monitoring daemon")
                return False

        self.is_running = True
        self.start_time = datetime.now()
        self.logger.info("MonitorService started")
        return True

    def stop(self) -> bool:
        """Stop the monitoring service.

        Returns:
            True if stopped successfully
        """
        if not self.is_running:
            self.logger.warning("MonitorService is not running")
            return True

        self.is_running = False

        # Stop the daemon
        if self.daemon_manager.is_running():
            self.daemon_manager.stop()

        # Clean up components
        self.cleanup()

        self.logger.info("MonitorService stopped")
        return True

    def status(self) -> MonitorStatus:
        """Get current monitoring status.

        Returns:
            MonitorStatus object with current system state
        """
        # Count agents by state
        active_count = 0
        idle_count = 0

        for target, status in self.health_checker.get_all_agent_statuses().items():
            if status.is_idle:
                idle_count += 1
            else:
                active_count += 1

        # Calculate uptime
        uptime = datetime.now() - self.start_time if self.start_time else timedelta(0)

        return MonitorStatus(
            is_running=self.is_running,
            active_agents=active_count,
            idle_agents=idle_count,
            last_cycle_time=self.last_cycle_time,
            uptime=uptime,
            cycle_count=self.cycle_count,
            errors_detected=self.errors_detected,
        )

    def check_health(self, session: str, window: str | None = None) -> dict[str, Any]:
        """Check health of specific session or window.

        Args:
            session: Session name
            window: Optional window number

        Returns:
            Health status information
        """
        target = f"{session}:{window}" if window else session

        # Check if it's a specific window
        if window:
            status = self.health_checker.check_agent_health(target)
            return {
                "target": target,
                "status": status.status,
                "is_responsive": status.is_responsive,
                "is_idle": status.is_idle,
                "consecutive_failures": status.consecutive_failures,
                "last_response": status.last_response.isoformat(),
            }

        # Check all windows in session
        agents = self.agent_monitor.discover_agents()
        session_agents = [a for a in agents if a.session == session]

        results = {}
        for agent in session_agents:
            status = self.health_checker.check_agent_health(agent.target)
            results[agent.target] = {
                "name": agent.display_name,
                "status": status.status,
                "is_responsive": status.is_responsive,
                "is_idle": status.is_idle,
            }

        return results

    def handle_recovery(self, session: str, window: str | None = None) -> bool:
        """Handle recovery for a specific session or window.

        Args:
            session: Session name
            window: Optional window number

        Returns:
            True if recovery was initiated
        """
        # Check if it's a PM
        target = f"{session}:{window}" if window else f"{session}:1"

        # Use PM recovery manager for PMs
        if window == "1" or window is None:
            return self.pm_recovery_manager.handle_recovery(session, "PM crash detected")

        # For other agents, check if recovery is needed
        status = self.health_checker.check_agent_health(target)
        if self.health_checker.should_attempt_recovery(target, status):
            # Notify PM about the issue
            _pm_target = f"{session}:1"
            self.notification_manager.notify_agent_crash(target, f"Agent unresponsive: {status.status}", session)
            self.health_checker.mark_recovery_attempted(target)
            return True

        return False

    def discover_agents(self) -> list[AgentInfo]:
        """Discover all active agents.

        Returns:
            List of AgentInfo objects
        """
        return self.agent_monitor.discover_agents()

    def run_monitoring_cycle(self) -> None:
        """Run a single monitoring cycle."""
        if not self.is_running:
            return

        start_time = time.time()

        try:
            # Discover agents
            agents = self.discover_agents()

            # Check health of each agent
            for agent in agents:
                try:
                    # Update state
                    content = self.tmux.capture_pane(agent.target)
                    self.state_tracker.update_agent_state(agent.target, content)

                    # Check health
                    status = self.health_checker.check_agent_health(agent.target)

                    # Handle issues
                    if status.status in ["critical", "unresponsive"]:
                        self.errors_detected += 1

                        # Check if it's a PM
                        if agent.window == "1":
                            self.pm_recovery_manager.check_and_recover_if_needed(agent.session)
                        else:
                            # Notify about non-PM agent issues
                            self.notification_manager.notify_agent_crash(
                                agent.target, f"Agent {status.status}", agent.session
                            )

                except Exception as e:
                    self.logger.error(f"Error checking agent {agent.target}: {e}")

            # Send queued notifications
            self.notification_manager.send_queued_notifications()

            # Update metrics
            self.cycle_count += 1
            self.last_cycle_time = time.time() - start_time

        except Exception as e:
            self.logger.error(f"Error in monitoring cycle: {e}")
            self.errors_detected += 1

    async def run_async(self) -> None:
        """Run monitoring service asynchronously."""
        if not self.start():
            raise RuntimeError("Failed to start MonitorService")

        try:
            while self.is_running:
                self.run_monitoring_cycle()
                await asyncio.sleep(self.check_interval)
        finally:
            self.stop()

    def run(self) -> None:
        """Run monitoring service synchronously."""
        if not self.start():
            raise RuntimeError("Failed to start MonitorService")

        try:
            while self.is_running:
                self.run_monitoring_cycle()
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            self.logger.info("Monitoring interrupted by user")
        finally:
            self.stop()
