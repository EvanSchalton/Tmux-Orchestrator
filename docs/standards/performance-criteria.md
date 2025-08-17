# CLI Performance Criteria

**Version**: 1.0
**Date**: 2025-08-16
**Critical Requirement**: All CLI commands must execute in < 3 seconds

## Overview

With CLI reflection driving MCP tool generation, CLI performance directly impacts MCP tool quality. This document establishes mandatory performance criteria for all CLI commands.

## 1. Performance Targets ✅

### 1.1 Command Categories

**✅ MANDATORY**: Performance targets by command type:

| Command Type | Target | Maximum | Examples |
|--------------|--------|---------|----------|
| Simple Query | < 0.5s | 1s | list, status, get |
| Single Operation | < 1s | 3s | spawn, kill, send |
| Batch Operation | < 3s | 10s | team deploy, broadcast |
| System Operation | < 2s | 5s | monitoring start/stop |

### 1.2 Response Time Breakdown

**✅ REQUIRED**: Time allocation for operations:

```
Total Time Budget: 3 seconds
├── Input Validation: < 50ms
├── TMux Operations: < 2s
├── Data Processing: < 500ms
├── JSON Formatting: < 100ms
└── Output Rendering: < 350ms
```

## 2. Performance Measurement ✅

### 2.1 Timing Implementation

**✅ MANDATORY**: Add timing to all commands:

```python
import time
from functools import wraps

def measure_performance(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time

            # Add to metadata
            if isinstance(result, dict):
                result.setdefault('metadata', {})
                result['metadata']['execution_time'] = round(execution_time, 3)

            # Warn if slow
            if execution_time > 3.0:
                logger.warning(f"{func.__name__} took {execution_time:.2f}s (> 3s limit)")

            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.2f}s: {e}")
            raise
    return wrapper
```

### 2.2 Performance Logging

**✅ REQUIRED**: Log performance metrics:

```python
# Performance log format
{
    "timestamp": "2024-01-01T00:00:00Z",
    "command": "spawn_agent",
    "execution_time": 1.234,
    "tmux_time": 0.987,
    "processing_time": 0.247,
    "status": "success",
    "slow_operation": false
}
```

## 3. Performance Optimization ✅

### 3.1 TMux Operation Optimization

**✅ MANDATORY**: Efficient TMux usage:

```python
# Good: Batch operations
async def list_all_agents():
    # Single tmux call with format
    result = await tmux.run("list-windows -a -F '#{session_name}:#{window_name}'")
    return parse_windows(result)

# Bad: Multiple calls
async def list_all_agents_slow():
    sessions = await tmux.list_sessions()
    agents = []
    for session in sessions:  # N+1 problem!
        windows = await tmux.list_windows(session)
        agents.extend(windows)
    return agents
```

### 3.2 Caching Strategy

**✅ REQUIRED**: Cache expensive operations:

```python
from functools import lru_cache
from datetime import datetime, timedelta

class PerformanceCache:
    def __init__(self, ttl_seconds=5):
        self._cache = {}
        self._ttl = timedelta(seconds=ttl_seconds)

    def get_or_compute(self, key, compute_func):
        if key in self._cache:
            value, timestamp = self._cache[key]
            if datetime.now() - timestamp < self._ttl:
                return value

        value = compute_func()
        self._cache[key] = (value, datetime.now())
        return value
```

### 3.3 Async Optimization

**✅ MANDATORY**: Proper async patterns:

```python
# Good: Concurrent operations
async def get_team_status(session):
    agents, metrics, health = await asyncio.gather(
        get_agents(session),
        get_metrics(session),
        get_health(session)
    )
    return combine_status(agents, metrics, health)

# Bad: Sequential operations
async def get_team_status_slow(session):
    agents = await get_agents(session)
    metrics = await get_metrics(session)
    health = await get_health(session)
    return combine_status(agents, metrics, health)
```

