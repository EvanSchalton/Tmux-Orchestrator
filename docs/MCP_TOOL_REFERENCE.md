# MCP Tool Reference: Complete Guide to All 92 Tools

## Overview
This reference documents all 92 auto-generated MCP tools available in tmux-orchestrator, organized by category with complete parameter specifications and usage examples.

## Tool Naming Convention
- **Top-level commands**: `tmux-orc_[command]`
- **Grouped commands**: `tmux-orc_[group]_[action]`

## Parameter Types
- **args**: Array of positional arguments `["arg1", "arg2"]`
- **options**: Dictionary of named options `{"key": "value", "flag": true}`

---

## 📋 Top-Level Commands (5 tools)

### tmux-orc_list
Lists all active agents across sessions with comprehensive status.

**Parameters:**
- `options`:
  - `json`: Return JSON output (boolean)

**Example:**
```python
# Human-readable format
tmux-orc_list()

# JSON format for parsing
result = tmux-orc_list(options={"json": true})
agents = result["result"]["agents"]
```

### tmux-orc_reflect
Generate complete CLI command structure via runtime introspection.

**Parameters:**
- `args`:
  - Format type: `["--format", "tree|json|markdown"]`
  - Filter: `["--filter", "pattern"]`
- `options`:
  - `include_hidden`: Include hidden commands (boolean)

**Example:**
```python
# Get JSON structure
tmux-orc_reflect(args=["--format", "json"])

# Filter for agent commands
tmux-orc_reflect(args=["--filter", "agent"])
```

### tmux-orc_status
Display comprehensive system status dashboard.

**Parameters:**
- `options`:
  - `json`: Return JSON output (boolean)

**Example:**
```python
# Get system status
status = tmux-orc_status(options={"json": true})
if status["result"]["summary"]["healthy"]:
    print("System healthy")
```

### tmux-orc_quick_deploy
Rapidly deploy optimized team configurations.

**Parameters:**
- `args`: `[team_type, size]`
  - team_type: "frontend", "backend", "fullstack", "testing"
  - size: Number string "2"-"6"
- `options`:
  - `project_name`: Custom project name (string)

**Example:**
```python
# Deploy a 4-person frontend team
tmux-orc_quick_deploy(args=["frontend", "4"])

# With custom project name
tmux-orc_quick_deploy(
    args=["backend", "3"],
    options={"project_name": "api-service"}
)
```

### tmux-orc_execute
Execute commands in tmux sessions.

**Parameters:**
- `args`: `[target, command]`
  - target: "session:window" format
  - command: Shell command to execute

**Example:**
```python
# Run a command in a session
tmux-orc_execute(args=["dev:0", "npm test"])
```

---

## 🤖 Agent Management (10 tools)

### tmux-orc_agent_deploy
Deploy an individual specialized agent.

**Parameters:**
- `args`: `[agent_type, role]`
  - agent_type: "frontend", "backend", "testing", "database", "docs", "devops"
  - role: "developer", "pm", "qa", "reviewer"

**Example:**
```python
tmux-orc_agent_deploy(args=["frontend", "developer"])
tmux-orc_agent_deploy(args=["backend", "pm"])
```

### tmux-orc_agent_message
Send a message directly to a specific agent.

**Parameters:**
- `args`: `[target, message]`
  - target: "session:window" format
  - message: Text to send

**Example:**
```python
tmux-orc_agent_message(args=["frontend:0", "Please review the login component"])
```

### tmux-orc_agent_send
Advanced message delivery with timing control.

**Parameters:**
- `args`: `[target, message]`
- `options`:
  - `delay`: Inter-operation delay (0.1-5.0 seconds)

**Example:**
```python
tmux-orc_agent_send(
    args=["backend:1", "Deploy the API changes"],
    options={"delay": 1.0}
)
```

### tmux-orc_agent_attach
Attach to an agent's terminal for direct interaction.

**Parameters:**
- `args`: `[target]`

**Example:**
```python
tmux-orc_agent_attach(args=["frontend:0"])
```

### tmux-orc_agent_restart
Restart a specific agent that has become unresponsive.

**Parameters:**
- `args`: `[target]`

**Example:**
```python
tmux-orc_agent_restart(args=["backend:2"])
```

### tmux-orc_agent_kill
Terminate a specific agent.

**Parameters:**
- `args`: `[target]`

**Example:**
```python
tmux-orc_agent_kill(args=["test:3"])
```

### tmux-orc_agent_kill_all
Terminate ALL agents across all sessions.

**Parameters:** None

**Example:**
```python
tmux-orc_agent_kill_all()
```

### tmux-orc_agent_info
Get detailed diagnostic info about specific agent.

**Parameters:**
- `args`: `[target]`
- `options`:
  - `json`: Return JSON output (boolean)

**Example:**
```python
info = tmux-orc_agent_info(args=["frontend:0"], options={"json": true})
```

### tmux-orc_agent_list
List all agents with health info.

**Parameters:**
- `options`:
  - `json`: Return JSON output (boolean)

