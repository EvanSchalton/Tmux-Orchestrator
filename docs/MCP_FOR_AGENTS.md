# MCP For Agents: A Practical Guide

## 🎯 Quick Start: Your First 5 Minutes

Hey there, newly spawned agent! 👋 You've just been created in a tmux session and you're wondering how to interact with the tmux-orchestrator system. Good news: you have **92 powerful MCP tools** at your disposal!

### What Are MCP Tools?

MCP (Model Context Protocol) tools are your direct interface to tmux-orchestrator. Instead of running bash commands like `tmux-orc agent list`, you can use MCP tools that:
- Execute faster with less overhead
- Return structured JSON data you can parse
- Provide better error messages
- Are specifically designed for AI agents like you

### Your First MCP Tool Call

Let's start by checking what agents are currently active:

```python
# Instead of this bash command:
# bash: tmux-orc list

# Use this MCP tool:
tmux-orc_list()
```

Boom! 💥 You just used your first MCP tool. Notice how you didn't need to use bash or parse text output?

## 🔍 Discovering MCP Tools: The Agent's Superpower

### Method 1: List All Available Tools
```python
# See ALL 92 tools available to you
tmux-orc_server_tools(options={"json": true})
```

This returns a complete list of every MCP tool you can use, organized by category.

### Method 2: Explore by Reflection
```python
# Discover the entire CLI structure (which maps to MCP tools)
tmux-orc_reflect(args=["--format", "json"])
```

This shows you the hierarchical command structure. Every command you see here has a corresponding MCP tool!

### Method 3: Pattern Recognition
MCP tools follow predictable naming patterns:
- Top-level command: `tmux-orc_[command]`
- Grouped command: `tmux-orc_[group]_[action]`

Examples:
- `tmux-orc_status()` - Top-level status command
- `tmux-orc_agent_message()` - Agent group, message action
- `tmux-orc_monitor_start()` - Monitor group, start action

## 🚀 Essential Operations Every Agent Should Know

### 1. Check System Status
```python
# Quick status check
tmux-orc_status()

# Detailed JSON status for parsing
status = tmux-orc_status(options={"json": true})
if status["success"]:
    active_agents = status["result"]["summary"]["active_agents"]
    print(f"There are {active_agents} agents currently active")
```

### 2. Communicate with Other Agents
```python
# Send a message to another agent
tmux-orc_agent_message(args=["frontend:0", "Hey, can you help with the login form?"])

# Or use the advanced send for more control
tmux-orc_agent_send(
    args=["backend:1", "STATUS UPDATE: Database migration complete"],
    options={"delay": 0.5}
)
```

### 3. Monitor Your Team
```python
# List all agents with their current status
agents = tmux-orc_agent_list(options={"json": true})

# Check a specific agent's health
agent_info = tmux-orc_agent_info(args=["frontend:0"], options={"json": true})
```

### 4. Deploy New Team Members
```python
# Need help? Spawn another agent!
tmux-orc_spawn_agent(args=["frontend", "dev-team:2"])

# Or deploy a whole team
tmux-orc_team_deploy(args=["backend", "3"])
```

### 5. Handle Errors Gracefully
```python
# MCP tools return structured errors
result = tmux-orc_agent_message(args=["invalid:target", "Hello"])
if not result["success"]:
    print(f"Error: {result['error']}")
    # Output: "Error: Session 'invalid' not found"
```

## 🆚 MCP Tools vs CLI Commands: When to Use What

### Use MCP Tools (Recommended for Agents) When:
✅ You need structured data for decision-making
✅ You're building automated workflows
✅ You want built-in error handling
✅ You're chaining multiple operations
✅ You need fast, direct execution

### Use CLI Commands (via bash) When:
🔧 You need shell features (pipes, redirects)
🔧 You're debugging and need raw output
🔧 You're following human instructions that use CLI syntax
🔧 The operation requires shell scripting
🔧 MCP tools aren't available (rare)

### Quick Comparison Example

**Task**: Get the status of all agents and count how many are active

**CLI Approach** (more complex):
```bash
# Using bash - requires text parsing
output=$(tmux-orc list)
active_count=$(echo "$output" | grep -c "🟢 Active")
echo "Active agents: $active_count"
```

**MCP Approach** (cleaner, faster):
```python
# Using MCP - structured data
result = tmux-orc_list(options={"json": true})
active_count = len([a for a in result["result"]["agents"] if a["status"] == "Active"])
print(f"Active agents: {active_count}")
```

## 📚 Common Patterns and Recipes

### Pattern 1: Health Check and Recovery
```python
# Regular health check pattern
def check_team_health():
    status = tmux-orc_team_status(args=["my-team"], options={"json": true})
    if status["success"]:
        unhealthy = [a for a in status["result"]["agents"] if a["health"] != "healthy"]
        for agent in unhealthy:
            # Attempt restart
            tmux-orc_agent_restart(args=[agent["target"]])
            # Notify PM
            tmux-orc_agent_message(
                args=["pm:0", f"Restarted unhealthy agent: {agent['target']}"]
            )
```

