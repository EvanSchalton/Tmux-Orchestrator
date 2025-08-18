# Python 3.11+ Typing Modernization - Detailed Module Analysis

## Core Monitoring Modules (36 files)

### High-Complexity Modules

#### 1. `core/monitoring/interfaces.py`
- **Occurrences**: 12+
- **Complexity**: High (abstract interfaces)
- **Patterns**: `Optional[T]`, `Tuple[bool, Optional[str]]`, `List[str]`
- **Risk**: High - Core interfaces affect entire monitoring system
- **Effort**: 2 hours

#### 2. `core/monitoring/state_tracker.py`
- **Occurrences**: 20+
- **Complexity**: High (state management)
- **Patterns**: `Dict[str, List[str]]`, `Set[str]`, `Optional[datetime]`
- **Risk**: Medium - State tracking is critical but well-isolated
- **Effort**: 1.5 hours

#### 3. `core/monitoring/cache_layer.py`
- **Occurrences**: 18+
- **Complexity**: High (caching logic)
- **Patterns**: Complex nested types, `Dict[str, Dict[str, Any]]`
- **Risk**: Medium - Performance-critical caching
- **Effort**: 1.5 hours

### Medium-Complexity Modules

#### 4. `core/monitoring/notification_manager.py`
- **Occurrences**: 10+
- **Complexity**: Medium
- **Patterns**: `List[NotificationEvent]`, `Dict[str, List[str]]`
- **Example**:
  ```python
  # Current
  self._queued_notifications: List[NotificationEvent] = []
  self._pm_notifications: Dict[str, List[str]] = defaultdict(list)

  # Target
  self._queued_notifications: list[NotificationEvent] = []
  self._pm_notifications: dict[str, list[str]] = defaultdict(list)
  ```
- **Risk**: Medium - User-facing notifications
- **Effort**: 1 hour

#### 5. `core/monitoring/pm_recovery_manager.py`
- **Occurrences**: 10+
- **Complexity**: Medium
- **Patterns**: `Tuple[bool, Optional[str], Optional[str]]`, `Dict[str, datetime]`
- **Risk**: High - PM recovery is mission-critical
- **Effort**: 1 hour

#### 6. `core/monitoring/strategies/async_polling_strategy.py`
- **Occurrences**: 14+
- **Complexity**: Medium (async patterns)
- **Patterns**: `Optional[TMuxConnectionPool]`, `List[AgentInfo]`
- **Risk**: Medium - Async polling affects performance
- **Effort**: 1 hour

### Low-Complexity Modules

#### 7. `core/monitoring/health_checker.py`
- **Occurrences**: 4+
- **Complexity**: Low
- **Patterns**: `Dict[str, AgentHealthStatus]`, `Optional[AgentHealthStatus]`
- **Risk**: Medium - Health checking is critical
- **Effort**: 0.5 hours

#### 8. `core/monitoring/metrics_collector.py`
- **Occurrences**: 12+
- **Complexity**: Low-Medium
- **Patterns**: `Optional[Dict[str, str]]`, `List[float]`
- **Risk**: Low - Metrics collection is supplementary
- **Effort**: 0.5 hours

## Core Recovery Modules (11 files)

### High-Priority Recovery Modules

#### 1. `core/recovery/pubsub_recovery_coordinator.py`
- **Occurrences**: 6+
- **Patterns**: `Dict[str, Set[str]]`, `List[str]`, `Optional[datetime]`
- **Risk**: High - Coordinates recovery operations
- **Effort**: 1 hour

#### 2. `core/recovery/briefing_manager.py`
- **Occurrences**: 4+
- **Patterns**: `Optional[str]`, `Dict[str, Any]`
- **Risk**: Medium - Manages agent briefings
- **Effort**: 0.5 hours

#### 3. `core/recovery/notification_manager.py`
- **Occurrences**: 6+
- **Patterns**: `List[Dict[str, Any]]`, `Optional[str]`
- **Risk**: Medium - Recovery notifications
- **Effort**: 0.5 hours

