# CLI Enhancement Code Review Standards

**Version**: 1.0
**Date**: 2025-08-16
**Applies To**: CLI commands, JSON output, performance optimization
**Key Principle**: CLI quality = MCP tool quality!

## Overview

With the architectural pivot to CLI reflection for MCP tools, CLI commands become the primary interface for all operations. This document establishes mandatory standards for CLI enhancement code review.

## 1. CLI Command Implementation Standards ✅

### 1.1 Command Structure Requirements

**✅ MANDATORY**: All CLI commands MUST follow consistent structure:

```python
@cli.command()
@click.option('--format', type=click.Choice(['text', 'json']), default='text')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@error_handler
async def command_name(format: str, verbose: bool) -> None:
    """
    Brief command description (one line).

    Detailed description explaining:
    - What the command does
    - When to use it
    - Expected outcomes
    """
    # Implementation
```

**✅ REQUIRED**: Command naming conventions:
```python
# Good examples
spawn_agent      # verb_noun format
get_status       # clear action
list_sessions    # descriptive
kill_agent       # direct action

# Bad examples
agent           # ambiguous
status          # unclear scope
do_thing        # vague action
```

### 1.2 Argument and Option Standards

**✅ MANDATORY**: Consistent argument/option patterns:

```python
# Required arguments first
@click.argument('session_name', required=True)
@click.argument('agent_type', required=False, default='developer')

# Options with clear defaults
@click.option('--project-path', '-p', type=click.Path(exists=True))
@click.option('--timeout', '-t', type=int, default=30, help='Timeout in seconds')
@click.option('--force', '-f', is_flag=True, help='Force operation')

# Format option ALWAYS included for JSON output
@click.option('--format', type=click.Choice(['text', 'json']), default='text')
```

**❌ FORBIDDEN**: Inconsistent option naming:
```python
# Don't mix styles
--projectPath    # Wrong: camelCase
--project_path   # Wrong: snake_case in CLI
--project-path   # Correct: kebab-case
```

### 1.3 Help Text Requirements

**✅ MANDATORY**: Comprehensive help text:

```python
@cli.command()
def spawn_agent():
    """
    Spawn a new Claude agent in a tmux session.

    Examples:
        # Basic usage
        tmux-orc spawn agent developer my-session

        # With options
        tmux-orc spawn agent pm my-session --project-path /app --briefing "Build the API"

        # JSON output
        tmux-orc spawn agent developer my-session --format json
    """
```

## 2. JSON Output Standards ✅

### 2.1 Consistent JSON Structure

**✅ MANDATORY**: All JSON responses MUST follow this structure:

```json
{
  "success": true,
  "timestamp": "2024-01-01T00:00:00Z",
  "command": "spawn_agent",
  "data": {
    // Command-specific data
  },
  "error": null,
  "metadata": {
    "version": "1.0.0",
    "execution_time": 1.234
  }
}
```

**✅ REQUIRED**: Error responses:
```json
{
  "success": false,
  "timestamp": "2024-01-01T00:00:00Z",
  "command": "spawn_agent",
  "data": null,
  "error": {
    "type": "ValidationError",
    "message": "Session name cannot be empty",
    "details": {
      "field": "session_name",
      "value": ""
    }
  },
  "metadata": {
    "version": "1.0.0",
    "execution_time": 0.123
  }
}
```

### 2.2 Data Type Consistency

**✅ MANDATORY**: Consistent data types across commands:

```python
# Timestamps: ISO 8601 format
"timestamp": "2024-01-01T00:00:00Z"

# Durations: Seconds as float
"execution_time": 1.234
"uptime": 3600.5

# Counts: Integers
"agent_count": 5
"total_sessions": 3

# IDs/Names: Strings
"session_id": "my-session"
"agent_type": "developer"

# Lists: Always arrays, even if empty
"agents": []
"errors": []
```

### 2.3 Field Naming Standards

**✅ REQUIRED**: Consistent field naming:

```python
# Use snake_case for all JSON fields
{
    "session_name": "my-session",      # Correct
    "agent_type": "developer",         # Correct
    "created_at": "2024-01-01",        # Correct
    "sessionName": "my-session",       # Wrong: camelCase
    "agent-type": "developer",         # Wrong: kebab-case
}
```

## 3. Error Handling Patterns ✅

### 3.1 Comprehensive Error Handling

**✅ MANDATORY**: All commands MUST handle common errors:

```python
@error_handler
async def command_implementation():
    try:
        # Validation
        if not session_name:
            raise ValidationError("Session name cannot be empty")

        # Operation
        result = await perform_operation()

    except ValidationError as e:
        return format_error(e, "ValidationError")
    except TMUXError as e:
        return format_error(e, "TMUXError")
    except TimeoutError as e:
        return format_error(e, "TimeoutError")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return format_error(e, "InternalError")
```

