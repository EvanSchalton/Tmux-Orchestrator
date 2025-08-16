# Plugin Development Guide - Monitoring Strategies

This guide explains how to create custom monitoring strategies for the Tmux Orchestrator monitoring system.

## Table of Contents
1. [Overview](#overview)
2. [Plugin Architecture](#plugin-architecture)
3. [Creating Your First Plugin](#creating-your-first-plugin)
4. [Plugin Lifecycle](#plugin-lifecycle)
5. [Available Components](#available-components)
6. [Best Practices](#best-practices)
7. [Testing Your Plugin](#testing-your-plugin)
8. [Distribution](#distribution)

## Overview

The monitoring system uses a plugin architecture that allows you to create custom monitoring strategies without modifying core code. Plugins can implement different algorithms for:

- Agent discovery and prioritization
- Health check scheduling
- Failure detection patterns
- Recovery strategies
- Performance optimizations

## Plugin Architecture

### Core Concepts

1. **MonitoringStrategyInterface**: The base interface all plugins must implement
2. **Component Injection**: Plugins receive monitoring components via context
3. **Async Support**: Plugins can leverage async/await for concurrent operations
4. **Metrics Integration**: Automatic performance tracking

### Directory Structure

Plugins can be placed in:
- Built-in: `tmux_orchestrator/core/monitoring/strategies/`
- User plugins: `~/.tmux-orchestrator/plugins/`

## Creating Your First Plugin

### Step 1: Import Required Interfaces

```python
from tmux_orchestrator.core.monitoring.interfaces import (
    MonitoringStrategyInterface,
    AgentMonitorInterface,
    StateTrackerInterface,
    NotificationManagerInterface,
    # ... other interfaces as needed
)
from tmux_orchestrator.core.monitoring.types import MonitorStatus
```

### Step 2: Implement the Strategy Interface

```python
class MyCustomStrategy(MonitoringStrategyInterface):
    """Custom monitoring strategy implementation."""

    def get_name(self) -> str:
        """Return a unique name for your strategy."""
        return "my_custom_strategy"

    def get_description(self) -> str:
        """Provide a human-readable description."""
        return "My custom monitoring strategy that does X, Y, Z"

    async def execute(self, context: Dict[str, Any]) -> MonitorStatus:
        """
        Main execution method for your strategy.

        Args:
            context: Dictionary containing:
                - Component interfaces (agent_monitor, state_tracker, etc.)
                - Configuration (config)
                - Logger (logger)
                - Metrics collector (metrics)
                - Other runtime data

        Returns:
            MonitorStatus with execution results
        """
        # Your monitoring logic here
        pass

    def get_required_components(self) -> List[type]:
        """
        Declare which components your strategy needs.

        Returns:
            List of interface types required
        """
        return [
            AgentMonitorInterface,
            StateTrackerInterface,
            NotificationManagerInterface,
        ]
```

### Step 3: Implement Your Monitoring Logic

```python
async def execute(self, context: Dict[str, Any]) -> MonitorStatus:
    # Extract components
    agent_monitor = context['agent_monitor']
    state_tracker = context['state_tracker']
    notification_manager = context['notification_manager']
    logger = context.get('logger')

    # Initialize status
    status = MonitorStatus(
        start_time=datetime.now(),
        agents_monitored=0,
        agents_healthy=0,
        agents_idle=0,
        agents_crashed=0,
        cycle_count=context.get('cycle_count', 0),
        errors_detected=0
    )

    try:
        # 1. Discover agents
        agents = agent_monitor.discover_agents()
        status.agents_monitored = len(agents)

        # 2. Apply your custom logic
        # For example: sort by priority, filter by criteria, etc.
        prioritized_agents = self._prioritize_agents(agents)

        # 3. Monitor agents
        for agent in prioritized_agents:
            # Your monitoring logic
            pass

        # 4. Send notifications
        notification_manager.send_queued_notifications()

        status.end_time = datetime.now()
        return status

    except Exception as e:
        logger.error(f"Error in custom strategy: {e}")
        status.errors_detected += 1
        return status
```

## Plugin Lifecycle

### Loading
1. Plugin discovered by PluginLoader
2. Plugin class instantiated
3. Required components validated

### Execution
1. `execute()` called with context
2. Plugin performs monitoring
3. Returns MonitorStatus

### Unloading
1. Plugin removed from active strategies
2. Any cleanup performed

## Available Components

### Core Components

#### AgentMonitorInterface
```python
# Discover all agents
agents = agent_monitor.discover_agents()

# Check if window is an agent
is_agent = agent_monitor.is_agent_window(target)

# Analyze agent content
analysis = agent_monitor.analyze_agent_content(target)
```

#### StateTrackerInterface
```python
# Update agent state
state = state_tracker.update_agent_state(target, content)

# Check idle status
is_idle = state_tracker.is_agent_idle(target)
idle_duration = state_tracker.get_idle_duration(target)

# Get session agents
agents = state_tracker.get_session_agents(session)
```

#### NotificationManagerInterface
```python
# Queue notifications
notification_manager.notify_agent_crash(target, error_type, session)
notification_manager.notify_agent_idle(target, idle_type, session)

# Send all queued notifications
count = notification_manager.send_queued_notifications()
```

#### CrashDetectorInterface
```python
# Detect crashes
is_crashed, reason = crash_detector.detect_crash(
    agent_info,
    window_content,
    idle_duration
)
```

#### PMRecoveryManagerInterface
```python
# Check PM health
is_healthy, pm_target, issue = pm_recovery_manager.check_pm_health(session)

# Recover PM
success = pm_recovery_manager.recover_pm(session, crashed_target)
```

### Optional Components

#### MetricsCollector
```python
metrics = context.get('metrics')
if metrics:
    metrics.start_timer("my_operation")
    # ... do work ...
    metrics.stop_timer("my_operation")

    metrics.increment_counter("custom.events")
    metrics.set_gauge("custom.queue_size", len(queue))
```

#### TMux Connection Pool
```python
tmux_pool = context.get('tmux_pool')
if tmux_pool:
    async with tmux_pool.acquire() as tmux:
        content = await asyncio.to_thread(
            tmux.capture_pane, target, lines=50
        )
```

#### Caching Layer
```python
cache = context.get('agent_cache')
if cache:
    # Try cache first
    content, status = await cache.get_agent_content(session, window)

    if status != CacheEntryStatus.FRESH:
        # Fetch and cache
        content = await fetch_content()
        await cache.set_agent_content(session, window, content)
```

## Best Practices

### 1. Error Handling
Always handle exceptions gracefully:
```python
try:
    # Risky operation
    result = await some_operation()
except Exception as e:
    logger.error(f"Operation failed: {e}")
    status.errors_detected += 1
    # Continue with next agent instead of failing entirely
```

### 2. Performance Considerations
- Use async operations for I/O
- Leverage caching when available
- Batch operations where possible
- Track performance with metrics

### 3. Logging
Use appropriate log levels:
```python
logger.debug("Detailed information for debugging")
logger.info("Important state changes")
logger.warning("Potential issues")
logger.error("Errors that don't stop execution")
```

### 4. Component Availability
Check for optional components:
```python
if 'tmux_pool' in context:
    # Use async operations
else:
    # Fall back to sync operations
```

### 5. State Management
Don't store state in the plugin instance - use StateTracker:
```python
# Bad: self.agent_states[target] = state
# Good: state_tracker.update_agent_state(target, content)
```

## Testing Your Plugin

### Unit Testing
```python
import pytest
from unittest.mock import Mock, AsyncMock

@pytest.mark.asyncio
async def test_my_strategy():
    # Create mocks
    agent_monitor = Mock(spec=AgentMonitorInterface)
    agent_monitor.discover_agents.return_value = [
        AgentInfo(target="session:0", session="session", window="0",
                  name="test", type="agent", status="active")
    ]

    # Create strategy
    strategy = MyCustomStrategy()

    # Execute
    context = {
        'agent_monitor': agent_monitor,
        'state_tracker': Mock(spec=StateTrackerInterface),
        'notification_manager': Mock(spec=NotificationManagerInterface),
    }

    status = await strategy.execute(context)

    # Assertions
    assert status.agents_monitored == 1
    assert status.errors_detected == 0
```

### Integration Testing
```python
# Test with real components
from tmux_orchestrator.core.monitoring.plugin_loader import PluginLoader

def test_plugin_loading():
    loader = PluginLoader(logger=logger)

    # Discover plugins
    plugins = loader.discover_plugins()

    # Find your plugin
    my_plugin = next(p for p in plugins if p.name == "my_custom_strategy")

    # Validate
    is_valid, error = loader.validate_plugin("my_custom_strategy")
    assert is_valid
```

### Manual Testing
1. Copy plugin to `~/.tmux-orchestrator/plugins/`
2. Run monitoring with your strategy:
   ```bash
   tmux-orc monitor --strategy my_custom_strategy
   ```

## Distribution

### As a Single File
Place your strategy in a single `.py` file:
```python
# ~/.tmux-orchestrator/plugins/priority_strategy.py
class PriorityBasedStrategy(MonitoringStrategyInterface):
    # Implementation
```

### As a Package
Create a package structure:
```
my_strategy_pack/
├── __init__.py
├── priority_strategy.py
├── utils.py
└── requirements.txt
```

### Publishing
1. Add metadata to your plugin:
   ```python
   __version__ = "1.0.0"
   __author__ = "Your Name"
   __description__ = "Priority-based monitoring strategy"
   ```

2. Create a README with:
   - Installation instructions
   - Configuration options
   - Usage examples
   - Performance characteristics

3. Consider publishing to:
   - GitHub (recommended)
   - PyPI (for pip installation)
   - Internal package repository

## Example: Complete Plugin

See the next section for a complete implementation of a PriorityBasedStrategy that demonstrates all these concepts in action.
