# Async Components Test Plan

## For: QA Engineer (monitor-refactor:5)
## Date: 2025-08-16
## Author: Senior Developer (monitor-refactor:3)
## Phase: 2 - Async Implementation

## Overview

This test plan covers all async components implemented in Phase 2, ensuring comprehensive coverage of functionality, performance, and edge cases.

## Test Scope

### Components to Test
1. **TMuxConnectionPool** (`tmux_pool.py`) - Target: 95% coverage
2. **AsyncMonitoringCache** (`cache.py`) - Target: 90% coverage
3. **AsyncHealthChecker** (`async_health_checker.py`) - Target: 95% coverage
4. **AsyncMonitorService** (`async_monitor_service.py`) - Target: 90% coverage

## 1. TMuxConnectionPool Tests

### Unit Tests

#### Test Pool Initialization
```python
async def test_pool_initialization():
    """Test pool creates minimum connections on init."""
    pool = TMuxConnectionPool(min_size=3, max_size=10)
    await pool.initialize()

    assert pool._initialized is True
    assert pool._pool.qsize() == 3
    assert pool.stats['connections_created'] == 3
```

#### Test Connection Acquisition
```python
async def test_connection_acquisition():
    """Test acquiring connections from pool."""
    pool = TMuxConnectionPool(min_size=2, max_size=5)
    await pool.initialize()

    # Acquire connection
    async with pool.acquire() as tmux:
        assert tmux is not None
        assert isinstance(tmux, TMUXManager)
        assert len(pool._active_connections) == 1

    # Verify connection returned to pool
    assert len(pool._active_connections) == 0
    assert pool._pool.qsize() == 2
```

#### Test Pool Exhaustion
```python
async def test_pool_exhaustion():
    """Test behavior when pool is exhausted."""
    pool = TMuxConnectionPool(min_size=1, max_size=2, connection_timeout=0.5)
    await pool.initialize()

    # Acquire all connections
    conn1 = await pool.acquire().__aenter__()
    conn2 = await pool.acquire().__aenter__()

    # Third should timeout
    with pytest.raises(asyncio.TimeoutError):
        async with pool.acquire():
            pass
```

#### Test Connection Recycling
```python
async def test_connection_recycling():
    """Test stale connections are recycled."""
    pool = TMuxConnectionPool(max_connection_age=0.1)  # 100ms age
    await pool.initialize()

    # Use connection
    async with pool.acquire() as tmux:
        pass

    # Wait for connection to become stale
    await asyncio.sleep(0.2)

    # Next acquisition should trigger recycling
    async with pool.acquire() as tmux:
        pass

    assert pool.stats['connections_recycled'] > 0
```

### Integration Tests

#### Test Concurrent Access
```python
async def test_concurrent_pool_access():
    """Test multiple concurrent acquisitions."""
    pool = TMuxConnectionPool(min_size=5, max_size=10)
    await pool.initialize()

    async def use_connection(i):
        async with pool.acquire() as tmux:
            # Simulate work
            await asyncio.sleep(0.1)
            return i

    # Run 20 concurrent operations
    tasks = [use_connection(i) for i in range(20)]
    results = await asyncio.gather(*tasks)

    assert len(results) == 20
    assert pool.stats['total_acquisitions'] == 20
```

## 2. AsyncMonitoringCache Tests

### Unit Tests

#### Test Basic Cache Operations
```python
async def test_cache_get_set():
    """Test basic cache get/set operations."""
    cache = AsyncMonitoringCache(default_ttl=1.0)

    # Set value
    await cache.set("key1", "value1")

    # Get value
    value = await cache.get("key1")
    assert value == "value1"
    assert cache.stats['hits'] == 1

    # Miss
    value = await cache.get("nonexistent")
    assert value is None
    assert cache.stats['misses'] == 1
```

