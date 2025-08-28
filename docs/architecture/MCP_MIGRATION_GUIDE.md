# MCP Migration Guide: From Manual to CLI Reflection Architecture

## Overview

This guide helps users migrate from the legacy manual MCP implementation to the new CLI reflection-based architecture in Tmux Orchestrator. The new architecture eliminates code duplication and provides automatic feature parity between CLI and MCP interfaces.

## Key Changes Summary

| Aspect | Old (Manual) | New (CLI Reflection) |
|--------|--------------|---------------------|
| Tool Implementation | Manual files in `server/tools/` | Auto-generated from CLI |
| Protocol | REST/FastAPI (incorrect) | JSON-RPC over stdio (correct) |
| Tool Count | 6 tools | 92 tools (auto-generated) |
| Maintenance | High - dual implementation | Zero - CLI is source of truth |
| New Features | Manual MCP updates required | Automatic MCP tool generation |

## Migration Steps

### 1. Update Your MCP Client Configuration

**Old Configuration (DEPRECATED):**
```json
{
  "mcpServers": {
    "tmux-orchestrator": {
      "command": "python",
      "args": ["-m", "tmux_orchestrator.server"],
      "env": {}
    }
  }
}
```

**New Configuration:**
```json
{
  "mcpServers": {
    "tmux-orchestrator": {
      "command": "python",
      "args": ["-m", "tmux_orchestrator.mcp_server"],
      "env": {}
    }
  }
}
```

### 2. Tool Naming Convention Changes

The new architecture uses a consistent naming convention that matches CLI commands:

**Old Tool Names:**
- `spawn_agent`
- `get_agent_status`
- `kill_agent`
- `send_message`
- `create_team`
- `run_quality_checks`

**New Tool Names (Auto-generated):**
- `tmux-orc_agent_spawn`
- `tmux-orc_agent_status`
- `tmux-orc_agent_kill`
- `tmux-orc_pubsub_send`
- `tmux-orc_team_deploy`
- `tmux-orc_agent_quality-check`

### 3. Tool Parameter Changes

#### Example: Spawning an Agent

**Old Method:**
```python
# Manual tool call
{
  "tool": "spawn_agent",
  "arguments": {
    "session_name": "dev-session",
    "agent_type": "developer",
    "window_number": 1,
    "context": "Custom context"
  }
}
```

**New Method:**
```python
# CLI reflection-based tool call
{
  "tool": "tmux-orc_spawn_agent",
  "arguments": {
    "agent_type": "developer",
    "session_window": "dev-session:1",
    "--context": "Custom context"  # Optional parameters use -- prefix
  }
}
```

### 4. Hierarchical Command Structure

The new architecture supports hierarchical commands with groups and subcommands:

```
tmux-orc
├── agent
│   ├── spawn
│   ├── status
│   ├── kill
│   └── restart
├── monitor
│   ├── start
│   ├── stop
│   └── status
└── team
    ├── deploy
    ├── status
    └── list
```

### 5. Discovering Available Tools

**Old Method:**
- Check `server/tools/` directory
- Read manual tool implementations

**New Method:**
```bash
# List all available commands/tools
tmux-orc reflect --format json

# Get help for specific command
tmux-orc agent spawn --help

# In MCP context, use the discovery tool
{
  "tool": "tmux-orc_reflect",
  "arguments": {
    "--format": "json"
  }
}
```

## Common Migration Scenarios

### Scenario 1: Agent Management

**Old:**
```python
# Spawn agent
spawn_agent(session_name="dev", agent_type="developer", window_number=1)

# Check status
get_agent_status(session_name="dev", window_number=1)

# Kill agent
kill_agent(session_name="dev", window_number=1)
```

**New:**
```python
# Spawn agent
tmux-orc_spawn_agent(agent_type="developer", session_window="dev:1")

# Check status
tmux-orc_agent_status(session_window="dev:1")

# Kill agent
tmux-orc_agent_kill(session_window="dev:1")
```

### Scenario 2: Team Operations

**Old:**
```python
# Create team (manual process)
create_team(team_name="backend-team", agents=["dev1", "dev2", "qa1"])
```

