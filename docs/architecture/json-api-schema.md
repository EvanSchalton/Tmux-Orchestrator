# JSON API Schema for CLI Commands

This document defines the consistent JSON schema used across all tmux-orchestrator CLI commands that support the `--json` flag for API integration and automation.

## Standard Response Structure

All JSON responses follow this consistent structure:

```json
{
  "success": boolean,
  "data": object | null,
  "error": string | null,
  "error_type": string | null,
  "timestamp": number,
  "command": string
}
```

### Core Fields

- `success`: Boolean indicating if the operation completed successfully
- `data`: Operation-specific data (null on failure)
- `error`: Human-readable error message (null on success)
- `error_type`: Machine-readable error type (null on success)
- `timestamp`: Unix timestamp of the response
- `command`: The command that generated this response

## Command-Specific Schemas

### spawn-orc Command

#### Success Response
```json
{
  "success": true,
  "data": {
    "script_path": string,
    "profile": string | null,
    "terminal": string,
    "launch_command": string,
    "instructions": string[],
    "workflow_steps": string[] | null,
    "message": string
  },
  "error": null,
  "error_type": null,
  "timestamp": number,
  "command": "spawn-orc"
}
```

#### Error Response
```json
{
  "success": false,
  "data": null,
  "error": string,
  "error_type": "TerminalDetectionError" | "CalledProcessError",
  "suggestions": string[] | null,
  "manual_instructions": string[] | null,
  "timestamp": number,
  "command": "spawn-orc"
}
```

### spawn pm Command

#### Success Response
```json
{
  "success": true,
  "data": {
    "role": "pm",
    "target": string,
    "window_name": string,
    "session_created": boolean,
    "claude_started": boolean,
    "context_sent": boolean,
    "extend": string | null
  },
  "error": null,
  "error_type": null,
  "timestamp": number,
  "command": "spawn pm"
}
```

#### Error Response
```json
{
  "success": false,
  "data": null,
  "error": string,
  "error_type": "ContextNotFound" | "WindowCreationError" | "WindowNotFound",
  "available_roles": string[] | null,
  "timestamp": number,
  "command": "spawn pm"
}
```

### spawn agent Command

#### Success Response
```json
{
  "success": true,
  "data": {
    "name": string,
    "target": string,
    "window_name": string,
    "briefing_sent": boolean
  },
  "error": null,
  "error_type": null,
  "timestamp": number,
  "command": "spawn agent"
}
```

#### Error Response
```json
{
  "success": false,
  "data": null,
  "error": string,
  "error_type": "ValidationError" | "RoleConflictError" | "WindowCreationError",
  "conflict_window": string | null,
  "validation_failed": string | null,
  "timestamp": number,
  "command": "spawn agent"
}
```

### execute Command

#### Success Response
```json
{
  "success": true,
  "data": {
    "project_name": string,
    "prd_file": string,
    "team_type": string,
    "team_size": number,
    "session": string,
    "project_dir": string,
    "monitoring_enabled": boolean,
    "task_generation_mode": "automatic" | "manual",
    "workflow_status": {
      "project_structure": "created",
      "team_deployed": boolean,
      "agents_deployed": number,
      "prd_analysis": "completed",
      "agent_briefings": "sent",
      "monitoring": "active" | "disabled"
    },
    "next_commands": string[]
  },
  "error": null,
  "error_type": null,
  "timestamp": number,
  "command": string
}
```

#### Error Response
```json
{
  "success": false,
  "data": null,
  "error": string,
  "error_type": "ProjectCreationError" | "TeamDeploymentError",
  "timestamp": number,
  "command": string
}
```

## Error Types

### Common Error Types
- `ValidationError`: Invalid input parameters
- `WindowCreationError`: Failed to create tmux window
- `WindowNotFound`: Created window could not be located
- `SessionCreationError`: Failed to create tmux session
- `ContextNotFound`: Requested role context not available
- `RoleConflictError`: Agent role already exists in session
- `TerminalDetectionError`: Could not detect suitable terminal emulator
- `CalledProcessError`: External command execution failed
- `ProjectCreationError`: Failed to create project structure
- `TeamDeploymentError`: Failed to deploy agent team

### Specific Error Fields
Some error responses include additional context fields:
- `suggestions`: Array of suggested solutions
- `manual_instructions`: Array of manual steps to resolve
- `available_roles`: List of available role contexts
- `conflict_window`: Target window causing role conflict
- `validation_failed`: Specific validation that failed

## Implementation Guidelines

### 1. Consistent Import Pattern
```python
if json:
    import json as json_module
    result = {...}
    console.print(json_module.dumps(result, indent=2))
    return
```

### 2. Error Handling Pattern
```python
except SomeException as e:
    if json:
        import json as json_module
        result = {
            "success": False,
            "error": str(e),
            "error_type": "SpecificErrorType",
            "timestamp": time.time(),
            "command": "command-name"
        }
        console.print(json_module.dumps(result, indent=2))
        return
    # Regular console output...
```

### 3. Success Response Pattern
```python
if json:
    import json as json_module
    import time
    result = {
        "success": True,
        "data": {
            # Command-specific data
        },
        "timestamp": time.time(),
        "command": "command-name"
    }
    console.print(json_module.dumps(result, indent=2))
else:
    # Regular console output...
```

## MCP Tool Integration

This JSON schema is designed for seamless integration with MCP (Model Context Protocol) tools:

1. **Consistent Structure**: All responses follow the same base schema
2. **Machine-Readable Errors**: Error types enable programmatic error handling
3. **Rich Context**: Success responses include all necessary data for follow-up actions
4. **Automation-Friendly**: Responses include next steps and operational status

## Testing JSON Output

Test commands with JSON output:

```bash
# Test orchestrator spawning
tmux-orc spawn-orc --json --no-launch

# Test PM spawning
tmux-orc spawn pm --session test-project --json

# Test agent spawning
tmux-orc spawn agent developer test-project --briefing "Test briefing" --json

# Test PRD execution
tmux-orc execute ./test-prd.md --json
```

## Version History

- v1.0: Initial schema definition for core commands
- v1.1: Added execute command schema
- v1.2: Enhanced error types and context fields
