# Best Practices for Hierarchical MCP Tools

## Overview

This guide provides comprehensive best practices for effectively using the new hierarchical MCP tool structure. These practices optimize performance, reduce errors, and improve the overall development experience.

## Core Principles

### 1. Think in Entities, Not Actions
**Old Mindset:** "Which tool do I need for spawning?"
**New Mindset:** "I'm working with agents, what actions are available?"

```json
// Recommended approach
{
  "tool": "tmux-orc_agent",
  "arguments": {
    "action": "help"  // Discover all agent-related actions
  }
}
```

### 2. Use Consistent Parameter Patterns
Hierarchical tools use standardized parameter names across all entities:

| Parameter | Purpose | Used By |
|-----------|---------|---------|
| `action` | Operation to perform | All tools |
| `session_window` | Target location | Agent, Monitor, PM |
| `name` | Entity identifier | Team, Task, Context |
| `format` | Output format | All tools with output |
| `verbose` | Detailed output | All tools |

### 3. Leverage Action Discovery
Each hierarchical tool supports action discovery:

```json
// Discover available actions
{
  "tool": "tmux-orc_monitor",
  "arguments": {
    "action": "actions"  // Returns: ["start", "stop", "status", ...]
  }
}

// Get help for specific action
{
  "tool": "tmux-orc_monitor",
  "arguments": {
    "action": "start",
    "help": true  // Shows parameters for start action
  }
}
```

## Entity-Specific Best Practices

### Agent Tool (`tmux-orc_agent`)

**Best Practices:**
1. Always specify agent type explicitly
2. Use descriptive contexts
3. Check status before operations

```json
// Good: Complete spawn specification
{
  "tool": "tmux-orc_agent",
  "arguments": {
    "action": "spawn",
    "type": "developer",
    "session_window": "backend:1",
    "context": "Implement user authentication API with OAuth2",
    "skills": ["python", "fastapi", "oauth2"]
  }
}

// Better: Check before spawn
{
  "tool": "tmux-orc_agent",
  "arguments": {
    "action": "status",
    "session_window": "backend:1"
  }
}
// Then spawn only if not exists
```

**Common Actions:**
- `spawn`: Create new agent
- `status`: Check agent health
- `kill`: Terminate agent
- `restart`: Restart with context preservation
- `logs`: View agent output

### Monitor Tool (`tmux-orc_monitor`)

**Best Practices:**
1. Start monitoring early in workflows
2. Use appropriate intervals
3. Export data regularly

```json
// Good: Comprehensive monitoring setup
{
  "tool": "tmux-orc_monitor",
  "arguments": {
    "action": "start",
    "session_window": "project:0",
    "interval": 30,
    "alerts": {
      "idle_threshold": 300,
      "error_threshold": 5,
      "memory_threshold": "80%"
    }
  }
}

// Better: Configure before starting
{
  "tool": "tmux-orc_monitor",
  "arguments": {
    "action": "configure",
    "profile": "production",
    "notifications": ["slack", "email"]
  }
}
```

### Team Tool (`tmux-orc_team`)

**Best Practices:**
1. Use configuration files for complex teams
2. Validate before deployment
3. Monitor team health

```json
// Good: Deploy with configuration
{
  "tool": "tmux-orc_team",
  "arguments": {
    "action": "deploy",
    "config": "backend-team.yaml",
    "validate": true
  }
}

// Better: Plan, validate, then deploy
{
  "tool": "tmux-orc_team",
  "arguments": {
    "action": "plan",
    "config": "backend-team.yaml",
    "output": "deployment-plan.json"
  }
}
```

### PubSub Tool (`tmux-orc_pubsub`)

**Best Practices:**
1. Use topics for broadcast messages
2. Include metadata for tracking
3. Implement acknowledgments

```json
// Good: Structured message with metadata
{
  "tool": "tmux-orc_pubsub",
  "arguments": {
    "action": "send",
    "target": "backend:1",
    "message": "Update user service to v2.0",
    "metadata": {
      "priority": "high",
      "ticket": "JIRA-123",
      "deadline": "2024-12-01"
    }
  }
}

// Better: Use topics for team-wide messages
{
  "tool": "tmux-orc_pubsub",
  "arguments": {
    "action": "publish",
    "topic": "backend-updates",
    "message": "API breaking change in v2.0",
    "require_ack": true
  }
}
```

## Common Patterns

### Pattern 1: Entity Lifecycle Management

