# Devcontainer Integration for TMUX Orchestrator

This guide shows how to integrate the TMUX Orchestrator into any project using development containers.

## Quick Setup for New Projects

### 1. Add to devcontainer.json

```json
{
  "name": "your-project-dev",
  "postCreateCommand": "bash scripts/install-tmux-orchestrator.sh",
  "remoteEnv": {
    "TMUX_ORCHESTRATOR_HOME": "/workspaces/your-project/.tmux-orchestrator",
    "TMUX_ORCHESTRATOR_REGISTRY": "/workspaces/your-project/.tmux-orchestrator/registry"
  }
}
```

### 2. Create Installation Script

Copy `scripts/install-tmux-orchestrator.sh` template (see below) to your project's `scripts/` directory.

### 3. Add Reference Documentation

Copy the entire `references/Tmux-Orchestrator/` directory to your project.

## Installation Script Template

Create `scripts/install-tmux-orchestrator.sh`:

```bash
#!/bin/bash
set -e

echo "=== Installing Tmux Orchestrator for [PROJECT NAME] ==="

# Install dependencies
if ! command -v tmux &> /dev/null; then
    echo "📦 Installing tmux..."
    sudo apt-get update && sudo apt-get install -y tmux bc
fi

# Create orchestrator directory
ORCH_DIR="/workspaces/[PROJECT_NAME]/.tmux-orchestrator"
mkdir -p "$ORCH_DIR/registry/logs" "$ORCH_DIR/registry/notes" "$ORCH_DIR/scripts" "$ORCH_DIR/commands"

# Copy reference scripts
REFS_DIR="/workspaces/[PROJECT_NAME]/references/Tmux-Orchestrator"
if [ -d "$REFS_DIR" ]; then
    cp "$REFS_DIR/schedule_with_note.sh" "$ORCH_DIR/scripts/"
    cp "$REFS_DIR/send-claude-message.sh" "$ORCH_DIR/scripts/"
    cp "$REFS_DIR/tmux_utils.py" "$ORCH_DIR/scripts/"
fi

# Create command shortcuts
sudo ln -sf "$ORCH_DIR/scripts/schedule_with_note.sh" /usr/local/bin/tmux-schedule
sudo ln -sf "$ORCH_DIR/scripts/send-claude-message.sh" /usr/local/bin/tmux-message

# Make executable
chmod +x "$ORCH_DIR/scripts/"*.sh

# Initialize registry
echo '[]' > "$ORCH_DIR/registry/sessions.json"
echo "# Orchestrator Notes" > "$ORCH_DIR/registry/notes/README.md"

# Create .gitignore
cat > "$ORCH_DIR/.gitignore" << 'EOF'
registry/logs/*
registry/notes/*
!registry/notes/README.md
registry/sessions.json
EOF

echo "✅ Tmux Orchestrator installation complete!"
```

## Project-Specific Commands

### Team Deployment Script

Create `scripts/tmux-deploy-team.sh` customized for your project:

```bash
#!/bin/bash
# Flexible TMUX Orchestrator Team Deployment
# Usage: ./tmux-deploy-team.sh <task-file> [project-name]

TASK_FILE="$1"
PROJECT_NAME="${2:-your-project}"

# ... (use corporate-coach version as template)
```

### Restart Script

Create `.tmux-orchestrator/restart.sh`:

```bash
#!/bin/bash
# [PROJECT NAME] TMUX Orchestrator Restart Script

# Kill existing sessions
tmux list-sessions | grep "$PROJECT_NAME" | cut -d: -f1 | xargs -I {} tmux kill-session -t {} 2>/dev/null || true

# Deploy team
bash "/workspaces/$PROJECT_NAME/scripts/tmux-deploy-team.sh" "$@"
```

## Directory Structure

Your project will have:

```
your-project/
├── .devcontainer/
│   └── devcontainer.json          # Contains tmux orchestrator setup
├── .tmux-orchestrator/             # Runtime directory (created automatically)
│   ├── restart.sh                  # Project restart script
│   ├── commands/                   # Orchestrator commands
│   ├── registry/                   # Session tracking
│   └── scripts/                    # Core scripts
├── scripts/
│   ├── install-tmux-orchestrator.sh # Installation script
│   └── tmux-deploy-team.sh         # Team deployment
├── references/
│   └── Tmux-Orchestrator/          # Full documentation and examples
├── .pm-schedule/                   # PM follow-up schedules (hidden)
└── .orchestrator-notes/            # Orchestrator notes (hidden)
```

## Customization Points

### 1. Agent Briefings

Modify the briefings in `scripts/tmux-deploy-team.sh` to match your project:

```bash
# Frontend briefing for React project
"You are the Frontend Developer for $PROJECT_NAME. Focus on React components..."

# Backend briefing for FastAPI project  
"You are the Backend Developer for $PROJECT_NAME. Focus on FastAPI endpoints..."
```

### 2. Task Analysis

Customize the task analysis logic:

```bash
# Detect project-specific patterns
if echo "$TASK_CONTENT" | grep -iE "(nextjs|react|tailwind)" > /dev/null; then
    NEEDS_FRONTEND=true
fi

if echo "$TASK_CONTENT" | grep -iE "(django|flask|fastapi)" > /dev/null; then
    NEEDS_BACKEND=true
fi
```

### 3. Project Paths

Update paths throughout:
- Change `/workspaces/corporate-coach` to your project path
- Update task file locations
- Modify monitoring scripts

## Testing the Integration

After setup:

1. **Rebuild devcontainer** to run installation
2. **Test restart**: `cd .tmux-orchestrator && ./restart.sh`
3. **Verify agents**: `tmux list-sessions`
4. **Check commands**: `tmux-message --help`

## Migration from Existing Projects

To migrate the orchestrator system to a new project:

1. Copy `references/Tmux-Orchestrator/` directory
2. Create `scripts/install-tmux-orchestrator.sh`
3. Update devcontainer.json
4. Customize scripts for your project structure
5. Test the installation

## Common Issues

### Permission Errors
```bash
# Fix command symlinks
sudo chmod +x /usr/local/bin/tmux-*
```

### Path Issues
```bash
# Verify environment variables
echo $TMUX_ORCHESTRATOR_HOME
echo $TMUX_ORCHESTRATOR_REGISTRY
```

### Session Conflicts
```bash
# Clean up old sessions
tmux kill-server
```

This integration pattern makes the TMUX Orchestrator easily reusable across any project with development containers.