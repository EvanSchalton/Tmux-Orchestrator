# LLM Optimization Guide: Achieving 95% Success Rate

## Current Status
- **Current Success Rate**: 81.8%
- **Target Success Rate**: 95%
- **Gap to Close**: 13.2%

## Key Issues Identified from QA Testing

### 1. Action Parameter Confusion (28% of failures)
LLMs often forget to include the required `action` parameter when using hierarchical tools.

**Problem Example:**
```json
{
  "tool": "tmux-orc_agent",
  "arguments": {
    "type": "developer",
    "session_window": "dev:1"
  }
}
```

**Solution with enumDescription:**
```json
{
  "tool": "tmux-orc_agent",
  "description": "Manage agent lifecycle and operations",
  "arguments": {
    "action": {
      "type": "string",
      "enum": ["spawn", "status", "kill", "restart", "logs", "health-check", "quality-check", "list", "pause", "resume"],
      "enumDescriptions": {
        "spawn": "Create a new agent in the specified session window",
        "status": "Check the current status and health of an agent",
        "kill": "Terminate an agent gracefully or forcefully",
        "restart": "Restart an agent while preserving its context",
        "logs": "View recent output and activity logs from an agent",
        "health-check": "Perform a comprehensive health check on an agent",
        "quality-check": "Run quality assurance checks on agent output",
        "list": "List all agents or filter by criteria",
        "pause": "Temporarily pause an agent's execution",
        "resume": "Resume a paused agent's execution"
      },
      "required": true,
      "description": "The action to perform on the agent"
    }
  }
}
```

### 2. Parameter Type Mismatches (22% of failures)
LLMs use strings for numeric and boolean values.

**Problem Examples:**
```json
{
  "interval": "30",      // Should be number
  "verbose": "true",     // Should be boolean
  "count": "5"           // Should be number
}
```

**Solution with Clear Type Definitions:**
```json
{
  "interval": {
    "type": "integer",
    "minimum": 1,
    "maximum": 3600,
    "default": 30,
    "description": "Monitoring interval in seconds (1-3600)"
  },
  "verbose": {
    "type": "boolean",
    "default": false,
    "description": "Enable verbose output (true/false, not string)"
  },
  "count": {
    "type": "integer",
    "minimum": 1,
    "description": "Number of items to process (numeric, not string)"
  }
}
```

### 3. Session Window Format Errors (18% of failures)
Incorrect session:window format or using old separate parameters.

**Problem Examples:**
```json
{
  "session": "backend",
  "window": "1"           // Should be combined
}
// OR
{
  "session_window": "backend-1"  // Wrong separator
}
```

**Solution with Format Validation:**
```json
{
  "session_window": {
    "type": "string",
    "pattern": "^[a-zA-Z0-9_-]+:[0-9]+$",
    "description": "Target location in format 'session:window' (e.g., 'backend:1', 'myproject:0')",
    "examples": ["backend:1", "frontend:2", "dev-team:0"],
    "errorMessage": "Must be in format 'session:window' with colon separator"
  }
}
```

### 4. Old Tool Name Usage (15% of failures)
LLMs still trying to use flat tool names.

**Solution with Tool Discovery Enhancement:**
```json
{
  "tool_aliases": {
    "tmux-orc_agent_spawn": {
      "correct_tool": "tmux-orc_agent",
      "correct_usage": {
        "tool": "tmux-orc_agent",
        "arguments": {
          "action": "spawn",
          "...": "other parameters"
        }
      },
      "deprecation_message": "Use tmux-orc_agent with action='spawn' instead"
    }
  }
}
```

### 5. Missing Required Parameters (10% of failures)
LLMs omit required parameters for specific actions.

**Solution with Action-Specific Requirements:**
```json
{
  "tmux-orc_agent": {
    "action_requirements": {
      "spawn": {
        "required": ["action", "type", "session_window"],
        "optional": ["context", "skills", "briefing", "extend"]
      },
      "status": {
        "required": ["action", "session_window"],
        "optional": ["verbose", "format"]
      },
      "kill": {
        "required": ["action", "session_window"],
        "optional": ["force", "cleanup"]
      }
    }
  }
}
```

### 6. Context and Briefing Confusion (7% of failures)
LLMs confuse when to use context vs briefing vs extend.

**Solution with Clear Descriptions:**
```json
{
  "context": {
    "type": "string",
    "description": "Primary instructions for the agent's task (use for main directives)",
    "example": "Implement user authentication API with OAuth2 support"
  },
  "briefing": {
    "type": "string",
    "description": "Detailed background information and requirements (use for comprehensive specs)",
    "example": "The system should support Google, GitHub, and email/password authentication..."
  },
  "extend": {
    "type": "string",
    "description": "Additional instructions to append to existing context (use to add requirements)",
    "example": "Also implement rate limiting and session management"
  }
}
```

## Recommended enumDescriptions for Each Tool

### tmux-orc_agent
```json
{
  "enumDescriptions": {
    "spawn": "Create a new agent with specified type and context in a tmux window",
    "status": "Get current status, health, and activity information for an agent",
    "kill": "Terminate an agent, optionally forcing if unresponsive",
    "restart": "Restart an agent preserving its context and state",
    "logs": "Retrieve recent output and debug logs from an agent",
    "health-check": "Run comprehensive health diagnostics on an agent",
    "quality-check": "Validate agent output quality and adherence to requirements",
    "list": "List all agents or filter by session, type, or status",
    "pause": "Temporarily suspend agent execution without terminating",
    "resume": "Resume execution of a paused agent"
  }
}
```

