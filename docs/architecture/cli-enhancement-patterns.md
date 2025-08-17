# CLI Enhancement Patterns for MCP Integration

## 🎯 Overview

This guide documents best practices and patterns for enhancing CLI commands to provide optimal MCP tool integration through CLI reflection architecture.

## 🔧 Core Enhancement Patterns

### **Pattern 1: JSON Output Support**

Every CLI command should support `--json` flag for structured output:

```python
import click
import json
from datetime import datetime

@click.command()
@click.option('--json', 'json_output', is_flag=True,
              help='Output in JSON format for MCP integration')
def command_name(json_output):
    """Command description that becomes MCP tool description."""

    # Perform operation
    result = perform_operation()

    if json_output:
        # Structured JSON response
        output = {
            "success": True,
            "data": result,
            "timestamp": datetime.now().isoformat(),
            "command": "command-name",
            "execution_time": execution_time
        }
        click.echo(json.dumps(output, indent=2))
    else:
        # Human-readable output
        click.echo(format_human_output(result))
```

### **Pattern 2: Consistent Error Handling**

Standardized error responses for both human and JSON output:

```python
def handle_command_error(error, json_output=False):
    """Consistent error handling across all commands."""

    if json_output:
        error_response = {
            "success": False,
            "error": str(error),
            "error_type": type(error).__name__,
            "timestamp": datetime.now().isoformat(),
            "suggestions": get_error_suggestions(error)
        }
        click.echo(json.dumps(error_response, indent=2))
        sys.exit(1)
    else:
        click.secho(f"Error: {error}", fg='red', err=True)
        suggestions = get_error_suggestions(error)
        if suggestions:
            click.echo("\nSuggestions:")
            for suggestion in suggestions:
                click.echo(f"  • {suggestion}")
        sys.exit(1)

@click.command()
@click.option('--json', 'json_output', is_flag=True)
def risky_command(json_output):
    """Command that might fail."""
    try:
        result = perform_risky_operation()
        # ... handle success
    except SpecificError as e:
        handle_command_error(e, json_output)
```

### **Pattern 3: Rich Help Documentation**

Comprehensive help text that translates well to MCP tool descriptions:

```python
@click.command(
    help="""
    Execute a comprehensive operation with multiple options.

    This command performs X, Y, and Z operations on the specified target.
    It's particularly useful for scenarios where you need to...

    Examples:
        tmux-orc command-name target --option value
        tmux-orc command-name target --json
        tmux-orc command-name --all --format detailed

    Use Cases:
        • Scenario 1: When you need to...
        • Scenario 2: For managing...
        • Scenario 3: To automate...

    Note: This command requires active tmux sessions.
    """,
    short_help="Execute comprehensive operation on target"
)
def command_name():
    """Docstring provides additional context."""
    pass
```

### **Pattern 4: Flexible Argument Handling**

Design commands to work well with MCP's args/options pattern:

```python
@click.command()
@click.argument('targets', nargs=-1, required=True)  # Variable positional args
@click.option('--format', type=click.Choice(['simple', 'detailed', 'json']),
              default='simple', help='Output format')
@click.option('--filter', help='Filter results by pattern')
@click.option('--timeout', type=int, default=30, help='Operation timeout in seconds')
@click.option('--json', 'json_output', is_flag=True, help='JSON output')
def flexible_command(targets, format, filter, timeout, json_output):
    """Command with flexible argument structure."""

    # Handle multiple targets
    results = []
    for target in targets:
        result = process_target(target, timeout=timeout)
        if filter and not matches_filter(result, filter):
            continue
        results.append(result)

    # Output handling
    if json_output or format == 'json':
        output_json(results)
    elif format == 'detailed':
        output_detailed(results)
    else:
        output_simple(results)
```

### **Pattern 5: Progress and Streaming Support**

For long-running operations, provide progress feedback:

```python
import click
import time

@click.command()
@click.option('--json', 'json_output', is_flag=True)
@click.option('--stream', is_flag=True, help='Stream progress updates')
def long_operation(json_output, stream):
    """Long-running operation with progress support."""

    total_steps = 100

    if json_output and not stream:
        # Batch JSON output
        results = perform_all_steps(total_steps)
        click.echo(json.dumps({
            "success": True,
            "data": results,
            "steps_completed": total_steps
        }))

    elif json_output and stream:
        # Streaming JSON output (JSONL format)
        for i in range(total_steps):
            result = perform_step(i)
            progress_update = {
                "type": "progress",
                "step": i + 1,
                "total": total_steps,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            click.echo(json.dumps(progress_update))

    else:
        # Human-readable progress bar
        with click.progressbar(range(total_steps),
                             label='Processing',
                             show_percent=True) as bar:
            for i in bar:
                perform_step(i)
```