## 4. Performance Testing ✅

### 4.1 Load Testing

**✅ REQUIRED**: Performance tests for all commands:

```python
import pytest
import asyncio
from time import time

@pytest.mark.performance
async def test_spawn_agent_performance():
    """Test spawn_agent completes within 3 seconds."""
    start = time()

    result = await spawn_agent(
        session_name="test-session",
        agent_type="developer"
    )

    duration = time() - start
    assert result['success'] is True
    assert duration < 3.0, f"spawn_agent took {duration:.2f}s (limit: 3s)"
```

### 4.2 Stress Testing

**✅ MANDATORY**: Test under load:

```python
@pytest.mark.stress
async def test_concurrent_operations():
    """Test system handles concurrent operations."""
    operations = [
        spawn_agent(f"session-{i}", "developer")
        for i in range(10)
    ]

    start = time()
    results = await asyncio.gather(*operations)
    duration = time() - start

    # All should succeed
    assert all(r['success'] for r in results)
    # Should complete reasonably fast
    assert duration < 30.0, f"10 concurrent spawns took {duration:.2f}s"
```

## 5. Performance Monitoring ✅

### 5.1 Real-time Monitoring

**✅ REQUIRED**: Monitor production performance:

```python
class PerformanceMonitor:
    def __init__(self):
        self.metrics = defaultdict(list)

    def record(self, command, duration):
        self.metrics[command].append(duration)

        # Alert on slow operations
        if duration > 3.0:
            logger.warning(
                f"Slow operation: {command} took {duration:.2f}s",
                extra={"command": command, "duration": duration}
            )

    def get_stats(self, command):
        times = self.metrics[command]
        if not times:
            return None

        return {
            "count": len(times),
            "avg": statistics.mean(times),
            "p50": statistics.median(times),
            "p95": np.percentile(times, 95),
            "p99": np.percentile(times, 99),
            "max": max(times)
        }
```

### 5.2 Performance Alerts

**✅ MANDATORY**: Alert on degradation:

```yaml
# Performance alert thresholds
alerts:
  - name: slow_command
    condition: execution_time > 3.0
    severity: warning

  - name: very_slow_command
    condition: execution_time > 10.0
    severity: critical

  - name: performance_degradation
    condition: avg_execution_time > 2.0
    window: 5m
    severity: warning
```

## 6. User Experience ✅

### 6.1 Progress Indicators

**✅ REQUIRED**: Show progress for operations > 1s:

```python
@click.command()
async def deploy_team(team_name, size):
    """Deploy a team with progress indication."""

    with click.progressbar(
        length=size,
        label='Spawning agents'
    ) as bar:
        for i in range(size):
            await spawn_single_agent(f"agent-{i}")
            bar.update(1)
```

### 6.2 Timeout Handling

**✅ MANDATORY**: Graceful timeout handling:

```python
async def with_timeout(coro, timeout=30):
    """Execute with timeout and user feedback."""
    try:
        return await asyncio.wait_for(coro, timeout)
    except asyncio.TimeoutError:
        click.echo(
            f"Operation timed out after {timeout}s. "
            f"Try with --timeout={timeout*2} for longer operations.",
            err=True
        )
        raise
```

## 7. Performance Review Checklist ✅

### Pre-Review Performance Checks

- [ ] Command completes in < 3 seconds
- [ ] Execution time included in metadata
- [ ] TMux operations are batched
- [ ] Async operations are concurrent
- [ ] Progress shown for slow operations
- [ ] Timeouts handled gracefully
- [ ] Performance tests included
- [ ] No N+1 query patterns

### Performance Red Flags

- 🚫 Multiple TMux calls in loops
- 🚫 Sequential async operations
- 🚫 Unbounded data fetching
- 🚫 Missing timeouts
- 🚫 No progress indicators
- 🚫 Synchronous I/O in async context

---

**Remember**: Fast CLI = Fast MCP tools = Happy users!