### 3.2 User-Friendly Error Messages

**✅ REQUIRED**: Clear, actionable error messages:

```python
# Good error messages
"Session 'my-session' not found. Use 'tmux-orc list sessions' to see available sessions."
"Agent type must be one of: developer, pm, qa, devops, reviewer"
"Operation timed out after 30 seconds. Try increasing --timeout."

# Bad error messages
"Error"
"Failed"
"Invalid input"
"Exception occurred"
```

### 3.3 Exit Codes

**✅ MANDATORY**: Consistent exit codes:

```python
# Exit code standards
0   # Success
1   # General error
2   # Validation error
3   # Resource not found
4   # Timeout
5   # Permission denied
10  # Internal error
```

## 4. Performance Standards ✅

### 4.1 Execution Time Limits

**✅ MANDATORY**: All commands MUST meet performance targets:

```python
# Performance requirements
Simple queries:      < 1 second
Complex operations:  < 3 seconds
Batch operations:    < 10 seconds

# Timeout enforcement
DEFAULT_TIMEOUT = 30  # seconds
MAX_TIMEOUT = 300     # 5 minutes
```

### 4.2 Progress Indicators

**✅ REQUIRED**: Progress feedback for long operations:

```python
# Operations > 1 second need progress
with click.progressbar(items, label='Processing agents') as bar:
    for item in bar:
        process_item(item)

# Or status messages
click.echo("Starting agent deployment...")
click.echo("Agent spawned successfully!")
```

### 4.3 Resource Optimization

**✅ MANDATORY**: Efficient resource usage:

```python
# Batch operations when possible
async def list_all_agents():
    # Good: Single tmux call
    sessions = await tmux.list_sessions()

    # Bad: Multiple calls
    for session in session_names:
        agents = await tmux.list_windows(session)
```

## 5. CLI Reflection Integration ✅

### 5.1 Dynamic Command Generation

**✅ REQUIRED**: Commands must support reflection:

```python
@cli.command()
@reflection_enabled
async def command_name():
    """Command description for reflection."""
    # Implementation that can be introspected
```

### 5.2 Metadata Requirements

**✅ MANDATORY**: Rich metadata for MCP tool generation:

```python
@cli.command()
@metadata({
    "mcp_tool_name": "spawn_agent",
    "category": "agent_management",
    "requires_session": True,
    "idempotent": False,
})
async def spawn_agent():
    """Spawn a new Claude agent."""
```

## 6. Testing Requirements ✅

### 6.1 Command Testing

**✅ MANDATORY**: Comprehensive CLI tests:

```python
def test_spawn_agent_success():
    """Test successful agent spawn."""
    result = runner.invoke(cli, ['spawn', 'agent', 'developer', 'test-session'])
    assert result.exit_code == 0
    assert "Agent spawned successfully" in result.output

def test_spawn_agent_json_output():
    """Test JSON output format."""
    result = runner.invoke(cli, ['spawn', 'agent', 'developer', 'test-session', '--format', 'json'])
    data = json.loads(result.output)
    assert data['success'] is True
    assert data['command'] == 'spawn_agent'
```

### 6.2 Error Testing

**✅ REQUIRED**: Test all error paths:

```python
def test_empty_session_name():
    """Test validation error for empty session."""
    result = runner.invoke(cli, ['spawn', 'agent', 'developer', ''])
    assert result.exit_code == 2
    assert "Session name cannot be empty" in result.output
```

## 7. Code Review Checklist ✅

### Pre-Review Checklist

- [ ] Command follows verb_noun naming convention
- [ ] --format option included for JSON output
- [ ] Comprehensive help text with examples
- [ ] Error handling covers all cases
- [ ] Exit codes follow standards
- [ ] Performance < 3 seconds
- [ ] JSON output follows structure
- [ ] Tests cover success and error cases

### Review Focus Areas

1. **Command Design**: Is the command intuitive and consistent?
2. **JSON Structure**: Does output match standards?
3. **Error Handling**: Are errors helpful and actionable?
4. **Performance**: Does execution meet time limits?
5. **Documentation**: Is help text comprehensive?
6. **Testing**: Are all paths covered?

### Approval Criteria

**✅ APPROVED**: All standards met, ready for deployment
**⚠️ CONDITIONAL**: Minor issues, fix before merge
**❌ REJECTED**: Major issues, requires rework

## 8. Migration Guidelines ✅

### From Manual MCP Tools to CLI

When migrating MCP tools to CLI commands:

1. **Preserve Functionality**: All MCP tool features in CLI
2. **Maintain Contracts**: Same parameters and responses
3. **Add CLI Features**: Progress, formatting, help
4. **Test Compatibility**: Ensure MCP server can reflect

---

**This checklist is MANDATORY for all CLI enhancement implementations.**

**Remember**: CLI quality = MCP tool quality!