### Pattern 2: Coordinated Team Communication
```python
# Broadcast to all team members
def team_announcement(team_name, message):
    # First, get team members
    team_info = tmux-orc_team_list(options={"json": true})

    # Then broadcast
    tmux-orc_team_broadcast(args=[team_name, message])

    # Verify delivery
    tmux-orc_monitor_logs(options={"lines": 10})
```

### Pattern 3: Progressive Deployment
```python
# Deploy agents one by one with verification
def safe_team_deployment(team_type, size):
    deployed = []
    for i in range(size):
        # Deploy single agent
        result = tmux-orc_spawn_agent(args=[team_type, f"{team_type}:{i}"])

        if result["success"]:
            deployed.append(f"{team_type}:{i}")
            # Wait and verify
            time.sleep(2)
            info = tmux-orc_agent_info(args=[f"{team_type}:{i}"], options={"json": true})
            if not info["success"]:
                # Rollback on failure
                for target in deployed:
                    tmux-orc_agent_kill(args=[target])
                return False
    return True
```

## 🎨 MCP Tool Categories: Your Toolkit

### 🤖 Agent Operations (Your Daily Drivers)
- `tmux-orc_agent_message()` - Your primary communication tool
- `tmux-orc_agent_status()` - Check on your colleagues
- `tmux-orc_agent_info()` - Get detailed agent information
- `tmux-orc_agent_restart()` - Help stuck teammates

### 📊 Monitoring (Stay Informed)
- `tmux-orc_monitor_dashboard()` - Visual system overview
- `tmux-orc_monitor_metrics()` - Performance data
- `tmux-orc_monitor_logs()` - Recent system activity

### 👥 Team Coordination (Work Together)
- `tmux-orc_team_broadcast()` - Message everyone at once
- `tmux-orc_team_status()` - Team health check
- `tmux-orc_team_recover()` - Fix team issues

### 🛠️ System Management (Advanced)
- `tmux-orc_spawn_agent()` - Create new helpers
- `tmux-orc_setup_mcp()` - Configure MCP settings
- `tmux-orc_daemon_status()` - Check background services

## 💡 Pro Tips from Experienced Agents

### 1. Always Use JSON Output
```python
# Good - Structured data
result = tmux-orc_status(options={"json": true})

# Less useful - Human-readable text
result = tmux-orc_status()
```

### 2. Check Success Before Using Data
```python
result = tmux-orc_agent_list(options={"json": true})
if result["success"]:
    # Safe to use result["result"]
    agents = result["result"]["agents"]
else:
    # Handle error
    print(f"Failed: {result['error']}")
```

### 3. Use Context for Better Decisions
```python
# Get your role context
context = tmux-orc_context_show(args=["orchestrator"])
# Use this to understand your responsibilities
```

### 4. Batch Operations When Possible
```python
# Instead of multiple individual messages
# Use broadcast for team-wide communication
tmux-orc_team_broadcast(args=["frontend", "Deployment starting in 5 minutes"])
```

## 🚨 Troubleshooting Common Issues

### "I can't find the MCP tool I need"
```python
# Solution: Discover all tools
all_tools = tmux-orc_server_tools(options={"json": true})
# Search for keywords in tool names
```

### "My MCP tool call failed"
```python
# Check the error details
result = tmux-orc_agent_message(args=["bad:target", "Hello"])
if not result["success"]:
    error = result["error"]
    # Often includes helpful suggestions!
    if "suggestions" in result:
        print(f"Try: {result['suggestions']}")
```

### "I need to run a complex shell command"
```python
# Sometimes bash is the right tool
# Use the execute command for shell operations
bash_result = tmux-orc_execute(args=["session:0", "grep -r 'TODO' *.py | wc -l"])
```

## 🎯 Your MCP Cheat Sheet

```python
# System Overview
tmux-orc_status(options={"json": true})
tmux-orc_list()

# Communication
tmux-orc_agent_message(args=[target, message])
tmux-orc_team_broadcast(args=[team, message])

# Health Checks
tmux-orc_agent_info(args=[target], options={"json": true})
tmux-orc_monitor_metrics()

# Team Management
tmux-orc_team_deploy(args=[type, size])
tmux-orc_spawn_agent(args=[type, target])

# Discovery
tmux-orc_server_tools(options={"json": true})
tmux-orc_reflect(args=["--format", "json"])
```

## 🌟 Remember: You're Part of a Team!

As an agent using MCP tools, you're part of a larger orchestrated system. Use these tools to:
- 🤝 Collaborate with other agents
- 📊 Monitor system health
- 🚀 Deploy help when needed
- 🔧 Fix problems proactively
- 📢 Communicate effectively

The MCP tools are your superpower - use them wisely and your team will thrive!

---

**Need more help?**
- Technical details: See [MCP_SERVER_COMMANDS.md](./MCP_SERVER_COMMANDS.md)
- Full tool reference: Use `tmux-orc_server_tools(options={"json": true})`
- Live examples: Check [MCP_COMMAND_EXAMPLES.md](./architecture/MCP_COMMAND_EXAMPLES.md)
