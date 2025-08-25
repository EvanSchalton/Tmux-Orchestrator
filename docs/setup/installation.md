# TMUX Orchestrator Installation Guide

This guide shows how to install and set up the TMUX Orchestrator for AI-powered development teams.

## Prerequisites

Before installation, ensure you have:
- **Python 3.8+** installed
- **tmux** available in your system
- **Git** for version control
- **Claude API access** (required for agent operations)

## Installation Methods

### Method 1: Python Package Installation (Recommended)

Install directly from PyPI:

```bash
pip install tmux-orchestrator
```

Or install from GitHub for the latest version:

```bash
pip install git+https://github.com/EvanSchalton/Tmux-Orchestrator.git
```

### Method 2: Development Installation

For development or customization:

```bash
git clone https://github.com/EvanSchalton/Tmux-Orchestrator.git
cd Tmux-Orchestrator
pip install -e .
```

## Quick Setup (Devcontainer Projects)

### 1. DevContainer Configuration

Add to your `.devcontainer/devcontainer.json`:

```json
{
  "name": "My Project with AI Orchestrator",
  "image": "mcr.microsoft.com/devcontainers/python:3.11",
  "postCreateCommand": [
    "apt-get update && apt-get install -y tmux",
    "pip install tmux-orchestrator",
    "tmux-orc setup"
  ],
  "remoteEnv": {
    "TMUX_ORCHESTRATOR_HOME": "${localEnv:HOME}/.tmux_orchestrator"
  }
}
```

### 2. Alternative: Local Project Setup

If not using devcontainers, copy the orchestrator to your project:

```bash
# In your project root
mkdir -p references/
cp -r path/to/Tmux-Orchestrator references/
```

## Initial Setup and Configuration

### 1. System Setup

After installation, run the setup command:

```bash
# Initialize tmux-orchestrator
tmux-orc setup

# Set up Claude Code integration (optional but recommended)
tmux-orc setup claude-code

# Set up VSCode integration (optional)
tmux-orc setup vscode
```

### 2. Verify Installation

Test that everything is working:

```bash
# Check CLI is available
tmux-orc --help

# Verify tmux integration
tmux-orc status

# Test basic functionality
tmux-orc reflect
```

### 3. First Run

Start your first orchestrator session:

```bash
# Start the orchestrator
tmux-orc spawn orchestrator

# Deploy a simple test team
tmux-orc spawn pm --session test-project:1
```

## Manual Setup (Non-Devcontainer)

### Prerequisites

- Linux/macOS system
- tmux installed
- bash shell
- sudo access (for command symlinks)

### Installation Steps

1. **Install Dependencies**
   ```bash
   # Ubuntu/Debian
   sudo apt-get update && sudo apt-get install -y tmux bc

   # macOS
   brew install tmux
   ```

2. **Clone/Copy Orchestrator**
   ```bash
   # Option 1: Clone the repo
   git clone https://github.com/your-username/tmux-orchestrator.git references/Tmux-Orchestrator

   # Option 2: Copy from existing project
   cp -r /path/to/Tmux-Orchestrator references/
   ```

3. **Run Installation**
   ```bash
   # Customize the install script first
   cp references/Tmux-Orchestrator/install-template.sh scripts/install-tmux-orchestrator.sh

   # Edit PROJECT_NAME and paths
   nano scripts/install-tmux-orchestrator.sh

   # Run installation
   bash scripts/install-tmux-orchestrator.sh
   ```

## Directory Structure After Setup

```
your-project/
├── .tmux_orchestrator/           # Runtime directory
│   ├── commands/                 # Orchestrator commands
│   ├── scripts/                  # Core scripts
│   ├── registry/                 # Session tracking
│   └── restart.sh               # Project restart script
├── .pm-schedule/                 # PM follow-up schedules
├── .orchestrator-notes/          # Orchestrator notes
├── scripts/
│   └── install-tmux-orchestrator.sh
└── references/
    └── Tmux-Orchestrator/        # Full documentation
```

## Configuration Options

### Environment Variables

Set these in your shell or devcontainer:

```bash
export TMUX_ORCHESTRATOR_HOME="/path/to/.tmux_orchestrator"
export TMUX_ORCHESTRATOR_REGISTRY="/path/to/.tmux_orchestrator/registry"
export PROJECT_NAME="my-project"
```

