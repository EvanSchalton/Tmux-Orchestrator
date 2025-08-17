# Daemon-PM Pubsub Coordination Protocols

This document outlines how Project Managers should integrate with the monitoring daemon through the pubsub messaging system for enhanced coordination.

## Quick Reference

```bash
# Check daemon notifications (last 30 minutes)
python3 -c "
from tmux_orchestrator.core.communication.pm_pubsub_integration import PMPubsubIntegration
pm = PMPubsubIntegration('$(tmux display-message -p \"#S:#I\")')
notifications = pm.get_daemon_notifications(30)
for n in notifications: print(f'[{n[\"priority\"]}] {n[\"raw_message\"]}')
"

# Monitor high-priority management messages
tmux-orc read --session $(tmux display-message -p "#S:#I") --filter "HIGH PRIORITY\\|CRITICAL" --tail 10

# Acknowledge daemon notification
tmux-orc publish --group management --tag acknowledgment "PM ACK: notification-id - investigated agent, all healthy"
```

## Integration Patterns

### 1. Daemon Notification Consumption

PMs should regularly check for daemon notifications using the pubsub integration:

```python
from tmux_orchestrator.core.communication.pm_pubsub_integration import PMPubsubIntegration

# Initialize for current PM session
pm_session = subprocess.check_output(["tmux", "display-message", "-p", "#S:#I"]).decode().strip()
pm_pubsub = PMPubsubIntegration(pm_session)

# Check for daemon notifications
notifications = pm_pubsub.get_daemon_notifications(since_minutes=30)
for notification in notifications:
    print(f"Priority: {notification['priority']}")
    print(f"Type: {notification['type']}")
    print(f"Message: {notification['raw_message']}")

    # Acknowledge if action taken
    if notification['type'] == 'failure':
        pm_pubsub.acknowledge_notification(
            notification['id'],
            "Investigated and restarted affected agent"
        )
```

### 2. Monitoring Script Integration

Add this to your PM startup routine:

```bash
# Create monitoring script
python3 -c "
from tmux_orchestrator.core.communication.pm_pubsub_integration import create_pm_monitoring_script
script_path = create_pm_monitoring_script()
print(f'Monitoring script created: {script_path}')
"

# Run periodic checks (every 10 minutes)
while true; do
    /tmp/pm_daemon_monitor.sh $(tmux display-message -p "#S:#I")
    sleep 600
done &
```

### 3. Recovery Action Handling

When daemon reports recovery actions:

```bash
# Check for recovery notifications
tmux-orc read --session $(tmux display-message -p "#S:#I") --filter "recovery" --tail 5 --json

# Standard response pattern
tmux-orc publish --group management --priority normal --tag pm-response \
  "PM verified recovery action: [session] is healthy, continuing normal operations"
```

## Message Types and Responses

### Daemon Health Alerts

**Incoming Message Pattern:**
```
⚠️ HIGH PRIORITY Agent backend-dev:2 idle 15min - investigate or restart
Tags: [monitoring, health, idle]
```

**PM Response Protocol:**
1. Send status request to affected agent
2. If unresponsive, restart agent
3. Acknowledge with action taken

```bash
# Check agent status
tmux-orc agent send backend-dev:2 "STATUS REQUEST: Please provide current task and progress"

# If no response in 2 minutes, restart
tmux-orc restart agent backend-dev:2

# Acknowledge to daemon
tmux-orc publish --group management --tag acknowledgment \
  "PM handled idle agent backend-dev:2 - restarted, now active"
```

### Critical System Events

**Incoming Message Pattern:**
```
🚨 CRITICAL PM crash detected session:1 - spawning replacement PM
Tags: [recovery, critical, pm-management]
```

**PM Response Protocol:**
1. Verify if replacement PM needed
2. Check session health
3. Update team coordination

### Agent Status Notifications

**Incoming Message Pattern:**
```
📨 All agents healthy - 3 active, 0 idle, monitoring stable
Tags: [monitoring, status, health]
```

**PM Response:**
- No action required for healthy status
- Use for team status updates to orchestrator

