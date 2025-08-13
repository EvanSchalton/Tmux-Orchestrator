# Phase 3: Large Test Files Analysis and Splitting Plan

## Overview
Following the successful completion of Phase 2 (100% test class elimination), Phase 3 focuses on quality enhancement through splitting large test files according to development-patterns.md guidelines.

**Target**: Test files should be under 300-500 lines for maintainability.

## Files Requiring Splitting (>500 lines)

### Priority 1: Critical Files (>700 lines)
1. **get_agent_status_test.py** (775 lines) - tests/test_server/test_tools/
   - Suggested split:
     - `agent_status_models_test.py` - Model validation tests
     - `agent_status_health_test.py` - Health check and metrics tests
     - `agent_status_activity_test.py` - Activity tracking tests
     - `agent_status_filters_test.py` - Filtering and query tests

### Priority 2: Large Files (550-700 lines)
2. **agent_test.py** (555 lines) - tests/test_cli/
   - Suggested split:
     - `agent_spawn_test.py` - Agent spawning tests
     - `agent_lifecycle_test.py` - Start/stop/restart tests
     - `agent_recovery_test.py` - Recovery and error handling tests

3. **schedule_checkin_test.py** (554 lines) - tests/test_server/test_tools/
   - Suggested split:
     - `checkin_basic_test.py` - Basic checkin functionality
     - `checkin_scheduling_test.py` - Scheduling logic tests
     - `checkin_integration_test.py` - Multi-agent and workflow tests

### Priority 3: Medium Files (450-550 lines)
4. **rate_limit_handling_test.py** (469 lines)
5. **create_team_test.py** (463 lines)
6. **create_pull_request_test.py** (447 lines)
7. **report_activity_integration_test.py** (447 lines) - Already part of a split, may be OK

### Backend Dev's Completed Work (Example to Follow)
- **report_activity_test.py** (819 lines) → Successfully split into:
  - `report_activity_basic_test.py` (221 lines)
  - `report_activity_edge_cases_test.py` (186 lines)
  - `report_activity_integration_test.py` (447 lines)
  - Maintained 98% coverage with 34 total tests

## Files Approaching Limit (400-450 lines) - Monitor
- integration_compaction_test.py (444 lines)
- assign_task_test.py (443 lines)
- monitor_crash_detection_test.py (427 lines)

## Splitting Guidelines

### 1. Logical Boundaries
- **By functionality**: Basic operations, edge cases, integration scenarios
- **By model/component**: Different models or components being tested
- **By complexity**: Simple unit tests vs complex integration tests

### 2. File Naming Convention
- Original: `feature_test.py`
- Split into: `feature_basic_test.py`, `feature_edge_cases_test.py`, `feature_integration_test.py`
- Or by component: `feature_models_test.py`, `feature_validation_test.py`, `feature_workflow_test.py`

### 3. Coverage Requirements
- Maintain or improve coverage percentage
- Ensure no tests are lost during splitting
- Verify all imports are properly updated

### 4. Process Steps
1. Analyze test file structure and identify logical boundaries
2. Create new test files with descriptive names
3. Move tests to appropriate files
4. Update imports and fixtures
5. Run tests to ensure nothing broke
6. Verify coverage remains the same or improves
7. Remove original file only after validation

## Metrics
- Current large files (>500 lines): 7 files
- Total lines to reorganize: ~3,884 lines
- Target after splitting: All files under 500 lines
- Stretch goal: Most files under 400 lines

## Success Criteria
- [ ] All test files under 500 lines
- [ ] Test coverage maintained or improved
- [ ] Logical organization improves test navigation
- [ ] All tests continue to pass
- [ ] Clear naming conventions followed