```python
# Comprehensive entity lifecycle
async def manage_entity_lifecycle(entity_type, identifier):
    tool = f"tmux-orc_{entity_type}"

    # 1. Check current status
    status = await call_tool(tool, {
        "action": "status",
        "identifier": identifier
    })

    # 2. Create if not exists
    if not status["exists"]:
        await call_tool(tool, {
            "action": "create",
            "identifier": identifier,
            "config": f"{entity_type}-config.yaml"
        })

    # 3. Monitor health
    health = await call_tool(tool, {
        "action": "health-check",
        "identifier": identifier
    })

    # 4. Handle issues
    if not health["healthy"]:
        await call_tool(tool, {
            "action": "restart",
            "identifier": identifier,
            "preserve_state": true
        })

    return status
```

### Pattern 2: Batch Operations

```python
# Efficient batch processing
async def batch_operation(entity_type, action, targets):
    tool = f"tmux-orc_{entity_type}"

    # Single call with multiple targets (preferred)
    result = await call_tool(tool, {
        "action": action,
        "targets": targets,  # Process all at once
        "parallel": true
    })

    return result
```

### Pattern 3: Progressive Enhancement

```python
# Start simple, add complexity as needed
async def progressive_deployment(team_name):
    # 1. Basic deployment
    result = await call_tool("tmux-orc_team", {
        "action": "deploy",
        "name": team_name
    })

    if result["success"]:
        # 2. Add monitoring
        await call_tool("tmux-orc_monitor", {
            "action": "start",
            "target": f"{team_name}:0"
        })

        # 3. Configure communication
        await call_tool("tmux-orc_pubsub", {
            "action": "create-channel",
            "name": f"{team_name}-updates"
        })

        # 4. Set up automation
        await call_tool("tmux-orc_orchestrator", {
            "action": "configure",
            "team": team_name,
            "automation": "continuous"
        })
```

## Performance Optimization

### 1. Use Bulk Operations
```json
// Inefficient: Multiple calls
for agent in agents:
    tmux-orc_agent(action="status", session_window=agent)

// Efficient: Single bulk call
{
  "tool": "tmux-orc_agent",
  "arguments": {
    "action": "status",
    "targets": ["backend:1", "backend:2", "backend:3"],
    "format": "summary"
  }
}
```

### 2. Cache Action Lists
```python
# Cache available actions at startup
CACHED_ACTIONS = {}

async def get_actions(entity):
    if entity not in CACHED_ACTIONS:
        result = await call_tool(f"tmux-orc_{entity}", {
            "action": "actions"
        })
        CACHED_ACTIONS[entity] = result["actions"]
    return CACHED_ACTIONS[entity]
```

### 3. Use Appropriate Detail Levels
```json
// Light: Status overview
{
  "tool": "tmux-orc_system",
  "arguments": {
    "action": "status",
    "detail": "summary"  // Minimal info
  }
}

// Heavy: Full diagnostic
{
  "tool": "tmux-orc_system",
  "arguments": {
    "action": "status",
    "detail": "full",  // Complete details
    "include_logs": true
  }
}
```

## Error Handling

### 1. Graceful Fallbacks
```python
async def safe_action(tool, primary_action, fallback_action, args):
    try:
        # Try primary action
        result = await call_tool(tool, {
            "action": primary_action,
            **args
        })
        return result
    except ActionNotFoundError:
        # Fall back to alternative
        return await call_tool(tool, {
            "action": fallback_action,
            **args
        })
```

### 2. Validation Before Execution
```python
async def validated_execution(tool, action, args):
    # 1. Validate action exists
    actions = await call_tool(tool, {"action": "actions"})
    if action not in actions["available"]:
        raise ValueError(f"Unknown action: {action}")

    # 2. Validate parameters
    validation = await call_tool(tool, {
        "action": action,
        "validate_only": true,
        **args
    })

    if validation["valid"]:
        # 3. Execute
        return await call_tool(tool, {
            "action": action,
            **args
        })
    else:
        raise ValueError(validation["errors"])
```

### 3. Comprehensive Error Context
```json
// Include context for debugging
{
  "tool": "tmux-orc_agent",
  "arguments": {
    "action": "spawn",
    "type": "developer",
    "session_window": "project:1",
    "error_context": {
      "workflow": "feature-development",
      "step": "backend-setup",
      "retry_count": 0
    }
  }
}
```

## Security Best Practices

