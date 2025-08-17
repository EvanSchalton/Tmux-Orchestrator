# Hierarchical MCP Integration Points - QA Reference

## Critical Integration Points

### 1. MCP Server (mcp_server.py)

#### Configuration Toggle
```python
# Location: __init__ method
hierarchical_mode: bool = True  # Toggle for A/B testing
```

**QA Testing Required:**
- Verify both modes work independently
- Ensure no cross-contamination between modes
- Test mode switching without restart

#### Tool Generation Pipeline
```python
# Modified method: generate_all_mcp_tools()
# Old: Generates 92 flat tools
# New: Generates ~20 hierarchical tools
```

**QA Focus Areas:**
- Tool count validation (92 vs 20)
- Name collision handling
- Registration success/failure

### 2. FastMCP Integration

#### Tool Registration
```python
# Critical integration point
self.mcp.tool(name=tool_name, description=description)(tool_function)
```

**Potential Issues:**
- Schema validation by FastMCP
- Parameter passing differences
- Async function handling

**Test Cases:**
```python
# Verify FastMCP accepts our schema format
assert mcp.get_tool_schema("agent")["properties"]["action"]
assert "enumDescriptions" in schema["properties"]["action"]
```

### 3. CLI Reflection Dependency

#### Command Discovery
```python
# Dependency: tmux-orc reflect --format json
# Used for: Dynamic tool generation
```

**QA Validation:**
- Test with missing CLI
- Test with outdated CLI version
- Test with partial reflection data

### 4. Subprocess Execution

#### Command Building
```python
# Pattern change:
# Old: ["tmux-orc", "agent-status"]
# New: ["tmux-orc", "agent", "status"]
```

**Edge Cases to Test:**
- Special characters in arguments
- Very long argument lists
- Timeout handling
- Concurrent executions

### 5. Error Response Format

#### Structure Change
```json
// Old format
{"error": "Command failed", "output": "..."}

// New format
{
  "success": false,
  "error_type": "invalid_action",
  "message": "Invalid action 'stats' for agent",
  "suggestion": "Valid actions: status, restart, message",
  "example": "Try: agent(action='status')",
  "did_you_mean": "status"
}
```

**Integration Impact:**
- Existing error handlers need updates
- Log parsing tools affected
- Monitoring systems need new patterns

### 6. Schema Validation

#### Conditional Requirements
```python
# New validation logic
if action == "message" and not target:
    raise ValidationError("message requires target")
```

**Test Matrix:**
| Action | Target Required | Args Required | Options |
|--------|----------------|---------------|---------|
| status | No | No | format |
| kill | Yes | No | force |
| message | Yes | Yes (1) | priority |
| deploy | No | Yes (2) | config |

### 7. LLM Tool Discovery

#### Metadata Changes
```python
# Additional fields for LLM
"x-llm-hints": {...}
"enumDescriptions": [...]
"examples": [...]
```

**Validation Points:**
- Metadata doesn't break existing tools
- Size limits on descriptions
- Special character handling

### 8. Performance Critical Paths

#### Startup Sequence
1. CLI reflection (~500ms)
2. Schema generation (~200ms)
3. Tool registration (~100ms per tool)

**Bottleneck Testing:**
- Startup with 1000+ sessions
- Reflection timeout scenarios
- Schema generation with bad data

### 9. State Management

#### Caching Considerations
```python
# Cached data
self.cli_structure  # Reflection results
self.generated_tools  # Tool definitions
self.subcommand_cache  # Group subcommands
```

**Test Scenarios:**
- Cache invalidation
- Memory growth over time
- Concurrent access

### 10. Backward Compatibility

#### Legacy Support
```python
# Must support old-style calls during migration
handle_legacy_tool_call("agent_status")  # → agent(action="status")
```

**Migration Testing:**
- Mixed mode operation
- Gradual rollout scenarios
- Rollback procedures

## Integration Test Checklist

### Pre-Integration
- [ ] Backup current MCP server
- [ ] Document current tool list
- [ ] Prepare rollback script
- [ ] Set up monitoring

### During Integration
- [ ] Enable hierarchical mode
- [ ] Verify tool generation
- [ ] Test each command group
- [ ] Monitor error rates
- [ ] Check performance metrics

### Post-Integration
- [ ] Validate all operations
- [ ] Compare error rates
- [ ] Review performance data
- [ ] Update documentation
- [ ] Plan gradual rollout

## Known Risks & Mitigations

### Risk 1: FastMCP Compatibility
**Mitigation:** Test with FastMCP test suite first

### Risk 2: CLI Version Mismatch
**Mitigation:** Version check on startup

### Risk 3: Performance Regression
**Mitigation:** A/B performance testing

### Risk 4: LLM Confusion
**Mitigation:** Clear migration documentation

## QA Environment Setup

```bash
# Enable debug logging
export MCP_DEBUG=true
export MCP_HIERARCHICAL_MODE=true

# Enable performance profiling
export MCP_PROFILE=true

# Set test timeouts
export MCP_TIMEOUT=30
```

## Monitoring Integration

### Metrics to Track
```python
# Add to monitoring
metrics.gauge('mcp.tools.count', len(tools))
metrics.gauge('mcp.tools.hierarchical', int(hierarchical_mode))
metrics.timer('mcp.generation.time', generation_time)
metrics.counter('mcp.errors.validation', validation_errors)
```

### Alert Thresholds
- Tool generation >5 seconds
- Error rate >5%
- Memory usage >500MB
- Tool count mismatch

## Support Documentation

### Troubleshooting Guide
1. If tools don't appear → Check reflection output
2. If validation fails → Review schema format
3. If performance degrades → Check cache size
4. If LLM fails → Verify enumDescriptions

### Debug Commands
```bash
# Check tool generation
tmux-orc reflect --format json | jq '.agent'

# Test specific tool
python -c "from mcp_server import test_tool; test_tool('agent')"

# Validate schema
python -m jsonschema validate --schema tool_schema.json
```
