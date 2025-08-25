"""
Default polling-based monitoring strategy.

This module implements the standard polling strategy that monitors agents
at regular intervals.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any

from ..interfaces import (
    AgentMonitorInterface,
    NotificationManagerInterface,
    PMRecoveryManagerInterface,
    StateTrackerInterface,
)
from ..types import AgentInfo, MonitorStatus
from .base_strategy import BaseMonitoringStrategy


class PollingMonitoringStrategy(BaseMonitoringStrategy):
    """Standard polling-based monitoring strategy."""

    def __init__(self):
        """Initialize the polling strategy."""
        super().__init__(name="polling", description="Standard polling-based monitoring at regular intervals")

        # Define required components
        self.add_required_component(AgentMonitorInterface)
        self.add_required_component(StateTrackerInterface)
        self.add_required_component(NotificationManagerInterface)
        self.add_required_component(PMRecoveryManagerInterface)

        # Strategy configuration
        self.poll_interval = 30  # seconds
        self.batch_size = 10  # agents to check concurrently

    async def execute(self, context: dict[str, Any]) -> MonitorStatus:
        """Execute the polling monitoring strategy.

        Args:
            context: Execution context with components

        Returns:
            Monitoring status
        """
        if not self.validate_context(context):
            raise ValueError("Missing required components in context")

        # Extract components
        agent_monitor: AgentMonitorInterface = context["AgentMonitorInterface"]
        state_tracker: StateTrackerInterface = context["StateTrackerInterface"]
        notification_manager: NotificationManagerInterface = context["NotificationManagerInterface"]
        pm_recovery_manager: PMRecoveryManagerInterface = context["PMRecoveryManagerInterface"]
        logger = context.get("logger")

        try:
            # Phase 1: Agent Discovery
            agents = agent_monitor.discover_agents()

            if logger:
                logger.info(f"Discovered {len(agents)} agents")

            # Update state tracker with discovered agents
            for agent in agents:
                state_tracker.update_agent_discovered(agent.target)

            # Phase 2: PM Health Checks
            # Get sessions from agent discovery
            sessions = list({agent.session for agent in agents})
            pm_issues = await self._check_pm_health(sessions, pm_recovery_manager, logger)

            # Phase 3: Agent Health Checks
            idle_agents, crashed_agents = await self._check_agent_health(agents, agent_monitor, state_tracker, logger)

            # Phase 4: Process Notifications
            await self._process_notifications(
                idle_agents, crashed_agents, pm_issues, notification_manager, state_tracker, logger
            )

            # Build status
            return MonitorStatus(
                is_running=True,
                active_agents=len(agents) - len(idle_agents),
                idle_agents=len(idle_agents),
                last_cycle_time=0.0,
                uptime=timedelta(0),
                cycle_count=1,
                errors_detected=len(crashed_agents),
                start_time=datetime.now(),
            )

        except Exception as e:
            if logger:
                logger.error(f"Error in polling strategy: {e}")

            return MonitorStatus(
                is_running=False,
                active_agents=0,
                idle_agents=0,
                last_cycle_time=0.0,
                uptime=timedelta(0),
                cycle_count=0,
                errors_detected=1,
                start_time=datetime.now(),
            )

    async def _check_pm_health(
        self, sessions: list[str], pm_recovery_manager: PMRecoveryManagerInterface, logger: Any | None
    ) -> list[dict[str, Any]]:
        """Check health of PMs in all sessions.

        Args:
            sessions: List of session names
            pm_recovery_manager: PM recovery manager
            logger: Optional logger

        Returns:
            List of PM issues found
        """
        pm_issues = []

        for session in sessions:
            try:
                is_healthy, pm_target, issue = pm_recovery_manager.check_pm_health(session)

                if not is_healthy:
                    pm_issues.append({"session": session, "target": pm_target, "issue": issue})

                    if pm_recovery_manager.should_attempt_recovery(session):
                        if logger:
                            logger.info(f"Attempting PM recovery for session {session}")

                        success = pm_recovery_manager.recover_pm(session, pm_target)

                        if logger:
                            if success:
                                logger.info(f"PM recovery successful for session {session}")
                            else:
                                logger.error(f"PM recovery failed for session {session}")

            except Exception as e:
                if logger:
                    logger.error(f"Error checking PM health in session {session}: {e}")

        return pm_issues

    async def _check_agent_health(
        self,
        agents: list[AgentInfo],
        agent_monitor: AgentMonitorInterface,
        state_tracker: StateTrackerInterface,
        logger: Any | None,
    ) -> tuple[list[AgentInfo], list[AgentInfo]]:
        """Check health of all agents.

        Args:
            agents: List of agents to check
            agent_monitor: Agent monitor component
            state_tracker: State tracker component
            logger: Optional logger

        Returns:
            Tuple of (idle_agents, crashed_agents)
        """
        idle_agents = []
        crashed_agents = []

        # Process agents in batches for efficiency
        for i in range(0, len(agents), self.batch_size):
            batch = agents[i : i + self.batch_size]

            # Check agents concurrently within batch
            tasks = []
            for agent in batch:
                tasks.append(self._check_single_agent(agent, agent_monitor, state_tracker, logger))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for agent, result in zip(batch, results):
                if isinstance(result, BaseException):
                    if logger:
                        logger.error(f"Error checking agent {agent.target}: {result}")
                    continue

                is_idle, is_crashed = result

                if is_crashed:
                    crashed_agents.append(agent)
                elif is_idle:
                    idle_agents.append(agent)

        return idle_agents, crashed_agents

    async def _check_single_agent(
        self,
        agent: AgentInfo,
        agent_monitor: AgentMonitorInterface,
        state_tracker: StateTrackerInterface,
        logger: Any | None,
    ) -> tuple[bool, bool]:
        """Check health of a single agent.

        Args:
            agent: Agent to check
            agent_monitor: Agent monitor component
            state_tracker: State tracker component
            logger: Optional logger

        Returns:
            Tuple of (is_idle, is_crashed)
        """
        try:
            # Check agent health using the interface method
            is_healthy, issue = agent_monitor.check_agent(agent)

            # Determine if idle or crashed based on issue
            is_idle = False
            is_crashed = False

            if not is_healthy and issue:
                if "idle" in issue.lower():
                    is_idle = True
                elif "crash" in issue.lower() or "error" in issue.lower():
                    is_crashed = True
                else:
                    # Default to idle for other issues
                    is_idle = True

            # Update state tracker with agent state
            state_tracker.update_agent_state(
                agent.target,
                {
                    "is_idle": is_idle,
                    "is_crashed": is_crashed,
                    "is_healthy": is_healthy,
                    "issue": issue,
                    "last_checked": datetime.now(),
                },
            )

            return is_idle, is_crashed

        except Exception as e:
            if logger:
                logger.error(f"Error analyzing agent {agent.target}: {e}")
            return False, False

    async def _process_notifications(
        self,
        idle_agents: list[AgentInfo],
        crashed_agents: list[AgentInfo],
        pm_issues: list[dict[str, Any]],
        notification_manager: NotificationManagerInterface,
        state_tracker: StateTrackerInterface,
        logger: Any | None,
    ) -> None:
        """Process and send notifications.

        Args:
            idle_agents: List of idle agents
            crashed_agents: List of crashed agents
            pm_issues: List of PM issues
            notification_manager: Notification manager component
            state_tracker: State tracker component
            logger: Optional logger
        """
        # Send crash notifications using interface methods
        for agent in crashed_agents:
            notification_manager.notify_agent_crash(
                agent_target=agent.target, error_message=f"Agent {agent.name} has crashed", session=agent.session
            )

        # Send idle notifications (with threshold check)
        for agent in idle_agents:
            idle_duration = state_tracker.get_idle_duration(agent.target)

            # Only notify if idle for significant time
            if idle_duration and idle_duration > 300:  # 5 minutes
                # Check if it's a fresh agent
                agent_state = state_tracker.get_agent_state(agent.target)
                if agent_state and agent_state.get("is_fresh"):
                    notification_manager.notify_fresh_agent(agent_target=agent.target)
                else:
                    # Use generic send_notification for idle agents
                    notification_manager.send_notification(
                        event_type="agent_idle",
                        message=f"Agent {agent.name} idle for {idle_duration:.0f}s",
                        details={"target": agent.target, "session": agent.session},
                    )

        # Send PM recovery notifications
        for issue in pm_issues:
            pm_target = issue.get("target", f"{issue['session']}:0")
            notification_manager.notify_recovery_needed(
                agent_target=pm_target, reason=f"PM recovery needed in session {issue['session']}: {issue['issue']}"
            )

        if logger:
            logger.debug(
                f"Processed {len(crashed_agents)} crash, {len(idle_agents)} idle, and {len(pm_issues)} PM notifications"
            )
