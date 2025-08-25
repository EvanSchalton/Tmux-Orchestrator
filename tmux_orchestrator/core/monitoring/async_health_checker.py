"""Async health checking component with caching and connection pooling."""

import asyncio
import logging
from datetime import datetime
from typing import Any, Optional

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.core.monitoring.cache import LayeredCache
from tmux_orchestrator.core.monitoring.health_checker import AgentHealthStatus, HealthChecker
from tmux_orchestrator.core.monitoring.tmux_pool import AsyncTMUXManager, TMuxConnectionPool
from tmux_orchestrator.utils.tmux import TMUXManager


class AsyncHealthChecker(HealthChecker):
    """Async version of health checker with performance optimizations.

    This class extends the base HealthChecker with async methods that use
    connection pooling and caching for improved performance at scale.
    """

    def __init__(
        self,
        tmux: TMUXManager,
        config: Config,
        logger: logging.Logger,
        tmux_pool: Optional[TMuxConnectionPool] = None,
        cache: Optional[LayeredCache] = None,
    ):
        """Initialize the async health checker.

        Args:
            tmux: TMUX manager instance (for sync compatibility)
            config: Configuration object
            logger: Logger instance
            tmux_pool: Optional TMux connection pool
            cache: Optional layered cache instance
        """
        super().__init__(tmux, config, logger)

        # Async infrastructure
        self.tmux_pool = tmux_pool
        self.async_tmux = AsyncTMUXManager(tmux_pool) if tmux_pool else None
        self.cache = cache or LayeredCache()

        # Async-specific state
        self._check_semaphore = asyncio.Semaphore(20)  # Limit concurrent health checks
        self._pending_checks: dict[str, asyncio.Task] = {}

    async def initialize_async(self) -> bool:
        """Initialize async components."""
        try:
            if self.tmux_pool and not self.tmux_pool._initialized:
                await self.tmux_pool.initialize()

            self.logger.info("AsyncHealthChecker initialized")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize AsyncHealthChecker: {e}")
            return False

    async def check_agent_health_async(self, target: str) -> AgentHealthStatus:
        """Async version of health check with caching and pooling.

        Args:
            target: Target identifier (session:window)

        Returns:
            AgentHealthStatus object with current health information
        """
        # Check if we already have a pending check for this target
        if target in self._pending_checks and not self._pending_checks[target].done():
            # Wait for the existing check to complete
            from typing import cast

            return cast(AgentHealthStatus, await self._pending_checks[target])

        # Create new check task
        check_task = asyncio.create_task(self._do_health_check_async(target))
        self._pending_checks[target] = check_task

        try:
            return await check_task
        finally:
            # Clean up completed task
            self._pending_checks.pop(target, None)

    async def _do_health_check_async(self, target: str) -> AgentHealthStatus:
        """Perform the actual health check with semaphore control."""
        async with self._check_semaphore:
            # Try to get from cache first
            cache_key = f"health_status:{target}"
            cached_status = await self.cache.get("agent_status", cache_key)

            if cached_status:
                # For cached status, still check if content changed
                if self.async_tmux:
                    current_hash = await self._get_content_hash_async(target)
                    if current_hash == cached_status.last_content_hash:
                        from typing import cast

                        return cast(AgentHealthStatus, cached_status)

            # Not in cache or content changed, perform full check
            if target not in self.agent_status:
                self.register_agent(target)

            status = self.agent_status[target]
            now = datetime.now()

            try:
                # Get content asynchronously
                if self.async_tmux:
                    content = await self.async_tmux.capture_pane_async(target, lines=50)
                else:
                    # Fallback to sync in executor
                    loop = asyncio.get_event_loop()
                    content = await loop.run_in_executor(None, self.tmux.capture_pane, target, 50)

                content_hash = str(hash(content))

                # Track activity changes
                if content_hash != status.last_content_hash:
                    status.activity_changes += 1
                    status.last_content_hash = content_hash
                    status.last_heartbeat = now

                # Check idle status asynchronously if idle monitor available
                if self.idle_monitor:
                    loop = asyncio.get_event_loop()
                    is_idle = await loop.run_in_executor(None, self.idle_monitor.is_agent_idle, target)
                    status.is_idle = is_idle
                else:
                    status.is_idle = False

                # Check responsiveness
                is_responsive = await self._check_agent_responsiveness_async(target, content, status.is_idle)

                # Update status
                if is_responsive:
                    status.is_responsive = True
                    status.consecutive_failures = 0
                    status.last_response = now
                    status.status = "healthy"
                else:
                    status.is_responsive = False
                    status.consecutive_failures += 1

                    if status.consecutive_failures >= self.max_failures:
                        status.status = "critical"
                    elif status.consecutive_failures >= 2:
                        status.status = "warning"
                    else:
                        status.status = "unresponsive"

                # Cache the result
                await self.cache.set("agent_status", cache_key, status, ttl=15.0)

            except Exception as e:
                self.logger.error(f"Error in async health check for {target}: {e}")
                status.consecutive_failures += 1
                status.is_responsive = False
                status.status = "critical"

            return status

    async def _get_content_hash_async(self, target: str) -> str:
        """Get content hash asynchronously with caching."""
        cache_key = f"content_hash:{target}"

        async def compute_hash():
            if self.async_tmux:
                content = await self.async_tmux.capture_pane_async(target, lines=50)
            else:
                loop = asyncio.get_event_loop()
                content = await loop.run_in_executor(None, self.tmux.capture_pane, target, 50)
            return str(hash(content))

        return await self.cache.get_layer("pane_content").get_or_compute(cache_key, compute_hash, ttl=5.0)

    async def _check_agent_responsiveness_async(self, target: str, content: str, is_idle: bool) -> bool:
        """Async version of responsiveness check.

        Can be extended to perform async validation checks.
        """
        # For now, delegate to sync version
        # In future, could add async API calls or other checks
        return self._check_agent_responsiveness(target, content, is_idle)

    async def check_multiple_agents_async(
        self, targets: list[str], max_concurrent: int = 10
    ) -> dict[str, AgentHealthStatus]:
        """Check health of multiple agents concurrently.

        Args:
            targets: List of target identifiers
            max_concurrent: Maximum concurrent checks

        Returns:
            Dictionary mapping targets to their health status
        """
        # Create semaphore for this batch
        semaphore = asyncio.Semaphore(max_concurrent)

        async def check_with_semaphore(target: str) -> tuple[str, AgentHealthStatus]:
            async with semaphore:
                status = await self.check_agent_health_async(target)
                return target, status

        # Check all agents concurrently
        tasks = [check_with_semaphore(target) for target in targets]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        statuses = {}
        for result in results:
            if isinstance(result, BaseException):
                self.logger.error(f"Error in batch health check: {result}")
            else:
                target, status = result
                statuses[target] = status

        return statuses

    async def should_attempt_recovery_async(self, target: str, status: Optional[AgentHealthStatus] = None) -> bool:
        """Async version of recovery check with caching."""
        # Check recovery cooldown from cache
        cache_key = f"recovery_cooldown:{target}"
        cooldown_active = await self.cache.get("agent_status", cache_key)

        if cooldown_active:
            return False

        # Use sync logic for the decision
        should_recover = self.should_attempt_recovery(target, status)

        if should_recover:
            # Set cooldown in cache
            await self.cache.set("agent_status", cache_key, True, ttl=float(self.recovery_cooldown))

        return should_recover

    async def mark_recovery_attempted_async(self, target: str) -> None:
        """Async version of marking recovery attempt."""
        # Update local state
        self.mark_recovery_attempted(target)

        # Also set in cache for distributed coordination
        cache_key = f"recovery_attempt:{target}"
        await self.cache.set("agent_status", cache_key, datetime.now().isoformat(), ttl=float(self.recovery_cooldown))

    async def get_health_summary_async(self) -> dict[str, Any]:
        """Get async health summary with statistics."""
        all_statuses = self.get_all_agent_statuses()

        healthy = sum(1 for s in all_statuses.values() if s.status == "healthy")
        warning = sum(1 for s in all_statuses.values() if s.status == "warning")
        critical = sum(1 for s in all_statuses.values() if s.status == "critical")
        unresponsive = sum(1 for s in all_statuses.values() if s.status == "unresponsive")

        # Get cache stats
        cache_stats = self.cache.get_layer("agent_status").get_stats()

        # Get pool stats if available
        pool_stats = {}
        if self.tmux_pool:
            pool_stats = self.tmux_pool.get_stats()

        return {
            "total_agents": len(all_statuses),
            "healthy": healthy,
            "warning": warning,
            "critical": critical,
            "unresponsive": unresponsive,
            "cache_stats": cache_stats,
            "pool_stats": pool_stats,
            "timestamp": datetime.now().isoformat(),
        }

    async def cleanup_async(self) -> None:
        """Async cleanup of resources."""
        # Cancel any pending checks
        for task in self._pending_checks.values():
            if not task.done():
                task.cancel()

        # Wait for cancellations
        if self._pending_checks:
            await asyncio.gather(*self._pending_checks.values(), return_exceptions=True)

        self._pending_checks.clear()

        # Clear cache
        await self.cache.clear_all()

        # Run sync cleanup
        self.cleanup()
