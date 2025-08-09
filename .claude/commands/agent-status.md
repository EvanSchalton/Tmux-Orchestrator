# Agent Status

Check the status of all running Claude agents and their current activities in the Corporate Coach project.

## Usage
```
/agent-status
```

## What it does

1. **Lists all relevant sessions** - Shows orchestrator and project sessions
2. **Shows window structure** - Displays all windows in each session
3. **Captures recent activity** - Shows last few lines from each agent
4. **Generates status report** - Formatted overview of all agents

## Output Format

The command generates a structured report showing:
- Current timestamp
- All active sessions
- Windows within each session
- Recent activity from each window

### Example Output
```
🤖 AGENT STATUS REPORT
=====================
Time: Wed Aug 7 10:30:45 UTC 2024

📦 Session: orchestrator
  🪟 Window 0: Orchestrator
     Recent activity:
       Monitoring 3 active agents
       Frontend: Implementing markdown editor
       Backend: Setting up Neo4j connection

📦 Session: corporate-coach-frontend
  🪟 Window 0: Claude-developer
     Recent activity:
       Working on FR1.2: Markdown toolbar
       Created MarkdownEditor.tsx component
       Running tests...

  🪟 Window 1: Shell
     Recent activity:
       npm test
       Test Suites: 12 passed, 12 total
       Tests: 45 passed, 45 total

📦 Session: corporate-coach-backend
  🪟 Window 0: Claude-developer
     Recent activity:
       Implementing Neo4j service layer
       Created neo4j_service.py
       Writing unit tests...
```

## Information Shown

For each agent/window:
- **Session name** - The tmux session identifier
- **Window name** - Descriptive window name
- **Recent activity** - Last 3 lines of meaningful output
- **Current status** - What the agent is working on

## Using the Information

The status report helps you:
1. **Monitor progress** - See what each agent is doing
2. **Identify blockers** - Spot stuck or idle agents
3. **Coordinate work** - Ensure agents aren't duplicating effort
4. **Track commits** - Verify git discipline is maintained

## Filtering Results

The command automatically filters to show only:
- Sessions with "orchestrator" in the name
- Sessions with "corporate-coach" in the name
- Active windows with recent output

## Interpreting Status

### Active Agent Signs
- Recent commands or output
- Working on specific files
- Running tests or builds
- Making commits

### Idle Agent Signs
- No recent activity
- Waiting at prompt
- Repeated status messages
- Error states

## Follow-up Actions

Based on status, you might:
1. **Send instructions** - Use `tmux-message` to guide agents
2. **Check logs** - Review full output with `tmux capture-pane`
3. **Deploy help** - Add PM or QA agents if needed
4. **Schedule check-ins** - Use `/schedule-checkin` for follow-ups

## Advanced Usage

### Check Specific Session
```bash
tmux list-windows -t corporate-coach-frontend
```

### Get Full Window Output
```bash
tmux capture-pane -t corporate-coach-frontend:0 -p | less
```

### Monitor in Real-time
```bash
tmux attach -t orchestrator
```

## Related Commands

- `/start-orchestrator` - Initialize orchestrator
- `/deploy-agent` - Deploy new agents
- `/schedule-checkin` - Schedule future check-ins
