# Start Project Session

Creates a new tmux session for a project with a human orchestrator window.

## Usage
```
/start-orchestrator [session-name]
```

Default session name: `project`

## What it does

1. **Creates project session** - Sets up a new tmux session for the project
2. **Creates orchestrator window** - Window 0 is reserved for human interaction
3. **Prepares for PM** - Ready to spawn a PM agent in window 1
4. **Returns access info** - Shows how to attach to the session

## Important Note

The orchestrator role is filled by a human, not a Claude agent. The human orchestrator:
- Creates team planning documents
- Spawns the PM agent with the plan
- Monitors high-level progress
- Makes architectural decisions

## Process Details

### 1. Session Creation
```bash
tmux new-session -d -s orchestrator -c /workspaces/corporate-coach
tmux rename-window -t orchestrator:0 "Orchestrator"
```

### 2. Human Orchestrator Window
```bash
# Window 0 is for human interaction - no Claude started
echo "Human orchestrator window ready"
```

### 3. Next Step: Create Team Plan
The human orchestrator should:
1. Create a team plan document in `.tmux_orchestrator/planning/`
2. Define required agents based on project needs
3. Include agent briefings and interaction diagrams
4. Spawn PM agent with: `tmux-orc agent spawn [session]:1 pm --briefing "..."`

### 4. Document-Driven Workflow
The system follows a document-driven approach where:
- Team plans are documents, not code templates
- Each team is bespoke for the project
- Agents are spawned individually from the plan
- Plans serve as recovery documentation

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