## Coordination Best Practices

### 1. Proactive Monitoring

Set up continuous monitoring in your PM session:

```bash
# Add to PM startup
echo "Setting up daemon monitoring..."
(
  while true; do
    # Check every 5 minutes for high-priority messages
    ALERTS=$(tmux-orc read --session $(tmux display-message -p "#S:#I") \
             --filter "CRITICAL\\|HIGH PRIORITY" --tail 1 --json | \
             jq -r '.stored_messages | length')

    if [ "$ALERTS" -gt 0 ]; then
      echo "🚨 New daemon alerts detected - checking..."
      tmux-orc read --session $(tmux display-message -p "#S:#I") \
        --filter "CRITICAL\\|HIGH PRIORITY" --tail 3
    fi

    sleep 300
  done
) &
```

### 2. Escalation Protocols

When daemon notifications require escalation:

```bash
# Escalate to orchestrator through orchestrator session (window 0)
tmux-orc agent send orchestrator:0 "
ESCALATION: Daemon Coordination Issue
- Issue: Multiple agent failures detected by daemon
- Actions Taken: Restarted 2 agents, 1 still unresponsive
- Recommendation: Review system resources and agent configs
- Need: Orchestrator guidance on scaling approach
"
```

### 3. Team Communication Integration

Include daemon status in team updates:

```bash
# Enhanced team status with daemon insights
tmux-orc agent broadcast "
TEAM STATUS UPDATE (with daemon insights):
- Active Agents: 3 (verified by monitoring daemon)
- Recent Issues: 1 idle timeout resolved
- Daemon Health: Stable, monitoring operational
- Team Velocity: On track
- Next Checkpoint: 2 hours
"
```

## Troubleshooting

### Pubsub System Issues

If pubsub messages aren't flowing:

```bash
# Check pubsub system health
tmux-orc status --format json

# Verify message store
ls -la ~/.tmux-orchestrator/messages/

# Test message flow
tmux-orc publish --group management --tag test "PM connectivity test"
tmux-orc read --session $(tmux display-message -p "#S:#I") --filter "test" --tail 1
```

### Daemon Communication Problems

If daemon isn't sending messages:

```bash
# Check daemon status
tmux-orc monitor status

# Request manual status update
tmux-orc publish --group management --tag status-request \
  "PM requesting daemon status update"

# Verify daemon logs
tail -f ~/.tmux-orchestrator/daemon.log
```

### Integration Script Failures

If the PM integration scripts fail:

```python
# Test integration directly
from tmux_orchestrator.core.communication.pm_pubsub_integration import PMPubsubIntegration
pm = PMPubsubIntegration()

# Check basic functionality
health = pm.monitor_pubsub_health()
print(f"Pubsub health: {health}")

# Test message retrieval
messages = pm.get_management_broadcasts("high")
print(f"High priority messages: {len(messages)}")
```

## Security Considerations

### Message Authentication

- Daemon messages include sender identification
- PMs should verify message sources for critical actions
- Use acknowledgment tags to track message handling

### Information Filtering

- Only process messages tagged for management group
- Ignore messages not relevant to PM responsibilities
- Filter sensitive information before team broadcasts

### Access Control

- PM pubsub integration respects session boundaries
- Messages are scoped to appropriate audience groups
- Acknowledgments include PM session identification

## Performance Optimization

### Message Polling

- Check for notifications every 5-10 minutes, not continuously
- Use filtered reads to reduce processing overhead
- Batch acknowledgments when possible

### Storage Management

- Pubsub system auto-rotates messages (1000 message limit)
- PMs don't need to manage message cleanup
- Use `--since` parameters to limit historical searches

## Integration Checklist

- [ ] PM session identified correctly (`#S:#I`)
- [ ] Daemon monitoring daemon is running
- [ ] Pubsub system health verified
- [ ] Message filtering working correctly
- [ ] Acknowledgment system tested
- [ ] Escalation protocols established
- [ ] Team communication patterns updated

Remember: The pubsub system enhances coordination but doesn't replace direct agent communication for task management.
