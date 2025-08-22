# MCP Agent Usage Guide

## 🚀 Quick Start for Claude Agents

### What is MCP?
MCP (Model Context Protocol) provides you with **92 auto-generated tools** to interact with tmux-orchestrator directly through Claude Desktop. These tools mirror all CLI commands but are optimized for LLM usage.

### How to Discover MCP Tools
When you need to perform any tmux-orchestrator operation, you have access to MCP tools that follow this naming pattern:
- `tmux-orc_[command]` for top-level commands
- `tmux-orc_[group]_[action]` for grouped commands

### Key Advantages of MCP Tools
1. **Direct Execution**: No need to use bash commands
2. **Structured Responses**: JSON-formatted results for easy parsing
3. **Error Handling**: Built-in validation and helpful error messages
4. **Type Safety**: Parameters are validated before execution

## 📋 Complete MCP Tool Categories

### 1. Top-Level Commands (5 tools)
These are your primary entry points for system-wide operations:

| MCP Tool | Purpose | Example Usage |
|----------|---------|---------------|
| `tmux-orc_list` | List all active agents | `tmux-orc_list()` |
| `tmux-orc_reflect` | Discover CLI structure | `tmux-orc_reflect(args=["--format", "json"])` |
| `tmux-orc_status` | System status overview | `tmux-orc_status(options={"json": true})` |
| `tmux-orc_quick_deploy` | Rapid team deployment | `tmux-orc_quick_deploy(args=["frontend", "3"])` |
| `tmux-orc_execute` | Execute commands in sessions | `tmux-orc_execute(args=["session:0", "ls -la"])` |

### 2. Agent Management (10 tools)
Complete lifecycle management for individual agents:

| MCP Tool | Purpose | Parameters |
|----------|---------|------------|
| `tmux-orc_agent_deploy` | Deploy new agent | `args: [agent_type, role]` |
| `tmux-orc_agent_status` | Check agent health | `options: {json: true}` |
| `tmux-orc_agent_message` | Send message to agent | `args: [target, message]` |
| `tmux-orc_agent_send` | Advanced message delivery | `args: [target, message], options: {delay: 0.5}` |
| `tmux-orc_agent_attach` | Attach to agent terminal | `args: [target]` |
| `tmux-orc_agent_restart` | Restart unresponsive agent | `args: [target]` |
| `tmux-orc_agent_kill` | Terminate specific agent | `args: [target]` |
| `tmux-orc_agent_kill_all` | Terminate all agents | No args required |
| `tmux-orc_agent_info` | Get detailed agent info | `args: [target], options: {json: true}` |
| `tmux-orc_agent_list` | List agents with details | `options: {json: true}` |

### 3. Monitoring & Health (10 tools)
System monitoring and health management:

| MCP Tool | Purpose | Parameters |
|----------|---------|------------|
| `tmux-orc_monitor_start` | Start monitoring daemon | `options: {interval: 15}` |
| `tmux-orc_monitor_stop` | Stop monitoring daemon | No args required |
| `tmux-orc_monitor_status` | Check daemon status | `options: {json: true}` |
| `tmux-orc_monitor_dashboard` | Show live dashboard | No args required |
| `tmux-orc_monitor_logs` | View monitoring logs | `options: {follow: true, lines: 50}` |
| `tmux-orc_monitor_recovery_start` | Enable auto-recovery | No args required |
| `tmux-orc_monitor_recovery_stop` | Disable auto-recovery | No args required |
| `tmux-orc_monitor_recovery_status` | Check recovery status | `options: {json: true}` |
| `tmux-orc_monitor_health_check` | Run immediate health check | No args required |
| `tmux-orc_monitor_metrics` | Display performance metrics | `options: {json: true}` |

### 4. Team Coordination (5 tools)
Manage teams of agents working together:

| MCP Tool | Purpose | Parameters |
|----------|---------|------------|
| `tmux-orc_team_deploy` | Create new team | `args: [team_type, size]` |
| `tmux-orc_team_status` | Check team health | `args: [team_name]` |
| `tmux-orc_team_list` | Show all teams | `options: {json: true}` |
| `tmux-orc_team_broadcast` | Message all team members | `args: [team_name, message]` |
| `tmux-orc_team_recover` | Recover failed agents | `args: [team_name]` |

