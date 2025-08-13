# Remaining Test Files Priority Analysis

Generated: 2025-08-12

## Summary
- **Total files with classes**: 34
- **Total classes remaining**: 81
- **Total functions**: 707

## Priority Groups

### 🔥 High Priority - Critical Core Functionality (6 files, 26 classes)
These files are central to the monitoring and recovery system, with complex setUp/tearDown patterns.

1. **tests/monitor_helpers_test.py** (10 classes, 46 functions)
   - **Complexity**: High - Multiple test classes for different helper functions
   - **Business Value**: Critical - Core monitoring state detection
   - **Risk**: High - Breaking changes could affect agent health monitoring
   - **Dependencies**: Fixture loading system, monitor_helpers module

2. **tests/test_core/test_recovery/detect_failure_test.py** (4 classes, 13 functions)
   - **Complexity**: Medium - Multiple test classes for failure detection scenarios
   - **Business Value**: Critical - Failure detection is core to auto-recovery
   - **Risk**: High - Affects system resilience
   - **Dependencies**: Recovery system, datetime mocking

3. **tests/monitor_auto_recovery_test.py** (3 classes, 12 functions)
   - **Complexity**: Medium - Complex mocking of recovery scenarios
   - **Business Value**: Critical - Auto-recovery is a key feature
   - **Risk**: High - Could break recovery mechanisms
   - **Dependencies**: Monitor, recovery system

4. **tests/monitor_crash_detection_test.py** (4 classes, 16 functions)
   - **Complexity**: Medium - Multiple crash scenarios
   - **Business Value**: Critical - Crash detection prevents zombie agents
   - **Risk**: High - Missing crashes could leave agents hanging
   - **Dependencies**: Monitor crash detection logic

5. **tests/test_core/error_handler_test.py** (1 class, 16 functions)
   - **Complexity**: Medium - Error handling patterns
   - **Business Value**: High - Central error management
   - **Risk**: Medium - Affects error reporting and recovery
   - **Dependencies**: Error handler core module

6. **tests/test_core/performance_optimizer_test.py** (2 classes, 16 functions)
   - **Complexity**: Medium - Performance measurement logic
   - **Business Value**: Medium-High - Affects system efficiency
   - **Risk**: Medium - Performance degradation
   - **Dependencies**: Performance optimizer module

### ⚡ Quick Wins - Simple Conversions (7 files, 11 classes)
These files have minimal setUp/tearDown and straightforward conversions.

1. **tests/compaction_detection_test.py** (1 class, 4 functions)
   - **Complexity**: Low - Single test class with simple assertions
   - **Business Value**: Medium - Prevents false idle alerts
   - **Risk**: Low - Well-isolated functionality
   - **Conversion Time**: ~15 minutes

2. **tests/monitor_daemon_resume_test.py** (1 class, 4 functions)
   - **Complexity**: Low - Single test class for daemon resumption
   - **Business Value**: Medium - Rate limit handling
   - **Risk**: Low - Specific scenario testing
   - **Conversion Time**: ~15 minutes

3. **tests/rate_limit_test.py** (2 classes, 10 functions)
   - **Complexity**: Low - Two simple test classes
   - **Business Value**: Medium - Rate limit detection
   - **Risk**: Low - Well-defined scope
   - **Conversion Time**: ~20 minutes

4. **tests/test_cli/errors_test.py** (1 class, 12 functions)
   - **Complexity**: Low - CLI testing with simple fixtures
   - **Business Value**: Low - UI commands
   - **Risk**: Low - No core logic affected
   - **Conversion Time**: ~20 minutes

5. **tests/test_cli/vscode_setup_test.py** (1 class, 12 functions)
   - **Complexity**: Low - VSCode integration tests
   - **Business Value**: Low - Development environment setup
   - **Risk**: Low - Peripheral functionality
   - **Conversion Time**: ~20 minutes

6. **tests/test_core/test_recovery/check_agent_health_test.py** (1 class, 6 functions)
   - **Complexity**: Low - Simple health check tests
   - **Business Value**: Medium - Agent health monitoring
   - **Risk**: Low - Straightforward logic
   - **Conversion Time**: ~15 minutes

7. **tests/monitor_pm_notifications_test.py** (4 classes, 13 functions)
   - **Complexity**: Low-Medium - PM notification scenarios
   - **Business Value**: Medium - PM communication
   - **Risk**: Low - Notification logic
   - **Conversion Time**: ~30 minutes