**New:**
```python
# Deploy team using configuration
tmux-orc_team_deploy(config="team-backend.yaml")

# Or quick deploy
tmux-orc_quick-deploy(team_type="backend", session_prefix="backend")
```

### Scenario 3: Monitoring

**Old:**
```python
# No comprehensive monitoring tools
```

**New:**
```python
# Start monitoring
tmux-orc_monitor_start(session_window="dev:0")

# Check daemon status
tmux-orc_daemon_status()

# View heartbeats
tmux-orc_monitor_heartbeat(session="dev")
```

## Breaking Changes

### 1. Removed Tools
The following manual tools have been removed or replaced:
- `handoff_work` → Use `tmux-orc_pubsub_send` with handoff message
- `schedule_checkin` → Use `tmux-orc_monitor_schedule`
- `track_task_status` → Use `tmux-orc_tasks_status`

### 2. Parameter Format Changes
- Session identification: `session_name` + `window_number` → `session_window` (format: "session:window")
- Optional parameters: Now require `--` prefix (e.g., `--context`, `--briefing`)
- Boolean flags: Convert to flag presence (e.g., `force=true` → `--force`)

### 3. Response Format Changes
All tools now return consistent JSON responses matching CLI output:
```json
{
  "success": true,
  "data": {...},
  "error": null
}
```

## Troubleshooting

### Issue: Tool Not Found
**Symptom:** MCP client reports "unknown tool"
**Solution:**
1. Ensure you're using the new MCP server: `python -m tmux_orchestrator.mcp_server`
2. Run `tmux-orc reflect` to verify the tool exists
3. Check tool naming convention (tmux-orc_group_command)

### Issue: Parameter Errors
**Symptom:** "Invalid arguments" error
**Solution:**
1. Use `tmux-orc [command] --help` to check parameter names
2. Remember optional parameters need `--` prefix
3. Use correct session:window format

### Issue: Legacy Code Dependencies
**Symptom:** Import errors or module not found
**Solution:**
1. Remove any imports from `tmux_orchestrator.server`
2. Update to use `tmux_orchestrator.mcp_server`
3. Check for legacy tool imports in your code

## Best Practices

### 1. Use CLI for Testing
Before using an MCP tool, test the equivalent CLI command:
```bash
# Test CLI command first
tmux-orc agent spawn developer myproject:1 --context "Build API"

# Then use in MCP
{
  "tool": "tmux-orc_agent_spawn",
  "arguments": {
    "agent_type": "developer",
    "session_window": "myproject:1",
    "--context": "Build API"
  }
}
```

### 2. Leverage Tool Discovery
Always use reflection to discover available tools and their parameters:
```bash
# Discover all tools
tmux-orc reflect --format json > available_tools.json

# Get specific command help
tmux-orc agent spawn --help
```

### 3. Monitor Migration Progress
Use the new monitoring tools to ensure your migrated setup is working:
```bash
# Check overall system status
tmux-orc status

# Monitor specific sessions
tmux-orc monitor status --session myproject
```

## Migration Checklist

- [ ] Update MCP client configuration to use `mcp_server`
- [ ] Replace old tool names with new CLI-based names
- [ ] Update parameter formats (session:window, -- prefixes)
- [ ] Remove dependencies on `server/` modules
- [ ] Test all critical workflows with new tools
- [ ] Update any automation scripts or integrations
- [ ] Document any custom adaptations needed

## Support and Resources

- **Documentation:** `/docs/architecture/MCP_HIERARCHICAL_ARCHITECTURE_DOCUMENTATION.md`
- **CLI Reference:** Run `tmux-orc reflect` for current commands
- **Examples:** See `/docs/architecture/mcp-examples.md` (coming soon)
- **Issues:** Report problems in project issue tracker

## Future Improvements

The next phase will introduce truly hierarchical tools to reduce the tool count from 92 to ~20:
- Group-based tools with action parameters
- Better organization for LLM consumption
- Simplified tool discovery

Stay tuned for updates in the project documentation.