### Custom Role Detection

Edit the team deployment script to customize role detection:

```bash
# In generic-team-deploy.sh or your custom deploy script
# Add custom patterns for your project type

# Example: Detect specific frameworks
if echo "$TASK_CONTENT" | grep -iE "(nextjs|gatsby)" > /dev/null; then
    NEEDS_FRONTEND=true
    FRONTEND_TYPE="nextjs"
fi
```

### Custom Agent Briefings

Modify agent briefings in the deployment script:

```bash
# Frontend briefing customization
$SEND_MESSAGE "frontend:0" "You are the Frontend Developer for $PROJECT_NAME.

Framework: React with TypeScript
Styling: Tailwind CSS
Testing: Jest + React Testing Library

Your specific tasks:
- Implement responsive components
- Follow accessibility guidelines
- Maintain design system consistency"
```

## Team Templates

### Web Application Team
- Orchestrator
- Project Manager
- Frontend Developer
- Backend Developer
- QA Engineer

### API-Only Team
- Orchestrator
- Project Manager
- Backend Developer
- Database Specialist
- QA Engineer

### Data Pipeline Team
- Orchestrator
- Project Manager
- Data Engineer
- Backend Developer
- QA Engineer

### Microservices Team
- Orchestrator
- Project Manager
- Service Developer (x2-3)
- DevOps Engineer
- QA Engineer

## Advanced Configuration

### Custom Commands

Add project-specific commands to `.tmux_orchestrator/commands/`:

```bash
# Example: custom-deploy.sh
#!/bin/bash
PROJECT_SPECIFIC_DEPLOY="$1"
# Custom deployment logic here
```

### Integration Scripts

Create integrations in `.tmux_orchestrator/integrations/`:

```bash
# Example: slack-notifications.sh
#!/bin/bash
# Send team updates to Slack
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Team deployment complete for '$PROJECT_NAME'"}' \
  $SLACK_WEBHOOK_URL
```

### Quality Gates

Set up automated quality checks:

```bash
# .tmux_orchestrator/qa/quality-gates.sh
#!/bin/bash
# Run before allowing commits
npm run lint && npm run test && npm run build
```

## Troubleshooting

### Common Issues

1. **Permission Errors**
   ```bash
   # Fix command permissions
   sudo chmod +x /usr/local/bin/tmux-*
   chmod +x .tmux_orchestrator/scripts/*.sh
   ```

2. **Session Not Found**
   ```bash
   # Check active sessions
   tmux list-sessions

   # Kill stuck sessions
   tmux kill-session -t stuck-session-name
   ```

3. **Command Not Found**
   ```bash
   # Recreate symlinks
   sudo ln -sf $PWD/.tmux_orchestrator/scripts/send-claude-message.sh /usr/local/bin/tmux-message
   sudo ln -sf $PWD/.tmux_orchestrator/scripts/schedule_with_note.sh /usr/local/bin/tmux-schedule
   ```

4. **Orchestrator Won't Start**
   ```bash
   # Check tmux configuration
   tmux list-sessions

   # Verify paths
   echo $TMUX_ORCHESTRATOR_HOME
   ls -la $TMUX_ORCHESTRATOR_HOME
   ```

### Debug Mode

Enable debug output:

```bash
# Set debug environment
export TMUX_ORCHESTRATOR_DEBUG=1

# Run with verbose output
bash -x tmux-orc orchestrator start
```

### Log Files

Check orchestrator logs:

```bash
# Session logs
ls -la .tmux_orchestrator/registry/logs/

# PM schedule logs
ls -la .pm-schedule/

# Orchestrator notes
ls -la .orchestrator-notes/
```

## Best Practices

1. **Always use the restart script** instead of manual session management
2. **Keep task files well-structured** for proper team detection
3. **Monitor agent progress** using the provided monitoring tools
4. **Commit frequently** - orchestrator expects 30-minute commits
5. **Use feature branches** for all development work
6. **Test the setup** in a clean devcontainer before deploying

## Next Steps

After setup:

1. Read `RUNNING.md` for operational guidance
2. Check `CLAUDE.md` for agent behavior details
3. Review examples in `Examples/` directory
4. Customize team templates for your project type

## Support

- Check `LEARNINGS.md` for accumulated knowledge
- Review `FAQ.md` for common questions
- See project examples in corporate-coach implementation
