# Old-Style Type Hints Analysis Report

## Summary
Found 72 Python files in `tmux_orchestrator/` (excluding tests) that still use old-style type hints from the `typing` module.

## Files Requiring Conversion

### Priority 1: Core Infrastructure (Critical Path)
These files are central to the system's operation and should be converted first:

1. **`tmux_orchestrator/utils/tmux.py`**
   - Imports: `from typing import Any, Dict, List, Tuple`
   - Usage patterns:
     - `Dict[str, Any]` → `dict[str, Any]`
     - `List[Dict[str, str]]` → `list[dict[str, str]]`
     - `Tuple[bool, str, float]` → `tuple[bool, str, float]`
   - High usage: Cache types, return types for listing methods

2. **`tmux_orchestrator/core/agent_manager.py`**
   - Imports: `from typing import Any, Optional`
   - Usage patterns:
     - `Optional[str]` → `str | None`
     - `Optional[str] = None` → `str | None = None`

3. **`tmux_orchestrator/cli/daemon.py`**
   - Imports: `from typing import Any, Dict, List, Optional`
   - Usage patterns:
     - `Optional[int]` → `int | None`

4. **`tmux_orchestrator/mcp_server.py`**
   - Imports: `from typing import Any, Callable, List`
   - Usage patterns:
     - `List[...]` → `list[...]`

### Priority 2: Core Components
Critical subsystems that other modules depend on:

5. **`tmux_orchestrator/core/monitoring/monitor_service.py`**
   - Multiple uses of `Optional[...]`, `Dict[str, Any]`, `List[AgentInfo]`

6. **`tmux_orchestrator/core/communication/mcp_protocol.py`**
7. **`tmux_orchestrator/core/agent_operations/spawn_agent.py`**
8. **`tmux_orchestrator/core/agent_operations/restart_agent.py`**
9. **`tmux_orchestrator/core/agent_operations/kill_agent.py`**

### Priority 3: CLI Commands
User-facing commands that should maintain consistency:

10. **`tmux_orchestrator/cli/team.py`**
11. **`tmux_orchestrator/cli/setup_claude.py`**
12. **`tmux_orchestrator/cli/recovery.py`**
13. **`tmux_orchestrator/cli/tasks.py`**
14. **`tmux_orchestrator/cli/pubsub.py`**
15. **`tmux_orchestrator/cli/lazy_loader.py`**

### Priority 4: Monitoring Subsystem
Large subsystem with many interconnected files:

16-30. All files in `tmux_orchestrator/core/monitoring/`:
    - `strategies/base_strategy.py`
    - `strategies/concurrent_strategy.py`
    - `strategies/polling_strategy.py`
    - `agent_monitor.py`
    - `health_checker.py`
    - `notification_manager.py`
    - `cache.py`
    - `state_tracker.py`
    - etc.

### Priority 5: Recovery Subsystem
31-38. All files in `tmux_orchestrator/core/recovery/`:
    - `recovery_logger.py`
    - `briefing_manager.py`
    - `auto_restart.py`
    - `notification_manager.py`
    - etc.

### Priority 6: Team Operations
39-41. Files in `tmux_orchestrator/core/team_operations/`:
    - `get_team_status.py`
    - `broadcast_to_team.py`
    - `deploy_team_optimized.py`

### Priority 7: Communication Subsystem
42-44. Files in `tmux_orchestrator/core/communication/`:
    - `send_message.py`
    - `broadcast_message.py`
    - `pm_pubsub_integration.py`

### Priority 8: Utility and Support Files
45-50. Lower priority files:
    - `tmux_orchestrator/utils/rate_limiter.py`
    - `tmux_orchestrator/utils/performance_benchmarks.py`
    - `tmux_orchestrator/core/error_handler.py`
    - `tmux_orchestrator/core/performance_optimizer.py`

### Priority 9: Experimental/Development Files
51-72. Files that appear to be experimental or development-focused:
    - Various `pubsub` related files
    - `mcp_critical_fixes.py`
    - `mcp_fresh.py`
    - Integration example files

## Common Patterns to Convert

1. **Optional Pattern**:
   - Old: `Optional[str]`
   - New: `str | None`

2. **List Pattern**:
   - Old: `List[Dict[str, str]]`
   - New: `list[dict[str, str]]`

3. **Dict Pattern**:
   - Old: `Dict[str, Any]`
   - New: `dict[str, Any]`

4. **Tuple Pattern**:
   - Old: `Tuple[bool, str, float]`
   - New: `tuple[bool, str, float]`

5. **Union Pattern**:
   - Old: `Union[str, int]`
   - New: `str | int`

6. **Set Pattern**:
   - Old: `Set[str]`
   - New: `set[str]`

## Conversion Strategy

1. **Start with Priority 1-2**: Core infrastructure files that many others depend on
2. **Use automated tools**: Consider using `pyupgrade` or similar for bulk conversion
3. **Manual review required**: For complex Union types and edge cases
4. **Test after each priority group**: Ensure no regressions
5. **Update imports**: Remove unnecessary `from typing import` statements

## Estimated Effort

- **Priority 1-3**: 2-3 hours (core files, high impact)
- **Priority 4-6**: 3-4 hours (large subsystems)
- **Priority 7-9**: 2-3 hours (utility and experimental files)
- **Total**: 7-10 hours for complete conversion

## Notes

- Some files may have already been partially converted
- Test files excluded from this analysis but should be converted separately
- Consider running `mypy` or similar type checker after conversion
- Update project's Python version requirement to 3.11+ in pyproject.toml