### 📊 Medium Priority - Server Tools (16 files, 27 classes)
MCP server tool tests with consistent patterns. Can be batch-converted.

1. **tests/test_server/test_tools/report_activity_test.py** (6 classes, 34 functions)
   - **Complexity**: Medium - Multiple activity type tests
   - **Pattern**: Consistent server tool testing pattern

2. **tests/test_server/test_tools/get_agent_status_test.py** (5 classes, 30 functions)
   - **Complexity**: Medium - Status checking logic
   - **Pattern**: Similar to other server tools

3. **tests/test_server/test_tools/schedule_checkin_test.py** (3 classes, 25 functions)
   - **Complexity**: Medium - Scheduling logic
   - **Pattern**: Temporal testing patterns

4. **tests/test_server/test_tools/create_team_test.py** (1 class, 23 functions)
   - **Complexity**: Medium - Team creation logic
   - **Pattern**: Standard server tool pattern

5. **tests/test_server/test_tools/track_task_status_test.py** (1 class, 21 functions)
   - **Complexity**: Low-Medium - Task tracking
   - **Pattern**: Status management

6. **tests/test_server/test_tools/handoff_work_test.py** (1 class, 21 functions)
   - **Complexity**: Medium - Work handoff logic
   - **Pattern**: Inter-agent communication

7-16. **Other server tool tests** (10 files, ~15 classes total)
   - Similar complexity and patterns
   - Can be converted as a batch using similar approaches

### 🔧 Low Priority - Complex/Peripheral (5 files, 17 classes)
These have complex inheritance or are less critical.

1. **tests/rate_limit_handling_test.py** (7 classes, 25 functions)
   - **Complexity**: High - Multiple test scenarios and complex mocking
   - **Business Value**: Medium - Rate limit is handled but not critical path
   - **Risk**: Low - Feature is additive
   - **Notes**: Consider simplifying before conversion

2. **tests/simplified_restart_system_test.py** (3 classes, 10 functions)
   - **Complexity**: High - System restart scenarios
   - **Business Value**: Medium - Restart functionality
   - **Risk**: Medium - System state management
   - **Notes**: May need architectural review

3. **tests/test_core/test_recovery/discover_agents_test.py** (2 classes, 11 functions)
   - **Complexity**: Medium - Agent discovery logic
   - **Business Value**: Medium - Agent management
   - **Risk**: Low - Discovery mechanism

4. **tests/test_core/test_recovery/restore_context_test.py** (2 classes, 9 functions)
   - **Complexity**: Medium - Context restoration
   - **Business Value**: Medium - Recovery functionality
   - **Risk**: Low - Context management

5. **tests/test_server/routes_basic_test.py** (3 classes, 11 functions)
   - **Complexity**: Low - Basic route testing
   - **Business Value**: Low - HTTP endpoints
   - **Risk**: Low - Web interface

## Conversion Strategy

### Phase 1: Quick Wins (Week 1)
- Convert all 7 quick win files
- Establish patterns for common conversions
- Document conversion patterns for team

### Phase 2: Critical Core (Week 2)
- Focus on monitor and recovery tests
- Ensure no regression in critical functionality
- Add integration tests if gaps found

### Phase 3: Server Tools Batch (Week 3)
- Convert server tool tests using established patterns
- Consider creating conversion script for repetitive patterns
- Validate MCP functionality remains intact

### Phase 4: Complex Files (Week 4)
- Review and potentially refactor complex test files
- Convert remaining low priority files
- Final validation and cleanup

## Key Patterns to Address

1. **Fixture Management**: Many files use class-level fixtures that need conversion to function-level
2. **Mock Patterns**: Consistent mocking patterns across server tools can be extracted
3. **Test Data**: Consider centralizing test data management
4. **Assertion Helpers**: Extract common assertion patterns into shared utilities

## Risk Mitigation

1. **Run full test suite after each file conversion**
2. **Keep original files until all related tests pass**
3. **Focus on one subsystem at a time**
4. **Add integration tests for critical paths before conversion**
5. **Use version control to track each conversion as separate commit**

## Success Metrics

- All tests passing with same or better coverage
- Reduced test execution time
- Simplified test maintenance
- Clear separation of unit and integration tests
- No production bugs from test conversion
