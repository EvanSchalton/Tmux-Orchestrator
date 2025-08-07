# Tmux Orchestrator Quick Start for Devcontainers

## 🚀 One-Line Installation

Add this to your `devcontainer.json`:

```json
{
  "postCreateCommand": "curl -sSL https://raw.githubusercontent.com/EvanSchalton/Tmux-Orchestrator/main/bootstrap.sh | bash"
}
```

## 📋 What You Get

- ✅ **Autonomous AI Agents** - Claude instances that work 24/7
- ✅ **Self-Scheduling** - Agents schedule their own check-ins
- ✅ **Multi-Agent Coordination** - Orchestrator manages multiple agents
- ✅ **Slash Commands** - `/orchestrator` and `/schedule` in Claude

## 🛠️ Basic Usage

### Start the Orchestrator
```bash
tmux-orchestrator start
```

### Send a Message
```bash
tmux-orchestrator send orchestrator:0 "Create a new React component"
```

### Schedule a Check-in
```bash
tmux-orchestrator schedule 30 orchestrator:0 "Review progress on React component"
```

## 📦 Full Integration Example

For a complete devcontainer setup with Tmux Orchestrator:

```json
{
  "name": "My Project with AI Orchestrator",
  "image": "mcr.microsoft.com/devcontainers/python:3.11",
  
  "postCreateCommand": [
    "curl -sSL https://raw.githubusercontent.com/EvanSchalton/Tmux-Orchestrator/main/bootstrap.sh | bash",
    "tmux-orchestrator start"
  ],
  
  "remoteEnv": {
    "TMUX_ORCHESTRATOR_HOME": "${localEnv:HOME}/.tmux-orchestrator"
  },
  
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-vscode.cpptools"
      ]
    }
  }
}
```

## 🔧 Advanced Setup

### Custom Installation Directory
```bash
curl -sSL https://raw.githubusercontent.com/EvanSchalton/Tmux-Orchestrator/main/bootstrap.sh | TMUX_ORCHESTRATOR_HOME=/opt/orchestrator bash
```

### Add Claude Commands
The bootstrap script automatically creates slash commands for Claude:
- `/orchestrator` - Send messages to the orchestrator
- `/schedule` - Schedule check-ins

### Environment Variables
- `TMUX_ORCHESTRATOR_HOME` - Installation directory
- `TMUX_ORCHESTRATOR_PROJECTS_DIR` - Default projects directory
- `TMUX_ORCHESTRATOR_CLAUDE_CMD` - Claude command (default: "claude --dangerously-skip-permissions")

## 📚 Examples

### Single Agent Project
```bash
# Start orchestrator
tmux-orchestrator start

# Create a project manager session
tmux new -s project-manager
claude  # Start Claude in the session

# Send initial task
tmux-orchestrator send project-manager:0 "Build a TODO app with React and TypeScript"
```

### Multi-Agent Setup
```bash
# Start orchestrator
tmux-orchestrator start orchestrator

# Create specialized agents
tmux new -d -s frontend-dev
tmux new -d -s backend-dev
tmux new -d -s tester

# Coordinate work
tmux-orchestrator send orchestrator:0 "Coordinate building a full-stack app using the three agents"
```

## 🐛 Troubleshooting

### Check Status
```bash
tmux-orchestrator status
```

### View Logs
```bash
ls ~/.tmux-orchestrator/registry/logs/
```

### Manual Installation
```bash
git clone https://github.com/EvanSchalton/Tmux-Orchestrator.git
cd Tmux-Orchestrator
./install.sh
```

## 📖 More Information

- [Full Documentation](README.md)
- [Architecture Guide](ARCHITECTURE.md)
- [Contributing](CONTRIBUTING.md)