# Tmux Orchestrator Quick Start Guide

## 🚀 One-Line Installation

Install directly from GitHub:

```bash
pip install git+https://github.com/EvanSchalton/Tmux-Orchestrator.git
```

For DevContainers, add this to your `devcontainer.json`:

```json
{
  "postCreateCommand": "apt-get update && apt-get install -y tmux && pip install git+https://github.com/EvanSchalton/Tmux-Orchestrator.git"
}
```

## 📋 What You Get

- ✅ **Autonomous AI Agents** - Claude instances that work 24/7
- ✅ **Self-Scheduling** - Agents schedule their own check-ins
- ✅ **Multi-Agent Coordination** - Orchestrator manages multiple agents
- ✅ **Slash Commands** - `/orchestrator` and `/schedule` in Claude

## 🛠️ Basic Usage

### Check System Requirements
```bash
tmux-orc setup
```

### Start the Orchestrator
```bash
tmux-orc orchestrator start
```

### Deploy a Team
```bash
tmux-orc team deploy frontend 3
```

### Send a Message to an Agent
```bash
tmux-orc agent message session:0 "Create a new React component"
```

### Schedule a Check-in
```bash
tmux-orc orchestrator schedule 30 "Review progress on React component"
```

## 📦 Full Integration Example

For a complete devcontainer setup with Tmux Orchestrator:

```json
{
  "name": "My Project with AI Orchestrator",
  "image": "mcr.microsoft.com/devcontainers/python:3.11",

  "postCreateCommand": [
    "apt-get update && apt-get install -y tmux",
    "pip install git+https://github.com/EvanSchalton/Tmux-Orchestrator.git",
    "tmux-orc setup all",
    "tmux-orc orchestrator start"
  ],

  "remoteEnv": {
    "TMUX_ORCHESTRATOR_HOME": "${localEnv:HOME}/.tmux_orchestrator"
  },

  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-vscode.terminal-tabs"
      ]
    }
  }
}
```

## 🔧 Advanced Setup

### Install to Custom Location
```bash
# Set environment variable before installation
export TMUX_ORCHESTRATOR_HOME=/opt/orchestrator
pip install git+https://github.com/EvanSchalton/Tmux-Orchestrator.git
```

### Setup Claude Code Integration
After installation, set up slash commands and MCP server:
```bash
tmux-orc setup claude-code
```

This creates:
- `/create-prd` - Generate PRD from description
- `/generate-tasks` - Create task list from PRD
- `/process-task-list` - Execute tasks with agent team

### Environment Variables
- `TMUX_ORCHESTRATOR_HOME` - Installation directory (default: `~/.tmux_orchestrator`)
- `TMUX_ORCHESTRATOR_PROJECTS_DIR` - Projects directory

## 📚 Examples

### PRD-Driven Development
```bash
# Create a PRD for your project
cat > todo-app.md << EOF
Build a TODO app with React and TypeScript
- User authentication
- CRUD operations for tasks
- Responsive design
EOF

# Execute with automatic team deployment
tmux-orc execute todo-app.md
```

### Manual Team Deployment
```bash
# Start orchestrator
tmux-orc orchestrator start

# Deploy a frontend team
tmux-orc team deploy frontend 3

# Deploy a backend team
tmux-orc team deploy backend 2

# Check all agents
tmux-orc list
```

### Quick Deploy for Common Projects
```bash
# Deploy optimized team configurations
tmux-orc quick-deploy frontend 3        # 3-agent frontend team
tmux-orc quick-deploy backend 4         # 4-agent backend team
tmux-orc quick-deploy fullstack 5       # 5-agent fullstack team
```

## 🐛 Troubleshooting

### Check System Status
```bash
# Comprehensive system check
tmux-orc status

# Check specific team
tmux-orc team status my-project

# List all agents
tmux-orc list
```

### View Logs
```bash
# Agent logs are stored in task directories
ls ~/.tmux_orchestrator/projects/*/logs/

# Monitor agent activity
tmux-orc monitor dashboard
```

### Manual Installation for Development
```bash
git clone https://github.com/EvanSchalton/Tmux-Orchestrator.git
cd Tmux-Orchestrator
poetry install
poetry shell
tmux-orc setup
```

## 📖 More Information

- [Full Documentation](README.md)
- [Architecture Guide](ARCHITECTURE.md)
- [Contributing](CONTRIBUTING.md)
