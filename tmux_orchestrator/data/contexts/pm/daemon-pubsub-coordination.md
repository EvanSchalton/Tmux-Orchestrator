# Daemon-Pubsub Coordination Guide

## Overview

The Tmux Orchestrator uses a high-performance messaging daemon to achieve sub-100ms message delivery between monitoring systems and agents. This replaces slow CLI-based messaging (5000ms) with daemon IPC for critical notifications.

## Architecture

### Components

1. **Messaging Daemon** (`messaging_daemon.py`)
   - Unix socket IPC server
   - Async message processing
   - Priority-based queuing
   - Performance tracking

2. **Pubsub CLI** (`cli/pubsub.py`)
   - Fast daemon client interface
   - Performance monitoring
   - Structured message filtering

3. **Monitor Integration**
   - `PubsubNotificationManager`: High-performance notification delivery
   - `MonitorPubsubClient`: Daemon client with CLI fallback
   - `PriorityMessageRouter`: Priority-based message routing

4. **Recovery Integration**
   - `PubsubRecoveryCoordinator`: Fast recovery notifications
   - Grace period tracking
   - Batch recovery operations

## Performance Requirements

- **Target**: <100ms message delivery
- **Critical Messages**: <50ms
- **High Priority**: <75ms
- **Normal Priority**: <100ms
- **Low Priority**: Batched, <500ms

## Message Priorities

### Critical (🚨)
- Agent crashes
- PM failures
- System emergencies

### High (🔧)
- Recovery needed
- Unresponsive agents
- Team-wide issues

### Normal (📋)
- Fresh agent alerts
- Status updates
- Team idle notifications

### Low (💤)
- Idle agent notifications
- Routine status checks
- Non-urgent updates

## PM Integration

### Quick Reference

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

## Structured Message Format

```json
{
  "id": "daemon-health-1234567890",
  "timestamp": "2025-01-15T10:30:45Z",
  "source": {
    "type": "daemon",
    "identifier": "monitoring-daemon"
  },
  "message": {
    "type": "notification",
    "category": "health",
    "priority": "high",
    "content": {
      "subject": "Agent Health Alert",
      "body": "Agent backend:1 has been idle for 30 minutes",
      "context": {
        "agent": "backend:1",
        "issue_type": "idle",
        "idle_duration": 1800
      }
    }
  },
  "metadata": {
    "requires_ack": true,
    "tags": ["health", "idle", "backend"],
    "correlation_id": "session-123"
  }
}
```

## Fallback Behavior

If the daemon is unavailable:

1. **Automatic CLI Fallback**: System falls back to CLI commands
2. **Performance Degradation**: Expect 5000ms instead of <100ms
3. **Retry Logic**: Critical messages are retried
4. **Logging**: Fallback events are logged for debugging

## Best Practices

### For Monitoring Systems

1. **Batch Low-Priority Messages**: Reduce overhead
2. **Use Priority Routing**: Ensure critical messages are fast
3. **Monitor Performance**: Track delivery times
4. **Handle Failures Gracefully**: Always have fallback

### For PMs

1. **Process Messages Regularly**: Check every 30-60 seconds
2. **Acknowledge Critical Messages**: Confirm receipt and action
3. **Use Filters**: Focus on relevant messages
4. **Respond to Escalations**: Handle critical issues promptly

## Troubleshooting

### Daemon Not Running

```bash
# Check status
tmux-orc pubsub status

# Start daemon
tmux-orc daemon start

# Check logs
tail -f ~/.tmux-orchestrator/logs/daemon.log
```

### Performance Issues

```bash
# Check queue depth
tmux-orc pubsub stats | grep "Queue Depth"

# Monitor delivery times
tmux-orc pubsub stats | grep "P95"

# Check for errors
grep ERROR ~/.tmux-orchestrator/logs/daemon.log
```

### Message Not Delivered

1. Check daemon status
2. Verify target exists
3. Check message priority
4. Review daemon logs
5. Test with CLI fallback

## Performance Testing

```bash
# Run performance tests
python tmux_orchestrator/tests/test_pubsub_performance.py

# Expected output:
🚀 Running performance tests (100 iterations)...

📊 PERFORMANCE TEST RESULTS
==========================

📈 Performance Summary:
direct_daemon:
  Messages: 100
  Min: 15.2ms
  Median: 42.3ms
  P95: 87.5ms
  Max: 112.3ms

🎯 Target Compliance (<100ms):
✅ direct_daemon: 94.0%
✅ pubsub_client: 96.0%
✅ priority_router: 95.5%
✅ batch_delivery: 98.2%
```

## Integration Checklist

- [ ] PM session identified correctly (`#S:#I`)
- [ ] Daemon monitoring script running
- [ ] Pubsub system health verified
- [ ] Message filtering working correctly
- [ ] Acknowledgment system tested
- [ ] Escalation protocols established
- [ ] Team communication patterns updated
- [ ] Performance targets validated (<100ms)

## Future Enhancements

1. **WebSocket Support**: For remote monitoring
2. **Message Persistence**: Durable queue for reliability
3. **Metrics Export**: Prometheus/Grafana integration
4. **Encryption**: For sensitive messages
5. **Multi-Daemon**: For redundancy and scale

Remember: The pubsub system enhances coordination with sub-100ms performance but doesn't replace direct agent communication for task management.
