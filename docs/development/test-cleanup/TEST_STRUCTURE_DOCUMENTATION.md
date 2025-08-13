# Tmux-Orchestrator Test Structure Documentation

## Current State (Post Phase 2)

### Overview
- **Total Test Files**: 58
- **Total Tests**: 832+ tests
- **Test Classes**: 0 (100% eliminated in Phase 2)
- **Testing Framework**: Pure pytest (no unittest.TestCase)

### Test Directory Organization

```
tests/
├── conftest.py                          # Global fixtures
├── test_cli/                            # CLI command tests
│   ├── agent_test.py                   # 555 lines (needs splitting)
│   ├── errors_test.py
│   ├── execute_test.py
│   ├── monitor_test.py
│   ├── orchestrator_test.py
│   ├── recovery_test.py
│   ├── setup_test.py
│   ├── tasks_test.py
│   ├── team_test.py
│   └── vscode_setup_test.py
│
├── test_core/                           # Core functionality tests
│   ├── error_handler_test.py
│   ├── performance_optimizer_test.py
│   └── test_recovery/                   # Recovery subsystem tests
│       ├── check_agent_health_test.py
│       ├── detect_failure_test.py
│       ├── discover_agents_test.py
│       └── restore_context_test.py
│
├── test_server/                         # Server and API tests
│   ├── mcp_server_test.py
│   ├── routes_basic_test.py
│   └── test_tools/                      # Server tools tests
│       ├── assign_task_test.py
│       ├── broadcast_message_test.py
│       ├── create_pull_request_test.py
│       ├── create_team_test.py
│       ├── get_agent_status_test.py    # 775 lines (needs splitting)
│       ├── get_messages_test.py
│       ├── get_session_status_test.py
│       ├── handoff_work_test.py
│       ├── kill_agent_test.py
│       ├── report_activity_basic_test.py      # Split example (221 lines)
│       ├── report_activity_edge_cases_test.py # Split example (186 lines)
│       ├── report_activity_integration_test.py # Split example (447 lines)
│       ├── run_quality_checks_test.py
│       ├── schedule_checkin_test.py    # 554 lines (needs splitting)
│       ├── send_message_test.py
│       ├── spawn_agent_test.py
│       └── track_task_status_test.py
│
├── test_integration/                    # Integration tests
│   └── end_to_end_test.py
│
└── [Root Level Tests]                   # Feature-specific tests
    ├── compaction_detection_realistic_test.py
    ├── compaction_detection_simple_test.py
    ├── compaction_detection_test.py
    ├── integration_combined_features_test.py
    ├── integration_compaction_test.py
    ├── integration_rate_limit_test.py
    ├── monitor_auto_recovery_test.py
    ├── monitor_autosubmit_test.py
    ├── monitor_crash_detection_test.py
    ├── monitor_daemon_resume_test.py
    ├── monitor_fixtures_dynamic_test.py
    ├── monitor_helpers_test.py
    ├── monitor_manual_test.py
    ├── monitor_message_detection_test.py
    ├── monitor_pm_notifications_test.py
    ├── rate_limit_handling_test.py
    ├── rate_limit_test.py
    └── simplified_restart_system_test.py
```

## Test Naming Conventions

### File Naming
- **Pattern**: `{module_name}_test.py`
- **NOT**: `test_{module_name}.py` (old pattern)
- **Examples**:
  - `monitor_test.py` ✅
  - `test_monitor.py` ❌

### Directory Naming
- **Pattern**: `test_{module}/`
- **Examples**:
  - `test_cli/` ✅
  - `test_server/` ✅
  - `test_core/` ✅

### Function Naming
- **Pattern**: `test_{feature}_{scenario}_{expected_outcome}`
- **Examples**:
  - `test_agent_spawn_valid_type_succeeds()`
  - `test_monitor_rate_limit_detection_pauses_execution()`
  - `test_report_activity_empty_description_raises_error()`

## Key Patterns and Standards

### 1. Pure Pytest Approach
- No test classes (`class Test*`)
- Function-based tests only
- Extensive use of fixtures
- Parametrized tests for multiple scenarios

### 2. Type Hints (Gap Identified)
- **Current**: Most test functions lack type hints
- **Target**: All functions should have `-> None` return type
- **Fixtures**: Should have typed returns

### 3. File Size Management
- **Target**: 300-500 lines per file
- **Current Issues**: 7 files exceed 500 lines
- **Solution**: Split by logical boundaries (basic/edge/integration)

### 4. Fixture Organization
- Global fixtures in `conftest.py`
- Local fixtures in test files with docstrings
- Proper scoping (function/module/session)

## Test Categories

### Unit Tests (Majority)
- Test individual functions/methods
- Mock external dependencies
- Fast execution
- Example: `monitor_helpers_test.py`

### Integration Tests
- Test component interactions
- May use real dependencies
- File prefix: `integration_`
- Example: `integration_rate_limit_test.py`

### Feature Tests
- Test specific features end-to-end
- Often combine multiple components
- Example: `compaction_detection_test.py`

## Coverage Analysis

### Current State
- **Total Tests**: 832+
- **Test Growth**: 7.9% increase during Phase 2
- **Framework**: 100% pytest (no unittest remaining)

### Coverage by Module
- Server tools: Well tested (each tool has dedicated test file)
- CLI commands: Comprehensive coverage
- Core functionality: Good coverage with dedicated test files
- Monitor features: Extensive testing with multiple test files

## Phase 3 Priorities

### 1. File Splitting (7 files)
Priority order based on size:
1. `get_agent_status_test.py` (775 lines)
2. `agent_test.py` (555 lines)
3. `schedule_checkin_test.py` (554 lines)
4. `rate_limit_handling_test.py` (469 lines)
5. `create_team_test.py` (463 lines)
6. `create_pull_request_test.py` (447 lines)
7. `report_activity_integration_test.py` (447 lines)

### 2. Type Hint Addition
- Add `-> None` to all test functions
- Type all fixture returns
- Update function parameters with types

### 3. Pattern Compliance
- Ensure consistent naming patterns
- Verify proper fixture usage
- Maintain test isolation

## Success Metrics

### Quantitative
- All test files < 500 lines
- 100% type hint coverage in tests
- Test count maintained or increased
- Coverage percentage maintained

### Qualitative
- Improved test navigation
- Logical organization
- Clear test purposes
- Easy maintenance

## Maintenance Guidelines

### When Adding Tests
1. Find the corresponding test file for your module
2. Add tests following naming conventions
3. Include type hints
4. Keep files under 500 lines
5. Use fixtures for setup

### When Refactoring Tests
1. Maintain test coverage
2. Follow splitting guidelines
3. Update imports carefully
4. Verify all tests pass
5. Document significant changes

### Regular Reviews
- Monitor file sizes monthly
- Review new tests for pattern compliance
- Update guidelines as needed
- Share learnings with team