#### Test TTL Expiration
```python
async def test_cache_ttl_expiration():
    """Test cache entries expire after TTL."""
    cache = AsyncMonitoringCache(default_ttl=0.1)  # 100ms TTL

    await cache.set("key1", "value1")

    # Should be available immediately
    assert await cache.get("key1") == "value1"

    # Wait for expiration
    await asyncio.sleep(0.2)

    # Should be expired
    assert await cache.get("key1") is None
    assert cache.stats['expirations'] == 1
```

#### Test Concurrent Access
```python
async def test_cache_concurrent_access():
    """Test cache is thread-safe under concurrent access."""
    cache = AsyncMonitoringCache()

    async def cache_operations(i):
        key = f"key{i % 10}"  # 10 unique keys
        await cache.set(key, i)
        value = await cache.get(key)
        return value

    # Run 100 concurrent operations
    tasks = [cache_operations(i) for i in range(100)]
    results = await asyncio.gather(*tasks)

    # All operations should succeed
    assert len(results) == 100
    assert None not in results
```

#### Test Get or Compute
```python
async def test_get_or_compute():
    """Test get_or_compute prevents duplicate computation."""
    cache = AsyncMonitoringCache()
    compute_count = 0

    async def expensive_compute():
        nonlocal compute_count
        compute_count += 1
        await asyncio.sleep(0.1)
        return "computed_value"

    # Launch multiple concurrent requests
    tasks = [
        cache.get_or_compute("key1", expensive_compute)
        for _ in range(10)
    ]
    results = await asyncio.gather(*tasks)

    # Should only compute once
    assert compute_count == 1
    assert all(r == "computed_value" for r in results)
```

### Integration Tests

#### Test Layered Cache
```python
async def test_layered_cache():
    """Test layered cache with different TTLs."""
    cache = LayeredCache()

    # Set in different layers
    await cache.set('pane_content', 'pane1', 'content1')
    await cache.set('agent_status', 'agent1', 'healthy')
    await cache.set('config', 'setting1', 'value1')

    # Verify different layers
    assert await cache.get('pane_content', 'pane1') == 'content1'
    assert await cache.get('agent_status', 'agent1') == 'healthy'
    assert await cache.get('config', 'setting1') == 'value1'

    # Check stats per layer
    stats = cache.get_all_stats()
    assert 'pane_content' in stats
    assert 'agent_status' in stats
```

## 3. AsyncHealthChecker Tests

### Unit Tests

#### Test Async Health Check
```python
async def test_async_health_check():
    """Test basic async health check."""
    mock_tmux = Mock(spec=TMUXManager)
    mock_tmux.capture_pane = Mock(return_value="Normal content")

    mock_pool = Mock(spec=TMuxConnectionPool)
    checker = AsyncHealthChecker(mock_tmux, Config(), Mock(), mock_pool)

    status = await checker.check_agent_health_async("session:1")

    assert status.target == "session:1"
    assert status.is_responsive is True
    assert status.status == "healthy"
```

#### Test Concurrent Health Checks
```python
async def test_concurrent_health_checks():
    """Test checking multiple agents concurrently."""
    checker = AsyncHealthChecker(Mock(), Config(), Mock())

    # Mock the internal check method
    async def mock_check(target):
        await asyncio.sleep(0.1)  # Simulate work
        return AgentHealthStatus(
            target=target,
            status="healthy",
            # ... other fields
        )

    checker._do_health_check_async = mock_check

    # Check 10 agents
    targets = [f"session:{i}" for i in range(10)]
    start = time.time()
    results = await checker.check_multiple_agents_async(targets)
    duration = time.time() - start

    assert len(results) == 10
    assert duration < 0.3  # Should be concurrent, not 1 second
```

