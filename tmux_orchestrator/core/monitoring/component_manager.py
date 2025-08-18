"""
Component Manager for coordinating monitoring system components.

This module orchestrates the AgentMonitor, NotificationManager, and StateTracker
to provide a unified monitoring interface that replaces the monolithic IdleMonitor.
"""

import logging
import time
from datetime import datetime

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.utils.tmux import TMUXManager

from .agent_monitor import AgentMonitor
from .crash_detector import CrashDetector
from .notification_manager import NotificationManager
from .state_tracker import StateTracker
from .types import AgentInfo, IdleAnalysis, IdleType, MonitorStatus


class MonitorCycleResult:
    """Result of a complete monitoring cycle."""

    def __init__(self):
        self.agents_discovered: int = 0
        self.agents_analyzed: int = 0
        self.idle_agents: int = 0
        self.notifications_sent: int = 0
        self.cycle_duration: float = 0.0
        self.errors: list[str] = []
        self.timestamp: datetime = datetime.now()

    @property
    def success(self) -> bool:
        """Check if cycle completed successfully."""
        return len(self.errors) == 0

    def add_error(self, error: str) -> None:
        """Add an error to the cycle result."""
        self.errors.append(error)


class ComponentManager:
    """
    Manages interaction between monitoring components.

    Coordinates AgentMonitor, NotificationManager, and StateTracker to provide
    a unified monitoring interface that replaces the monolithic approach.
    """

    def __init__(self, tmux: TMUXManager, config: Config | None = None):
        """Initialize the component manager."""
        if config is None:
            config = Config.load()

        self.tmux = tmux
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.agent_monitor = AgentMonitor(tmux, config, self.logger)
        self.notification_manager = NotificationManager(tmux, config, self.logger)
        self.state_tracker = StateTracker(tmux, config, self.logger)
        self.crash_detector = CrashDetector(tmux, self.logger)

        # Monitoring state
        self._is_running = False
        self._start_time: datetime | None = None
        self._cycle_count = 0
        self._total_cycle_time = 0.0
        self._last_cycle_time = 0.0
        self._errors_detected = 0

        # Performance tracking
        self._performance_history: list[float] = []
        self._max_history_size = 100

    def initialize(self) -> bool:
        """
        Initialize all monitoring components.

        Returns:
            True if all components initialized successfully
        """
        self.logger.info("Initializing ComponentManager")

        try:
            # Initialize all components
            components = [
                ("AgentMonitor", self.agent_monitor),
                ("NotificationManager", self.notification_manager),
                ("StateTracker", self.state_tracker),
            ]

            for name, component in components:
                if not component.initialize():
                    self.logger.error(f"Failed to initialize {name}")
                    return False
                self.logger.debug(f"Successfully initialized {name}")

            self._start_time = datetime.now()
            self.logger.info("ComponentManager initialization complete")
            return True

        except Exception as e:
            self.logger.error(f"ComponentManager initialization failed: {e}")
            return False

    def cleanup(self) -> None:
        """Clean up all monitoring components."""
        self.logger.info("Cleaning up ComponentManager")

        try:
            # Cleanup all components
            self.agent_monitor.cleanup()
            self.notification_manager.cleanup()
            self.state_tracker.cleanup()

            # Reset state
            self._is_running = False
            self._start_time = None

            self.logger.info("ComponentManager cleanup complete")

        except Exception as e:
            self.logger.error(f"Error during ComponentManager cleanup: {e}")

    def start_monitoring(self) -> bool:
        """
        Start the monitoring system.

        Returns:
            True if monitoring started successfully
        """
        if self._is_running:
            self.logger.warning("Monitoring is already running")
            return True

        try:
            if not self.initialize():
                return False

            self._is_running = True
            self.logger.info("Monitoring system started")
            return True

        except Exception as e:
            self.logger.error(f"Failed to start monitoring: {e}")
            return False

    def stop_monitoring(self) -> bool:
        """
        Stop the monitoring system.

        Returns:
            True if monitoring stopped successfully
        """
        if not self._is_running:
            self.logger.warning("Monitoring is not running")
            return True

        try:
            self._is_running = False
            self.cleanup()
            self.logger.info("Monitoring system stopped")
            return True

        except Exception as e:
            self.logger.error(f"Failed to stop monitoring: {e}")
            return False

    def execute_monitoring_cycle(self) -> MonitorCycleResult:
        """
        Execute a complete monitoring cycle.

        Returns:
            MonitorCycleResult with cycle statistics and results
        """
        cycle_start = time.perf_counter()
        result = MonitorCycleResult()

        try:
            self.logger.debug("Starting monitoring cycle")

            # Step 1: Discover agents
            agents = self._discover_and_cache_agents(result)

            # Step 2: Analyze each agent
            self._analyze_agents(agents, result)

            # Step 2.5: Check for PM crashes across all sessions
            self._check_pm_health(result)

            # Step 3: Send queued notifications
            result.notifications_sent = self.notification_manager.send_queued_notifications()

            # Step 4: Update statistics
            cycle_end = time.perf_counter()
            result.cycle_duration = cycle_end - cycle_start
            self._update_performance_stats(result.cycle_duration)

            self.logger.debug(
                f"Monitoring cycle complete: {result.agents_discovered} agents, "
                f"{result.idle_agents} idle, {result.notifications_sent} notifications, "
                f"{result.cycle_duration:.3f}s"
            )

        except Exception as e:
            cycle_end = time.perf_counter()
            result.cycle_duration = cycle_end - cycle_start
            result.add_error(f"Monitoring cycle failed: {e}")
            self.logger.error(f"Monitoring cycle error: {e}")
            self._errors_detected += 1

        return result

    def _discover_and_cache_agents(self, result: MonitorCycleResult) -> list[AgentInfo]:
        """Discover agents and update caches."""
        try:
            agents = self.agent_monitor.discover_agents()
            result.agents_discovered = len(agents)

            # Update state tracker with discovered agents
            for agent in agents:
                self.state_tracker.track_session_agent(agent)

            return agents

        except Exception as e:
            result.add_error(f"Agent discovery failed: {e}")
            return []

    def _analyze_agents(self, agents: list[AgentInfo], result: MonitorCycleResult) -> None:
        """Analyze all agents for idle state and notifications."""
        for agent in agents:
            try:
                # Analyze agent content for idle state
                analysis = self.agent_monitor.analyze_agent_content(agent.target)
                result.agents_analyzed += 1

                # Update state tracking
                content = analysis.content_hash or ""
                self.state_tracker.update_agent_state(agent.target, content)

                # Handle idle agents
                if analysis.is_idle:
                    result.idle_agents += 1
                    self._handle_idle_agent(agent, analysis)

                # Handle error states
                if analysis.error_detected:
                    self._handle_agent_error(agent, analysis)

                # Handle fresh agents
                if analysis.idle_type == IdleType.FRESH_AGENT:
                    self._handle_fresh_agent(agent)

            except Exception as e:
                result.add_error(f"Analysis failed for {agent.target}: {e}")
                self.logger.error(f"Failed to analyze agent {agent.target}: {e}")

    def _handle_idle_agent(self, agent: AgentInfo, analysis: IdleAnalysis) -> None:
        """Handle idle agent notifications and tracking."""
        try:
            # Skip certain idle types for notifications
            if analysis.idle_type in [IdleType.COMPACTION_STATE]:
                return

            # Send idle notification
            self.notification_manager.notify_agent_idle(
                target=agent.target,
                idle_type=analysis.idle_type,
                session=agent.session,
                metadata={"agent_name": agent.name, "agent_type": agent.type, "idle_confidence": analysis.confidence},
            )

            # Check for team-wide idleness
            self._check_team_idle_status(agent.session)

        except Exception as e:
            self.logger.error(f"Error handling idle agent {agent.target}: {e}")

    def _handle_agent_error(self, agent: AgentInfo, analysis: IdleAnalysis) -> None:
        """Handle agent error states."""
        try:
            self.notification_manager.notify_agent_crash(
                target=agent.target,
                error_type=analysis.error_type or "unknown",
                session=agent.session,
                metadata={"agent_name": agent.name, "agent_type": agent.type, "error_confidence": analysis.confidence},
            )

            # Consider recovery if needed
            self.notification_manager.notify_recovery_needed(
                target=agent.target, issue=f"Agent in error state: {analysis.error_type}", session=agent.session
            )

        except Exception as e:
            self.logger.error(f"Error handling agent error for {agent.target}: {e}")

    def _handle_fresh_agent(self, agent: AgentInfo) -> None:
        """Handle fresh agent notifications."""
        try:
            self.notification_manager.notify_fresh_agent(
                target=agent.target,
                session=agent.session,
                metadata={"agent_name": agent.name, "agent_type": agent.type},
            )

        except Exception as e:
            self.logger.error(f"Error handling fresh agent {agent.target}: {e}")

    def _check_team_idle_status(self, session: str) -> None:
        """Check if entire team in session is idle."""
        try:
            session_agents = self.state_tracker.get_session_agents(session)
            if not session_agents:
                return

            # Count idle agents in session
            idle_count = sum(1 for agent in session_agents if self.state_tracker.is_agent_idle(agent.target))

            # If all agents are idle, mark team as idle
            if idle_count == len(session_agents) and idle_count > 0:
                if not self.state_tracker.is_team_idle(session):
                    self.state_tracker.set_team_idle(session)
                    self.notification_manager.notify_team_idle(session=session, agent_count=idle_count)
            else:
                # Team is not idle anymore
                if self.state_tracker.is_team_idle(session):
                    self.state_tracker.clear_team_idle(session)

        except Exception as e:
            self.logger.error(f"Error checking team idle status for {session}: {e}")

    def _update_performance_stats(self, cycle_time: float) -> None:
        """Update performance statistics."""
        self._cycle_count += 1
        self._total_cycle_time += cycle_time
        self._last_cycle_time = cycle_time

        # Maintain performance history
        self._performance_history.append(cycle_time)
        if len(self._performance_history) > self._max_history_size:
            self._performance_history.pop(0)

    def get_status(self) -> MonitorStatus:
        """
        Get current monitoring system status.

        Returns:
            MonitorStatus with current system state
        """
        uptime = datetime.now() - self._start_time if self._start_time else None

        # Count current agents
        all_agents = self.agent_monitor.get_all_cached_agents()
        idle_agents = len(self.state_tracker.get_all_idle_agents())

        return MonitorStatus(
            is_running=self._is_running,
            active_agents=len(all_agents),
            idle_agents=idle_agents,
            last_cycle_time=self._last_cycle_time,
            uptime=uptime or datetime.now() - datetime.now(),  # Zero timedelta if not started
            cycle_count=self._cycle_count,
            errors_detected=self._errors_detected,
        )

    def get_performance_stats(self) -> dict[str, float]:
        """Get performance statistics."""
        if not self._performance_history:
            return {"avg_cycle_time": 0.0, "min_cycle_time": 0.0, "max_cycle_time": 0.0, "total_cycles": 0}

        return {
            "avg_cycle_time": sum(self._performance_history) / len(self._performance_history),
            "min_cycle_time": min(self._performance_history),
            "max_cycle_time": max(self._performance_history),
            "total_cycles": self._cycle_count,
        }

    def is_agent_idle(self, target: str) -> bool:
        """Check if specific agent is idle."""
        return self.state_tracker.is_agent_idle(target)

    def get_agent_info(self, target: str) -> AgentInfo | None:
        """Get information for specific agent."""
        return self.agent_monitor.get_cached_agent_info(target)

    def reset_agent_tracking(self, target: str) -> None:
        """Reset tracking for specific agent."""
        self.state_tracker.reset_agent_state(target)

    def force_notification_send(self) -> int:
        """Force sending of queued notifications."""
        return self.notification_manager.send_queued_notifications()

    def _check_pm_health(self, result: MonitorCycleResult) -> None:
        """Check PM health across all active sessions."""
        try:
            # Get all sessions with agents
            sessions = set()
            for agent in self.agent_monitor.get_all_cached_agents():
                sessions.add(agent.session)

            # Check PM health in each session
            for session_name in sessions:
                try:
                    crashed, pm_target = self.crash_detector.detect_pm_crash(session_name)

                    if crashed:
                        if pm_target:
                            self.logger.error(f"PM crash detected in session {session_name} at {pm_target}")
                            self.notification_manager.notify_agent_crash(
                                target=pm_target,
                                error_type="PM crash detected",
                                session=session_name,
                                metadata={"component": "PM", "recovery_needed": True},
                            )
                        else:
                            self.logger.error(f"PM missing entirely in session {session_name}")
                            self.notification_manager.notify_recovery_needed(
                                target=f"{session_name}:0",  # Assume PM should be at window 0
                                issue="PM missing from session",
                                session=session_name,
                                metadata={"component": "PM", "recovery_type": "respawn"},
                            )
                    else:
                        self.logger.debug(f"PM health check passed for session {session_name}")

                except Exception as e:
                    self.logger.error(f"Error checking PM health in session {session_name}: {e}")
                    result.add_error(f"PM health check failed for {session_name}: {e}")

        except Exception as e:
            self.logger.error(f"Error during PM health check: {e}")
            result.add_error(f"PM health check failed: {e}")
