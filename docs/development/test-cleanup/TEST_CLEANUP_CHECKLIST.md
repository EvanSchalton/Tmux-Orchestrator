# Test Cleanup Checklist - Pattern Violations and Required Improvements

## Summary of Audit Findings

After thorough review of the test codebase against `.claude/commands/development-patterns.md`, I've identified several pattern violations that need to be addressed.

## Critical Pattern Violations

### 1. Test File Naming Convention Violations
**Pattern**: All test files must end with `_test.py` (not start with `test_`)
**Violations Found**:
- [ ] All files in root tests/ directory start with `test_` instead of ending with `_test.py`
  - `test_integration_combined_features.py` → `integration_combined_features_test.py`
  - `test_monitor_auto_recovery.py` → `monitor_auto_recovery_test.py`
  - `test_monitor_crash_detection.py` → `monitor_crash_detection_test.py`
  - And 20+ more files
- [ ] Mixed naming in test_server/test_tools/ (some use `_test.py`, others use `test_`)
  - `test_get_session_status.py` → `get_session_status_test.py`
  - `test_send_message.py` → `send_message_test.py`

### 2. Test Directory Structure Violations
**Pattern**: Test directories must start with `test_`
**Current Structure**: ✅ Already compliant (test_cli/, test_core/, test_server/, test_integration/)

### 3. Test Class vs Function Violations
**Pattern**: Use test functions not classes (prefer `def test_*()` over `class Test*:`)
**Violations Found**:
- [ ] Multiple files using test classes instead of functions:
  - `test_monitor_helpers.py`: Uses `TestClaudeInterfaceDetection`, `TestAgentStateDetection`, etc.
  - `test_compaction_detection.py`: Uses test classes
  - `test_integration_combined_features.py`: Uses test classes
  - `test_integration_compaction.py`: Uses test classes
  - `test_integration_rate_limit.py`: Uses test classes
  - And 10+ more files

### 4. Large Test File Violations
**Pattern**: Keep test files under 300-500 lines for maintainability
**Violations Found**:
- [ ] `test_server/test_tools/report_activity_test.py`: 837 lines → needs splitting
- [ ] `test_server/test_tools/get_agent_status_test.py`: 790 lines → needs splitting
- [ ] `test_server/test_tools/schedule_checkin_test.py`: 563 lines → needs splitting
- [ ] `test_cli/agent_test.py`: 555 lines → needs splitting
- [ ] Several other files over 400 lines

### 5. Test Organization Issues
**Pattern**: Tests should mirror application code structure with one-function-per-file pattern
**Current State**:
- ✅ Good: test_core/test_agent_operations/ properly mirrors core/agent_operations/
- ❌ Bad: Many test files don't follow the one-function-per-file pattern
- ❌ Bad: Some tests are grouped by feature rather than mirroring source structure

### 6. Missing Type Hints
**Pattern**: Type hint everything including test functions, fixtures, and variables
**Status**: Need to audit individual files for missing type hints

### 7. Test Fixture Issues
**Pattern**: Use factory fixtures with test_uuid for traceability
**Status**: Need to verify all fixtures use proper patterns

## Required Actions

### Phase 1: File Naming Standardization
1. [ ] Rename all test files from `test_*.py` to `*_test.py`
2. [ ] Update all imports affected by renaming
3. [ ] Verify pytest discovery still works after renaming

### Phase 2: Convert Test Classes to Functions
1. [ ] Convert all test classes to individual test functions
2. [ ] Group related tests using pytest markers if needed
3. [ ] Ensure proper test isolation after conversion

### Phase 3: Split Large Test Files
1. [ ] Break down files over 500 lines into feature-focused files
2. [ ] Each split file should test a specific aspect/function
3. [ ] Follow one-function-per-file pattern where applicable

### Phase 4: Restructure Tests to Mirror Source
1. [ ] Create proper directory structure mirroring tmux_orchestrator/
2. [ ] Move tests to appropriate locations based on source code
3. [ ] Ensure each source file has corresponding test file

### Phase 5: Type Hint Compliance
1. [ ] Add type hints to all test functions
2. [ ] Add type hints to all fixtures
3. [ ] Add type hints to all test variables and parameters

### Phase 6: Test Quality Improvements
1. [ ] Implement proper factory fixtures with test_uuid
2. [ ] Remove any hardcoded test data
3. [ ] Ensure proper use of pytest.mark.parametrize
4. [ ] Remove tests for built-in functionality

### Phase 7: Coverage and Quality Gates
1. [ ] Run pytest with coverage to ensure 100% coverage maintained
2. [ ] Run mypy to verify type checking passes
3. [ ] Run ruff to ensure code quality
4. [ ] Update CI/CD to enforce these standards

## Success Criteria
- [ ] All test files follow `*_test.py` naming convention
- [ ] No test classes - only test functions
- [ ] No test file exceeds 500 lines
- [ ] Tests properly mirror source code structure
- [ ] 100% type hint coverage in tests
- [ ] All quality checks (pytest, mypy, ruff) pass
- [ ] Test coverage remains at or above current levels
- [ ] Documentation updated with new test structure guidelines

## Coordination Points with Backend Dev
1. File renaming strategy and git history preservation
2. Test splitting approach for large files
3. Handling of shared fixtures during restructuring
4. Migration timeline to minimize disruption
5. CI/CD updates needed for new structure