#### Test Check Deduplication
```python
async def test_health_check_deduplication():
    """Test duplicate checks are deduplicated."""
    checker = AsyncHealthChecker(Mock(), Config(), Mock())
    check_count = 0

    async def counting_check(target):
        nonlocal check_count
        check_count += 1
        await asyncio.sleep(0.1)
        return Mock(target=target, status="healthy")

    checker._do_health_check_async = counting_check

    # Launch duplicate checks
    tasks = [
        checker.check_agent_health_async("session:1")
        for _ in range(5)
    ]
    results = await asyncio.gather(*tasks)

    # Should only check once
    assert check_count == 1
    assert all(r.target == "session:1" for r in results)
```

### Integration Tests

#### Test with Real TMUX
```python
async def test_health_check_with_real_tmux():
    """Test health checking with actual TMUX sessions."""
    # This test requires a TMUX environment
    tmux = TMUXManager()
    pool = TMuxConnectionPool(min_size=2, max_size=5)
    await pool.initialize()

    cache = LayeredCache()
    checker = AsyncHealthChecker(tmux, Config(), logging.getLogger(), pool, cache)

    # Create test session
    tmux.create_session("test-session")
    tmux.create_window("test-session", "1")

    try:
        # Check health
        status = await checker.check_agent_health_async("test-session:1")
        assert status.status in ["healthy", "idle"]

        # Check caching
        start = time.time()
        status2 = await checker.check_agent_health_async("test-session:1")
        duration = time.time() - start

        assert duration < 0.01  # Should be cached
        assert status2.target == status.target

    finally:
        tmux.kill_session("test-session")
        await pool.close()
```

## 4. AsyncMonitorService Tests

### Unit Tests

#### Test Service Initialization
```python
async def test_service_initialization():
    """Test async service initialization."""
    service = AsyncMonitorService(Mock(), Config(), Mock())

    # Mock component initialization
    service.initialize = Mock(return_value=True)
    service.tmux_pool.initialize = AsyncMock()
    service.async_health_checker.initialize_async = AsyncMock()
    service._load_plugins = AsyncMock()
    service._select_strategy = AsyncMock()

    result = await service.initialize_async()

    assert result is True
    service.tmux_pool.initialize.assert_called_once()
    service._load_plugins.assert_called_once()
```

#### Test Monitoring Cycle
```python
async def test_monitoring_cycle():
    """Test running async monitoring cycle."""
    service = AsyncMonitorService(Mock(), Config(), Mock())

    # Mock strategy
    mock_strategy = Mock()
    mock_strategy.execute = AsyncMock(return_value=Mock(errors_detected=0))
    service.current_strategy = mock_strategy

    # Run cycle
    await service.run_monitoring_cycle_async()

    assert service.cycle_count == 1
    mock_strategy.execute.assert_called_once()
```

### Integration Tests

#### Test Full Monitoring Flow
```python
async def test_full_monitoring_flow():
    """Test complete monitoring flow with all components."""
    tmux = TMUXManager()
    config = Config()
    logger = logging.getLogger("test")

    service = AsyncMonitorService(tmux, config, logger)

    # Initialize
    await service.initialize_async()

    try:
        # Start monitoring
        assert await service.start_async() is True

        # Let it run for a few cycles
        await asyncio.sleep(2)

        # Get metrics
        metrics = await service.get_performance_metrics_async()

        assert metrics['base_status']['is_running'] is True
        assert metrics['connection_pool']['pool_size'] >= 5
        assert 'cache_performance' in metrics

    finally:
        await service.stop_async()
```

## Performance Tests

### Load Test - 50 Agents
```python
async def test_50_agent_performance():
    """Test performance with 50 agents."""
    # Setup mock environment with 50 agents
    service = AsyncMonitorService(Mock(), Config(), Mock())

    # Mock 50 agents
    agents = [
        AgentInfo(f"session{i//5}:{i%5}", f"session{i//5}",
                  str(i%5), f"agent{i}", "dev", "active")
        for i in range(50)
    ]
    service.discover_agents = Mock(return_value=agents)

    # Time monitoring cycle
    start = time.time()
    await service.run_monitoring_cycle_async()
    duration = time.time() - start

    # Must complete in under 1 second
    assert duration < 1.0, f"Cycle took {duration}s, target is <1s"
```

