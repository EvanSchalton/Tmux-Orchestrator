"""Tests for performance optimizer."""

import asyncio
import time
from unittest.mock import Mock

import pytest

from tmux_orchestrator.core.performance_optimizer import (
    MCPConnectionPool,
    OptimizationConfig,
    PerformanceOptimizer,
    create_optimized_config,
)
from tmux_orchestrator.utils.tmux import TMUXManager


class TestPerformanceOptimizer:
    """Test cases for performance optimizer."""

    @pytest.fixture
    def tmux(self) -> Mock:
        """Create mock TMUXManager."""
        return Mock(spec=TMUXManager)

    @pytest.fixture
    def optimizer(self, tmux: Mock) -> PerformanceOptimizer:
        """Create performance optimizer instance."""
        return PerformanceOptimizer(tmux)

    def test_optimize_list_operations_with_cache(self, optimizer: PerformanceOptimizer, tmux: Mock) -> None:
        """Test list operations optimization with caching."""
        # Mock tmux responses
        tmux.list_sessions.return_value = [
            {"name": "project1", "created": "123"},
            {"name": "project2", "created": "124"},
        ]
        tmux.list_windows.side_effect = [
            [{"index": "0", "name": "main"}],
            [{"index": "0", "name": "main"}, {"index": "1", "name": "dev"}],
        ]

        # First call - cache miss
        result1 = optimizer.optimize_list_operations()
        assert optimizer._metrics.cache_misses == 1
        assert optimizer._metrics.cache_hits == 0
        assert len(result1) == 2
        assert len(result1["project1"]) == 1
        assert len(result1["project2"]) == 2

        # Second call - cache hit
        result2 = optimizer.optimize_list_operations()
        assert optimizer._metrics.cache_hits == 1
        assert result1 == result2

        # Verify tmux was only called once
        assert tmux.list_sessions.call_count == 1

    def test_optimize_list_operations_parallel(self, tmux: Mock) -> None:
        """Test parallel window fetching."""
        config = OptimizationConfig(enable_async_operations=True)
        optimizer = PerformanceOptimizer(tmux, config)

        # Mock many sessions
        sessions = [{"name": f"project{i}", "created": str(i)} for i in range(10)]
        tmux.list_sessions.return_value = sessions
        tmux.list_windows.return_value = [{"index": "0", "name": "main"}]

        result = optimizer.optimize_list_operations()

        assert len(result) == 10
        assert optimizer._metrics.agent_count == 10

    def test_batch_send_messages(self, optimizer: PerformanceOptimizer, tmux: Mock) -> None:
        """Test batch message sending."""
        tmux.send_keys.return_value = True

        messages = [{"target": f"session{i}:0", "content": f"Message {i}"} for i in range(25)]

        results = optimizer.batch_send_messages(messages)

        assert len(results) == 25
        assert all(results)
        assert optimizer._metrics.batch_operations_count == 3  # 25 messages / 10 batch size

    def test_batch_send_messages_disabled(self, tmux: Mock) -> None:
        """Test message sending with batching disabled."""
        config = OptimizationConfig(enable_batching=False)
        optimizer = PerformanceOptimizer(tmux, config)
        tmux.send_keys.return_value = True

        messages = [{"target": f"session{i}:0", "content": f"Message {i}"} for i in range(5)]

        results = optimizer.batch_send_messages(messages)

        assert len(results) == 5
        assert tmux.send_keys.call_count == 5
        assert optimizer._metrics.batch_operations_count == 0

    def test_get_agent_status_bulk(self, optimizer: PerformanceOptimizer, tmux: Mock) -> None:
        """Test bulk agent status retrieval."""
        tmux.capture_pane.side_effect = lambda agent_id: f"Content for {agent_id}"

        agent_ids = [f"session{i}:0" for i in range(5)]
        results = optimizer.get_agent_status_bulk(agent_ids)

        assert len(results) == 5
        for agent_id in agent_ids:
            assert agent_id in results
            assert results[agent_id]["online"]
            assert results[agent_id]["responsive"]

    def test_get_agent_status_bulk_with_errors(self, optimizer: PerformanceOptimizer, tmux: Mock) -> None:
        """Test bulk status retrieval with some errors."""

        def mock_capture(agent_id):
            if "2" in agent_id:
                raise Exception("Connection failed")
            return f"Content for {agent_id}"

        tmux.capture_pane.side_effect = mock_capture

        agent_ids = [f"session{i}:0" for i in range(5)]
        results = optimizer.get_agent_status_bulk(agent_ids)

        assert len(results) == 5
        assert "error" in results["session2:0"]
        assert results["session2:0"]["status"] == "error"
        assert optimizer._metrics.error_rate > 0

    def test_optimize_team_deployment_small(self, optimizer: PerformanceOptimizer) -> None:
        """Test team deployment optimization for small teams."""
        result = optimizer.optimize_team_deployment(5)

        assert result["recommended_batch_size"] == 1
        assert not result["use_parallel_deployment"]
        assert result["stagger_startup_ms"] == 0
        assert result["session_distribution"]["sessions"] == 1
        assert result["session_distribution"]["agents_per_session"] == 5

    def test_optimize_team_deployment_medium(self, optimizer: PerformanceOptimizer) -> None:
        """Test team deployment optimization for medium teams."""
        result = optimizer.optimize_team_deployment(25)

        assert result["recommended_batch_size"] == 5
        assert result["use_parallel_deployment"]
        assert result["stagger_startup_ms"] == 100
        assert result["session_distribution"]["sessions"] == 3
        assert result["session_distribution"]["agents_per_session"] == 10

    def test_optimize_team_deployment_large(self, optimizer: PerformanceOptimizer) -> None:
        """Test team deployment optimization for large teams."""
        result = optimizer.optimize_team_deployment(75)

        assert result["recommended_batch_size"] == 15
        assert result["use_parallel_deployment"]
        assert result["stagger_startup_ms"] == 100
        assert result["session_distribution"]["sessions"] == 5
        assert result["session_distribution"]["agents_per_session"] == 15
        assert "warnings" in result
        assert len(result["warnings"]) > 0

    def test_cache_expiration(self, tmux: Mock) -> None:
        """Test cache expiration."""
        config = OptimizationConfig(cache_ttl_seconds=1)
        optimizer = PerformanceOptimizer(tmux, config)

        tmux.list_sessions.return_value = [{"name": "test", "created": "123"}]
        tmux.list_windows.return_value = []

        # First call
        optimizer.optimize_list_operations()
        assert optimizer._metrics.cache_misses == 1

        # Wait for cache to expire
        time.sleep(1.1)

        # Second call should miss cache
        optimizer.optimize_list_operations()
        assert optimizer._metrics.cache_misses == 2
        assert tmux.list_sessions.call_count == 2

    def test_clear_cache(self, optimizer: PerformanceOptimizer) -> None:
        """Test cache clearing."""
        # Add some cached data
        optimizer._set_cached("test_key", "test_value")
        assert optimizer._get_cached("test_key") == "test_value"

        # Clear cache
        optimizer.clear_cache()
        assert optimizer._get_cached("test_key") is None
        assert optimizer._metrics.cache_hits == 0
        assert optimizer._metrics.cache_misses == 0

    def test_performance_metrics(self, optimizer: PerformanceOptimizer) -> None:
        """Test performance metrics calculation."""
        # Simulate some operations
        optimizer._metrics.batch_operations_count = 10
        optimizer._metrics.error_rate = 2  # 2 errors
        optimizer._update_response_metrics(0.5)
        optimizer._update_response_metrics(0.3)

        metrics = optimizer.get_performance_metrics()

        assert metrics.error_rate == 20.0  # 2/10 * 100
        assert metrics.response_time_avg > 0
        assert metrics.response_time_p95 >= 0.5

    def test_shutdown(self, optimizer: PerformanceOptimizer) -> None:
        """Test optimizer shutdown."""
        # Add some data
        optimizer._set_cached("test", "value")

        # Shutdown
        optimizer.shutdown()

        # Verify cleanup
        assert len(optimizer._cache) == 0
        assert optimizer._executor._shutdown

    def test_create_optimized_config_small(self) -> None:
        """Test config creation for small deployments."""
        config = create_optimized_config(10)

        assert config.batch_size == 10
        assert config.connection_pool_size == 10
        assert config.max_concurrent_operations == 20

    def test_create_optimized_config_medium(self) -> None:
        """Test config creation for medium deployments."""
        config = create_optimized_config(30)

        assert config.batch_size == 15
        assert config.connection_pool_size == 20
        assert config.max_concurrent_operations == 30

    def test_create_optimized_config_large(self) -> None:
        """Test config creation for large deployments."""
        config = create_optimized_config(100)

        assert config.batch_size == 20
        assert config.connection_pool_size == 30
        assert config.max_concurrent_operations == 50


