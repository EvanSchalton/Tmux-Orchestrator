# Start Tmux Orchestrator

Initializes the Tmux Orchestrator environment for managing multiple Claude agents in the Corporate Coach project.

## Usage
```
/start-orchestrator [session-name]
```

Default session name: `orchestrator`

## What it does

1. **Creates orchestrator session** - Sets up a new tmux session for the orchestrator
2. **Starts Claude** - Launches Claude in the orchestrator window
3. **Sends briefing** - Provides the orchestrator with its responsibilities and context
4. **Returns access info** - Shows how to attach to the session

## Process Details

### 1. Session Creation
```bash
tmux new-session -d -s orchestrator -c /workspaces/corporate-coach
tmux rename-window -t orchestrator:0 "Orchestrator"
```

### 2. Claude Initialization
```bash
tmux send-keys -t orchestrator:0 "claude" Enter
sleep 5  # Wait for Claude to start
```

### 3. Orchestrator Briefing
The orchestrator receives instructions to:
- Manage multiple Claude agents across components
- Coordinate frontend, backend, and database teams
- Monitor progress and resolve blockers
- Ensure code quality and git discipline
- Reference the Tmux Orchestrator documentation

### 4. Window Organization
The orchestrator is instructed to rename all tmux windows with descriptive names for better organization.

## Example Output
```
🚀 Creating orchestrator session...
🤖 Starting Claude...
📋 Sending orchestrator briefing...
✅ Orchestrator started! Access with: tmux attach -t orchestrator
```

## Next Steps

After starting the orchestrator:
1. Deploy agents with `/deploy-agent`
2. Monitor with `/agent-status`
3. Schedule check-ins with `/schedule-checkin`

## Troubleshooting

- **Session already exists**: The orchestrator is already running. Attach with `tmux attach -t orchestrator`
- **Claude not responding**: Check if Claude is installed and accessible
- **Permission denied**: Ensure the installation script has been run

## Related Commands

- `/deploy-agent` - Deploy new agents
- `/agent-status` - Check agent statuses
- `/schedule-checkin` - Schedule future check-ins