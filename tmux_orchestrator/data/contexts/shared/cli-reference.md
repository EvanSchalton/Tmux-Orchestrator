# Complete CLI Command Reference

## Context Management

### List Available Contexts
```bash
tmux-orc context list
```
Shows: orchestrator, pm, cleanup, tmux-comms, etc.

### View Context Content
```bash
tmux-orc context show orchestrator  # Your own context
tmux-orc context show pm           # PM context for reference
tmux-orc context show tmux-comms   # TMUX communication guide
```

### Spawn Agent with Context
```bash
tmux-orc context spawn pm --session project:1
tmux-orc context spawn cleanup --session maintenance:1
```

## Agent Management

### Spawn Agents
```bash
# Spawn PM (recommended method)
tmux-orc spawn pm --session project:1

# Spawn custom agent
tmux-orc spawn agent developer project:2 --briefing "You are a backend developer..."

# Spawn agent with context file
tmux-orc spawn agent qa-engineer project:3 --context-file contexts/qa.md
```

### List Agents
```bash
# List all active agents
tmux-orc agent list

# List with JSON output
tmux-orc agent list --json

# Filter by session
tmux-orc agent list | grep project
```

### Check Agent Status
```bash
# Detailed agent status
tmux-orc agent status project:2

# Quick health check
tmux-orc agent status project:2 --health-only
```

### Send Messages
```bash
# Send message to agent (uses C-Enter for submission)
tmux-orc agent send project:2 "Please implement the login feature"

# Send multiline message
tmux-orc agent send project:2 "TASK: Implement auth
REQUIREMENTS:
- JWT tokens
- Secure storage
- Tests required"
```

### Agent Lifecycle
```bash
# Kill specific agent
tmux-orc agent kill project:2

# Kill all agents (with confirmation)
tmux-orc agent kill-all

# Kill all agents (no confirmation)
tmux-orc agent kill-all --force

# Restart an agent
tmux-orc agent restart project:2
```

## Session Management

### List Sessions
```bash
# List all tmux sessions with details
tmux-orc session list

# JSON format for scripting
tmux-orc session list --json

# With agent count
tmux-orc session list --with-agents
```

### Attach to Sessions
```bash
# Attach to specific session
tmux-orc session attach project

# Attach in read-only mode
tmux-orc session attach project --read-only

# Attach to specific window
tmux-orc session attach project:2
```

### Create Sessions
```bash
# Create new session
tmux-orc session create project

# Create with specific window count
tmux-orc session create project --windows 5
```

## Monitoring and Health

### Daemon Control
```bash
# Start monitoring daemon
tmux-orc monitor start

# Start with custom interval
tmux-orc monitor start --interval 30

# Start with supervision (auto-restart)
tmux-orc monitor start --supervised

# Stop monitoring
tmux-orc monitor stop

# Check status
tmux-orc monitor status
```

### View Logs
```bash
# View last 20 lines
tmux-orc monitor logs

# View last 50 lines
tmux-orc monitor logs -n 50

# Follow logs live
tmux-orc monitor logs -f

# Session-specific logs
tmux-orc monitor logs --session project
```

### Dashboard
```bash
# Launch interactive dashboard
tmux-orc monitor dashboard

# Filter by session
tmux-orc monitor dashboard --session project

# Auto-refresh every 10 seconds
tmux-orc monitor dashboard --refresh 10

# JSON output for integration
tmux-orc monitor dashboard --json
```

### Performance Monitoring
```bash
# Show performance metrics
tmux-orc monitor performance

# Analyze performance
tmux-orc monitor performance --analyze

# Get optimization tips
tmux-orc monitor performance --optimize

# For specific agent count
tmux-orc monitor performance --agent-count 75
```

### Recovery Daemon
```bash
# Start recovery daemon
tmux-orc monitor recovery-start

# With custom config
tmux-orc monitor recovery-start -c recovery.conf

# Stop recovery
tmux-orc monitor recovery-stop

# Check recovery status
tmux-orc monitor recovery-status

# Detailed recovery info
tmux-orc monitor recovery-status -v

# Recovery logs
tmux-orc monitor recovery-logs -f
```

## Task Management

### Create Project
```bash
# Create task structure
tmux-orc tasks create my-project

# With template
tmux-orc tasks create my-project --template api-project
```

### List Tasks
```bash
# View all tasks
tmux-orc tasks list

# Filter by project
tmux-orc tasks list --project my-project

# Show completed tasks
tmux-orc tasks list --include-completed
```

### Distribute Tasks
```bash
# Distribute to agents
tmux-orc tasks distribute

# To specific session
tmux-orc tasks distribute --session project

# Dry run
tmux-orc tasks distribute --dry-run
```

## Team Management

### Team Composition
```bash
# Interactive team composition
tmux-orc team compose my-project --interactive

# From PRD
tmux-orc team compose my-project --prd ./prd.md

# Using template
tmux-orc team compose my-project --template api-heavy
```

### List Templates
```bash
# Show available agent templates
tmux-orc team list-templates
```

### Deploy Team
```bash
# Deploy custom team
tmux-orc team deploy my-project

# Deploy standard team
tmux-orc team deploy-standard --type fullstack --size 5 my-project
```

### Team Status
```bash
# Show team status
tmux-orc team status my-project

# With performance metrics
tmux-orc team status my-project --metrics
```

## Utility Commands

### Version Info
```bash
# Show version
tmux-orc --version

# Verbose version with system info
tmux-orc version --verbose
```

### Help
```bash
# General help
tmux-orc --help

# Command-specific help
tmux-orc agent --help
tmux-orc monitor start --help
```

### Debug Mode
```bash
# Run with debug output
tmux-orc --debug agent list

# Verbose logging
tmux-orc -v monitor status

# Super verbose
tmux-orc -vv agent send project:2 "test"
```

## Quick Reference Tables

### Common Operations

| Task | Command |
|------|---------|
| Spawn PM | `tmux-orc spawn pm --session project:1` |
| Send message | `tmux-orc agent send project:2 "message"` |
| Check health | `tmux-orc agent status project:2` |
| View logs | `tmux-orc monitor logs -f` |
| Kill agent | `tmux-orc agent kill project:2` |

### Session Patterns

| Pattern | Meaning |
|---------|---------|
| `project:1` | Session "project", window 1 |
| `dev:2` | Session "dev", window 2 |
| `test:0` | Session "test", window 0 |

### Agent Types

| Type | Purpose |
|------|---------|
| `pm` | Project Manager |
| `developer` | Software Developer |
| `qa-engineer` | Quality Assurance |
| `devops` | DevOps Engineer |
| `architect` | Technical Architect |

## Environment Variables

```bash
# Set custom tmux socket
export TMUX_ORCHESTRATOR_SOCKET=/tmp/tmux-1000/custom

# Enable debug logging
export TMUX_ORCHESTRATOR_DEBUG=1

# Custom config location
export TMUX_ORCHESTRATOR_CONFIG=~/.config/tmux-orc/config.yaml
```

## Configuration Files

### Locations Checked (in order)
1. `./tmux-orchestrator.yaml`
2. `~/.config/tmux-orchestrator/config.yaml`
3. `~/.tmux-orchestrator.yaml`
4. `/etc/tmux-orchestrator/config.yaml`

### Example Config
```yaml
monitoring:
  interval: 30
  supervised: true

logging:
  level: INFO
  file: ~/.tmux-orchestrator/logs/main.log

agent:
  default_shell: /bin/bash
  startup_timeout: 30
```

Remember: When in doubt, use `--help` on any command!
