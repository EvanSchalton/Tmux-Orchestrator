# Daemon-PM Messaging Protocol Specification

## Overview

This document defines the structured messaging protocol for daemon-PM coordination through the pubsub system, replacing direct tmux send_keys with a more robust and structured approach.

## Message Structure

### Base Message Format

```json
{
  "id": "unique-message-id",
  "timestamp": "2025-08-17T10:30:00Z",
  "source": {
    "type": "daemon|pm|agent|orchestrator",
    "identifier": "daemon-monitor|pm:0|backend-dev:2"
  },
  "target": {
    "type": "broadcast|session|window|group",
    "identifier": "pm:0|session-name|management"
  },
  "message": {
    "type": "notification|request|response|acknowledgment",
    "category": "health|recovery|status|task|escalation",
    "priority": "critical|high|normal|low",
    "content": {
      "subject": "Brief subject line",
      "body": "Detailed message content",
      "context": {},
      "actions": []
    }
  },
  "metadata": {
    "tags": ["monitoring", "health", "recovery"],
    "ttl": 3600,
    "requires_ack": true,
    "correlation_id": "parent-message-id"
  }
}
```

## Message Types

### 1. Health Notifications

```json
{
  "message": {
    "type": "notification",
    "category": "health",
    "priority": "high",
    "content": {
      "subject": "Agent Idle Alert",
      "body": "Agent backend-dev:2 has been idle for 15 minutes",
      "context": {
        "agent": "backend-dev:2",
        "idle_duration": 900,
        "last_activity": "2025-08-17T10:15:00Z"
      },
      "actions": [
        {"id": "restart", "label": "Restart Agent"},
        {"id": "investigate", "label": "Check Status"},
        {"id": "reassign", "label": "Reassign Tasks"}
      ]
    }
  }
}
```

### 2. Recovery Actions

```json
{
  "message": {
    "type": "notification",
    "category": "recovery",
    "priority": "critical",
    "content": {
      "subject": "PM Crash Recovery",
      "body": "PM in session project-x:1 crashed - spawning replacement",
      "context": {
        "crashed_pm": "project-x:1",
        "crash_time": "2025-08-17T10:28:00Z",
        "recovery_action": "spawn_replacement",
        "new_pm": "project-x:1"
      },
      "actions": [
        {"id": "verify", "label": "Verify Recovery"},
        {"id": "transfer_state", "label": "Transfer Context"}
      ]
    }
  }
}
```

### 3. Status Requests

```json
{
  "message": {
    "type": "request",
    "category": "status",
    "priority": "normal",
    "content": {
      "subject": "Team Status Request",
      "body": "Requesting current status of all team agents",
      "context": {
        "session": "project-x",
        "request_type": "team_health"
      }
    }
  }
}
```

### 4. PM Acknowledgments

```json
{
  "message": {
    "type": "acknowledgment",
    "category": "health",
    "priority": "normal",
    "content": {
      "subject": "Idle Alert Acknowledged",
      "body": "Investigated backend-dev:2 - agent restarted and assigned new tasks",
      "context": {
        "original_message_id": "msg-12345",
        "action_taken": "restart",
        "result": "success"
      }
    }
  }
}
```

## Tag Taxonomy

### System Tags
- `monitoring` - Messages from monitoring daemon
- `management` - PM coordination messages
- `recovery` - Recovery action notifications
- `health` - Health check results
- `escalation` - Issues requiring attention

### Priority Tags
- `critical` - Immediate action required
- `high` - Urgent but not blocking
- `normal` - Standard priority
- `low` - Informational only

### Action Tags
- `requires_ack` - PM must acknowledge
- `auto_action` - Automated response taken
- `manual_review` - Human review needed

## Integration Points

### 1. Monitoring Daemon Integration

Replace direct tmux send_keys with pubsub messages:

```python
# OLD: Direct notification
self.tmux.send_keys(pm_target, "Agent idle: backend-dev:2", literal=True)

# NEW: Structured pubsub message
await self._send_pubsub_notification(
    target=pm_target,
    category="health",
    priority="high",
    subject="Agent Idle Alert",
    body=f"Agent {agent_target} has been idle for {idle_time} minutes",
    context={
        "agent": agent_target,
        "idle_duration": idle_time * 60,
        "last_activity": last_activity
    },
    actions=["restart", "investigate", "reassign"],
    tags=["monitoring", "health", "idle"],
    requires_ack=True
)
```

### 2. PM Consumption Pattern

```python
# PM-side message handler
async def handle_daemon_message(self, message: Dict[str, Any]):
    msg_type = message["message"]["type"]
    category = message["message"]["category"]
    
    if msg_type == "notification":
        if category == "health":
            await self._handle_health_notification(message)
        elif category == "recovery":
            await self._handle_recovery_notification(message)
    elif msg_type == "request":
        await self._handle_status_request(message)
```

### 3. Message Filtering

```python
# Get high-priority daemon messages
high_priority = await pubsub.read(
    session=pm_session,
    filters={
        "source.type": "daemon",
        "message.priority": ["critical", "high"],
        "metadata.tags": ["monitoring"]
    },
    since_minutes=30
)

# Get unacknowledged health alerts
pending_acks = await pubsub.read(
    session=pm_session,
    filters={
        "message.category": "health",
        "metadata.requires_ack": True,
        "status": "unacknowledged"
    }
)
```

## Message Flow Diagrams

### Health Check Flow

```
Daemon -> Pubsub -> PM
  |         |        |
  |         |        v
  |         |    Evaluate
  |         |        |
  |         |        v
  |         |    Take Action
  |         |        |
  |         v        v
  |     Store    Send Ack
  |         |        |
  v         v        v
Log    History   Pubsub
```

### Recovery Action Flow

```
Daemon Detects Crash
        |
        v
   Send Critical
   Recovery Msg
        |
        v
    Pubsub Queue
        |
        +--------+--------+
        |                 |
        v                 v
    PM Receives      Orchestrator
        |             Notified
        v                 |
   Verify Recovery        |
        |                 |
        v                 v
    Send Ack         Monitor
```

## Performance Considerations

1. **Message Batching**: Group related notifications to reduce message volume
2. **Priority Queuing**: Process critical messages before normal priority
3. **TTL Management**: Auto-expire old notifications to prevent queue buildup
4. **Selective Delivery**: Use tags and filters to reduce unnecessary processing

## Security and Validation

1. **Source Verification**: Validate message source before processing
2. **Action Authorization**: Ensure PMs can only acknowledge their own team's messages
3. **Message Integrity**: Include checksums for critical messages
4. **Audit Trail**: Log all acknowledgments and actions taken

## Migration Strategy

1. **Phase 1**: Implement pubsub wrapper in monitoring daemon
2. **Phase 2**: Add PM-side message handlers
3. **Phase 3**: Gradually replace direct notifications
4. **Phase 4**: Remove legacy notification code

## Example Implementation

```python
class DaemonPubsubIntegration:
    """Daemon-side pubsub integration for structured messaging."""
    
    async def send_health_alert(self, agent_target: str, issue: str, context: dict):
        """Send structured health alert through pubsub."""
        message = self._build_message(
            type="notification",
            category="health",
            priority=self._determine_priority(issue),
            subject=f"Agent Health Alert: {agent_target}",
            body=self._format_issue_description(issue, context),
            context=context,
            tags=["monitoring", "health", issue.lower()],
            requires_ack=True
        )
        
        # Determine target PM
        session = agent_target.split(":")[0]
        pm_target = f"{session}:1"  # Standard PM window
        
        # Send via pubsub
        await self.pubsub_client.publish(
            target=pm_target,
            message=json.dumps(message),
            priority=message["message"]["priority"],
            tags=message["metadata"]["tags"]
        )
```