**Example:**
```python
agents = tmux-orc_agent_list(options={"json": true})
```

### tmux-orc_agent_status
Show comprehensive status of all agents.

**Parameters:**
- `options`:
  - `json`: Return JSON output (boolean)

**Example:**
```python
status = tmux-orc_agent_status(options={"json": true})
```

---

## 📊 Monitoring & Health (10 tools)

### tmux-orc_monitor_start
Start monitoring daemon with interval.

**Parameters:**
- `options`:
  - `interval`: Check interval in seconds (default: 15)

**Example:**
```python
tmux-orc_monitor_start(options={"interval": 30})
```

### tmux-orc_monitor_stop
Stop the monitoring daemon completely.

**Parameters:** None

**Example:**
```python
tmux-orc_monitor_stop()
```

### tmux-orc_monitor_status
Check monitoring daemon status and health.

**Parameters:**
- `options`:
  - `json`: Return JSON output (boolean)

**Example:**
```python
monitor = tmux-orc_monitor_status(options={"json": true})
```

### tmux-orc_monitor_dashboard
Show live interactive monitoring dashboard.

**Parameters:** None

**Example:**
```python
tmux-orc_monitor_dashboard()
```

### tmux-orc_monitor_logs
View monitoring logs with follow option.

**Parameters:**
- `options`:
  - `follow`: Follow log output (boolean)
  - `lines`: Number of lines to show

**Example:**
```python
tmux-orc_monitor_logs(options={"follow": true, "lines": 50})
```

### tmux-orc_monitor_recovery_start
Enable automatic agent recovery when failures detected.

**Parameters:** None

**Example:**
```python
tmux-orc_monitor_recovery_start()
```

### tmux-orc_monitor_recovery_stop
Disable automatic agent recovery feature.

**Parameters:** None

**Example:**
```python
tmux-orc_monitor_recovery_stop()
```

### tmux-orc_monitor_recovery_status
Check if auto-recovery is enabled and recent recovery actions.

**Parameters:**
- `options`:
  - `json`: Return JSON output (boolean)

**Example:**
```python
recovery = tmux-orc_monitor_recovery_status(options={"json": true})
```

### tmux-orc_monitor_health_check
Run immediate health check on all agents.

**Parameters:** None

**Example:**
```python
tmux-orc_monitor_health_check()
```

### tmux-orc_monitor_metrics
Display performance metrics and system statistics.

**Parameters:**
- `options`:
  - `json`: Return JSON output (boolean)

**Example:**
```python
metrics = tmux-orc_monitor_metrics(options={"json": true})
```

---

## 👥 Team Coordination (5 tools)

### tmux-orc_team_deploy
Create new team of agents.

**Parameters:**
- `args`: `[team_type, size]`
  - team_type: "dev", "qa", "ops", etc.
  - size: Number of agents (string)

**Example:**
```python
tmux-orc_team_deploy(args=["dev", "4"])
```

### tmux-orc_team_status
Check specific team health.

**Parameters:**
- `args`: `[team_name]`
- `options`:
  - `json`: Return JSON output (boolean)

**Example:**
```python
tmux-orc_team_status(args=["frontend"], options={"json": true})
```

### tmux-orc_team_list
Show all active teams with member counts.

**Parameters:**
- `options`:
  - `json`: Return JSON output (boolean)

**Example:**
```python
teams = tmux-orc_team_list(options={"json": true})
```

### tmux-orc_team_broadcast
Send message to all team members.

**Parameters:**
- `args`: `[team_name, message]`

**Example:**
```python
tmux-orc_team_broadcast(args=["backend", "Meeting in 5 minutes"])
```

### tmux-orc_team_recover
Recover failed agents in team.

**Parameters:**
- `args`: `[team_name]`

**Example:**
```python
tmux-orc_team_recover(args=["frontend"])
```

---

## 🚀 Spawning (3 tools)

### tmux-orc_spawn_agent
Create new agent with role.

**Parameters:**
- `args`: `[agent_type, target]`
  - agent_type: Agent specialization
  - target: "session:window" format

**Example:**
```python
tmux-orc_spawn_agent(args=["frontend", "ui:0"])
```

### tmux-orc_spawn_pm
Create new Project Manager agent.

**Parameters:**
- `args`: `[project_name, target]`

**Example:**
```python
tmux-orc_spawn_pm(args=["ecommerce", "pm:0"])
```

### tmux-orc_spawn_orchestrator
Create system orchestrator agent.

**Parameters:**
- `args`: `[target]`

**Example:**
```python
tmux-orc_spawn_orchestrator(args=["orchestrator:0"])
```

---

## 📚 Context Management (4 tools)

### tmux-orc_context_orchestrator
Show orchestrator role context and guidelines.

**Parameters:** None

**Example:**
```python
tmux-orc_context_orchestrator()
```

### tmux-orc_context_pm
Show Project Manager role context and guidelines.

**Parameters:** None

**Example:**
```python
tmux-orc_context_pm()
```

### tmux-orc_context_list
List all available context templates.

