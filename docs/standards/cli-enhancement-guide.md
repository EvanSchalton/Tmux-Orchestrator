# CLI Enhancement Guide

**Version**: 1.0
**Date**: 2025-08-16
**Purpose**: Standards for CLI command development
**Key Principle**: CLI quality = MCP tool quality via reflection

## 1. JSON Output Format Standards

### 1.1 Standard JSON Response Structure

**✅ MANDATORY**: All CLI commands with `--json` flag MUST return this exact structure:

```json
{
  "success": true,
  "timestamp": "2024-01-01T12:00:00Z",
  "command": "quick_deploy",
  "data": {
    "project_name": "myproject",
    "team_type": "frontend",
    "team_size": 3,
    "session": "myproject",
    "agents_spawned": 3,
    "pm_briefed": true,
    "monitoring_started": true
  },
  "error": null,
  "metadata": {
    "version": "2.1.23",
    "execution_time": 12.45,
    "warnings": []
  }
}
```

### 1.2 Error Response Format

```json
{
  "success": false,
  "timestamp": "2024-01-01T12:00:00Z",
  "command": "quick_deploy",
  "data": null,
  "error": {
    "type": "ValidationError",
    "message": "Team size must be between 1 and 10",
    "code": "E_VALIDATION_001",
    "details": {
      "team_size": 15,
      "max_allowed": 10
    }
  },
  "metadata": {
    "version": "2.1.23",
    "execution_time": 0.23,
    "warnings": []
  }
}
```

### 1.3 Implementation Pattern

```python
import json
from datetime import datetime
from tmux_orchestrator import __version__

@click.command()
@click.option("--json", is_flag=True, help="Output in JSON format")
def quick_deploy(json_flag: bool):
    """Deploy a project with agents quickly."""
    try:
        # Perform operation
        result = deploy_project()

        if json_flag:
            response = {
                "success": True,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "command": "quick_deploy",
                "data": result,
                "error": None,
                "metadata": {
                    "version": __version__,
                    "execution_time": get_execution_time(),
                    "warnings": []
                }
            }
            click.echo(json.dumps(response, indent=2))
        else:
            # Rich console output
            display_deployment_results(result)

    except Exception as e:
        if json_flag:
            error_response = {
                "success": False,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "command": "quick_deploy",
                "data": None,
                "error": {
                    "type": type(e).__name__,
                    "message": str(e),
                    "code": "E_ERROR_001"
                },
                "metadata": {
                    "version": __version__,
                    "execution_time": get_execution_time(),
                    "warnings": []
                }
            }
            click.echo(json.dumps(error_response, indent=2))
            ctx.exit(1)
        else:
            console.print(f"[red]✗ Error: {e}[/red]")
            ctx.exit(1)
```

## 2. Error Handling Standards

### 2.1 Standard Exit Codes

```python
EXIT_SUCCESS = 0           # Success
EXIT_GENERAL_ERROR = 1     # General error
EXIT_VALIDATION_ERROR = 2  # Input validation failed
EXIT_NOT_FOUND = 3         # Resource not found
EXIT_TIMEOUT = 4           # Operation timeout
EXIT_PERMISSION = 5        # Permission denied
EXIT_INTERNAL = 10         # Internal system error
```

### 2.2 Error Message Pattern

```python
# ✅ GOOD Error Messages
"Project 'myproject' already exists. Use --force to overwrite."
"Team size must be between 1 and 10. Got: 15"
"Session 'frontend' not found. Use 'tmux-orc list' to see available sessions."

# ❌ BAD Error Messages
"Error"
"Invalid input"
"Operation failed"
```

## 3. Help Text Standards

### 3.1 Command Documentation Template

```python
@click.command()
def quick_deploy():
    """Deploy a complete project with AI agents in minutes.

    Creates a new project structure, deploys a team of specialized
    Claude agents, and starts monitoring. Perfect for rapid prototyping
    and development kickoff.

    Examples:
        # Deploy frontend team
        tmux-orc quick-deploy myproject frontend 3

        # Deploy with JSON output
        tmux-orc quick-deploy myproject backend 4 --json

        # Deploy with custom options
        tmux-orc quick-deploy myproject fullstack 5 \\
            --prd requirements.md \\
            --no-monitor

    This command will:
    • Create project structure
    • Deploy specialized agent team
    • Brief agents with project context
    • Start monitoring daemon

    Output:
        Default: Rich progress display
        --json: Structured deployment data
    """
    pass
```

## 4. Code Review Checklist

### 4.1 JSON Output Verification

- [ ] `--json` flag implemented
- [ ] Response follows standard structure
- [ ] `success` field is boolean
- [ ] `timestamp` is ISO 8601 format
- [ ] `command` field matches command name
- [ ] Error responses include type, message, code
- [ ] `execution_time` included in metadata

### 4.2 Error Handling Verification

- [ ] All exceptions caught and handled
- [ ] Exit codes match error types
- [ ] Error messages are specific and actionable
- [ ] JSON errors follow standard format
- [ ] No sensitive data in error messages

### 4.3 Help Text Verification

- [ ] Brief one-line description
- [ ] Detailed explanation with context
- [ ] Multiple realistic examples
- [ ] Clear parameter descriptions
- [ ] Output format documented

---

**More sections coming...**
