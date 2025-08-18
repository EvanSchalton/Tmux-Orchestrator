# Sprint 2 Test Plan: CLI Server Commands

## Overview
Test plan for validating new CLI server commands implementation in Sprint 2.

## Test Objectives
1. Verify all CLI server commands function correctly
2. Validate JSON output compatibility for MCP
3. Ensure performance meets requirements (<500ms target)
4. Test error handling and edge cases

## Test Cases

### TC-001: CLI Server Start Command
**Description**: Verify CLI server can be started via command
**Pre-conditions**: tmux-orchestrator installed
**Test Steps**:
1. Run `tmux-orc server start`
2. Verify server process launches
3. Check server responds to health checks
4. Validate PID file creation

**Expected Results**: Server starts successfully, health check passes

### TC-002: CLI Server Stop Command
**Description**: Verify CLI server can be stopped gracefully
**Pre-conditions**: Server running
**Test Steps**:
1. Run `tmux-orc server stop`
2. Verify graceful shutdown
3. Check process termination
4. Validate PID file removal

**Expected Results**: Server stops cleanly

### TC-003: CLI Server Status Command
**Description**: Verify server status reporting
**Pre-conditions**: None
**Test Steps**:
1. Run `tmux-orc server status` (server stopped)
2. Start server
3. Run `tmux-orc server status` (server running)
4. Validate JSON output with `--json` flag

**Expected Results**: Accurate status in both states

### TC-004: CLI Server Restart Command
**Description**: Verify server restart functionality
**Pre-conditions**: Server running
**Test Steps**:
1. Note server PID
2. Run `tmux-orc server restart`
3. Verify new PID
4. Check no downtime in logs

**Expected Results**: Server restarts with new process

### TC-005: CLI Server Logs Command
**Description**: Verify log access functionality
**Pre-conditions**: Server has been running
**Test Steps**:
1. Run `tmux-orc server logs`
2. Run `tmux-orc server logs --tail 50`
3. Run `tmux-orc server logs --follow` (test interrupt)
4. Validate log format and content

**Expected Results**: Logs displayed correctly

### TC-006: Performance Validation
**Description**: Verify server commands meet performance targets
**Pre-conditions**: Server installed
**Test Steps**:
1. Time each server command execution
2. Run commands 10 times, calculate average
3. Test under load (multiple concurrent requests)

**Expected Results**: All commands <500ms average

### TC-007: Error Handling
**Description**: Verify graceful error handling
**Pre-conditions**: Various
**Test Steps**:
1. Start server when already running
2. Stop server when not running
3. Invalid command arguments
4. Permission denied scenarios

**Expected Results**: Clear error messages, no crashes

## Automation Strategy
- Create pytest test suite in `/tests/sprint2/test_cli_server_commands.py`
- Use subprocess for command execution
- Mock where appropriate for edge cases
- Performance benchmarking with time.perf_counter()

## Success Criteria
- All test cases pass
- Performance <500ms for all commands
- No regressions in existing functionality
- Clean error handling