**Parameters:**
- `options`:
  - `json`: Return JSON output (boolean)

**Example:**
```python
contexts = tmux-orc_context_list(options={"json": true})
```

### tmux-orc_context_show
Display specific context content.

**Parameters:**
- `args`: `[context_name]`

**Example:**
```python
tmux-orc_context_show(args=["security"])
```

---

## 🔧 Additional Command Groups

### Project Manager (6 tools)
- `tmux-orc_pm_deploy`
- `tmux-orc_pm_status`
- `tmux-orc_pm_restart`
- `tmux-orc_pm_message`
- `tmux-orc_pm_health`
- `tmux-orc_pm_info`

### Orchestrator (7 tools)
- `tmux-orc_orchestrator_deploy`
- `tmux-orc_orchestrator_status`
- `tmux-orc_orchestrator_restart`
- `tmux-orc_orchestrator_message`
- `tmux-orc_orchestrator_plan`
- `tmux-orc_orchestrator_review`
- `tmux-orc_orchestrator_approve`

### Setup (7 tools)
- `tmux-orc_setup_all`
- `tmux-orc_setup_claude_code`
- `tmux-orc_setup_mcp`
- `tmux-orc_setup_shell`
- `tmux-orc_setup_verify`
- `tmux-orc_setup_reset`
- `tmux-orc_setup_info`

### Recovery (4 tools)
- `tmux-orc_recovery_start`
- `tmux-orc_recovery_stop`
- `tmux-orc_recovery_status`
- `tmux-orc_recovery_test`

### Session (2 tools)
- `tmux-orc_session_list`
- `tmux-orc_session_create`

### PubSub (8 tools)
- `tmux-orc_pubsub_publish`
- `tmux-orc_pubsub_subscribe`
- `tmux-orc_pubsub_unsubscribe`
- `tmux-orc_pubsub_channels`
- `tmux-orc_pubsub_subscribers`
- `tmux-orc_pubsub_history`
- `tmux-orc_pubsub_clear`
- `tmux-orc_pubsub_status`

### Daemon (5 tools)
- `tmux-orc_daemon_start`
- `tmux-orc_daemon_stop`
- `tmux-orc_daemon_status`
- `tmux-orc_daemon_restart`
- `tmux-orc_daemon_logs`

### Tasks (7 tools)
- `tmux-orc_tasks_add`
- `tmux-orc_tasks_list`
- `tmux-orc_tasks_complete`
- `tmux-orc_tasks_remove`
- `tmux-orc_tasks_assign`
- `tmux-orc_tasks_status`
- `tmux-orc_tasks_clear`

### Errors (4 tools)
- `tmux-orc_errors_list`
- `tmux-orc_errors_clear`
- `tmux-orc_errors_report`
- `tmux-orc_errors_analyze`

### Server (5 tools)
- `tmux-orc_server_start`
- `tmux-orc_server_status`
- `tmux-orc_server_tools`
- `tmux-orc_server_setup`
- `tmux-orc_server_toggle`

---

## 🎯 Common Parameter Patterns

### Target Format
Most agent operations use the `session:window` format:
```python
# Standard format
"frontend:0"     # Frontend session, window 0
"backend:1"      # Backend session, window 1
"testing:2"      # Testing session, window 2

# Advanced format (with pane)
"dev:0.1"        # Dev session, window 0, pane 1
```

### JSON Output Option
Most read operations support JSON output:
```python
# Always prefer JSON for parsing
result = tmux-orc_[tool](options={"json": true})
if result["success"]:
    data = result["result"]
```

### Message Delivery
Message operations typically need target and message:
```python
# Simple message
tmux-orc_[group]_message(args=[target, message])

# Advanced with delay
tmux-orc_[group]_send(args=[target, message], options={"delay": 0.5})
```

### Deployment Patterns
Deployment operations need type and size/location:
```python
# Team deployment
tmux-orc_team_deploy(args=[team_type, size])

# Individual agent
tmux-orc_agent_deploy(args=[agent_type, role])

# Spawn with target
tmux-orc_spawn_[type](args=[...params, target])
```

---

## 📖 Quick Lookup by Task

### "I need to check system health"
- `tmux-orc_status()`
- `tmux-orc_monitor_metrics()`
- `tmux-orc_agent_list()`

### "I need to communicate with agents"
- `tmux-orc_agent_message()`
- `tmux-orc_agent_send()`
- `tmux-orc_team_broadcast()`

### "I need to deploy new resources"
- `tmux-orc_quick_deploy()`
- `tmux-orc_team_deploy()`
- `tmux-orc_spawn_agent()`

### "I need to fix problems"
- `tmux-orc_agent_restart()`
- `tmux-orc_team_recover()`
- `tmux-orc_monitor_recovery_start()`

### "I need to understand the system"
- `tmux-orc_reflect()`
- `tmux-orc_server_tools()`
- `tmux-orc_context_list()`

---

**Remember**: All MCP tools are auto-generated from the CLI. New CLI commands automatically become available as MCP tools!