### tmux-orc_monitor
```json
{
  "enumDescriptions": {
    "start": "Begin monitoring a session or specific window with configurable alerts",
    "stop": "Stop monitoring and clean up resources",
    "status": "Check current monitoring status and active alerts",
    "metrics": "Retrieve performance metrics and statistics",
    "configure": "Update monitoring thresholds, alerts, and notification settings",
    "health-check": "Verify monitoring system functionality",
    "list": "List all active monitoring instances",
    "pause": "Temporarily disable monitoring without stopping",
    "resume": "Re-enable paused monitoring",
    "export": "Export monitoring data to file or external system"
  }
}
```

### tmux-orc_team
```json
{
  "enumDescriptions": {
    "deploy": "Deploy a complete team configuration from YAML file",
    "status": "Check deployment status and team member health",
    "list": "List all deployed teams with summary information",
    "update": "Modify team composition or configuration",
    "cleanup": "Remove team and free all associated resources"
  }
}
```

### tmux-orc_pubsub
```json
{
  "enumDescriptions": {
    "send": "Send a direct message to a specific agent or window",
    "broadcast": "Send a message to all agents in a session or matching criteria",
    "subscribe": "Subscribe an agent to specific topics or channels",
    "publish": "Publish a message to a topic for all subscribers",
    "history": "Retrieve message history with optional filters",
    "ack": "Acknowledge receipt or completion of a message",
    "list": "List all active channels, topics, or subscriptions",
    "clear": "Clear message history or remove stale channels"
  }
}
```

## Implementation Strategy for 95% Success Rate

### 1. Enhanced Tool Descriptions
```python
def generate_tool_description(entity, actions):
    return {
        "name": f"tmux-orc_{entity}",
        "description": f"Hierarchical tool for {entity} management. Always include 'action' parameter.",
        "arguments": {
            "action": {
                "type": "string",
                "enum": list(actions.keys()),
                "enumDescriptions": actions,
                "required": True,
                "description": "REQUIRED: The specific operation to perform"
            }
        }
    }
```

### 2. Validation with Helpful Errors
```python
def validate_hierarchical_call(tool, arguments):
    if not arguments.get("action"):
        return {
            "error": "Missing required 'action' parameter",
            "hint": f"For {tool}, you must specify an action like 'spawn', 'status', etc.",
            "example": {
                "tool": tool,
                "arguments": {
                    "action": "status",
                    "session_window": "example:1"
                }
            }
        }
    # Additional validation...
```

### 3. Smart Parameter Coercion
```python
def coerce_parameters(params):
    """Intelligently fix common parameter mistakes"""
    coerced = {}

    for key, value in params.items():
        # Remove -- prefix if present
        if key.startswith("--"):
            key = key[2:]

        # Convert string booleans
        if value in ["true", "false"]:
            coerced[key] = value == "true"
        # Convert string numbers
        elif isinstance(value, str) and value.isdigit():
            coerced[key] = int(value)
        else:
            coerced[key] = value

    return coerced
```

### 4. Migration Hints in Error Messages
```python
ERROR_MESSAGES = {
    "unknown_tool": {
        "tmux-orc_agent_spawn": "Tool 'tmux-orc_agent_spawn' not found. Use 'tmux-orc_agent' with action='spawn'",
        "tmux-orc_monitor_start": "Tool 'tmux-orc_monitor_start' not found. Use 'tmux-orc_monitor' with action='start'",
        # ... more mappings
    }
}
```

## Testing Strategy for LLM Success

### 1. Automated Test Cases
```python
test_cases = [
    {
        "description": "Agent spawn with all parameters",
        "expected_tool": "tmux-orc_agent",
        "expected_args": {
            "action": "spawn",
            "type": "developer",
            "session_window": "test:1",
            "context": "Test context"
        }
    },
    # ... comprehensive test suite
]
```

### 2. Success Metrics Tracking
```python
def track_llm_success(request, response, success):
    metrics = {
        "timestamp": datetime.now(),
        "tool": request.get("tool"),
        "action": request.get("arguments", {}).get("action"),
        "success": success,
        "failure_reason": None if success else analyze_failure(request, response)
    }
    log_metrics(metrics)
```

### 3. Continuous Improvement Loop
1. Monitor LLM usage patterns
2. Identify new failure modes
3. Update enumDescriptions and validation
4. Test improvements
5. Deploy updates
6. Measure success rate change

## Quick Reference for LLM Developers

### Always Remember:
1. **Every hierarchical tool needs `action` parameter**
2. **Use proper JSON types (not strings for numbers/booleans)**
3. **Session window format is `session:window` with colon**
4. **No `--` prefixes on parameters**
5. **Check enumDescriptions for available actions**

### Common Patterns:
```json
// Entity management
{
  "tool": "tmux-orc_[entity]",
  "arguments": {
    "action": "[verb]",
    "target": "[identifier]",
    "[params]": "[values]"
  }
}

// Status checking
{
  "tool": "tmux-orc_[entity]",
  "arguments": {
    "action": "status",
    "session_window": "[session]:[window]"
  }
}

// Listing/Discovery
{
  "tool": "tmux-orc_[entity]",
  "arguments": {
    "action": "list",
    "filter": "[optional criteria]"
  }
}
```

## Conclusion

By implementing these optimizations:
1. Clear enumDescriptions for all actions
2. Intelligent parameter validation and coercion
3. Helpful error messages with examples
4. Migration hints for old tool names
5. Comprehensive test coverage

We can close the 13.2% gap and achieve the 95% LLM success rate target. The key is making the hierarchical structure intuitive and self-documenting through rich metadata and smart error handling.
