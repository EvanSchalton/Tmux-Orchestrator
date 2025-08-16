"""
Async-enhanced polling strategy with caching and connection pooling.

This strategy leverages the TMux connection pool and caching layer
for improved performance while maintaining the sequential monitoring pattern.
"""

import asyncio
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..cache_layer import AgentContentCache, TMuxCommandCache
from ..interfaces import (
    AgentMonitorInterface,
    CrashDetectorInterface,
    MonitoringStrategyInterface,
    NotificationManagerInterface,
    PMRecoveryManagerInterface,
    StateTrackerInterface,
)
from ..metrics_collector import MetricsCollector
from ..tmux_pool import AsyncTMUXManager, TMuxConnectionPool
from ..types import AgentInfo, CacheEntryStatus, MonitorStatus


class AsyncPollingStrategy(MonitoringStrategyInterface):
    """Async-aware polling strategy with performance optimizations."""

    def __init__(
        self,
        tmux_pool: Optional[TMuxConnectionPool] = None,
        agent_cache: Optional[AgentContentCache] = None,
        command_cache: Optional[TMuxCommandCache] = None,
        metrics: Optional[MetricsCollector] = None,
    ):
        """Initialize async polling strategy.

        Args:
            tmux_pool: TMux connection pool
            agent_cache: Agent content cache
            command_cache: TMux command cache
            metrics: Metrics collector
        """
        self.tmux_pool = tmux_pool
        self.agent_cache = agent_cache
        self.command_cache = command_cache
        self.metrics = metrics
        self._async_tmux: Optional[AsyncTMUXManager] = None

    def get_name(self) -> str:
        """Get strategy name."""
        return "async_polling"

    def get_description(self) -> str:
        """Get strategy description."""
        return "Async-enhanced polling with caching and connection pooling"

    async def execute(self, context: Dict[str, Any]) -> MonitorStatus:
        """Execute the async polling strategy.

        Args:
            context: Execution context with components

        Returns:
            MonitorStatus with cycle results
        """
        # Initialize async components if not provided
        await self._ensure_async_components(context)

        # Extract components
        agent_monitor = context["agent_monitor"]
        state_tracker = context["state_tracker"]
        crash_detector = context["crash_detector"]
        notification_manager = context["notification_manager"]
        pm_recovery_manager = context["pm_recovery_manager"]
        logger = context.get("logger")

        # Start timing
        _cycle_start = time.time()
        if self.metrics:
            self.metrics.start_timer("monitoring.cycle")

        # Initialize status
        status = MonitorStatus(
            start_time=context.get("start_time", datetime.now()),
            agents_monitored=0,
            agents_healthy=0,
            agents_idle=0,
            agents_crashed=0,
            cycle_count=context.get("cycle_count", 0),
            errors_detected=0,
        )

        try:
            # Phase 1: Discover agents with caching
            agents = await self._discover_agents_cached(agent_monitor)
            status.agents_monitored = len(agents)

            if logger:
                logger.debug(f"Discovered {len(agents)} agents for monitoring")

            # Phase 2: Monitor agents with optimizations
            await self._monitor_agents_optimized(
                agents, agent_monitor, state_tracker, crash_detector, notification_manager, status, logger
            )

            # Phase 3: Check PM health across sessions
            sessions = state_tracker.get_all_sessions()
            await self._check_pm_health_async(sessions, pm_recovery_manager, notification_manager, logger)

            # Phase 4: Send notifications
            notifications_sent = notification_manager.send_queued_notifications()
            if notifications_sent > 0 and logger:
                logger.info(f"Sent {notifications_sent} notification batches")

            # Update final status
            status.end_time = datetime.now()

            # Record metrics
            if self.metrics:
                _cycle_duration = self.metrics.stop_timer("monitoring.cycle")
                self.metrics.record_monitor_cycle(status)

                # Record cache statistics
                if self.agent_cache:
                    cache_stats = self.agent_cache.get_stats()
                    self.metrics.set_gauge("cache.agent.hit_rate", cache_stats["hit_rate"])
                    self.metrics.set_gauge("cache.agent.entries", float(cache_stats["entries"]))

            return status

        except Exception as e:
            if logger:
                logger.error(f"Error in async polling strategy: {e}")
            status.errors_detected += 1
            status.end_time = datetime.now()
            return status

    async def _ensure_async_components(self, context: Dict[str, Any]) -> None:
        """Ensure async components are initialized."""
        # Initialize pool if not provided
        if not self.tmux_pool:
            self.tmux_pool = TMuxConnectionPool(min_size=5, max_size=20, logger=context.get("logger"))
            await self.tmux_pool.initialize()

        # Create async TMux manager
        self._async_tmux = AsyncTMUXManager(self.tmux_pool)

        # Initialize caches if not provided
        if not self.agent_cache:
            self.agent_cache = AgentContentCache(metrics_collector=self.metrics, logger=context.get("logger"))
            await self.agent_cache.initialize()

        if not self.command_cache:
            self.command_cache = TMuxCommandCache(metrics_collector=self.metrics, logger=context.get("logger"))
            await self.command_cache.initialize()

    async def _discover_agents_cached(self, agent_monitor: AgentMonitorInterface) -> List[AgentInfo]:
        """Discover agents with caching."""
        # Check cache first
        if self.command_cache:
            sessions, cache_status = await self.command_cache.get_sessions()

            if cache_status == CacheEntryStatus.FRESH:
                # Use cached data to build agent list
                agents = []
                for session in sessions:
                    windows, window_status = await self.command_cache.get_windows(session["name"])
                    if window_status in [CacheEntryStatus.FRESH, CacheEntryStatus.STALE]:
                        # Build agents from cached data
                        for window in windows:
                            if agent_monitor.is_agent_window(f"{session['name']}:{window['index']}"):
                                agent_info = AgentInfo(
                                    target=f"{session['name']}:{window['index']}",
                                    session=session["name"],
                                    window=str(window["index"]),
                                    name=window.get("name", ""),
                                    type="agent",
                                    status="active",
                                )
                                agents.append(agent_info)

                if agents:
                    return agents

        # Fall back to direct discovery
        agents = agent_monitor.discover_agents()

        # Cache the session/window data for next time
        if self.command_cache and self._async_tmux:
            try:
                sessions = await self._async_tmux.list_sessions_async()
                await self.command_cache.set_sessions(sessions)

                for session in sessions:
                    windows = await self._async_tmux.list_windows_async(session["name"])
                    await self.command_cache.set_windows(session["name"], windows)
            except Exception:
                pass  # Cache population is best-effort

        return agents

    async def _monitor_agents_optimized(
        self,
        agents: List[AgentInfo],
        agent_monitor: AgentMonitorInterface,
        state_tracker: StateTrackerInterface,
        crash_detector: CrashDetectorInterface,
        notification_manager: NotificationManagerInterface,
        status: MonitorStatus,
        logger: Optional[Any],
    ) -> None:
        """Monitor agents with caching and async optimizations."""
        for agent_info in agents:
            try:
                # Check cache first
                content = None
                cache_hit = False

                if self.agent_cache:
                    cached_content, cache_status = await self.agent_cache.get_agent_content(
                        agent_info.session, agent_info.window
                    )

                    if cache_status in [CacheEntryStatus.FRESH, CacheEntryStatus.STALE]:
                        content = cached_content
                        cache_hit = True

                        if self.metrics:
                            self.metrics.increment_counter("agent.cache_hits")

                # Fetch content if not cached
                if content is None and self._async_tmux:
                    if self.metrics:
                        self.metrics.start_timer("agent.content_fetch")

                    content = await self._async_tmux.capture_pane_async(agent_info.target, lines=50)

                    if self.metrics:
                        self.metrics.stop_timer("agent.content_fetch")

                    # Cache for next time
                    if self.agent_cache and content:
                        await self.agent_cache.set_agent_content(agent_info.session, agent_info.window, content)

                # Fall back to sync method if needed
                if content is None:
                    idle_analysis = agent_monitor.analyze_agent_content(agent_info.target)
                    content = idle_analysis.content

                # Update state
                agent_state = state_tracker.update_agent_state(agent_info.target, content)

                # Check for crashes
                is_crashed, crash_reason = crash_detector.detect_crash(
                    agent_info,
                    content.split("\n") if content else [],
                    state_tracker.get_idle_duration(agent_info.target),
                )

                if is_crashed:
                    status.agents_crashed += 1
                    notification_manager.notify_agent_crash(
                        target=agent_info.target, error_type=crash_reason or "Unknown error", session=agent_info.session
                    )
                elif state_tracker.is_agent_idle(agent_info.target):
                    status.agents_idle += 1

                    # Update cache with longer TTL for idle agents
                    if self.agent_cache and not cache_hit:
                        await self.agent_cache.set_agent_content(
                            agent_info.session, agent_info.window, content, is_idle=True
                        )

                    # Send appropriate notifications
                    if agent_state.is_fresh:
                        notification_manager.notify_fresh_agent(target=agent_info.target, session=agent_info.session)
                else:
                    status.agents_healthy += 1

            except Exception as e:
                if logger:
                    logger.error(f"Error monitoring agent {agent_info.target}: {e}")
                status.errors_detected += 1

    async def _check_pm_health_async(
        self,
        sessions: List[str],
        pm_recovery_manager: PMRecoveryManagerInterface,
        notification_manager: NotificationManagerInterface,
        logger: Optional[Any],
    ) -> None:
        """Check PM health asynchronously."""
        # Create tasks for parallel PM checks
        tasks = []
        for session in sessions:
            task = self._check_single_pm_async(session, pm_recovery_manager, notification_manager, logger)
            tasks.append(task)

        # Execute PM checks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Log any errors
        for session, result in zip(sessions, results):
            if isinstance(result, Exception) and logger:
                logger.error(f"Error checking PM in session {session}: {result}")

    async def _check_single_pm_async(
        self,
        session: str,
        pm_recovery_manager: PMRecoveryManagerInterface,
        notification_manager: NotificationManagerInterface,
        logger: Optional[Any],
    ) -> None:
        """Check a single PM asynchronously."""
        try:
            is_healthy, pm_target, issue = pm_recovery_manager.check_pm_health(session)

            if not is_healthy and pm_recovery_manager.should_attempt_recovery(session):
                if logger:
                    logger.warning(f"PM issue detected in {session}: {issue}")

                notification_manager.notify_recovery_needed(
                    target=pm_target or session, issue=issue or "PM not found", session=session
                )

                if pm_recovery_manager.recover_pm(session, pm_target):
                    if logger:
                        logger.info(f"Successfully recovered PM in {session}")

                    # Invalidate cache for recovered session
                    if self.agent_cache:
                        await self.agent_cache.invalidate_session(session)
                else:
                    if logger:
                        logger.error(f"Failed to recover PM in {session}")

        except Exception as e:
            if logger:
                logger.error(f"Error in async PM health check: {e}")
            raise

    def get_required_components(self) -> List[type]:
        """Get required component interfaces."""
        return [
            AgentMonitorInterface,
            StateTrackerInterface,
            CrashDetectorInterface,
            NotificationManagerInterface,
            PMRecoveryManagerInterface,
        ]

    async def cleanup(self) -> None:
        """Clean up async resources."""
        # Clean up caches
        for cache in [self.agent_cache, self.command_cache]:
            if cache:
                await cache.cleanup()

        # Note: Pool cleanup should be handled by the service that created it
