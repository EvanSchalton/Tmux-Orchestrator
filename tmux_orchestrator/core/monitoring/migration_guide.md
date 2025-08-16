# Monitor.py Migration Guide

## Overview
This guide outlines the migration path from the monolithic `monitor.py` (2,227 lines) to the new modular architecture.

## Architecture Changes

### Old Architecture (monitor.py)
- Single monolithic `IdleMonitor` class
- All functionality mixed together
- Hard to test individual components
- Difficult to extend or modify

### New Architecture
- **Service Layer**: `MonitorService` facade orchestrates components
- **Dependency Injection**: `ServiceContainer` manages component lifecycles
- **Plugin System**: Extensible monitoring strategies
- **Clean Interfaces**: Each component has a defined contract

## Migration Steps

### Phase 1: Setup Infrastructure (Senior Dev)

1. **Update monitor_modular.py** to use new components:
```python
from .monitoring.service_container import ServiceContainer
from .monitoring.monitor_service import MonitorService
from .monitoring.interfaces import *

class ModularIdleMonitor:
    def __init__(self, tmux: TMUXManager, config: Optional[Config] = None):
        # ... existing init code ...

        # Initialize service container
        self.container = ServiceContainer(self.logger)

        # Initialize monitor service
        self.monitor_service = MonitorService(config, tmux, self.logger, self.container)
```

2. **Replace ComponentManager with MonitorService**:
```python
def _run_monitoring_daemon(self, interval: int):
    """Run the monitoring daemon loop."""
    # Initialize components
    if not self.monitor_service.initialize():
        self.logger.error("Failed to initialize monitor service")
        return

    try:
        while not self._should_shutdown():
            # Run monitoring cycle
            status = asyncio.run(self.monitor_service.run_monitoring_cycle())

            # Log status
            self.logger.info(f"Monitoring cycle complete: {status}")

            # Sleep until next cycle
            time.sleep(interval)
    finally:
        self.monitor_service.cleanup()
```

### Phase 2: Component Integration (Backend Dev)

1. **Wire MetricsCollector into MonitorService**:
```python
# In monitor_service.py _register_core_services():
if not self.container.has(MetricsCollectorInterface):
    from .metrics_collector import MetricsCollector
    builder = ServiceBuilder(self.container)
    builder.add(MetricsCollectorInterface).use(
        lambda: MetricsCollector(self.config, self.logger)
    ).as_singleton().build()

# In run_monitoring_cycle():
metrics = self.container.resolve(MetricsCollectorInterface)
metrics.record_monitor_cycle(status)
```

2. **Split StateTracker** into focused components:
- `AgentStateTracker`: Only agent state management
- `SessionTracker`: Only session tracking
- `IdleTracker`: Only idle time tracking

### Phase 3: Strategy Implementation (Senior Dev)

1. **Update monitoring daemon to use strategies**:
```python
def _run_monitoring_daemon(self, interval: int):
    # Load monitoring strategy
    strategy_name = self.config.monitoring_strategy or "polling"
    strategy = self._load_strategy(strategy_name)

    # Create execution context
    context = {
        'AgentMonitorInterface': self.container.resolve(AgentMonitorInterface),
        'StateTrackerInterface': self.container.resolve(StateTrackerInterface),
        'NotificationManagerInterface': self.container.resolve(NotificationManagerInterface),
        'PMRecoveryManagerInterface': self.container.resolve(PMRecoveryManagerInterface),
        'logger': self.logger
    }

    while not self._should_shutdown():
        status = asyncio.run(strategy.execute(context))
        time.sleep(interval)
```

### Phase 4: Feature Flags (Backend Dev)

Add feature flags for gradual rollout:

```python
class Config:
    # ... existing config ...
    use_modular_monitor: bool = False  # Feature flag
    monitoring_strategy: str = "polling"  # Strategy selection
```

Update CLI to check feature flag:
```python
# In cli/monitor.py
if config.use_modular_monitor:
    from tmux_orchestrator.core.monitor_modular import ModularIdleMonitor
    monitor = ModularIdleMonitor(tmux, config)
else:
    from tmux_orchestrator.core.monitor import IdleMonitor
    monitor = IdleMonitor(tmux, config)
```

### Phase 5: Testing & Validation (QA)

1. **Unit Tests** for each component
2. **Integration Tests** for component interactions
3. **Performance Tests** comparing old vs new
4. **Regression Tests** ensuring CLI compatibility

## Backward Compatibility

### Maintain Existing APIs:
- `tmux-orc monitor start/stop/status` must work identically
- PM notifications must have same format
- State files must be compatible

### Data Migration:
- Read existing state files in new components
- Convert to new format gradually
- Keep backward compatibility for 2-3 releases

## Rollout Plan

1. **Week 1**: Complete Phase 1-2, internal testing
2. **Week 2**: Complete Phase 3-4, beta testing
3. **Week 3**: Phase 5 testing, documentation
4. **Week 4**: Gradual rollout with feature flags

## Risk Mitigation

1. **Feature Flags**: Allow instant rollback
2. **Parallel Running**: Can run both systems side-by-side
3. **Comprehensive Logging**: Track all state changes
4. **Health Checks**: Monitor performance metrics

## Success Criteria

- ✅ All existing functionality preserved
- ✅ No performance degradation
- ✅ Improved testability (90%+ coverage)
- ✅ Reduced complexity (no file > 300 lines)
- ✅ Plugin system functional
- ✅ Zero downtime migration
