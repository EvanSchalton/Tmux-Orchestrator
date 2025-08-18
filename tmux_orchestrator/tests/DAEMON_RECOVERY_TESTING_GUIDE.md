# Daemon Recovery Testing Guide

## Overview
This guide provides comprehensive testing instructions for the critical daemon recovery fixes implemented in the tmux-orchestrator monitoring system.

## Fixed Issues
1. **False Positive Crash Detection**: Removed '$ ' from crash indicators, added smart shell prompt detection
2. **PM Recovery Cooldown**: Added 5-minute cooldown between recovery attempts
3. **Team Notification Bug**: Fixed duplicate method signatures in notification system
4. **Singleton Enforcement**: Verified proper implementation of singleton pattern

## Test Suite Structure

### Main Test File
- `tmux_orchestrator/tests/test_daemon_recovery_fixes.py` - Comprehensive test suite

### Test Classes
1. `TestFalsePositiveCrashDetection` - False positive prevention tests
2. `TestPMRecoveryCooldown` - Recovery cooldown mechanism tests  
3. `TestTeamNotificationFixes` - Team notification method tests
4. `TestSingletonEnforcement` - Singleton pattern tests
5. `TestIntegrationScenarios` - End-to-end integration tests

## QA Testing Focus Areas

### 1. False Positive Crash Detection
**Critical Test**: Agents discussing shell prompts should NOT trigger crashes

**Test Scenarios**:
```bash
# Run false positive tests
pytest tmux_orchestrator/tests/test_daemon_recovery_fixes.py::TestFalsePositiveCrashDetection -v

# Manual validation:
# 1. Create agent that discusses shell prompts in conversation
# 2. Verify daemon doesn't mark it as crashed
# 3. Test actual shell prompt at end DOES trigger crash
```

**Key Test Cases**:
- Dollar signs in normal conversation ("The cost is $50")
- Discussing killed processes ("The process was killed")
- Tool output with dollar amounts
- Actual shell prompts at terminal end (should trigger crash)

### 2. PM Recovery Cooldown
**Critical Test**: Rapid PM recovery attempts should be blocked

**Test Scenarios**:
```bash
# Run cooldown tests
pytest tmux_orchestrator/tests/test_daemon_recovery_fixes.py::TestPMRecoveryCooldown -v

# Manual validation:
# 1. Kill PM in a session
# 2. Verify daemon recovers PM
# 3. Kill PM again immediately
# 4. Verify daemon waits 5 minutes before next recovery
```

**Key Timings**:
- First recovery: Should happen immediately
- Second recovery within 5 minutes: Should be blocked
- Recovery after 5+ minutes: Should be allowed

### 3. Team Notification System
**Critical Test**: PM recovery notifications should work without errors

**Test Scenarios**:
```bash
# Run notification tests
pytest tmux_orchestrator/tests/test_daemon_recovery_fixes.py::TestTeamNotificationFixes -v

# Manual validation:
# 1. Create session with PM + agents
# 2. Kill PM
# 3. Verify other agents receive recovery notification
# 4. Check daemon logs for any method signature errors
```

**Expected Behavior**:
- All team agents receive "PM recovered" message
- No method signature errors in logs
- Notifications sent to correct agent windows

### 4. Singleton Enforcement
**Critical Test**: Only one monitor daemon should run at a time

**Test Scenarios**:
```bash
# Run singleton tests
pytest tmux_orchestrator/tests/test_daemon_recovery_fixes.py::TestSingletonEnforcement -v

# Manual validation:
# 1. Start monitor daemon
# 2. Try to start second daemon
# 3. Verify second attempt fails/uses existing daemon
```

**Expected Behavior**:
- Second daemon start uses existing instance
- PID file prevents multiple daemons
- Thread-safe instance creation

## Running the Complete Test Suite

### Prerequisites
```bash
# Ensure pytest is available
pip install pytest

# Ensure test dependencies are met
cd /workspaces/Tmux-Orchestrator
```

### Run All Tests
```bash
# Run complete daemon recovery test suite
pytest tmux_orchestrator/tests/test_daemon_recovery_fixes.py -v

# Run with detailed output
pytest tmux_orchestrator/tests/test_daemon_recovery_fixes.py -v -s

# Run specific test class
pytest tmux_orchestrator/tests/test_daemon_recovery_fixes.py::TestFalsePositiveCrashDetection -v
```

## Integration Testing Scenarios

### Scenario 1: Complete PM Recovery Flow
1. Start monitoring daemon
2. Create session with PM and agents
3. Kill PM to trigger recovery
4. Verify recovery happens
5. Kill PM again immediately
6. Verify cooldown prevents immediate recovery
7. Wait 5+ minutes
8. Kill PM again
9. Verify recovery works after cooldown

### Scenario 2: False Positive Prevention
1. Start monitoring daemon
2. Create agents in sessions
3. Have agents discuss shell prompts, killed processes, failures
4. Monitor daemon logs for false crash detections
5. Verify only actual crashes trigger recovery

### Scenario 3: Notification System
1. Start monitoring daemon
2. Create session with PM + multiple agents
3. Trigger PM recovery
4. Verify all agents receive notifications
5. Check logs for any notification errors

## Expected Log Messages

### Successful Operation
```
[INFO] PM recovery cooldown active - waiting X minutes
[INFO] PM recovered successfully at test-session:1
[DEBUG] Ignoring crash indicator '$ ' - appears to be normal output
[INFO] All team agents notified of PM recovery
```

### Error Conditions (Should NOT Occur)
```
[ERROR] Multiple notification methods found
[ERROR] Method signature mismatch in _notify_team_of_pm_recovery
[ERROR] Multiple monitor daemons detected
```

## Post-Test Verification

### Daemon Stability Checklist
- [ ] No false positive crash detections in logs
- [ ] PM recovery cooldown working (5-minute intervals)
- [ ] Team notifications successful without errors
- [ ] Single daemon instance maintained
- [ ] No method signature errors in logs
- [ ] Proper shell prompt detection at terminal end

### Log Analysis
Check daemon logs at:
- `.tmux_orchestrator/logs/idle-monitor.log`
- Look for the "Expected Log Messages" patterns above
- Verify no "Error Conditions" are present

## Troubleshooting

### Common Issues
1. **Tests failing with import errors**: Ensure tmux_orchestrator package is importable
2. **Mock failures**: Verify TMUXManager and logger mocks are properly configured
3. **Timing issues**: Some tests use datetime mocking - check system clock

### Debug Commands
```bash
# Check daemon status
tmux-orc monitor status

# View recent logs
tail -f .tmux_orchestrator/logs/idle-monitor.log

# List tmux sessions for manual testing
tmux list-sessions
```

## Success Criteria

### Test Suite Must Pass
- All test classes pass without errors
- Integration scenarios complete successfully
- No regressions in existing functionality

### Manual Validation Must Confirm
- False positive crash detection eliminated
- PM recovery cooldown prevents thrashing
- Team notifications work reliably
- Singleton pattern enforced properly

## Contact
For questions about these tests or the fixes, contact the Backend Developer who implemented the changes.