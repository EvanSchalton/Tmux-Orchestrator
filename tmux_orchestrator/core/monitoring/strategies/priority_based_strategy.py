"""
Priority-based monitoring strategy example.

This plugin demonstrates how to create a custom monitoring strategy that
prioritizes agents based on configurable criteria such as role, session,
crash history, and idle patterns.
"""

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import IntEnum
from typing import Any, Optional

from ..interfaces import (
    AgentMonitorInterface,
    CrashDetectorInterface,
    MonitoringStrategyInterface,
    NotificationManagerInterface,
    PMRecoveryManagerInterface,
    StateTrackerInterface,
)
from ..types import AgentInfo, MonitorStatus

# Plugin metadata
__version__ = "1.0.0"
__author__ = "Tmux Orchestrator Team"
__description__ = "Priority-based monitoring that checks critical agents first"


class AgentPriority(IntEnum):
    """Priority levels for agents."""

    CRITICAL = 1  # Highest priority
    HIGH = 2
    NORMAL = 3
    LOW = 4
    MINIMAL = 5  # Lowest priority


@dataclass
class PrioritizedAgent:
    """Agent with priority metadata."""

    agent_info: AgentInfo
    priority: AgentPriority
    priority_score: float
    reason: str


class PriorityBasedStrategy(MonitoringStrategyInterface):
    """
    Monitoring strategy that prioritizes agents based on configurable criteria.

    This strategy demonstrates:
    - Custom agent prioritization
    - Configurable monitoring behavior
    - Adaptive monitoring based on agent history
    - Efficient resource usage for large agent pools
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """Initialize priority-based strategy.

        Args:
            config: Configuration options including:
                - critical_roles: List of role patterns for critical agents
                - priority_sessions: Session patterns to prioritize
                - max_concurrent_checks: Maximum parallel health checks
                - adaptive_mode: Enable adaptive prioritization
                - check_timeout: Timeout for individual checks
        """
        self.config = config or {}

        # Configuration with defaults
        self.critical_roles = self.config.get(
            "critical_roles",
            [
                r".*pm.*",  # Project managers
                r".*orchestrator.*",  # Orchestrators
                r".*api.*",  # API services
                r".*database.*",  # Database agents
            ],
        )

        self.priority_sessions = self.config.get(
            "priority_sessions",
            [
                r".*production.*",
                r".*prod-.*",
                r".*critical.*",
            ],
        )

        self.max_concurrent = self.config.get("max_concurrent_checks", 5)
        self.adaptive_mode = self.config.get("adaptive_mode", True)
        self.check_timeout = self.config.get("check_timeout", 10.0)

        # Runtime state
        self.crash_history: dict[str, list[datetime]] = {}
        self.false_positive_agents: set[str] = set()

    def get_name(self) -> str:
        """Get strategy name."""
        return "priority_based"

    def get_description(self) -> str:
        """Get strategy description."""
        return (
            f"Priority-based monitoring with {self.max_concurrent} concurrent checks. "
            f"Adaptive mode: {'enabled' if self.adaptive_mode else 'disabled'}"
        )

    async def execute(self, context: dict[str, Any]) -> MonitorStatus:
        """Execute priority-based monitoring.

        Args:
            context: Execution context with components

        Returns:
            MonitorStatus with results
        """
        # Extract components
        agent_monitor = context["agent_monitor"]
        state_tracker = context["state_tracker"]
        crash_detector = context["crash_detector"]
        notification_manager = context["notification_manager"]
        pm_recovery_manager = context["pm_recovery_manager"]
        logger = context.get("logger")
        metrics = context.get("metrics")

        # Initialize status
        status = MonitorStatus(
            start_time=datetime.now(),
            agents_monitored=0,
            agents_healthy=0,
            agents_idle=0,
            agents_crashed=0,
            cycle_count=context.get("cycle_count", 0),
            errors_detected=0,
        )

        try:
            # Phase 1: Discover and prioritize agents
            if metrics:
                metrics.start_timer("priority.discovery")

            agents = agent_monitor.discover_agents()
            prioritized_agents = self._prioritize_agents(agents, state_tracker)

            if metrics:
                metrics.stop_timer("priority.discovery")
                metrics.record_histogram("priority.agent_count", len(agents))

            if logger:
                logger.info(
                    f"Discovered {len(agents)} agents: "
                    f"{sum(1 for a in prioritized_agents if a.priority == AgentPriority.CRITICAL)} critical, "
                    f"{sum(1 for a in prioritized_agents if a.priority == AgentPriority.HIGH)} high priority"
                )

            # Phase 2: Check critical agents first (serial for immediate attention)
            critical_agents = [a for a in prioritized_agents if a.priority == AgentPriority.CRITICAL]

            for p_agent in critical_agents:
                await self._check_agent(
                    p_agent, agent_monitor, state_tracker, crash_detector, notification_manager, status, logger, metrics
                )
                status.agents_monitored += 1

            # Phase 3: Check remaining agents in priority order (concurrent batches)
            remaining_agents = [a for a in prioritized_agents if a.priority != AgentPriority.CRITICAL]

            # Process in priority batches
            for priority in [AgentPriority.HIGH, AgentPriority.NORMAL, AgentPriority.LOW, AgentPriority.MINIMAL]:
                batch = [a for a in remaining_agents if a.priority == priority]

                if not batch:
                    continue

                # Process batch concurrently
                await self._check_batch_concurrent(
                    batch, agent_monitor, state_tracker, crash_detector, notification_manager, status, logger, metrics
                )

                status.agents_monitored += len(batch)

                # Early exit if taking too long
                elapsed = (datetime.now() - status.start_time).total_seconds()
                if elapsed > 30 and priority >= AgentPriority.LOW:
                    if logger:
                        logger.warning(
                            f"Monitoring cycle running long ({elapsed:.1f}s), "
                            f"skipping {sum(1 for a in remaining_agents if a.priority > priority)} low priority agents"
                        )
                    break

            # Phase 4: PM health checks (always do these)
            await self._check_pm_health(
                state_tracker.get_all_sessions(), pm_recovery_manager, notification_manager, logger
            )

            # Phase 5: Send notifications
            notifications_sent = notification_manager.send_queued_notifications()
            if notifications_sent > 0 and logger:
                logger.info(f"Sent {notifications_sent} notification batches")

            # Update final status
            status.end_time = datetime.now()

            # Record metrics
            if metrics:
                cycle_duration = (status.end_time - status.start_time).total_seconds()
                metrics.record_histogram("priority.cycle_duration", cycle_duration)
                metrics.set_gauge("priority.agents_skipped", len(agents) - status.agents_monitored)

            return status

        except Exception as e:
            if logger:
                logger.error(f"Error in priority-based strategy: {e}")
            status.errors_detected += 1
            status.end_time = datetime.now()
            return status

    def _prioritize_agents(
        self, agents: list[AgentInfo], state_tracker: StateTrackerInterface
    ) -> list[PrioritizedAgent]:
        """Prioritize agents based on configured criteria.

        Args:
            agents: List of discovered agents
            state_tracker: State tracker for agent history

        Returns:
            List of prioritized agents sorted by priority
        """
        prioritized = []

        for agent in agents:
            # Calculate priority based on multiple factors
            priority = AgentPriority.NORMAL
            score = 0.0
            reasons = []

            # 1. Check critical roles
            agent_name = agent.name.lower()
            for pattern in self.critical_roles:
                if re.match(pattern, agent_name, re.IGNORECASE):
                    priority = AgentPriority.CRITICAL
                    score += 100
                    reasons.append(f"critical role: {pattern}")
                    break

            # 2. Check priority sessions
            for pattern in self.priority_sessions:
                if re.match(pattern, agent.session, re.IGNORECASE):
                    if priority > AgentPriority.HIGH:
                        priority = AgentPriority.HIGH
                    score += 50
                    reasons.append(f"priority session: {pattern}")
                    break

            # 3. Check crash history (adaptive)
            if self.adaptive_mode:
                recent_crashes = self._get_recent_crashes(agent.target)
                if recent_crashes > 2:
                    if priority > AgentPriority.HIGH:
                        priority = AgentPriority.HIGH
                    score += 30 * recent_crashes
                    reasons.append(f"crash-prone ({recent_crashes} recent)")
                elif recent_crashes == 0 and agent.target not in self.false_positive_agents:
                    # Stable agents can be checked less frequently
                    if priority == AgentPriority.NORMAL:
                        priority = AgentPriority.LOW
                    score -= 20
                    reasons.append("stable history")

            # 4. Check current state
            agent_state = state_tracker.get_agent_state(agent.target)
            if agent_state:
                # Fresh agents need attention
                if agent_state.is_fresh:
                    if priority > AgentPriority.HIGH:
                        priority = AgentPriority.HIGH
                    score += 40
                    reasons.append("fresh agent")

                # Long idle agents might need help
                idle_duration = state_tracker.get_idle_duration(agent.target)
                if idle_duration and idle_duration > 600:  # 10 minutes
                    score += 20
                    reasons.append(f"long idle ({idle_duration:.0f}s)")

            # 5. PM agents always high priority
            if "pm" in agent_name or "project" in agent_name:
                if priority > AgentPriority.HIGH:
                    priority = AgentPriority.HIGH
                score += 60
                reasons.append("project manager")

            # Create prioritized agent
            p_agent = PrioritizedAgent(
                agent_info=agent, priority=priority, priority_score=score, reason=", ".join(reasons) or "default"
            )
            prioritized.append(p_agent)

        # Sort by priority (ascending) then score (descending)
        prioritized.sort(key=lambda a: (a.priority, -a.priority_score))

        return prioritized

    async def _check_agent(
        self,
        p_agent: PrioritizedAgent,
        agent_monitor: AgentMonitorInterface,
        state_tracker: StateTrackerInterface,
        crash_detector: CrashDetectorInterface,
        notification_manager: NotificationManagerInterface,
        status: MonitorStatus,
        logger: Any | None,
        metrics: Any | None,
    ) -> None:
        """Check a single prioritized agent."""
        agent_info = p_agent.agent_info

        try:
            # Add timeout for low priority agents
            timeout = None if p_agent.priority <= AgentPriority.HIGH else self.check_timeout

            if timeout:
                await asyncio.wait_for(
                    self._perform_agent_check(
                        agent_info, agent_monitor, state_tracker, crash_detector, notification_manager, status, logger
                    ),
                    timeout=timeout,
                )
            else:
                await self._perform_agent_check(
                    agent_info, agent_monitor, state_tracker, crash_detector, notification_manager, status, logger
                )

            # Record priority metrics
            if metrics:
                metrics.increment_counter(f"priority.checked.{p_agent.priority.name.lower()}")

        except asyncio.TimeoutError:
            if logger:
                logger.warning(f"Timeout checking {agent_info.target} (priority: {p_agent.priority.name})")
            status.errors_detected += 1
        except Exception as e:
            if logger:
                logger.error(f"Error checking {agent_info.target}: {e}")
            status.errors_detected += 1

    async def _perform_agent_check(
        self,
        agent_info: AgentInfo,
        agent_monitor: AgentMonitorInterface,
        state_tracker: StateTrackerInterface,
        crash_detector: CrashDetectorInterface,
        notification_manager: NotificationManagerInterface,
        status: MonitorStatus,
        logger: Any | None,
    ) -> None:
        """Perform the actual agent health check."""
        # Analyze agent content
        idle_analysis = agent_monitor.analyze_agent_content(agent_info.target)

        # Update state
        agent_state = state_tracker.update_agent_state(agent_info.target, idle_analysis.content)

        # Check for crashes
        is_crashed, crash_reason = crash_detector.detect_crash(
            agent_info, idle_analysis.content.split("\n"), state_tracker.get_idle_duration(agent_info.target)
        )

        if is_crashed:
            status.agents_crashed += 1
            self._record_crash(agent_info.target)

            notification_manager.notify_agent_crash(
                target=agent_info.target, error_type=crash_reason or "Unknown error", session=agent_info.session
            )
        elif idle_analysis.is_idle:
            status.agents_idle += 1

            if agent_state.is_fresh:
                notification_manager.notify_fresh_agent(target=agent_info.target, session=agent_info.session)
        else:
            status.agents_healthy += 1

            # Track stable agents
            if self.adaptive_mode and agent_info.target not in self.false_positive_agents:
                if self._get_recent_crashes(agent_info.target) == 0:
                    self.false_positive_agents.add(agent_info.target)

    async def _check_batch_concurrent(
        self,
        batch: list[PrioritizedAgent],
        agent_monitor: AgentMonitorInterface,
        state_tracker: StateTrackerInterface,
        crash_detector: CrashDetectorInterface,
        notification_manager: NotificationManagerInterface,
        status: MonitorStatus,
        logger: Any | None,
        metrics: Any | None,
    ) -> None:
        """Check a batch of agents concurrently."""
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def check_with_semaphore(p_agent):
            async with semaphore:
                await self._check_agent(
                    p_agent, agent_monitor, state_tracker, crash_detector, notification_manager, status, logger, metrics
                )

        # Check all agents in batch
        tasks = [check_with_semaphore(p_agent) for p_agent in batch]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _check_pm_health(
        self,
        sessions: list[str],
        pm_recovery_manager: PMRecoveryManagerInterface,
        notification_manager: NotificationManagerInterface,
        logger: Any | None,
    ) -> None:
        """Check PM health for all sessions."""
        for session in sessions:
            try:
                is_healthy, pm_target, issue = pm_recovery_manager.check_pm_health(session)

                if not is_healthy and pm_recovery_manager.should_attempt_recovery(session):
                    if logger:
                        logger.warning(f"PM issue in {session}: {issue}")

                    notification_manager.notify_recovery_needed(
                        target=pm_target or session, issue=issue or "PM not found", session=session
                    )

                    if pm_recovery_manager.recover_pm(session, pm_target):
                        if logger:
                            logger.info(f"Recovered PM in {session}")
                    else:
                        if logger:
                            logger.error(f"Failed to recover PM in {session}")

            except Exception as e:
                if logger:
                    logger.error(f"Error checking PM in {session}: {e}")

    def _record_crash(self, target: str) -> None:
        """Record a crash for adaptive prioritization."""
        if target not in self.crash_history:
            self.crash_history[target] = []

        self.crash_history[target].append(datetime.now())

        # Remove from false positive list
        self.false_positive_agents.discard(target)

        # Keep only recent history (last hour)
        cutoff = datetime.now() - timedelta(hours=1)
        self.crash_history[target] = [t for t in self.crash_history[target] if t > cutoff]

    def _get_recent_crashes(self, target: str) -> int:
        """Get number of recent crashes for an agent."""
        if target not in self.crash_history:
            return 0

        # Count crashes in last 30 minutes
        cutoff = datetime.now() - timedelta(minutes=30)
        recent = [t for t in self.crash_history[target] if t > cutoff]
        return len(recent)

    def get_required_components(self) -> list[type]:
        """Get required component interfaces."""
        return [
            AgentMonitorInterface,
            StateTrackerInterface,
            CrashDetectorInterface,
            NotificationManagerInterface,
            PMRecoveryManagerInterface,
        ]
