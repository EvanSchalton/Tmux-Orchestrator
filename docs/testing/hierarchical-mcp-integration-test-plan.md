# Hierarchical MCP Integration Test Plan

## Overview
This comprehensive test plan ensures smooth integration of the hierarchical MCP tool system into the existing tmux-orchestrator infrastructure.

## Test Phases

### Phase 1: Unit Testing (Development Complete)
- ✅ Schema generation for all 16 command groups
- ✅ Error formatting with suggestions
- ✅ Conditional validation logic
- ✅ Tool function generation

### Phase 2: Integration Testing (Current Focus)

#### 2.1 MCP Server Integration
```python
# Test Cases
def test_hierarchical_mode_toggle():
    """Verify hierarchical mode can be enabled/disabled."""
    # Test with hierarchical_mode=True
    server = FreshCLIToMCPServer(hierarchical_mode=True)
    tools = server.generate_all_mcp_tools()
    assert len(tools) < 25  # Should be ~20 tools

    # Test with hierarchical_mode=False
    server = FreshCLIToMCPServer(hierarchical_mode=False)
    tools = server.generate_all_mcp_tools()
    assert len(tools) > 85  # Should be ~92 tools

def test_backwards_compatibility():
    """Ensure flat mode still works correctly."""
    # All 92 operations must work in flat mode

def test_tool_registration():
    """Verify FastMCP accepts hierarchical tools."""
    # Test registration with enhanced metadata
```

#### 2.2 CLI Command Coverage
Test matrix for all 16 command groups:

| Group | Actions | Priority | Test Focus |
|-------|---------|----------|------------|
| agent | 10 | HIGH | Target validation, message handling |
| monitor | 10 | HIGH | Daemon operations, options |
| team | 5 | HIGH | Multi-arg handling |
| pm | 6 | MEDIUM | Broadcast operations |
| orchestrator | 7 | MEDIUM | Complex scheduling |
| setup | 7 | LOW | Configuration handling |
| spawn | 3 | HIGH | Agent type validation |
| recovery | 4 | MEDIUM | Error recovery flows |
| session | 2 | LOW | Simple operations |
| pubsub | 4 | MEDIUM | Message routing |
| pubsub-fast | 4 | LOW | Performance testing |
| daemon | 5 | MEDIUM | Service management |
| tasks | 7 | MEDIUM | CRUD operations |
| errors | 4 | LOW | Error reporting |
| server | 5 | LOW | Server lifecycle |
| context | 4 | LOW | Static content |

#### 2.3 Parameter Validation Testing
```python
# Test conditional requirements
test_cases = [
    # Valid cases
    ("agent", {"action": "status"}, True),
    ("agent", {"action": "kill", "target": "app:0"}, True),
    ("agent", {"action": "message", "target": "app:0", "args": ["Hi"]}, True),

    # Invalid cases - missing required params
    ("agent", {"action": "kill"}, False),  # Missing target
    ("agent", {"action": "message", "target": "app:0"}, False),  # Missing message

    # Invalid target format
    ("agent", {"action": "kill", "target": "invalid"}, False),
]
```

#### 2.4 Error Response Testing
```python
def test_error_formatting():
    """Verify LLM-friendly error responses."""
    response = agent(action="stats")  # Typo
    assert response["error_type"] == "invalid_action"
    assert "did_you_mean" in response
    assert response["did_you_mean"] == "status"
    assert "Valid actions:" in response["suggestion"]
```

### Phase 3: Performance Testing

#### 3.1 Startup Performance
- Measure tool generation time
- Compare hierarchical vs flat generation
- Target: <2 seconds for full generation

#### 3.2 Execution Performance
- Command execution latency
- Concurrent tool execution
- Memory usage comparison

#### 3.3 Scale Testing
```bash
# Stress test with multiple concurrent operations
for i in {1..100}; do
    tmux-orc agent status &
done
wait
```

### Phase 4: LLM Integration Testing

#### 4.1 Claude Integration
- Test with Claude 3.5 Sonnet
- Measure tool selection accuracy
- Target: 95%+ success rate

#### 4.2 Common Patterns
Test frequent usage patterns:
```python
patterns = [
    "Check agent status",
    "Send message to frontend agent",
    "Restart the backend agent",
    "Deploy a new QA engineer",
    "Start monitoring with 30 second interval"
]
```

#### 4.3 Error Recovery
- Test typo correction
- Validate error suggestions
- Measure retry success rate

### Phase 5: End-to-End Testing

#### 5.1 Workflow Testing
Complete workflows using hierarchical tools:
1. Deploy team → Check status → Send messages → Monitor health
2. Start monitoring → Detect issue → Restart agent → Verify recovery
3. Create PM → Deploy team → Coordinate tasks → Generate reports

#### 5.2 Migration Testing
- Deploy with subset of hierarchical tools
- Gradually enable more groups
- Monitor for issues

## Test Environment Setup

### Requirements
```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-mock

# Set up test environment
export MCP_HIERARCHICAL_MODE=true
export MCP_TEST_MODE=true
```

### Test Data
- Mock tmux sessions
- Sample agent configurations
- Test message payloads

## Success Criteria

### Functional
- ✅ All 92 operations work correctly
- ✅ Tool count reduced to ~20
- ✅ No regression in functionality
- ✅ Error messages are helpful

### Performance
- ✅ Tool generation <2 seconds
- ✅ Execution latency <100ms overhead
- ✅ Memory usage reduced by >50%

### LLM Integration
- ✅ 95%+ tool selection accuracy
- ✅ Clear error recovery paths
- ✅ Intuitive parameter handling

## Risk Mitigation

### Rollback Plan
1. Set `MCP_HIERARCHICAL_MODE=false`
2. Restart MCP server
3. Verify flat tools are restored
4. Monitor for issues

### Gradual Rollout
1. Start with 3 groups (agent, monitor, team)
2. Monitor metrics for 24 hours
3. Add 5 more groups
4. Full rollout after validation

## Testing Schedule

| Week | Focus | Deliverable |
|------|-------|-------------|
| 1 | Integration & Unit Tests | Test suite complete |
| 2 | Performance & Scale | Performance report |
| 3 | LLM Integration | Accuracy metrics |
| 4 | End-to-End & Migration | Go/No-go decision |

## Automation

### CI/CD Integration
```yaml
# .github/workflows/mcp-hierarchical-tests.yml
name: Hierarchical MCP Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Integration Tests
        run: |
          pytest tests/test_hierarchical_mcp.py -v
          pytest tests/test_mcp_integration.py -v
      - name: Performance Tests
        run: |
          python tests/benchmark_mcp_generation.py
```

## Monitoring & Metrics

### Key Metrics to Track
1. Tool generation time
2. Tool selection accuracy
3. Error rate by action type
4. Memory usage
5. User success rate

### Dashboards
- Real-time tool usage
- Error frequency by type
- Performance trends
- LLM accuracy tracking
