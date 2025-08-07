# TMUX Orchestrator CLI & MCP Server Quick Start

## Installation

```bash
# Install with pip (once published)
pip install tmux-orchestrator

# Or install from source
git clone https://github.com/yourusername/tmux-orchestrator
cd tmux-orchestrator
pip install -e .
```

## CLI Usage

### Basic Commands

```bash
# Deploy a new team
tmux-orc deploy tasks.md

# List all agents
tmux-orc list

# Show agent status dashboard
tmux-orc status

# Restart team
tmux-orc restart tasks.md

# Recover missing agents
tmux-orc recover
```

### Agent Management

```bash
# Deploy individual agent
tmux-orc agent deploy frontend developer

# Send message to agent
tmux-orc agent message "corporate-coach-frontend:2" "Please implement the login form"

# Attach to agent terminal
tmux-orc agent attach "corporate-coach-frontend:2"

# Show agent status
tmux-orc agent status
```

### Project Manager Commands

```bash
# Trigger PM status review
tmux-orc pm checkin

# Send message to PM
tmux-orc pm message "Please review the frontend progress"

# PM broadcast to all agents
tmux-orc pm broadcast "Team meeting in 5 minutes"

# Custom check-in
tmux-orc pm custom-checkin --custom-message "Please report blockers"
```

### Monitoring

```bash
# Start idle monitor
tmux-orc monitor start --interval 10

# Stop idle monitor
tmux-orc monitor stop

# View monitor logs
tmux-orc monitor logs

# Follow logs in real-time
tmux-orc monitor logs -f

# Check monitor status
tmux-orc monitor status
```

### Orchestrator

```bash
# Start orchestrator
tmux-orc orchestrator start

# Schedule check-in
tmux-orc orchestrator schedule 30 "Time for status update"

# Check orchestrator status
tmux-orc orchestrator status
```

## MCP Server

### Starting the Server

```bash
# Start MCP server
tmux-orc-server

# Or with custom host/port
tmux-orc-server --host 0.0.0.0 --port 8080
```

### Using the SDK in Your Agents

```python
from tmux_orchestrator import Agent

# Initialize agent
agent = Agent("frontend", "developer")

# Register with orchestrator
agent.register()

# Send message to another agent
agent.send_message("backend:2", "API endpoint ready at /api/v1/users")

# Check for messages
messages = agent.get_messages()
for msg in messages:
    print(f"From {msg.from_agent}: {msg.content}")

# Report status
agent.report_status("Working on user authentication feature")

# Report activity (prevents idle detection)
agent.report_activity()

# Request help
agent.request_help("Need help with Redux state management")

# Get assigned tasks
tasks = agent.get_tasks()

# Update task status
agent.update_task_status(task_id, "in_progress")

# Hand off work
agent.handoff_work("frontend:2", "Please complete the CSS styling")

# Use as context manager (auto-registers and unregisters)
with Agent("backend", "developer") as agent:
    agent.send_message("pm:2", "Database migration completed")
```

## Configuration

Create `.tmux-orchestrator/config.yml`:

```yaml
project:
  name: my-project
  path: /path/to/project

team:
  pm:
    enabled: true
    window: 2
  agents:
    - type: frontend
      role: developer
      window: 2
    - type: backend
      role: developer  
      window: 2

monitoring:
  idle_check_interval: 10
  notification_cooldown: 300

server:
  host: 127.0.0.1
  port: 8000
```

## Environment Variables

```bash
# Set MCP server URL for agents
export TMUX_ORCHESTRATOR_URL=http://localhost:8000

# Set project path
export TMUX_ORCHESTRATOR_PROJECT=/path/to/project
```

## Common Workflows

### Deploy and Monitor a Team

```bash
# 1. Start orchestrator
tmux-orc orchestrator start

# 2. Deploy team
tmux-orc deploy planning/tasks.md

# 3. Start monitoring
tmux-orc monitor start

# 4. Watch status
tmux-orc status

# 5. Follow monitor logs
tmux-orc monitor logs -f
```

### Manage Individual Agents

```bash
# Check who's idle
tmux-orc status

# Message specific agent
tmux-orc agent message "frontend:2" "Please review the PR"

# Trigger PM review
tmux-orc pm checkin
```

### Recovery and Restart

```bash
# Recover crashed agents
tmux-orc recover

# Full restart
tmux-orc restart tasks.md
```

## Tips

1. **Use shell aliases** for common commands:
   ```bash
   alias tol="tmux-orc list"
   alias tos="tmux-orc status"
   alias tom="tmux-orc monitor"
   ```

2. **Start the MCP server** in a separate terminal or as a service for better agent coordination

3. **Configure your agents** to use the SDK instead of direct tmux commands for more reliable communication

4. **Monitor the logs** regularly to catch idle agents early

5. **Use configuration files** instead of command-line arguments for complex setups