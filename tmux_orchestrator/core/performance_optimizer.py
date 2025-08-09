"""Performance optimization for large-scale agent deployments."""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Optional

from tmux_orchestrator.utils.tmux import TMUXManager


@dataclass
class PerformanceMetrics:
    """Performance metrics for system monitoring."""

    agent_count: int = 0
    response_time_avg: float = 0.0
    response_time_p95: float = 0.0
    cpu_usage: float = 0.0
    memory_usage_mb: float = 0.0
    message_throughput: float = 0.0
    error_rate: float = 0.0
    batch_operations_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0


@dataclass
class OptimizationConfig:
    """Configuration for performance optimization."""

    enable_batching: bool = True
    batch_size: int = 10
    batch_timeout_ms: int = 100
    enable_caching: bool = True
    cache_ttl_seconds: int = 60
    connection_pool_size: int = 20
    max_concurrent_operations: int = 50
    enable_async_operations: bool = True
    response_timeout_seconds: int = 30


class PerformanceOptimizer:
    """Optimize TMUX Orchestrator for 50+ agent deployments."""

    def __init__(self, tmux: TMUXManager, config: Optional[OptimizationConfig] = None) -> None:
        """Initialize performance optimizer."""
        self.tmux = tmux
        self.config = config or OptimizationConfig()
        self._cache: dict[str, tuple[Any, float]] = {}
        self._batch_queue: list[dict[str, Any]] = []
        self._executor = ThreadPoolExecutor(max_workers=self.config.connection_pool_size)
        self._metrics = PerformanceMetrics()

    def optimize_list_operations(self) -> dict[str, list[dict[str, Any]]]:
        """Optimize listing operations with caching and batching."""
        cache_key = "all_agents_list"

        # Check cache first
        if self.config.enable_caching:
            cached = self._get_cached(cache_key)
            if cached is not None:
                self._metrics.cache_hits += 1
                return cached  # type: ignore
            self._metrics.cache_misses += 1

        # Get all sessions and windows in parallel
        sessions = self.tmux.list_sessions() or []

        if self.config.enable_async_operations:
            # Parallel window fetching
            with ThreadPoolExecutor(max_workers=min(len(sessions), self.config.connection_pool_size)) as executor:
                futures = {
                    executor.submit(self._get_session_windows, session["name"]): session
                    for session in sessions
                }

                all_agents = {}
                for future in futures:
                    session = futures[future]
                    windows = future.result()
                    all_agents[session["name"]] = windows
        else:
            # Sequential fallback
            all_agents = {}
            for session in sessions:
                all_agents[session["name"]] = self._get_session_windows(session["name"])

        # Cache results
        if self.config.enable_caching:
            self._set_cached(cache_key, all_agents)

        self._metrics.agent_count = sum(len(windows) for windows in all_agents.values())
        return all_agents

    def batch_send_messages(self, messages: list[dict[str, str]]) -> list[bool]:
        """Send multiple messages in optimized batches."""
        if not self.config.enable_batching:
            # Non-batched fallback
            return [self.tmux.send_keys(msg["target"], msg["content"]) for msg in messages]

        results = []

        # Process in batches
        for i in range(0, len(messages), self.config.batch_size):
            batch = messages[i:i + self.config.batch_size]

            if self.config.enable_async_operations:
                # Parallel batch processing
                with ThreadPoolExecutor(max_workers=self.config.batch_size) as executor:
                    batch_futures = [
                        executor.submit(self.tmux.send_keys, msg["target"], msg["content"])
                        for msg in batch
                    ]
                    batch_results = [f.result() for f in batch_futures]
            else:
                # Sequential batch processing
                batch_results = [
                    self.tmux.send_keys(msg["target"], msg["content"])
                    for msg in batch
                ]

            results.extend(batch_results)
            self._metrics.batch_operations_count += 1

        return results

    def get_agent_status_bulk(self, agent_ids: list[str]) -> dict[str, dict[str, Any]]:
        """Get status for multiple agents efficiently."""
        start_time = time.time()

        if self.config.enable_async_operations:
            # Parallel status fetching
            with ThreadPoolExecutor(max_workers=self.config.max_concurrent_operations) as executor:
                futures = {
                    executor.submit(self._get_single_agent_status, agent_id): agent_id
                    for agent_id in agent_ids
                }

                results = {}
                for future in futures:
                    agent_id = futures[future]
                    try:
                        status = future.result(timeout=self.config.response_timeout_seconds)
                        results[agent_id] = status
                    except Exception as e:
                        results[agent_id] = {"error": str(e), "status": "error"}
                        self._metrics.error_rate += 1
        else:
            # Sequential fallback
            results = {}
            for agent_id in agent_ids:
                try:
                    results[agent_id] = self._get_single_agent_status(agent_id)
                except Exception as e:
                    results[agent_id] = {"error": str(e), "status": "error"}
                    self._metrics.error_rate += 1

        # Update metrics
        elapsed = time.time() - start_time
        self._update_response_metrics(elapsed)

        return results

    def optimize_team_deployment(self, team_size: int) -> dict[str, Any]:
        """Optimize team deployment for large teams."""
        optimization_suggestions: dict[str, Any] = {
            "recommended_batch_size": min(team_size // 5, 20),
            "use_parallel_deployment": team_size > 10,
            "stagger_startup_ms": 100 if team_size > 20 else 0,
            "session_distribution": self._calculate_session_distribution(team_size),
            "resource_limits": self._calculate_resource_limits(team_size),
        }

        if team_size > 50:
            warnings = [
                "Consider splitting into multiple smaller teams",
                "Enable connection pooling for better performance",
                "Monitor system resources during deployment",
            ]
            optimization_suggestions["warnings"] = warnings

        return optimization_suggestions

    def get_performance_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics."""
        # Calculate error rate percentage
        if self._metrics.batch_operations_count > 0:
            self._metrics.error_rate = (self._metrics.error_rate / self._metrics.batch_operations_count) * 100

        return self._metrics

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._cache.clear()
        self._metrics.cache_hits = 0
        self._metrics.cache_misses = 0

    def shutdown(self) -> None:
        """Shutdown performance optimizer and cleanup resources."""
        self._executor.shutdown(wait=True)
        self.clear_cache()

    # Private helper methods

    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self.config.cache_ttl_seconds:
                return value
            else:
                del self._cache[key]
        return None

    def _set_cached(self, key: str, value: Any) -> None:
        """Set cached value with timestamp."""
        self._cache[key] = (value, time.time())

    def _get_session_windows(self, session_name: str) -> list[dict[str, Any]]:
        """Get windows for a session with caching."""
        cache_key = f"session_windows_{session_name}"

        if self.config.enable_caching:
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached  # type: ignore

        windows = self.tmux.list_windows(session_name) or []

        if self.config.enable_caching:
            self._set_cached(cache_key, windows)

        return windows

    def _get_single_agent_status(self, agent_id: str) -> dict[str, Any]:
        """Get status for a single agent."""
        cache_key = f"agent_status_{agent_id}"

        if self.config.enable_caching:
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached  # type: ignore

        # Get agent pane content
        content = self.tmux.capture_pane(agent_id)
        status = {
            "online": content is not None,
            "last_activity": time.time() if content else None,
            "responsive": content is not None and len(content) > 0,
        }

        if self.config.enable_caching:
            self._set_cached(cache_key, status)

        return status

    def _calculate_session_distribution(self, team_size: int) -> dict[str, int]:
        """Calculate optimal session distribution for team size."""
        if team_size <= 10:
            return {"sessions": 1, "agents_per_session": team_size}
        elif team_size <= 30:
            sessions = (team_size + 9) // 10  # 10 agents per session
            return {"sessions": sessions, "agents_per_session": 10}
        else:
            sessions = (team_size + 14) // 15  # 15 agents per session for large teams
            return {"sessions": sessions, "agents_per_session": 15}

    def _calculate_resource_limits(self, team_size: int) -> dict[str, Any]:
        """Calculate recommended resource limits based on team size."""
        base_memory_mb = 512
        memory_per_agent = 256

        return {
            "recommended_memory_mb": base_memory_mb + (team_size * memory_per_agent),
            "recommended_cpu_cores": max(2, team_size // 10),
            "max_concurrent_operations": min(team_size, 50),
            "connection_pool_size": min(team_size // 2, 30),
        }

    def _update_response_metrics(self, response_time: float) -> None:
        """Update response time metrics."""
        # Simple moving average for demo - in production use proper statistics
        if self._metrics.response_time_avg == 0:
            self._metrics.response_time_avg = response_time
        else:
            self._metrics.response_time_avg = (self._metrics.response_time_avg * 0.9) + (response_time * 0.1)

        # Update P95 (simplified)
        if response_time > self._metrics.response_time_p95:
            self._metrics.response_time_p95 = response_time


# Connection pool for MCP operations
class MCPConnectionPool:
    """Connection pooling for MCP server operations."""

    def __init__(self, pool_size: int = 20) -> None:
        """Initialize connection pool."""
        self.pool_size = pool_size
        self._connections: list[Any] = []
        self._available: asyncio.Queue = asyncio.Queue(maxsize=pool_size)
        self._lock = asyncio.Lock()

    async def acquire(self) -> Any:
        """Acquire a connection from the pool."""
        return await self._available.get()

    async def release(self, connection: Any) -> None:
        """Release a connection back to the pool."""
        await self._available.put(connection)

    async def initialize(self) -> None:
        """Initialize the connection pool."""
        async with self._lock:
            for _ in range(self.pool_size):
                # In real implementation, create actual MCP connections
                connection = {"id": len(self._connections), "active": True}
                self._connections.append(connection)
                await self._available.put(connection)

    async def close(self) -> None:
        """Close all connections in the pool."""
        async with self._lock:
            while not self._available.empty():
                await self._available.get()
            self._connections.clear()


def create_optimized_config(agent_count: int) -> OptimizationConfig:
    """Create optimized configuration based on agent count."""
    config = OptimizationConfig()

    if agent_count > 50:
        config.batch_size = 20
        config.connection_pool_size = 30
        config.max_concurrent_operations = 50
        config.cache_ttl_seconds = 120
    elif agent_count > 20:
        config.batch_size = 15
        config.connection_pool_size = 20
        config.max_concurrent_operations = 30
        config.cache_ttl_seconds = 90
    else:
        config.batch_size = 10
        config.connection_pool_size = 10
        config.max_concurrent_operations = 20
        config.cache_ttl_seconds = 60

    return config
