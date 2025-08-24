# CLI Reflection Test Plan for Pip-Installable Tmux-Orchestrator

## Executive Summary
This test plan covers comprehensive validation of the simplified pip-installable tmux-orchestrator architecture. Tests focus on the CLI reflection approach for auto-generating MCP tools, ensuring 100% test coverage, <3s performance requirements, and local developer environment compatibility.

## Test Scope

### 6 Core Auto-Generated Tools
1. **spawn** - Agent creation in tmux sessions
2. **list** - List all active agents
3. **status** - System status dashboard
4. **execute** - Execute PRD with team deployment
5. **team** - Team management operations (group command)
6. **quick-deploy** - Rapid team deployment

## Test Categories

### 1. Unit Tests
- **Tool Discovery**: Validate each tool is discoverable via CLI reflection
- **Parameter Parsing**: Test parameter extraction and type inference
- **Schema Generation**: Verify JSON schema creation for each tool
- **Error Handling**: Test graceful handling of malformed CLI output

### 2. Integration Tests
- **End-to-End Flow**: CLI discovery → Tool generation → Execution
- **Cross-Tool Communication**: Test tool interactions (spawn → list → status)
- **Session Management**: Validate tmux session lifecycle management
- **State Persistence**: Ensure tool state is maintained across calls

### 3. Performance Tests
- **Individual Tool Execution**: Each tool must execute in <3s
- **Average Performance**: 6-tool average must be <3s
- **Discovery Latency**: CLI reflection must complete in <2s
- **Concurrent Execution**: Support 10 concurrent tool calls

### 4. JSON Validation Tests
- **Schema Compliance**: Output matches expected JSON schema
- **Field Validation**: All required fields present and typed correctly
- **Unicode Support**: Proper handling of special characters
- **Large Payload**: Test with 1MB+ JSON responses

## Test Matrix

| Tool | Unit Tests | Integration | Performance | JSON Valid |
|------|------------|-------------|-------------|------------|
| spawn | ✓ 10 tests | ✓ 5 tests | ✓ <1s target | ✓ Schema |
| list | ✓ 8 tests | ✓ 4 tests | ✓ <0.5s target | ✓ Array |
| status | ✓ 8 tests | ✓ 4 tests | ✓ <1s target | ✓ Object |
| execute | ✓ 12 tests | ✓ 6 tests | ✓ <2s target | ✓ Complex |
| team | ✓ 15 tests | ✓ 7 tests | ✓ <1.5s target | ✓ Nested |
| quick-deploy | ✓ 10 tests | ✓ 5 tests | ✓ <2s target | ✓ Schema |

## Test Data Requirements

### Mock CLI Structures
```json
{
  "spawn": {
    "type": "command",
    "help": "Create new Claude agent in tmux session",
    "parameters": {
      "session_name": {"type": "str", "required": true},
      "agent_type": {"type": "str", "default": "developer"},
      "project_path": {"type": "str", "required": false}
    }
  }
}
```

### Expected MCP Tool Output
```json
{
  "name": "spawn",
  "description": "Create new Claude agent in tmux session",
  "inputSchema": {
    "type": "object",
    "properties": {
      "session_name": {"type": "string"},
      "agent_type": {"type": "string", "default": "developer"},
      "project_path": {"type": "string"}
    },
    "required": ["session_name"]
  }
}
```

## Performance Benchmarks

### Target Metrics
- **P50 (Median)**: <1s for simple commands, <2s for complex
- **P95**: <2.5s for all commands
- **P99**: <3s for all commands (hard requirement)
- **Throughput**: 10 requests/second minimum

### Load Testing Scenarios
1. **Single Tool Burst**: 100 calls to one tool in 10s
2. **Mixed Load**: Rotating through all 6 tools, 60 calls/minute
3. **Concurrent Teams**: 5 teams spawning simultaneously
4. **Stress Test**: Maximum concurrent operations until degradation

## Integration Test Scenarios

### Scenario 1: Team Deployment Workflow
1. Execute PRD → Deploy team → List agents → Check status
2. Validate each step completes successfully
3. Verify state consistency across tools
4. Performance: Total workflow <10s

### Scenario 2: Agent Recovery Flow
1. Spawn agent → Kill agent → List (verify gone) → Respawn
2. Test state cleanup and recreation
3. Validate session management
4. Performance: Each operation <2s

### Scenario 3: Multi-Team Coordination
1. Quick-deploy 3 teams → Broadcast message → Get all status
2. Test concurrent team operations
3. Validate isolation between teams
4. Performance: Total <15s for 3 teams

### Scenario 4: Error Recovery
1. Attempt invalid operations → Verify error responses
2. Test rollback and cleanup
3. Validate system stability
4. Performance: Error handling <1s

## JSON Output Validation

### Schema Validation Rules
1. **Required Fields**: success, data/error, timestamp
2. **Type Safety**: Strict type checking on all fields
3. **Null Handling**: Explicit null vs undefined
4. **Array Bounds**: Max 1000 items in arrays
5. **String Limits**: Max 10KB per string field

### Validation Test Cases
```python
# Example validation test
def test_spawn_output_schema():
    result = await spawn_tool.execute({
        "session_name": "test-session",
        "agent_type": "developer"
    })

    assert validate_json_schema(result, SPAWN_SCHEMA)
    assert result["success"] == True
    assert "session" in result["data"]
    assert "target" in result["data"]
```

## Test Execution Plan

### Phase 1: Package Development (Current)
- ✓ Create all test files
- ✓ Implement mock-based tests
- ✓ Validate test coverage
- ✓ Performance baseline with mocks
- ✓ Pip installable architecture tests

### Phase 2: Local Installation Testing
- Test pip install tmux-orchestrator
- Validate tmux-orc setup workflow
- Test CLI reflection with bundled MCP server
- Performance testing in local environments
- Cross-platform compatibility (Linux/macOS)

### Phase 3: Distribution Validation
- PyPI package validation
- User installation workflows
- Developer onboarding tests
- Documentation accuracy verification

## Success Criteria

### Functional
- [ ] All 6 tools auto-generate successfully
- [ ] 100% test coverage achieved
- [ ] All integration scenarios pass
- [ ] Error handling works correctly

### Performance
- [ ] All tools execute <3s (P99)
- [ ] Average execution <1.5s
- [ ] CLI discovery <2s
- [ ] 10 concurrent operations supported

### Quality
- [ ] JSON validation 100% pass rate
- [ ] No memory leaks detected
- [ ] Graceful degradation under load
- [ ] Clear error messages

## Risk Mitigation

### High Risk Areas
1. **CLI Changes**: Monitor tmux-orc updates
2. **Performance**: Pre-cache CLI reflection data
3. **Concurrency**: Implement proper locking
4. **JSON Size**: Streaming for large responses

### Contingency Plans
1. **Fallback**: Manual tool definitions if reflection fails
2. **Caching**: Aggressive caching of CLI structure
3. **Rate Limiting**: Prevent overload scenarios
4. **Monitoring**: Real-time performance tracking

## Appendix: Test File Locations

- `/tests/mcp/test_auto_generated_tools.py` - Core tool tests
- `/tests/mcp/test_cli_reflection_approach.py` - CLI reflection tests
- `/tests/mcp/test_json_validation.py` - JSON schema validation
- `/tests/mcp/test_performance_benchmarks.py` - Performance suite
- `/tests/mcp/test_integration_scenarios.py` - E2E scenarios
