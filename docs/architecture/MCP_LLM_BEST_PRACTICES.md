# LLM Best Practices for Hierarchical MCP Tools

## Overview

This guide provides best practices for Large Language Models (LLMs) when interacting with the hierarchical MCP tool structure in Tmux Orchestrator. Following these practices ensures efficient tool usage, reduces errors, and improves task completion rates.

## Core Principles

### 1. Tool Discovery First
Always discover available tools before attempting to use them. The tool landscape can change as the CLI evolves.

```json
{
  "tool": "tmux-orc_reflect",
  "arguments": {
    "--format": "json"
  }
}
```

### 2. Hierarchical Navigation
Understand the command hierarchy to navigate efficiently:

```
tmux-orc (root)
├── Direct commands (list, status, reflect)
├── Command groups (agent, monitor, team)
└── Subcommands (agent spawn, agent status)
```

### 3. Progressive Exploration
Start broad and narrow down:
1. Check top-level commands
2. Explore relevant command groups
3. Execute specific subcommands

## Tool Usage Patterns

### Pattern 1: Entity-Action Structure
Most tools follow an entity-action pattern:
- Entity: `agent`, `monitor`, `team`, `daemon`
- Action: `spawn`, `status`, `kill`, `restart`

**Example:**
```json
{
  "tool": "tmux-orc_agent_spawn",
  "arguments": {
    "agent_type": "developer",
    "session_window": "project:1"
  }
}
```

### Pattern 2: Session:Window Format
Always use the `session:window` format for identifying tmux locations:
- ✅ Correct: `"session_window": "myproject:1"`
- ❌ Wrong: `"session": "myproject", "window": "1"`

### Pattern 3: Optional Parameters
Optional parameters require the `--` prefix:
```json
{
  "tool": "tmux-orc_spawn_agent",
  "arguments": {
    "agent_type": "pm",
    "session_window": "project:1",
    "--context": "Custom PM context",
    "--extend": "Additional instructions"
  }
}
```

## Efficient Tool Selection

### 1. Use Semantic Matching
Match user intent to tool categories:

| User Intent | Tool Category | Example Tools |
|------------|---------------|---------------|
| Create/Start | spawn, deploy, start | `agent_spawn`, `monitor_start`, `team_deploy` |
| Check/View | status, list, show | `agent_status`, `monitor_list`, `daemon_status` |
| Stop/Remove | kill, stop, cleanup | `agent_kill`, `monitor_stop`, `daemon_cleanup` |
| Modify | restart, update, configure | `agent_restart`, `context_update` |

### 2. Leverage Command Groups
Group related operations:

**Agent Management Suite:**
```python
# Instead of searching through 92 tools, focus on agent group
agent_tools = [
    "tmux-orc_agent_spawn",
    "tmux-orc_agent_status",
    "tmux-orc_agent_kill",
    "tmux-orc_agent_restart",
    "tmux-orc_agent_health-check",
    "tmux-orc_agent_quality-check"
]
```

### 3. Common Task Workflows

**Workflow: Deploy and Monitor a Team**
```python
# 1. Deploy the team
tmux-orc_team_deploy(config="backend-team.yaml")

# 2. Check deployment status
tmux-orc_team_status(name="backend-team")

# 3. Start monitoring
tmux-orc_monitor_start(session_window="backend-team:0")

# 4. Verify monitoring
tmux-orc_monitor_status(session="backend-team")
```

## Error Handling Best Practices

### 1. Validate Before Execution
Always check prerequisites:

```python
# Before spawning an agent, verify session exists
tmux-orc_status()  # Check overall system

# Before killing an agent, confirm it exists
tmux-orc_agent_status(session_window="dev:1")
```

### 2. Handle Common Errors

**Session Not Found:**
```python
# Error: Session 'myproject' not found
# Solution: Create session first or verify session name
tmux-orc_list()  # List available sessions
```

**Invalid Parameters:**
```python
# Error: Unrecognized arguments
# Solution: Check exact parameter names
tmux-orc_reflect(command="agent spawn")  # Get command details
```

### 3. Graceful Degradation
Have fallback strategies:

```python
try:
    # Try specific monitoring command
    tmux-orc_monitor_health_check(session="dev")
except ToolError:
    # Fall back to general status
    tmux-orc_monitor_status(session="dev")
```

## Performance Optimization

### 1. Batch Related Operations
Group related tool calls to reduce overhead:

```python
# Good: Batch status checks
sessions = ["dev", "qa", "prod"]
statuses = [tmux-orc_agent_status(session_window=f"{s}:1") for s in sessions]

# Avoid: Sequential unrelated calls
tmux-orc_agent_status(session_window="dev:1")
tmux-orc_team_list()
tmux-orc_agent_status(session_window="qa:1")
```

### 2. Cache Tool Discoveries
Store tool information for reuse within a session:

```python
# Cache at session start
available_tools = tmux-orc_reflect(format="json")

# Reuse throughout session
if "tmux-orc_agent_spawn" in available_tools:
    # Use tool
```

### 3. Use Appropriate Detail Levels
Choose the right tool for the information needed:

```python
# Quick check: Use status
tmux-orc_status()  # Lightweight overview

# Detailed info: Use specific commands
tmux-orc_monitor_metrics(session="dev", window=1)  # Detailed metrics
```

## Advanced Patterns

### 1. Context-Aware Tool Selection
Consider the current system state:

```python
# Check if monitoring is already running before starting
monitor_status = tmux-orc_monitor_status()
if not monitor_status["active"]:
    tmux-orc_monitor_start(session_window="dev:0")
```

### 2. Tool Chaining
Chain tools for complex operations:

```python
# Complex workflow: Deploy team with monitoring
def deploy_monitored_team(team_name, config):
    # 1. Deploy team
    result = tmux-orc_team_deploy(config=config)

    # 2. Extract session info
    session = result["session_prefix"]

    # 3. Start monitoring
    tmux-orc_monitor_start(session_window=f"{session}:0")

    # 4. Configure alerts
    tmux-orc_monitor_configure(
        session=session,
        "--alert-threshold": "error"
    )

    return result
```

### 3. Dynamic Tool Generation
For future hierarchical implementation:

```python
# Future pattern: Group-based tools
tmux-orc_group_action(
    group="agent",
    action="spawn",
    parameters={
        "type": "developer",
        "session_window": "dev:1"
    }
)
```

## Common Pitfalls to Avoid

### 1. Hardcoding Tool Names
❌ **Don't:**
```python
# Hardcoded tool names
tools = ["spawn_agent", "kill_agent"]  # Old names
```

✅ **Do:**
```python
# Discover current tools
tools = tmux-orc_reflect(format="json")
```

### 2. Ignoring Optional Parameters
❌ **Don't:**
```python
tmux-orc_agent_spawn("developer", "dev:1", "context")  # Positional
```

✅ **Do:**
```python
tmux-orc_agent_spawn(
    agent_type="developer",
    session_window="dev:1",
    **{"--context": "context"}  # Named with prefix
)
```

### 3. Assuming Tool Availability
❌ **Don't:**
```python
# Assume tool exists
tmux-orc_experimental_feature()  # May not exist
```

✅ **Do:**
```python
# Check availability first
if tool_exists("tmux-orc_experimental_feature"):
    tmux-orc_experimental_feature()
```

## Testing and Validation

### 1. Test Tool Calls
Always test in safe environments:

```python
# Test with dry-run or info commands first
tmux-orc_agent_spawn(
    agent_type="developer",
    session_window="test:1",
    **{"--dry-run": True}  # If supported
)
```

### 2. Validate Responses
Check tool response structure:

```python
response = tmux-orc_agent_status(session_window="dev:1")
assert "success" in response
assert "data" in response
if not response["success"]:
    handle_error(response["error"])
```

### 3. Monitor Tool Performance
Track tool execution times:

```python
import time

start = time.time()
result = tmux-orc_team_deploy(config="large-team.yaml")
duration = time.time() - start

if duration > 30:  # Threshold
    log_slow_operation("team_deploy", duration)
```

## Future-Proofing

### 1. Prepare for Hierarchical Tools
The next evolution will reduce tools from 92 to ~20:

**Current (Flat):**
```python
tmux-orc_agent_spawn
tmux-orc_agent_status
tmux-orc_agent_kill
```

**Future (Hierarchical):**
```python
tmux-orc_agent(action="spawn", ...)
tmux-orc_agent(action="status", ...)
tmux-orc_agent(action="kill", ...)
```

### 2. Abstract Tool Interfaces
Create abstraction layers:

```python
class TmuxOrcInterface:
    def agent_operation(self, action, **kwargs):
        # Current: Map to specific tools
        tool_name = f"tmux-orc_agent_{action}"
        return call_tool(tool_name, **kwargs)

        # Future: Use hierarchical tool
        # return call_tool("tmux-orc_agent", action=action, **kwargs)
```

## Summary Checklist

- [ ] Always discover tools before use (`tmux-orc_reflect`)
- [ ] Use correct parameter formats (session:window, -- prefixes)
- [ ] Follow entity-action patterns for tool selection
- [ ] Validate prerequisites before operations
- [ ] Handle errors gracefully with fallbacks
- [ ] Cache tool discoveries for performance
- [ ] Test tool calls in safe environments
- [ ] Prepare for future hierarchical structure

## Resources

- **Tool Discovery:** `tmux-orc reflect --format json`
- **Command Help:** `tmux-orc [command] --help`
- **Migration Guide:** `/docs/architecture/MCP_MIGRATION_GUIDE.md`
- **Architecture Docs:** `/docs/architecture/MCP_HIERARCHICAL_ARCHITECTURE_DOCUMENTATION.md`