class TestMCPConnectionPool:
    """Test cases for MCP connection pool."""

    @pytest.mark.asyncio
    async def test_connection_pool_initialization(self) -> None:
        """Test connection pool initialization."""
        pool = MCPConnectionPool(pool_size=5)
        await pool.initialize()

        assert len(pool._connections) == 5
        assert pool._available.qsize() == 5

    @pytest.mark.asyncio
    async def test_acquire_release_connection(self) -> None:
        """Test acquiring and releasing connections."""
        pool = MCPConnectionPool(pool_size=3)
        await pool.initialize()

        # Acquire connection
        conn1 = await pool.acquire()
        assert conn1 is not None
        assert pool._available.qsize() == 2

        # Acquire another
        conn2 = await pool.acquire()
        assert conn2 is not None
        assert pool._available.qsize() == 1

        # Release first connection
        await pool.release(conn1)
        assert pool._available.qsize() == 2

        # Release second connection
        await pool.release(conn2)
        assert pool._available.qsize() == 3

    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion(self) -> None:
        """Test behavior when pool is exhausted."""
        pool = MCPConnectionPool(pool_size=2)
        await pool.initialize()

        # Acquire all connections
        conn1 = await pool.acquire()
        conn2 = await pool.acquire()
        assert conn1 is not None
        assert conn2 is not None

        # Try to acquire another (should block)
        acquire_task = asyncio.create_task(pool.acquire())

        # Give it time to block
        await asyncio.sleep(0.1)
        assert not acquire_task.done()

        # Release a connection
        await pool.release(conn1)

        # Now acquire should complete
        conn3 = await acquire_task
        assert conn3 is not None

    @pytest.mark.asyncio
    async def test_connection_pool_close(self) -> None:
        """Test closing connection pool."""
        pool = MCPConnectionPool(pool_size=3)
        await pool.initialize()

        # Close pool
        await pool.close()

        assert len(pool._connections) == 0
        assert pool._available.empty()