### 5. Spawning Agents (3 tools)
Specialized agent creation:

| MCP Tool | Purpose | Parameters |
|----------|---------|------------|
| `tmux-orc_spawn_agent` | Create agent with role | `args: [agent_type, "session:window"]` |
| `tmux-orc_spawn_pm` | Create Project Manager | `args: [project_name, "session:window"]` |
| `tmux-orc_spawn_orchestrator` | Create orchestrator | `args: ["session:window"]` |

### 6. Context Management (4 tools)
Access and manage agent contexts:

| MCP Tool | Purpose | Parameters |
|----------|---------|------------|
| `tmux-orc_context_orchestrator` | Show orchestrator context | No args required |
| `tmux-orc_context_pm` | Show PM context | No args required |
| `tmux-orc_context_list` | List available contexts | `options: {json: true}` |
| `tmux-orc_context_show` | Display specific context | `args: [context_name]` |

### 7. Additional Command Groups

**Project Manager Operations (6 tools)**
- `tmux-orc_pm_deploy`, `tmux-orc_pm_status`, `tmux-orc_pm_restart`, etc.

**Orchestrator Management (7 tools)**
- `tmux-orc_orchestrator_deploy`, `tmux-orc_orchestrator_status`, etc.

**Setup & Configuration (7 tools)**
- `tmux-orc_setup_claude_code`, `tmux-orc_setup_mcp`, `tmux-orc_setup_all`, etc.

**Recovery Operations (4 tools)**
- `tmux-orc_recovery_start`, `tmux-orc_recovery_stop`, `tmux-orc_recovery_status`, etc.

**PubSub Communication (8 tools)**
- `tmux-orc_pubsub_publish`, `tmux-orc_pubsub_subscribe`, `tmux-orc_pubsub_channels`, etc.

**Daemon Control (5 tools)**
- `tmux-orc_daemon_start`, `tmux-orc_daemon_stop`, `tmux-orc_daemon_status`, etc.

**Task Management (7 tools)**
- `tmux-orc_tasks_add`, `tmux-orc_tasks_list`, `tmux-orc_tasks_complete`, etc.

**Error Handling (4 tools)**
- `tmux-orc_errors_list`, `tmux-orc_errors_clear`, `tmux-orc_errors_report`, etc.

**MCP Server Management (5 tools)**
- `tmux-orc_server_start`, `tmux-orc_server_status`, `tmux-orc_server_tools`, etc.

## 🎯 When to Use MCP vs CLI

### Use MCP Tools When:
1. **You're a Claude agent** operating through Claude Desktop
2. **You need structured responses** for parsing and decision-making
3. **You want automatic error handling** and parameter validation
4. **You're building automated workflows** that chain multiple operations

### Use CLI Commands (via bash) When:
1. **You need shell features** like pipes, redirects, or command chaining
2. **You're debugging** and need raw output
3. **You're writing shell scripts** for system integration
4. **MCP tools aren't available** in your environment

## 💡 Common Usage Patterns

### Pattern 1: Agent Health Check
```python
# Using MCP tools for comprehensive health check
result = tmux-orc_agent_status(options={"json": true})
if result["success"]:
    agents = result["result"]["agents"]
    for agent in agents:
        if agent["status"] == "error":
            tmux-orc_agent_restart(args=[agent["target"]])
```

### Pattern 2: Team Deployment
```python
# Deploy a frontend team with monitoring
tmux-orc_monitor_start(options={"interval": 15})
tmux-orc_team_deploy(args=["frontend", "4"])
tmux-orc_team_status(args=["frontend"])
```

### Pattern 3: Message Broadcasting
```python
# Send coordinated messages to multiple agents
targets = ["frontend:0", "frontend:1", "backend:0"]
for target in targets:
    tmux-orc_agent_send(
        args=[target, "Please prepare for deployment"],
        options={"delay": 0.5}
    )
```

