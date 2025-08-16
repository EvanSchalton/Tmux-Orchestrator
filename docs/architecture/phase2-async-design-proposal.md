# Phase 2 Async Implementation Design Proposal

## Date: 2025-08-16
## Author: Senior Developer (monitor-refactor:3)
## For: Architect (monitor-refactor:2)

## Overview
This document proposes the async implementation approach for Phase 2, building on the Backend Dev's excellent plugin system and concurrent strategy.

## Current State Analysis

### Backend Dev's Contributions
1. **ConcurrentMonitoringStrategy**: Already implements async patterns with:
   - Semaphore-based concurrency control (max 10 concurrent operations)
   - Async agent monitoring with `asyncio.gather()`
   - Error isolation through exception handling
   - Clean separation of concerns

2. **Plugin System**: Provides:
   - Strategy pattern for swappable monitoring approaches
   - Service container with dependency injection
   - Clean interfaces for all components

### Components Needing Async Updates
1. **HealthChecker**: Currently synchronous, needs async methods
2. **MonitorService**: Facade needs async coordination capabilities
3. **TMUXManager**: Needs connection pooling for concurrent operations
4. **State/Cache Layer**: Need async-safe implementations

## Proposed Async Architecture

### 1. Async HealthChecker Design
```python
class AsyncHealthChecker(HealthChecker):
    """Async version of health checker with connection pooling."""

    async def check_agent_health_async(self, target: str) -> AgentHealthStatus:
        """Async health check with concurrent TMUX operations."""
        # Use connection pool for TMUX operations
        async with self.tmux_pool.acquire() as tmux:
            content = await tmux.capture_pane_async(target)
            # ... rest of health check logic
```

### 2. TMux Connection Pool Design
```python
class TMuxConnectionPool:
    """Connection pool for TMUX operations."""

    def __init__(self, min_size: int = 5, max_size: int = 20):
        self._pool = asyncio.Queue(maxsize=max_size)
        self._semaphore = asyncio.Semaphore(max_size)

    async def acquire(self) -> TMuxConnection:
        """Acquire connection from pool."""
        async with self._semaphore:
            return await self._get_or_create_connection()
```

### 3. Caching Layer Design
```python
class AsyncMonitoringCache:
    """Thread-safe async caching for monitoring data."""

    def __init__(self, ttl: int = 30):
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

    async def get_or_compute(self, key: str,
                           compute_fn: Callable[[], Awaitable[T]]) -> T:
        """Get from cache or compute if missing/expired."""
        async with self._lock:
            if self._is_valid(key):
                return self._cache[key].value

        # Compute outside lock to allow concurrency
        value = await compute_fn()

        async with self._lock:
            self._cache[key] = CacheEntry(value, time.time())
        return value
```

### 4. Async MonitorService Integration
```python
class AsyncMonitorService(MonitorService):
    """Async-aware monitor service facade."""

    async def run_monitoring_cycle_async(self) -> None:
        """Run monitoring cycle with async strategy."""
        # Use concurrent strategy by default
        strategy = self.strategy_selector.get_strategy("concurrent")

        context = {
            'health_checker': self.async_health_checker,
            'tmux_pool': self.tmux_pool,
            'cache': self.monitoring_cache,
            # ... other components
        }

        status = await strategy.execute(context)
        await self._process_status(status)
```

## Implementation Plan

### Phase 2A: Core Async Infrastructure (Days 5-6)
1. **TMux Connection Pool**:
   - Implement connection lifecycle management
   - Add health checking for connections
   - Handle connection recycling

2. **Async Cache Layer**:
   - Implement TTL-based caching
   - Add cache warming strategies
   - Ensure thread-safety with asyncio locks

3. **Base Async Components**:
   - Create AsyncHealthChecker
   - Update interfaces to support both sync/async

### Phase 2B: Integration (Day 7)
1. **MonitorService Updates**:
   - Add async monitoring cycle
   - Integrate with plugin system
   - Maintain backward compatibility

2. **Strategy Selection**:
   - Default to concurrent strategy for async
   - Fall back to polling for sync
   - Allow runtime strategy switching

## Performance Considerations

### Connection Pool Sizing
- **Min connections**: 5 (handle baseline load)
- **Max connections**: 20 (prevent TMUX server overload)
- **Connection timeout**: 30s (recycle stale connections)

### Concurrency Limits
- **Agent checks**: 10 concurrent (from Backend Dev's strategy)
- **PM checks**: 5 concurrent (more complex operations)
- **Cache operations**: Unlimited (memory-only)

### Caching Strategy
- **Agent status**: 30s TTL (balance freshness vs. performance)
- **Session list**: 60s TTL (changes less frequently)
- **Pane content**: 10s TTL (for rapid re-checks)

## Compatibility Requirements

### Backward Compatibility
1. All existing sync methods remain functional
2. Async methods have `_async` suffix
3. MonitorService auto-selects sync/async based on context

### Migration Path
1. Components gain async methods alongside sync
2. Strategies can declare async capability
3. Gradual migration of call sites

## Testing Strategy

### Unit Tests
- Mock async TMUX operations
- Test connection pool edge cases
- Verify cache concurrency safety

### Integration Tests
- Real TMUX server with multiple sessions
- Stress test with 50+ agents
- Measure performance improvements

### Performance Benchmarks
- Baseline: Current sync implementation
- Target: 50% reduction in monitoring cycle time
- Metric: Sub-second cycle for 50 agents

## Questions for Architect

1. **Connection Pool Implementation**:
   - Should we use an existing library (e.g., `asyncio-pool`) or build custom?
   - How should we handle TMUX server connection limits?

2. **Cache Invalidation**:
   - Should we implement event-based invalidation?
   - How to handle cache coherency across multiple monitors?

3. **Error Handling**:
   - Should async errors bubble up or be contained?
   - How to handle partial failures in concurrent operations?

4. **Configuration**:
   - Should async be opt-in or opt-out?
   - How to expose tuning parameters (pool size, concurrency, TTL)?

## Recommendations

1. **Start with TMux Pool**: Most critical for performance
2. **Leverage Existing Strategy**: Build on Backend Dev's concurrent implementation
3. **Incremental Migration**: Add async capabilities without breaking changes
4. **Focus on Hot Paths**: Prioritize health checking and pane capture

## Next Steps

Awaiting your feedback on:
1. Overall async architecture approach
2. Specific implementation choices
3. Priority of components to implement
4. Integration with existing plugin system

Ready to begin implementation upon your approval!
