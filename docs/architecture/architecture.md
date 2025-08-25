# TMUX Orchestrator Architecture

## Overview
TMUX Orchestrator is evolving from a collection of bash scripts into a comprehensive CLI tool with an MCP (Model Context Protocol) server for seamless agent coordination.

## Components

### 1. CLI Interface (`tmux-orc`)
A Python-based CLI that replaces VS Code tasks and bash scripts.

**Core Commands:**
```bash
# Team Management
tmux-orc deploy <task-file>              # Deploy a new team
tmux-orc restart <task-file>             # Restart existing team
tmux-orc recover                         # Recover missing agents
tmux-orc list                            # List all agents
tmux-orc status                          # Show agent status dashboard

# Agent Management
tmux-orc agent deploy <type> <role>      # Deploy individual agent
tmux-orc agent message <target> <msg>    # Send message to agent
tmux-orc agent attach <session:window>   # Attach to agent terminal

# PM Operations
tmux-orc pm checkin                      # Trigger PM status review
tmux-orc pm message <message>            # Direct message to PM
tmux-orc pm broadcast <message>          # PM broadcast to all agents

# Monitoring
tmux-orc monitor start [interval]        # Start idle monitor daemon
tmux-orc monitor stop                    # Stop idle monitor
tmux-orc monitor logs                    # View monitor logs
tmux-orc monitor status                  # Check monitor status

# Orchestrator
tmux-orc orchestrator start              # Start orchestrator session
tmux-orc orchestrator schedule <min> <msg> # Schedule check-ins
```

### 2. MCP Server
Provides programmatic access for agents to coordinate without tmux send-keys.

**Endpoints:**
```
# Agent Registration & Discovery
POST   /agents/register              # Register new agent
GET    /agents                       # List all agents
GET    /agents/{id}/status          # Get agent status
DELETE /agents/{id}                 # Unregister agent

# Communication
POST   /messages/send               # Send message to agent
GET    /messages/inbox/{agent_id}   # Get agent's messages
POST   /messages/broadcast          # Broadcast to all agents

# Task Management
POST   /tasks/assign                # Assign task to agent
GET    /tasks/{agent_id}           # Get agent's tasks
PUT    /tasks/{id}/status          # Update task status

# Monitoring
GET    /monitor/idle-agents        # Get list of idle agents
POST   /monitor/report-activity    # Agent reports activity
GET    /monitor/logs              # Get monitor logs

# Coordination
POST   /coordination/request-help  # Agent requests help
GET    /coordination/dependencies  # Get task dependencies
POST   /coordination/handoff       # Hand off work to another agent
```

### 3. Agent SDK
Python library for agents to interact with the orchestrator.

```python
from tmux_orchestrator import Agent, Message

# Initialize agent
agent = Agent("frontend", "developer")

# Register with orchestrator
agent.register()

# Send message to another agent
agent.send_message("backend:2", "API endpoint ready at /api/v1/users")

# Check for messages
messages = agent.get_messages()

# Report status
agent.report_status("Working on user authentication feature")

# Request help
agent.request_help("Need help with Redux state management")
```

### 4. Configuration
YAML-based configuration for projects and teams.

```yaml
# .tmux_orchestrator/config.yml
project:
  name: corporate-coach
  path: /workspaces/corporate-coach

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
    - type: testing
      role: qa
      window: 2

monitoring:
  idle_check_interval: 10
  notification_cooldown: 300

orchestrator:
  auto_commit_interval: 1800  # 30 minutes
  health_check_interval: 60
```

## Migration Path

1. **Phase 1: CLI Framework**
   - Set up Python project structure
   - Implement basic CLI commands wrapping existing scripts
   - Add configuration system

2. **Phase 2: MCP Server**
   - Implement FastAPI server
   - Create agent registration system
   - Add messaging endpoints

3. **Phase 3: Agent Integration**
   - Create Python SDK for agents
   - Update agent briefings to use SDK
   - Migrate from tmux send-keys to API calls

4. **Phase 4: Advanced Features**
   - Real-time monitoring dashboard
   - Task dependency management
   - Agent performance metrics
   - Automated scaling

## Benefits

1. **Better UX**: Single CLI command vs multiple scripts
2. **Programmatic Access**: Agents can communicate via API
3. **Scalability**: Can manage multiple projects/teams
4. **Reliability**: Proper error handling and recovery
5. **Observability**: Better logging and monitoring
6. **Extensibility**: Easy to add new features
