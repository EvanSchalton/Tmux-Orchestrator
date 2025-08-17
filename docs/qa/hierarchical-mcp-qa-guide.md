# Hierarchical MCP Implementation - QA Guide

## Overview
This document guides QA testing for the hierarchical MCP tool transformation, which reduces 92 flat tools to ~20 hierarchical tools while maintaining 100% functionality.

## Implementation Approach

### 1. Tool Transformation Pattern
```python
# BEFORE: 92 Flat Tools
agent_status()      # Check agent status
agent_kill()        # Kill an agent
agent_message()     # Send message to agent
agent_restart()     # Restart an agent
# ... 88 more tools

# AFTER: ~20 Hierarchical Tools
agent(action="status")
agent(action="kill", target="session:0")
agent(action="message", target="session:1", args=["Hello"])
agent(action="restart", target="session:2")
# ... 15 more group tools
```

### 2. Key Implementation Components

#### HierarchicalSchemaBuilder
- Dynamically generates JSON schemas with conditional validation
- Creates `if/then` rules based on action selection
- Ensures proper parameter requirements per action

#### HierarchicalToolGenerator
- Converts CLI groups into single hierarchical tools
- Maintains auto-generation from CLI reflection
- Preserves all existing functionality

### 3. Schema Structure
Each hierarchical tool has:
- `action` (required): Enum of available subcommands
- `target`: Session:window format (when needed)
- `args`: Positional arguments array
- `options`: Key-value options dict

## Testing Requirements

### 1. Functionality Preservation
Every operation from the 92 flat tools must work identically in hierarchical form:

| Flat Tool | Hierarchical Equivalent | Test Priority |
|-----------|------------------------|---------------|
| `agent_status()` | `agent(action="status")` | HIGH |
| `agent_kill("proj:0")` | `agent(action="kill", target="proj:0")` | HIGH |
| `agent_message("proj:1", "Hi")` | `agent(action="message", target="proj:1", args=["Hi"])` | HIGH |
| `monitor_start(interval=30)` | `monitor(action="start", options={"interval": 30})` | HIGH |
| `team_deploy("frontend", 4)` | `team(action="deploy", args=["frontend", "4"])` | MEDIUM |

### 2. Validation Testing
Test conditional schema validation:

```python
# Should fail - missing required target
agent(action="kill")  # ❌ Error: target required for kill action

# Should fail - missing message content
agent(action="message", target="proj:0")  # ❌ Error: message content required

# Should succeed
agent(action="list")  # ✅ No target needed for list
agent(action="kill", target="proj:0")  # ✅ Valid kill command
```

### 3. Edge Cases
- Actions with optional parameters
- Boolean flags vs value options
- Multiple positional arguments
- Special characters in arguments
- Timeout handling
- JSON output parsing

### 4. Performance Testing
- Measure tool discovery time
- Compare execution speed (flat vs hierarchical)
- Memory usage with schema caching
- Concurrent tool execution

## Test Coverage Matrix

### Command Groups to Test
1. **agent** (10 actions) - Individual agent management
2. **monitor** (10 actions) - Health monitoring
3. **pm** (6 actions) - Project manager operations
4. **context** (4 actions) - Context briefings
5. **team** (5 actions) - Team management
6. **orchestrator** (7 actions) - System management
7. **setup** (7 actions) - Configuration
8. **spawn** (3 actions) - Agent spawning
9. **recovery** (4 actions) - Recovery ops
10. **session** (2 actions) - Session management
11. **pubsub** (4 actions) - Pub/sub operations
12. **pubsub-fast** (4 actions) - Optimized pub/sub
13. **daemon** (5 actions) - Daemon management
14. **tasks** (7 actions) - Task operations
15. **errors** (4 actions) - Error handling
16. **server** (5 actions) - Server operations

### Individual Commands (5 total)
- list
- reflect
- status
- quick-deploy
- (catch-all for unknown commands)

## Automated Test Suite Location
Test implementations should be placed in:
- `/workspaces/Tmux-Orchestrator/tests/test_hierarchical_mcp.py`
- `/workspaces/Tmux-Orchestrator/tests/test_mcp_tool_reduction.py`

## Success Criteria
1. ✅ All 92 operations work identically
2. ✅ Tool count reduced to ~20
3. ✅ Schema validation prevents invalid calls
4. ✅ Performance remains acceptable (<100ms overhead)
5. ✅ LLM success rate ≥ 95%
6. ✅ Backward compatibility maintained
