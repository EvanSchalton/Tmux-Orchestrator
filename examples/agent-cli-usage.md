# Agent CLI Usage Examples

This document shows how agents use CLI commands instead of shell scripts for communication.

## PM Agent Examples

### Reading Agent Status
```bash
# Check frontend developer output
tmux-orc read --session frontend:0 --tail 50

# Search for test failures across all devs
tmux-orc search "FAILED" --group development

# Check message history
tmux-orc read --session backend:0 --since "2024-01-01T10:00:00"
```

### Sending Instructions
```bash
# Direct message to specific agent
tmux-orc publish --session frontend:0 "Please run npm test and share results"

# Broadcast to all developers
tmux-orc publish --group development "Code freeze at 3pm for deployment"

# High priority bug fix request
tmux-orc publish --session backend:0 --priority high --tag bug "Fix auth endpoint returning 500"
```

### Monitoring System
```bash
# Check overall system status
tmux-orc status

# Get messaging statistics
tmux-orc pubsub status

# List all active agents
tmux-orc list
```

## Developer Agent Examples

### Reporting Status
```bash
# Proactive status update
tmux-orc publish --session pm:0 "
**STATUS UPDATE Frontend-Dev**:
✅ Completed: Login form component with validation
🔄 Currently: Working on registration form
🚧 Next: Password reset flow
⏱️ ETA: 2 hours
❌ Blockers: None
"

# Report test results
tmux-orc publish --session pm:0 --tag test-results "All tests passing (47 total, 0 failures)"

# Request help
tmux-orc publish --session pm:0 --priority high --tag blocked "Need API endpoint specs for user profile"
```

## QA Agent Examples

### Bug Reporting
```bash
# Batch bug report
tmux-orc publish --group development --priority high --tag qa-bugs "
**BUG REPORT BATCH**

1. Login form: Submit button remains disabled with valid input
   - Steps: Enter valid email/password
   - Expected: Button enables
   - Actual: Button stays disabled

2. Registration: No error message for duplicate email
   - Steps: Register with existing email
   - Expected: Error message shown
   - Actual: Silent failure
"

# Request test data
tmux-orc publish --session backend:0 "Need test user accounts with various permission levels"
```

## Daemon Examples

### Publishing Idle Status
```bash
# Notify PM about idle agents
tmux-orc publish --group management --tag idle "Agents frontend:0, backend:0, qa:0 are idle"

# System health update
tmux-orc publish --group management "All agents healthy, 0 errors in last hour"
```

## MCP Server Alternative

Agents can also use HTTP requests to the MCP server:

### Python Example
```python
import requests

# Send message
response = requests.post("http://localhost:8000/agents/message", json={
    "target": "pm:0",
    "message": "Feature complete, ready for review",
    "priority": "normal",
    "tags": ["complete", "review-needed"]
})

# Get agent status
response = requests.get("http://localhost:8000/agents/frontend:0/status")
status = response.json()

# Broadcast to group
response = requests.post("http://localhost:8000/coordination/broadcast", json={
    "group": "development",
    "message": "Deployment starting in 10 minutes"
})
```

### JavaScript Example
```javascript
// Send message
fetch('http://localhost:8000/agents/message', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        target: 'pm:0',
        message: 'Tests failing, investigating',
        priority: 'high'
    })
});

// Read agent output
fetch('http://localhost:8000/agents/frontend:0/output?lines=50')
    .then(res => res.json())
    .then(data => console.log(data.output));
```

## Fallback to Direct TMUX

When CLI/MCP unavailable:

```bash
# Send message (old way)
/workspaces/Tmux-Orchestrator/send-claude-message.sh "pm:0" "Status update"

# Read output (old way)
tmux capture-pane -t frontend:0 -p | tail -50
```

## Best Practices

1. **Use CLI First**: Try CLI commands before falling back to scripts
2. **Tag Messages**: Use --tag for better filtering and search
3. **Set Priority**: Use --priority for urgent messages
4. **Batch Communications**: Group related messages together
5. **Include Context**: Make messages self-contained
6. **Check Delivery**: Verify important messages were received
