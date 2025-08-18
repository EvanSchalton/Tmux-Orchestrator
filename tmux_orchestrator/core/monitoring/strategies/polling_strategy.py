"""
Default polling-based monitoring strategy.

This module implements the standard polling strategy that monitors agents
at regular intervals.
"""

import asyncio
from datetime import datetime
from typing import Any

from ..interfaces import (
    AgentMonitorInterface,
    NotificationManagerInterface,
    PMRecoveryManagerInterface,
    StateTrackerInterface,
)
from ..types import AgentInfo, MonitorStatus, NotificationEvent, NotificationType
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
                state_tracker.update_agent_discovered(agent)

            # Phase 2: PM Health Checks
            sessions = state_tracker.get_active_sessions()
            pm_issues = await self._check_pm_health(sessions, pm_recovery_manager, logger)

            # Phase 3: Agent Health Checks
            idle_agents, crashed_agents = await self._check_agent_health(agents, agent_monitor, state_tracker, logger)

            # Phase 4: Process Notifications
            await self._process_notifications(
                idle_agents, crashed_agents, pm_issues, notification_manager, state_tracker, logger
            )

            # Phase 5: State Cleanup
            state_tracker.cleanup_stale_data()

            # Build status
            return MonitorStatus(
                total_agents=len(agents),
                idle_agents=len(idle_agents),
                crashed_agents=len(crashed_agents),
                active_sessions=len(sessions),
                last_check=datetime.now(),
                error=None,
            )

        except Exception as e:
            if logger:
                logger.error(f"Error in polling strategy: {e}")

            return MonitorStatus(
                total_agents=0,
                idle_agents=0,
                crashed_agents=0,
                active_sessions=0,
                last_check=datetime.now(),
                error=str(e),
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
                if isinstance(result, Exception):
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
            # Analyze agent state
            idle_analysis = agent_monitor.analyze_idle_state(agent)

            # Update state tracker
            if idle_analysis.is_idle:
                state_tracker.update_agent_idle(agent, idle_analysis)
            else:
                state_tracker.update_agent_active(agent)

            # Check for crash
            is_crashed = idle_analysis.crash_reason is not None

            if is_crashed:
                state_tracker.update_agent_crashed(agent, idle_analysis.crash_reason)

            return idle_analysis.is_idle, is_crashed

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
        # Queue crash notifications
        for agent in crashed_agents:
            event = NotificationEvent(
                type=NotificationType.AGENT_CRASH,
                agent_info=agent,
                message=f"Agent {agent.name} has crashed",
                timestamp=datetime.now(),
            )
            notification_manager.queue_notification(event)

        # Queue idle notifications (with threshold check)
        for agent in idle_agents:
            idle_duration = state_tracker.get_idle_duration(agent.target)

            # Only notify if idle for significant time
            if idle_duration and idle_duration > 300:  # 5 minutes
                event = NotificationEvent(
                    type=NotificationType.AGENT_IDLE,
                    agent_info=agent,
                    message=f"Agent {agent.name} idle for {idle_duration:.0f}s",
                    timestamp=datetime.now(),
                )
                notification_manager.queue_notification(event)

        # Queue PM recovery notifications
        for issue in pm_issues:
            # Create a minimal agent info for PM
            pm_agent = AgentInfo(
                target=issue.get("target", f"{issue['session']}:0"),
                session=issue["session"],
                window="0",
                name="PM",
                type="pm",
            )

            event = NotificationEvent(
                type=NotificationType.RECOVERY_NEEDED,
                agent_info=pm_agent,
                message=f"PM recovery needed in session {issue['session']}: {issue['issue']}",
                timestamp=datetime.now(),
            )
            notification_manager.queue_notification(event)

        # Process the notification queue
        notification_manager.process_queue()

        if logger:
            logger.debug(
                f"Processed {len(crashed_agents)} crash, "
                f"{len(idle_agents)} idle, and {len(pm_issues)} PM notifications"
            )