### Pattern 4: System Monitoring
```python
# Set up comprehensive monitoring
tmux-orc_monitor_start()
tmux-orc_monitor_recovery_start()
status = tmux-orc_monitor_status(options={"json": true})
if status["result"]["daemon_healthy"]:
    tmux-orc_monitor_dashboard()
```

## 🔧 Error Handling

### Common MCP Error Responses

1. **Invalid Target Format**
```json
{
    "success": false,
    "error": "Invalid target format. Expected 'session:window'",
    "example": "frontend:0"
}
```

2. **Session Not Found**
```json
{
    "success": false,
    "error": "Session 'nonexistent' not found",
    "available_sessions": ["frontend", "backend", "testing"]
}
```

3. **Missing Required Parameter**
```json
{
    "success": false,
    "error": "Missing required 'action' parameter",
    "valid_actions": ["start", "stop", "status"],
    "example": "monitor(action='start')"
}
```

### Error Recovery Strategies

1. **Automatic Retry with Backoff**
```python
for attempt in range(3):
    result = tmux-orc_agent_send(args=[target, message])
    if result["success"]:
        break
    time.sleep(2 ** attempt)  # Exponential backoff
```

2. **Fallback to Alternative Methods**
```python
# If MCP fails, try CLI
result = tmux-orc_agent_message(args=[target, message])
if not result["success"]:
    # Fallback to bash command
    bash_result = run_bash(f"tmux-orc agent message {target} '{message}'")
```

## 📊 Performance Considerations

### MCP Tool Performance Characteristics
- **Tool Discovery**: <100ms (cached after first use)
- **Command Execution**: 50ms-3s depending on operation
- **JSON Parsing Overhead**: <10ms
- **Error Handling**: Adds ~20ms validation time

### Optimization Tips
1. **Batch Operations**: Use team/broadcast commands vs individual messages
2. **Cache Status**: Use monitor daemon for cached status vs live queries
3. **JSON Output**: Always use `{"json": true}` for structured data
4. **Parallel Execution**: MCP tools can be called concurrently

## 🔍 Discovery and Introspection

### Finding Available Tools
```python
# Discover all MCP tools
tmux-orc_server_tools(options={"json": true})

# Reflect on CLI structure
tmux-orc_reflect(args=["--format", "json"])
```

### Getting Help for Specific Tools
Each MCP tool includes built-in documentation:
- Tool descriptions explain purpose
- Parameter schemas show required/optional args
- Error messages include valid values and examples

## 🚨 Important Notes

### Security Considerations
- MCP tools operate with same permissions as CLI
- No additional authentication required
- Local-only operations (no network exposure)
- Input sanitization prevents injection attacks

### Compatibility
- All 92 MCP tools auto-generated from CLI
- New CLI commands automatically become MCP tools
- No version mismatch between MCP and CLI
- Backward compatibility maintained

### Best Practices
1. **Always check success**: Verify `result["success"]` before using data
2. **Use structured output**: Add `options={"json": true}` for parsing
3. **Handle errors gracefully**: Implement fallback strategies
4. **Monitor performance**: Use timing for optimization
5. **Document tool usage**: Help other agents learn patterns

## 📚 Additional Resources

### Related Documentation
- [MCP Server Commands](./MCP_SERVER_COMMANDS.md) - Technical implementation details
- [MCP Hierarchical Architecture](./architecture/MCP_HIERARCHICAL_ARCHITECTURE_DOCUMENTATION.md) - Architecture overview
- [MCP Command Examples](./architecture/MCP_COMMAND_EXAMPLES.md) - Complex workflow examples
- [MCP LLM Best Practices](./architecture/MCP_LLM_BEST_PRACTICES.md) - Optimization strategies

### Quick Reference Card
```
Top Commands: list, reflect, status, quick-deploy, execute
Agent Ops: deploy, message, send, attach, restart, kill, info
Monitoring: start, stop, status, dashboard, logs, metrics
Team Mgmt: deploy, status, list, broadcast, recover
Spawning: agent, pm, orchestrator
Contexts: show, list, orchestrator, pm
```

Remember: When in doubt, use `tmux-orc_reflect()` to discover available commands and `tmux-orc_server_tools()` to list all MCP tools!
