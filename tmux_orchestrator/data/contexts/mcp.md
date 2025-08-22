# MCP (Model Context Protocol) Guide for Agents

## Quick Start: Using MCP Tools

As a Claude agent in tmux-orchestrator, you have access to **92 powerful MCP tools** that let you interact with the system directly without using bash commands.

### Your First MCP Tool

Instead of running bash commands like `tmux-orc list`, use MCP tools:

```python
# Check what agents are active
tmux-orc_list()

# Get detailed system status
tmux-orc_status(options={"json": true})
```

### Discovering Available Tools

```python
# See all 92 MCP tools
tmux-orc_server_tools(options={"json": true})

# Explore command structure
tmux-orc_reflect(args=["--format", "json"])
```

### MCP Tool Naming Pattern

- Top-level: `tmux-orc_[command]`
- Grouped: `tmux-orc_[group]_[action]`

Examples:
- `tmux-orc_status()` - Top-level status
- `tmux-orc_agent_message()` - Agent group, message action
- `tmux-orc_monitor_start()` - Monitor group, start action

## Essential Operations

### 1. Communication
```python
# Send message to another agent
tmux-orc_agent_message(args=["frontend:0", "Need help with login form"])

# Broadcast to team
tmux-orc_team_broadcast(args=["backend", "Deployment starting"])
```

### 2. Health Monitoring
```python
# Check specific agent
info = tmux-orc_agent_info(args=["backend:1"], options={"json": true})

# Monitor all agents
agents = tmux-orc_agent_list(options={"json": true})
```

### 3. Deployment
```python
# Spawn new agent
tmux-orc_spawn_agent(args=["frontend", "ui:2"])

# Deploy team
tmux-orc_team_deploy(args=["qa", "3"])
```

## When to Use MCP vs CLI

### Use MCP Tools When:
- ✅ You need structured JSON responses
- ✅ Building automated workflows
- ✅ Chaining multiple operations
- ✅ You want automatic error handling

### Use CLI (bash) When:
- 🔧 You need shell features (pipes, redirects)
- 🔧 Following human instructions that use CLI syntax
- 🔧 Debugging with raw output

## Error Handling

MCP tools return structured errors:

```python
result = tmux-orc_agent_message(args=["invalid:0", "Hello"])
if not result["success"]:
    print(f"Error: {result['error']}")
    # Often includes suggestions!
```

## Common Patterns

### Health Check Pattern
```python
status = tmux-orc_agent_status(options={"json": true})
if status["success"]:
    unhealthy = [a for a in status["result"]["agents"]
                 if a["status"] == "error"]
    for agent in unhealthy:
        tmux-orc_agent_restart(args=[agent["target"]])
```

### Coordination Pattern
```python
# Get team status
team = tmux-orc_team_status(args=["frontend"], options={"json": true})

# Message all active members
for agent in team["result"]["agents"]:
    if agent["status"] == "active":
        tmux-orc_agent_send(
            args=[agent["target"], "Meeting in 5 minutes"],
            options={"delay": 0.5}
        )
```

## MCP Tool Categories

- **Agent Operations**: message, status, restart, kill, info
- **Monitoring**: start, stop, dashboard, metrics, logs
- **Team Management**: deploy, broadcast, status, recover
- **Spawning**: agent, pm, orchestrator
- **System**: setup, reflect, execute

## Pro Tips

1. **Always use JSON output** for parsing: `options={"json": true}`
2. **Check success** before using results: `if result["success"]:`
3. **Use appropriate delays** for message operations
4. **Batch operations** when possible (team broadcast vs individual messages)

## Need More Help?

For comprehensive documentation, see:
- `/docs/MCP_FOR_AGENTS.md` - Tutorial-style guide
- `/docs/MCP_TOOL_REFERENCE.md` - All 92 tools reference
- `/docs/MCP_EXAMPLES_AND_ERROR_HANDLING.md` - Real-world examples

Or discover tools dynamically:
```python
tmux-orc_server_tools(options={"json": true})
```

Remember: MCP tools are your superpower - they're faster, more reliable, and designed specifically for AI agents like you!
