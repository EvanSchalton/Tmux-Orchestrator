# CLI JSON API Schema

This document defines the consistent JSON schema used across all tmux-orchestrator CLI commands for MCP tool automation and API integration.

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

## Command Schemas

### spawn-orc Command

#### Success Response - No Launch Mode
```json
{
  "success": true,
  "data": {
    "script_path": "/tmp/tmux-orc-startup.sh",
    "profile": string | null,
    "terminal": "auto",
    "launch_command": string,
    "instructions": [
      "Script created successfully",
      "To launch manually, run: {script_path}"
    ]
  },
  "timestamp": number,
  "command": "spawn-orc"
}
```

#### Success Response - GUI Mode
```json
{
  "success": true,
  "data": {
    "terminal": string,
    "profile": string | null,
    "script_path": string,
    "terminal_command": string[],
    "workflow_steps": [
      "Create a feature request: planning/feature-xyz.md",
      "Use Claude's /create-prd command with the file",
      "Answer the PRD survey questions",
      "The orchestrator will spawn a PM with the PRD",
      "The PM will use /generate-tasks to create task list",
      "The PM will spawn the team and begin work"
    ],
    "message": "Orchestrator terminal launched successfully"
  },
  "timestamp": number,
  "command": "spawn-orc"
}
```

#### Error Response
```json
{
  "success": false,
  "error": string,
  "error_type": "TerminalDetectionError" | "CalledProcessError",
  "suggestions": string[] | null,
  "manual_instructions": string[] | null,
  "timestamp": number,
  "command": "spawn-orc"
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
    "team_type": "frontend" | "backend" | "fullstack" | "custom",
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
    "next_commands": [
      "tmux-orc agent send {project}:0 'status update'",
      "tmux-orc tasks status {project}",
      "tmux-orc team status {project}",
      "tmux-orc dashboard --session {project}"
    ]
  },
  "timestamp": number,
  "command": "execute {prd_file}"
}
```

#### Error Response
```json
{
  "success": false,
  "error": string,
  "error_type": "UnboundLocalError" | "ProjectCreationError" | "TeamDeploymentError",
  "timestamp": number,
  "command": "execute {prd_file}"
}
```

## Error Types

### Common Error Types
- `TerminalDetectionError`: Could not detect suitable terminal emulator
- `CalledProcessError`: External command execution failed
- `UnboundLocalError`: Variable scope issue (development/debugging)
- `ProjectCreationError`: Failed to create project structure
- `TeamDeploymentError`: Failed to deploy agent team

### Error Context Fields
- `suggestions`: Array of suggested solutions
- `manual_instructions`: Array of manual steps to resolve
- `available_options`: List of available choices/options

## MCP Tool Integration

### Automation Patterns

1. **Orchestrator Spawning**:
```bash
tmux-orc spawn-orc --json --no-launch
# Returns script path for execution
```

2. **Automated PRD Execution**:
```bash
tmux-orc execute ./prd.md --json --auto --no-monitor
# Returns project details and next steps
```

3. **Status Monitoring**:
```bash
tmux-orc status --json
tmux-orc list --json
```

### Response Processing

The JSON responses are designed for:
- **Machine Processing**: Consistent structure enables automated parsing
- **Error Handling**: Specific error types for programmatic error handling
- **Workflow Continuation**: Next steps and operational status included
- **Rich Context**: All necessary data for follow-up automation

## Implementation Guidelines

### Consistent JSON Output Pattern
```python
if output_json:
    result = {
        "success": True/False,
        "data": {...} if success else None,
        "error": error_message if not success else None,
        "error_type": "ErrorType" if not success else None,
        "timestamp": time.time(),
        "command": "command-name"
    }
    console.print(json.dumps(result, indent=2))
    return
```

### Error Handling Pattern
```python
except SpecificException as e:
    if output_json:
        result = {
            "success": False,
            "error": str(e),
            "error_type": "SpecificErrorType",
            "timestamp": time.time(),
            "command": command_name
        }
        console.print(json.dumps(result, indent=2))
        return
    # Regular console output...
```

## Testing Commands

```bash
# Test orchestrator spawning
tmux-orc spawn-orc --json --no-launch

# Test PRD execution
tmux-orc execute ./test-prd.md --json --auto --no-monitor --skip-planning

# Test system status
tmux-orc status --json
tmux-orc list --json
```

## Version History

- v1.0: Initial schema definition
- v1.1: Added execute command comprehensive schema
- v1.2: Enhanced error types and context fields
- v1.3: MCP automation patterns and implementation guidelines