### Stress Test - Connection Pool
```python
async def test_connection_pool_stress():
    """Stress test connection pool under heavy load."""
    pool = TMuxConnectionPool(min_size=5, max_size=20)
    await pool.initialize()

    async def stress_operation(i):
        try:
            async with pool.acquire() as tmux:
                await asyncio.sleep(random.uniform(0.01, 0.1))
                return True
        except asyncio.TimeoutError:
            return False

    # Run 1000 operations
    start = time.time()
    tasks = [stress_operation(i) for i in range(1000)]
    results = await asyncio.gather(*tasks)
    duration = time.time() - start

    success_rate = sum(results) / len(results)
    assert success_rate > 0.95  # >95% success rate
    assert pool.stats['acquisition_timeouts'] < 50  # <5% timeouts

    print(f"Completed 1000 operations in {duration:.2f}s")
    print(f"Success rate: {success_rate:.1%}")
    print(f"Pool stats: {pool.get_stats()}")
```

## Edge Cases & Error Handling

### Test Graceful Degradation
```python
async def test_graceful_degradation():
    """Test system degrades gracefully when components fail."""
    service = AsyncMonitorService(Mock(), Config(), Mock())

    # Simulate pool failure
    service.tmux_pool.acquire = AsyncMock(side_effect=Exception("Pool failed"))

    # Should fall back to sync operations
    await service.run_monitoring_cycle_async()

    # Service should still be running
    assert service.errors_detected > 0
    # But not crashed
```

### Test Resource Cleanup
```python
async def test_resource_cleanup():
    """Test all resources are cleaned up properly."""
    service = AsyncMonitorService(Mock(), Config(), Mock())
    await service.initialize_async()
    await service.start_async()

    # Track resources
    pool_closed = False
    cache_cleared = False

    # Mock cleanup methods
    service.tmux_pool.close = AsyncMock(side_effect=lambda: setattr(locals(), 'pool_closed', True))
    service.cache.clear_all = AsyncMock(side_effect=lambda: setattr(locals(), 'cache_cleared', True))

    # Stop service
    await service.stop_async()

    # Verify cleanup
    service.tmux_pool.close.assert_called_once()
    service.cache.clear_all.assert_called_once()
```

## Test Execution Plan

### Phase 1: Unit Tests (Days 1-2)
1. Run all unit tests for each component
2. Achieve coverage targets
3. Fix any failing tests

### Phase 2: Integration Tests (Day 3)
1. Set up test TMUX environment
2. Run integration tests
3. Validate component interactions

### Phase 3: Performance Tests (Day 4)
1. Run load tests with varying agent counts
2. Stress test connection pool
3. Benchmark against sync implementation

### Phase 4: Edge Case Testing (Day 5)
1. Test error scenarios
2. Validate graceful degradation
3. Ensure proper cleanup

## Success Criteria

1. **Coverage**: Meet or exceed target coverage for each component
2. **Performance**: Sub-second monitoring cycles for 50 agents
3. **Reliability**: 100% pass rate for all tests
4. **Stability**: No memory leaks over extended runs

## Tools & Commands

```bash
# Run all async tests
pytest tests/test_async_*.py -v --cov=tmux_orchestrator.core.monitoring --cov-report=html

# Run specific component tests
pytest tests/test_tmux_pool.py -v
pytest tests/test_cache.py -v
pytest tests/test_async_health_checker.py -v
pytest tests/test_async_monitor_service.py -v

# Run performance tests
pytest tests/performance/test_async_performance.py -v --benchmark

# Run stress tests
pytest tests/stress/test_connection_pool_stress.py -v -s
```

## Reporting

Please provide:
1. Coverage report for each component
2. Performance benchmark results
3. List of any failing tests with details
4. Recommendations for improvements

---

Ready to begin testing! Please coordinate with me for any clarifications or additional test scenarios needed.
