# MCP (Model Context Protocol) Guide for Agents

## Quick Start: Using MCP Tools

As a Claude agent in tmux-orchestrator, you have access to **92 powerful MCP tools** that let you interact with the system directly without using bash commands.

### Your First MCP Tool

Instead of running bash commands like `tmux-orc list`, use MCP tools:

```
# Check what agents are active
mcp__tmux-orchestrator__list with kwargs="action=list"

# Get detailed system status
mcp__tmux-orchestrator__monitor with kwargs="action=status"
```

### Discovering Available Tools

```
# See all 92 MCP tools available (if MCP tools are enabled)
Look for tools starting with mcp__tmux-orchestrator__ in Claude Code interface

# Explore command structure via CLI
Use CLI: tmux-orc reflect --format json
```

### MCP Tool Naming Pattern

**Actual MCP Tools:**
- Root commands: `mcp__tmux-orchestrator__[command]` with `kwargs="action=[command]"`
- Grouped commands: `mcp__tmux-orchestrator__[group]` with `kwargs="action=[action] args=[...]"`

Examples:
- `mcp__tmux-orchestrator__list` with `kwargs="action=list"` - List agents
- `mcp__tmux-orchestrator__agent` with `kwargs="action=message args=[target, message]"` - Send message
- `mcp__tmux-orchestrator__monitor` with `kwargs="action=start"` - Start monitoring

## Essential Operations

### 1. Communication
```
# Send message to another agent
mcp__tmux-orchestrator__agent with kwargs="action=send args=[frontend:0, Need help with login form]"

# Broadcast to team
mcp__tmux-orchestrator__team with kwargs="action=broadcast args=[backend, Deployment starting]"
```

### 2. Health Monitoring
```
# Check specific agent status
mcp__tmux-orchestrator__agent with kwargs="action=status target=backend:1"

# Monitor all agents
mcp__tmux-orchestrator__agent with kwargs="action=list"
```

### 3. Deployment
```
# Spawn new agent
mcp__tmux-orchestrator__spawn with kwargs="action=agent args=[frontend, ui:2]"

# Deploy team
mcp__tmux-orchestrator__team with kwargs="action=deploy args=[qa, 3]"
```

## When to Use MCP vs CLI

### Use MCP Tools When:
- ✅ You need structured JSON responses
- ✅ Building automated workflows
- ✅ Chaining multiple operations
- ✅ You want automatic error handling
- ✅ **PREFERRED**: Use MCP whenever possible for consistency

### Use CLI (bash) When:
- 🔧 You need shell features (pipes, redirects)
- 🔧 Following human instructions that use CLI syntax
- 🔧 Debugging with raw output
- 🔧 MCP tools are not available in your Claude Code session

## Error Handling

MCP tools return structured errors with helpful guidance:

```
# If you get an error like "tool not found"
Check that MCP tools are enabled in your Claude Code interface (look for tools icon)

# If you get parameter errors
Verify your kwargs string format: "action=command args=[array, of, args]"
```

## Common Patterns

### Health Check Pattern
```
# Check team status
mcp__tmux-orchestrator__team with kwargs="action=status args=[project-name]"

# If agents are unhealthy, restart them
mcp__tmux-orchestrator__agent with kwargs="action=restart target=backend:1"
```

### Coordination Pattern
```
# Get team status first
mcp__tmux-orchestrator__team with kwargs="action=status args=[frontend]"

# Message all team members
mcp__tmux-orchestrator__team with kwargs="action=broadcast args=[frontend, Meeting in 5 minutes]"

# Or send individual messages
mcp__tmux-orchestrator__agent with kwargs="action=send args=[frontend:2, Please review PR #123]"
```

## MCP Tool Categories

- **Agent Operations**: message, status, restart, kill, list, send
- **Monitoring**: start, stop, status, dashboard
- **Team Management**: deploy, broadcast, status, recover
- **Spawning**: agent, pm, orchestrator
- **System**: list, reflect, status

## Critical Parameter Format

**All MCP tools use `kwargs` parameter as a string:**

```
✅ CORRECT: kwargs="action=list"
✅ CORRECT: kwargs="action=send args=[target, message]"
✅ CORRECT: kwargs="action=status target=session:window"

❌ WRONG: Direct function calls like tmux-orc_list()
❌ WRONG: Using parentheses and args parameters
❌ WRONG: JSON format in kwargs
```

## Pro Tips

1. **Always use string format for kwargs**: `kwargs="action=command"`
2. **Include action parameter**: Every MCP tool needs `action=` specified
3. **Use arrays for multiple args**: `args=[item1, item2]`
4. **Check MCP availability**: Look for tools icon in Claude Code
5. **Fall back to CLI gracefully**: If MCP not available, use `tmux-orc` commands

## Need More Help?

### If MCP Tools Are Available
Use them! They provide better structure and error handling.

### If MCP Tools Are NOT Available
Fall back to CLI commands:
```bash
tmux-orc list
tmux-orc agent send target "message"
tmux-orc team broadcast team-name "message"
```

### Dynamic Discovery
```bash
# Always current CLI syntax
tmux-orc reflect
tmux-orc --help
tmux-orc [command] --help
```

Remember: **MCP tools are preferred when available** - they're designed specifically for AI agent coordination and provide structured responses perfect for automation!