### 1. Validate Inputs
```python
ALLOWED_ACTIONS = {
    "agent": ["spawn", "status", "kill"],
    "monitor": ["start", "stop", "status"],
    # ... etc
}

def validate_action(entity, action):
    return action in ALLOWED_ACTIONS.get(entity, [])
```

### 2. Sanitize Parameters
```python
def sanitize_params(params):
    # Remove any potentially dangerous characters
    sanitized = {}
    for key, value in params.items():
        if isinstance(value, str):
            # Basic sanitization
            sanitized[key] = value.replace(";", "").replace("&", "")
        else:
            sanitized[key] = value
    return sanitized
```

### 3. Audit Tool Usage
```json
// Enable audit logging
{
  "tool": "tmux-orc_system",
  "arguments": {
    "action": "configure",
    "audit_logging": true,
    "audit_level": "all",
    "audit_destination": "/logs/tool-usage.log"
  }
}
```

## Integration Patterns

### 1. With CI/CD Pipelines
```yaml
# GitHub Actions example
- name: Deploy Team
  run: |
    tmux-orc call '{
      "tool": "tmux-orc_team",
      "arguments": {
        "action": "deploy",
        "config": "${{ env.TEAM_CONFIG }}",
        "environment": "${{ env.DEPLOY_ENV }}"
      }
    }'
```

### 2. With Monitoring Systems
```python
# Prometheus integration
async def export_metrics():
    metrics = await call_tool("tmux-orc_monitor", {
        "action": "export",
        "format": "prometheus",
        "endpoint": "/metrics"
    })
    return metrics
```

### 3. With Chat Systems
```python
# Slack integration
async def handle_slack_command(command, args):
    # Map Slack commands to tool actions
    tool_mapping = {
        "/agent-status": ("agent", "status"),
        "/team-deploy": ("team", "deploy"),
        "/monitor-start": ("monitor", "start")
    }

    if command in tool_mapping:
        tool, action = tool_mapping[command]
        return await call_tool(f"tmux-orc_{tool}", {
            "action": action,
            **parse_slack_args(args)
        })
```

## Debugging Tips

### 1. Use Verbose Mode
```json
{
  "tool": "tmux-orc_agent",
  "arguments": {
    "action": "spawn",
    "type": "developer",
    "session_window": "debug:1",
    "verbose": true,  // Detailed output
    "debug": true     // Extra debugging info
  }
}
```

### 2. Trace Tool Calls
```python
# Enable tracing
os.environ["TMUX_ORC_TRACE"] = "true"

# All tool calls will be logged with:
# - Input parameters
# - Execution time
# - Output results
# - Any errors
```

### 3. Test in Isolation
```json
// Test mode for validation
{
  "tool": "tmux-orc_team",
  "arguments": {
    "action": "deploy",
    "config": "test-team.yaml",
    "dry_run": true,  // Don't actually deploy
    "explain": true   // Show what would happen
  }
}
```

## Migration Tips

### 1. Gradual Adoption
Start with one entity type and expand:
1. Week 1: Migrate all agent operations
2. Week 2: Add monitor operations
3. Week 3: Include team operations
4. Week 4: Complete remaining tools

### 2. Compatibility Layer
```python
# Temporary compatibility wrapper
def compat_tool_call(old_tool_name, args):
    # Map old tool to new format
    parts = old_tool_name.split("_")
    entity = parts[2]  # tmux-orc_[entity]_[action]
    action = "_".join(parts[3:])

    return call_tool(f"tmux-orc_{entity}", {
        "action": action,
        **migrate_args(args)
    })
```

### 3. Learning Resources
- Interactive tool explorer: `tmux-orc explore`
- Practice environment: `tmux-orc sandbox`
- Migration assistant: `tmux-orc migrate assist`

## Summary Checklist

- [ ] Understand entity-based organization
- [ ] Use action discovery for exploration
- [ ] Implement proper error handling
- [ ] Optimize with bulk operations
- [ ] Validate inputs before execution
- [ ] Use appropriate detail levels
- [ ] Enable audit logging for production
- [ ] Test with dry_run mode
- [ ] Cache frequently used data
- [ ] Follow security best practices

## Conclusion

The hierarchical tool structure provides a more intuitive and maintainable approach to MCP tool usage. By following these best practices, you can maximize efficiency, reduce errors, and create more robust integrations. Remember: think in entities, validate before executing, and leverage the built-in discovery features to explore available functionality.
