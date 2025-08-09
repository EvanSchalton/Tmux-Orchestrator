# Schedule Check-in

Schedule a future check-in for a Claude agent or orchestrator in the Corporate Coach project.

## Usage
```
/schedule-checkin <minutes> <target> "<note>"
```

### Parameters
- **minutes** (required): How many minutes in the future
- **target** (required): The tmux target (session:window format)
- **note** (required): Description of what to check

## Examples
```
/schedule-checkin 30 orchestrator:0 "Review agent progress and check for blockers"
/schedule-checkin 60 corporate-coach-frontend:0 "Verify markdown editor tests are complete"
/schedule-checkin 15 corporate-coach-backend:Claude-pm "Check code review status"
```

## What it does

1. **Validates target** - Ensures the target window exists
2. **Schedules message** - Uses system scheduler to send future message
3. **Confirms scheduling** - Shows when check-in will occur
4. **Sends reminder** - At scheduled time, sends note to target

## Target Format

Targets follow tmux naming convention:
- `session:window` - Target a specific window
- `session:window.pane` - Target a specific pane (if split)

Common targets:
- `orchestrator:0` - Main orchestrator
- `corporate-coach-frontend:Claude-developer` - Frontend developer
- `corporate-coach-backend:Claude-pm` - Backend PM

## Check-in Notes

Good check-in notes are:
- **Specific** - "Check PR review status" not "Check status"
- **Actionable** - "Deploy QA agent if tests failing"
- **Contextual** - "Verify Neo4j integration after backend work"

### Examples of Good Notes
- "Review git commits and ensure 30-minute discipline"
- "Check if markdown toolbar implementation is complete"
- "Verify all agents have pushed their work"
- "Assess if additional QA resources needed"
- "Confirm database migrations ran successfully"

## Scheduling Strategy

### Orchestrator Check-ins
- Every 15-30 minutes for general oversight
- After major milestones
- When coordinating multiple agents

### Agent Check-ins
- Every 30-60 minutes for progress updates
- After specific task completion times
- When dependencies might be ready

### Critical Check-ins
- Before end of work session
- After deployments or major changes
- When agents report blockers

## Output Format

### Success
```
✅ Scheduled check-in for orchestrator:0 in 30 minutes: Review agent progress
```

### Error
```
❌ Target 'invalid:window' does not exist
Available targets: orchestrator:0, corporate-coach-frontend:0
```

## How It Works

The command uses the `at` scheduler to:
1. Wait the specified number of minutes
2. Send the note as a message to the target
3. The agent/orchestrator sees the reminder and acts

## Viewing Scheduled Check-ins

Check pending jobs:
```bash
atq
```

Cancel a scheduled job:
```bash
atrm <job-number>
```

## Best Practices

1. **Regular cadence** - Set consistent check-in intervals
2. **Clear notes** - Make the purpose obvious
3. **Cascading checks** - Orchestrator → PM → Developers
4. **Time zones** - Remember agents work in UTC
5. **Buffer time** - Allow time for task completion

## Common Patterns

### Morning Standup
```
/schedule-checkin 5 orchestrator:0 "Start morning agent standup"
```

### Task Completion
```
/schedule-checkin 45 corporate-coach-frontend:0 "Should have markdown editor working by now"
```

### End of Day
```
/schedule-checkin 480 orchestrator:0 "End of day: ensure all agents committed work"
```

## Integration with Orchestrator

The orchestrator can:
- Schedule its own future check-ins
- Cascade check-ins to all agents
- Adjust schedules based on progress
- Track check-in compliance

## Related Commands

- `/start-orchestrator` - Initialize orchestrator
- `/deploy-agent` - Deploy agents to check on
- `/agent-status` - Immediate status check
