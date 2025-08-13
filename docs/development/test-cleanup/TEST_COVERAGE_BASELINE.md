# Test Coverage Baseline Report

## Current Coverage Metrics
- **Overall Coverage**: 17%
- **Total Lines**: 10,698
- **Covered Lines**: 8,342
- **Branch Coverage**: 3,346 branches, 3 covered

## Coverage by Module

### Low Coverage Areas (Critical for Improvement)
1. **Utils Module**:
   - `claude_interface.py`: 0% coverage (131 lines uncovered)
   - `tmux.py`: 12% coverage (needs significant work)

2. **Server Tools** (Most need attention):
   - `run_quality_checks.py`: 21% coverage
   - `kill_agent.py`: 22% coverage
   - `schedule_checkin.py`: 23% coverage
   - `restart_agent.py`: 23% coverage
   - `spawn_agent.py`: 30% coverage
   - `report_activity.py`: 32% coverage
   - `track_task_status.py`: 33% coverage
   - `send_message.py`: 41% coverage

3. **Core Monitor Module**:
   - Generally well tested but some gaps remain

## Test Execution Issues
- One test currently failing: `test_compaction_detection.py::TestCompactionDetection::test_detects_compacting_above_input_box`
- This needs to be fixed as part of the cleanup

## Quality Requirements for Cleanup
1. **Maintain or improve current 17% baseline**
2. **Target 100% coverage per development-patterns.md**
3. **All tests must pass after restructuring**
4. **Coverage reports must include branch coverage**

## Recommendations
1. Start with high-value, low-coverage modules
2. Write missing tests as part of the restructuring
3. Use coverage reports to identify untested code paths
4. Implement coverage-driven development approach