## Utility Modules

### 1. `utils/tmux.py`
- **Occurrences**: 13
- **Complexity**: High (system interface)
- **Patterns**: Complex command types, `List[Dict[str, Any]]`
- **Risk**: High - Core TMUX integration
- **Effort**: 2 hours
- **Special Considerations**: Low-level system calls, error handling

### 2. `utils/rate_limiter.py`
- **Occurrences**: 2
- **Complexity**: Low
- **Patterns**: `Optional[datetime]`, `Dict[str, float]`
- **Risk**: Low - Well-isolated functionality
- **Effort**: 0.25 hours

## CLI Modules

### 1. `cli/daemon.py`
- **Occurrences**: 1
- **Patterns**: `Optional[int]`
- **Example**:
  ```python
  # Current
  from typing import Optional
  pid: Optional[int] = None

  # Target
  pid: int | None = None
  ```
- **Risk**: Low - Simple type usage
- **Effort**: 0.25 hours

### 2. `cli/pubsub.py`
- **Occurrences**: 8
- **Patterns**: `List[str]`, `Dict[str, Any]`
- **Risk**: Medium - Messaging interface
- **Effort**: 0.5 hours

## Transformation Priority Matrix

### Wave 1: Low-Risk Utilities (Start Here)
1. `utils/rate_limiter.py` - 15 minutes
2. `cli/daemon.py` - 15 minutes
3. `utils/performance_benchmarks.py` - 15 minutes
4. `core/monitoring/metrics_collector.py` - 30 minutes

**Total Wave 1**: 1.25 hours

### Wave 2: Medium-Risk CLI
1. `cli/pubsub.py` - 30 minutes
2. `cli/team.py` - 15 minutes
3. `cli/tasks.py` - 15 minutes
4. `cli/recovery.py` - 15 minutes

**Total Wave 2**: 1.25 hours

### Wave 3: Core Monitoring (Careful Testing)
1. `core/monitoring/health_checker.py` - 30 minutes
2. `core/monitoring/notification_manager.py` - 1 hour
3. `core/monitoring/agent_monitor.py` - 45 minutes
4. `core/monitoring/strategies/` - 3 hours

**Total Wave 3**: 5.25 hours

### Wave 4: Critical Systems (Extensive Testing)
1. `core/monitoring/interfaces.py` - 2 hours
2. `utils/tmux.py` - 2 hours
3. `core/recovery/` modules - 3 hours
4. `core/monitoring/pm_recovery_manager.py` - 1 hour

**Total Wave 4**: 8 hours

## Testing Strategy Per Module

### Unit Test Coverage Required
- **interfaces.py**: 100% - Core contracts
- **tmux.py**: 95% - System integration
- **pm_recovery_manager.py**: 95% - Critical functionality
- **notification_manager.py**: 90% - User-facing
- **health_checker.py**: 90% - Monitoring accuracy

### Integration Test Focus
1. Agent spawn/recovery workflows
2. Monitoring state transitions
3. Notification delivery
4. Cache consistency
5. Async operation handling

## Risk Mitigation

### Pre-transformation Checklist
1. ✓ Ensure full test suite passes
2. ✓ Create git branch for changes
3. ✓ Run mypy baseline check
4. ✓ Document current behavior

### Per-Module Process
1. Transform type hints
2. Update imports
3. Run module tests
4. Run integration tests
5. Manual verification
6. Commit with detailed message

### Rollback Plan
- Git revert per module
- Feature flag for new type system (if needed)
- Parallel testing environment
- Gradual rollout by module

## Success Metrics

1. **Type Coverage**: 100% of legacy types converted
2. **Test Pass Rate**: 100% maintained
3. **Mypy Compliance**: No new type errors
4. **Performance**: No regression in benchmarks
5. **Code Review**: All changes peer-reviewed