### **Pattern 6: Validation and Preprocessing**

Validate inputs early with helpful error messages:

```python
@click.command()
@click.argument('session_name')
@click.option('--json', 'json_output', is_flag=True)
def validated_command(session_name, json_output):
    """Command with input validation."""

    # Validation
    validation_errors = []

    if not session_name:
        validation_errors.append("Session name cannot be empty")

    if not re.match(r'^[a-zA-Z0-9_-]+$', session_name):
        validation_errors.append(
            "Session name must contain only letters, numbers, hyphens, and underscores"
        )

    if len(session_name) > 50:
        validation_errors.append("Session name must be 50 characters or less")

    if validation_errors:
        if json_output:
            click.echo(json.dumps({
                "success": False,
                "error": "Validation failed",
                "validation_errors": validation_errors,
                "timestamp": datetime.now().isoformat()
            }))
        else:
            click.secho("Validation errors:", fg='red')
            for error in validation_errors:
                click.echo(f"  • {error}")
        sys.exit(1)

    # Proceed with valid input
    execute_command(session_name)
```

## 🏗️ Command Structure Patterns

### **Pattern 7: Subcommand Organization**

Group related functionality for better MCP tool organization:

```python
@click.group()
def agent():
    """Agent management commands."""
    pass

@agent.command()
@click.argument('target')
@click.option('--json', 'json_output', is_flag=True)
def status(target, json_output):
    """Get agent status."""
    # Implementation

@agent.command()
@click.argument('target')
@click.argument('message')
@click.option('--json', 'json_output', is_flag=True)
def send(target, message, json_output):
    """Send message to agent."""
    # Implementation

# Results in MCP tools: agent_status, agent_send
```

### **Pattern 8: Common Options via Decorators**

Reduce boilerplate with shared option decorators:

```python
def common_options(f):
    """Common options for all commands."""
    f = click.option('--json', 'json_output', is_flag=True,
                    help='Output in JSON format')(f)
    f = click.option('--verbose', '-v', is_flag=True,
                    help='Verbose output')(f)
    f = click.option('--quiet', '-q', is_flag=True,
                    help='Suppress non-essential output')(f)
    return f

@click.command()
@common_options
@click.argument('target')
def command_with_common_options(target, json_output, verbose, quiet):
    """Command using common options."""
    # All commands get consistent options
```

### **Pattern 9: Context and Configuration**

Use Click context for shared state:

```python
@click.group()
@click.pass_context
def cli(ctx):
    """Main CLI group."""
    # Initialize shared context
    ctx.ensure_object(dict)
    ctx.obj['config'] = load_config()
    ctx.obj['tmux'] = TMUXManager()

@cli.command()
@click.pass_context
@click.option('--json', 'json_output', is_flag=True)
def status(ctx, json_output):
    """Get system status using shared context."""
    tmux = ctx.obj['tmux']
    config = ctx.obj['config']

    # Use shared resources
    status_info = get_status(tmux, config)
```

## 📊 Output Format Standards

### **JSON Output Schema**

Standardized JSON response format:

```python
# Success Response
{
    "success": true,
    "data": {
        // Command-specific data
    },
    "metadata": {
        "command": "command-name",
        "timestamp": "2025-08-16T23:00:00Z",
        "execution_time": 1.234,
        "version": "1.0.0"
    }
}

# Error Response
{
    "success": false,
    "error": "Error message",
    "error_type": "ErrorClassName",
    "error_code": "ERR_SPECIFIC_CODE",
    "suggestions": [
        "Try this solution",
        "Check this configuration"
    ],
    "metadata": {
        "command": "command-name",
        "timestamp": "2025-08-16T23:00:00Z"
    }
}

# List/Collection Response
{
    "success": true,
    "data": {
        "items": [...],
        "total_count": 42,
        "filtered_count": 10,
        "page": 1,
        "page_size": 10
    },
    "metadata": {...}
}
```

### **Human-Readable Output Patterns**

Consistent formatting for terminal output:

```python
def format_agent_list(agents):
    """Format agent list for human consumption."""
    if not agents:
        click.echo("No agents found.")
        return

    # Header
    click.secho("Active Agents", bold=True)
    click.echo("=" * 50)

    # Table format
    for agent in agents:
        status_color = {
            'active': 'green',
            'idle': 'yellow',
            'error': 'red'
        }.get(agent['status'], 'white')

        click.echo(
            f"{agent['name']:20} "
            f"{click.style(agent['status']:10, fg=status_color)} "
            f"{agent['last_activity']}"
        )

    # Summary
    click.echo("=" * 50)
    click.echo(f"Total: {len(agents)} agents")
```

## 🧪 Testing CLI Enhancements

### **Testing JSON Output**

```python
def test_command_json_output(runner):
    """Test JSON output format."""
    result = runner.invoke(command_name, ['--json'])

    assert result.exit_code == 0

    # Parse JSON
    output = json.loads(result.output)

    # Validate structure
    assert output['success'] is True
    assert 'data' in output
    assert 'metadata' in output
    assert output['metadata']['command'] == 'command-name'
```

### **Testing Error Handling**

```python
def test_command_error_handling(runner):
    """Test error handling in JSON mode."""
    result = runner.invoke(command_name, ['invalid-arg', '--json'])

    assert result.exit_code == 1

    output = json.loads(result.output)
    assert output['success'] is False
    assert 'error' in output
    assert 'error_type' in output
```

## 🚀 Migration Checklist

When enhancing existing CLI commands:

1. **Add JSON Support**
   - [ ] Add `--json` flag
   - [ ] Implement JSON output formatting
   - [ ] Test JSON structure validity

2. **Standardize Error Handling**
   - [ ] Use consistent error response format
   - [ ] Include helpful error suggestions
   - [ ] Ensure proper exit codes

3. **Improve Help Text**
   - [ ] Write comprehensive help with examples
   - [ ] Add short_help for tool descriptions
   - [ ] Include use cases and scenarios

4. **Validate Inputs**
   - [ ] Add input validation
   - [ ] Provide clear validation errors
   - [ ] Support both JSON and human error output

5. **Test Enhancement**
   - [ ] Test JSON output format
   - [ ] Test error scenarios
   - [ ] Verify MCP tool generation

## 📚 Example: Full Command Enhancement

Before enhancement:
```python
@click.command()
@click.argument('session')
def basic_command(session):
    """Basic command."""
    result = do_something(session)
    click.echo(f"Result: {result}")
```

After enhancement:
```python
@click.command(
    help="""
    Execute operation on specified session.

    Examples:
        tmux-orc enhanced-command my-session
        tmux-orc enhanced-command my-session --json
        tmux-orc enhanced-command my-session --timeout 60
    """,
    short_help="Execute operation on session"
)
@click.argument('session')
@click.option('--timeout', type=int, default=30, help='Operation timeout')
@click.option('--json', 'json_output', is_flag=True, help='JSON output')
def enhanced_command(session, timeout, json_output):
    """Execute operation with enhanced features."""
    start_time = time.time()

    try:
        # Validation
        if not session or not session.strip():
            raise ValueError("Session name cannot be empty")

        # Execute
        result = do_something(session, timeout=timeout)
        execution_time = time.time() - start_time

        # Output
        if json_output:
            click.echo(json.dumps({
                "success": True,
                "data": {
                    "session": session,
                    "result": result
                },
                "metadata": {
                    "command": "enhanced-command",
                    "execution_time": execution_time,
                    "timestamp": datetime.now().isoformat()
                }
            }, indent=2))
        else:
            click.echo(f"✅ Operation completed for session: {session}")
            click.echo(f"Result: {result}")
            click.echo(f"Execution time: {execution_time:.2f}s")

    except Exception as e:
        if json_output:
            click.echo(json.dumps({
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "metadata": {
                    "command": "enhanced-command",
                    "timestamp": datetime.now().isoformat()
                }
            }, indent=2))
        else:
            click.secho(f"❌ Error: {e}", fg='red', err=True)
        sys.exit(1)
```

## 🎯 Key Principles

1. **CLI First**: The CLI command is the source of truth
2. **Consistent JSON**: All commands follow same JSON schema
3. **Rich Help**: Comprehensive help becomes good MCP tool descriptions
4. **Error Clarity**: Clear errors in both human and JSON formats
5. **Progressive Enhancement**: Add features without breaking existing usage

By following these patterns, every CLI enhancement automatically improves the MCP tools generated through CLI reflection.
