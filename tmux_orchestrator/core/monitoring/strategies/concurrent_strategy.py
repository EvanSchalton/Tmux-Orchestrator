"""
Concurrent monitoring strategy for improved scalability.

This strategy monitors agents concurrently using asyncio to improve
performance when dealing with many agents.
"""

import asyncio
from typing import Any

from ..interfaces import (
    AgentMonitorInterface,
    CrashDetectorInterface,
    MonitoringStrategyInterface,
    NotificationManagerInterface,
    PMRecoveryManagerInterface,
    StateTrackerInterface,
)
from ..types import MonitorStatus


class ConcurrentMonitoringStrategy(MonitoringStrategyInterface):
    """Concurrent monitoring strategy using asyncio for parallel agent checks."""

    def __init__(self, max_concurrent: int = 10):
        """Initialize concurrent strategy.

        Args:
            max_concurrent: Maximum number of concurrent agent checks
        """
        self.max_concurrent = max_concurrent

    def get_name(self) -> str:
        """Get strategy name."""
        return "concurrent"

    def get_description(self) -> str:
        """Get strategy description."""
        return f"Concurrent monitoring with up to {self.max_concurrent} parallel agent checks"

    async def execute(self, context: dict[str, Any]) -> MonitorStatus:
        """Execute the concurrent monitoring strategy.

        Args:
            context: Execution context with components

        Returns:
            MonitorStatus with cycle results
        """
        # Extract components
        agent_monitor = context["agent_monitor"]
        state_tracker = context["state_tracker"]
        crash_detector = context["crash_detector"]
        notification_manager = context["notification_manager"]
        pm_recovery_manager = context["pm_recovery_manager"]
        logger = context["logger"]

        # Initialize status
        status = MonitorStatus(
            start_time=context.get("start_time"),
            agents_monitored=0,
            agents_healthy=0,
            agents_idle=0,
            agents_crashed=0,
            cycle_count=context.get("cycle_count", 0),
            errors_detected=0,
        )

        try:
            # Discover agents
            agents = agent_monitor.discover_agents()
            status.agents_monitored = len(agents)

            logger.info(f"Starting concurrent monitoring of {len(agents)} agents")

            # Create semaphore for concurrency control
            semaphore = asyncio.Semaphore(self.max_concurrent)

            # Create monitoring tasks
            tasks = []
            for agent_info in agents:
                task = self._monitor_agent_with_semaphore(
                    agent_info, semaphore, agent_monitor, state_tracker, crash_detector, notification_manager, logger
                )
                tasks.append(task)

            # Execute all monitoring tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error monitoring agent {agents[i].target}: {result}")
                    status.errors_detected += 1
                elif result:
                    # Update status counters based on result
                    if result.get("crashed"):
                        status.agents_crashed += 1
                    elif result.get("idle"):
                        status.agents_idle += 1
                    else:
                        status.agents_healthy += 1

            # Check PMs concurrently
            sessions = state_tracker.get_all_sessions()
            pm_tasks = []

            for session in sessions:
                pm_task = self._check_pm_health_async(session, pm_recovery_manager, notification_manager, logger)
                pm_tasks.append(pm_task)

            # Execute PM checks
            pm_results = await asyncio.gather(*pm_tasks, return_exceptions=True)

            for i, result in enumerate(pm_results):
                if isinstance(result, Exception):
                    logger.error(f"Error checking PM in {sessions[i]}: {result}")
                    status.errors_detected += 1

            # Send notifications
            notifications_sent = notification_manager.send_queued_notifications()
            if notifications_sent > 0:
                logger.info(f"Sent {notifications_sent} notification batches")

            # Update final status
            status.end_time = context.get("end_time")

            return status

        except Exception as e:
            logger.error(f"Fatal error in concurrent strategy: {e}")
            status.errors_detected += 1
            return status

    async def _monitor_agent_with_semaphore(
        self, agent_info, semaphore, agent_monitor, state_tracker, crash_detector, notification_manager, logger
    ):
        """Monitor a single agent with semaphore control.

        Returns:
            dict with monitoring results
        """
        async with semaphore:
            return await self._monitor_agent_async(
                agent_info, agent_monitor, state_tracker, crash_detector, notification_manager, logger
            )

    async def _monitor_agent_async(
        self, agent_info, agent_monitor, state_tracker, crash_detector, notification_manager, logger
    ):
        """Asynchronously monitor a single agent.

        Returns:
            dict with monitoring results
        """
        target = agent_info.target
        result = {"crashed": False, "idle": False, "healthy": False}

        try:
            # Analyze agent content
            idle_analysis = agent_monitor.analyze_agent_content(target)

            # Update state
            agent_state = state_tracker.update_agent_state(target, idle_analysis.content)

            # Check for crashes
            is_crashed, crash_reason = crash_detector.detect_crash(
                agent_info, idle_analysis.content.split("\n"), state_tracker.get_idle_duration(target)
            )

            if is_crashed:
                result["crashed"] = True
                notification_manager.notify_agent_crash(
                    target=target, error_type=crash_reason or "Unknown error", session=agent_info.session
                )

            elif idle_analysis.is_idle:
                result["idle"] = True

                if agent_state.is_fresh:
                    notification_manager.notify_fresh_agent(target=target, session=agent_info.session)
                else:
                    notification_manager.notify_agent_idle(
                        target=target,
                        idle_type=idle_analysis.idle_type,
                        session=agent_info.session,
                        metadata={"idle_duration": idle_analysis.idle_duration},
                    )
            else:
                result["healthy"] = True

            # Check team idle status
            await self._check_team_idle_async(agent_info.session, state_tracker, notification_manager)

            return result

        except Exception as e:
            logger.error(f"Error in async agent monitoring for {target}: {e}")
            raise

    async def _check_pm_health_async(self, session, pm_recovery_manager, notification_manager, logger):
        """Asynchronously check PM health."""
        try:
            is_healthy, pm_target, issue = pm_recovery_manager.check_pm_health(session)

            if not is_healthy and pm_recovery_manager.should_attempt_recovery(session):
                logger.warning(f"PM issue in {session}: {issue}")

                notification_manager.notify_recovery_needed(
                    target=pm_target or session, issue=issue or "PM not found", session=session
                )

                if pm_recovery_manager.recover_pm(session, pm_target):
                    logger.info(f"Recovered PM in {session}")
                else:
                    logger.error(f"Failed to recover PM in {session}")
                    raise RuntimeError(f"PM recovery failed in {session}")

        except Exception as e:
            logger.error(f"Error in async PM health check for {session}: {e}")
            raise

    async def _check_team_idle_async(self, session, state_tracker, notification_manager):
        """Asynchronously check team idle status."""
        session_agents = state_tracker.get_session_agents(session)
        total_agents = len(session_agents)
        idle_agents = sum(1 for a in session_agents if state_tracker.is_agent_idle(a.target))

        if total_agents > 0 and idle_agents == total_agents:
            if not state_tracker.is_team_idle(session):
                state_tracker.set_team_idle(session)
                notification_manager.notify_team_idle(session=session, agent_count=idle_agents)
        else:
            state_tracker.clear_team_idle(session)

    def get_required_components(self) -> list[type]:
        """Get required component interfaces."""
        return [
            AgentMonitorInterface,
            StateTrackerInterface,
            CrashDetectorInterface,
            NotificationManagerInterface,
            PMRecoveryManagerInterface,
        ]
