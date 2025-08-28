# CLI Enhancement Coding Standards

## Overview
This document establishes coding standards for the Tmux Orchestrator CLI reflection architecture. These standards ensure maintainable, secure, and high-quality CLI code that integrates seamlessly with the MCP tool generation system.

## Core Architecture Principles

### 1. CLI Reflection Architecture
- **Single Source of Truth**: CLI commands are the authoritative implementation
- **Zero Dual Implementation**: Never manually create MCP tools that duplicate CLI functionality
- **Dynamic Discovery**: Use `tmux-orc reflect --format json` for runtime command structure discovery
- **Automatic Tool Generation**: Every CLI command becomes an MCP tool via reflection

### 2. Separation of Concerns
```python
# ✅ CORRECT: CLI delegates to business logic
@click.command()
def spawn_agent(name: str, session: str):
    """Spawn a new agent."""
    result = AgentOperations.spawn(name, session)
    display_result(result)

# ❌ INCORRECT: Business logic in CLI
@click.command()
def spawn_agent(name: str, session: str):
    """Spawn a new agent."""
    subprocess.run(['tmux', 'new-session', ...])  # Business logic in CLI
```

## Command Structure Standards

### 1. Required Command Elements
Every CLI command MUST include:

```python
@click.command()
@click.option('--json', is_flag=True, help='Output in JSON format')
@click.pass_context
def command_name(ctx: click.Context, json: bool, ...):
    """
    Brief description of what the command does.

    Examples:
        tmux-orc command-name --option value
        tmux-orc command-name target:session:1 --json

    Args:
        param1: Description of parameter
        param2: Description of parameter
    """
    try:
        # Delegate to business logic
        result = BusinessLogic.operation(...)

        # Format output
        if json:
            click.echo(format_json_response(result))
        else:
            display_formatted_result(result)

    except Exception as e:
        handle_error(e, json=json)
```

### 2. JSON Output Standardization
All commands supporting `--json` MUST use this format:

```python
# Success Response
{
    "success": true,
    "data": {...},
    "timestamp": "2025-08-17T12:34:56Z",
    "command": "command-name",
    "execution_time": 1.23
}

# Error Response
{
    "success": false,
    "error": "Human readable message",
    "error_type": "ErrorClassName",
    "timestamp": "2025-08-17T12:34:56Z",
    "command": "command-name",
    "execution_time": 0.45
}
```

### 3. Help Text Standards
```python
@click.command()
def command_name():
    """
    Brief one-line description (used in command listings).

    Detailed description explaining what the command does,
    when to use it, and any important considerations.

    Examples:
        # Basic usage
        tmux-orc command-name basic-arg

        # Advanced usage with options
        tmux-orc command-name advanced-arg --option value --json

        # Real-world scenario
        tmux-orc command-name session:1 --briefing "Custom briefing"

    Args:
        arg1: Clear description with expected format
        arg2: Description including valid values or ranges

    Notes:
        Any important warnings, limitations, or prerequisites.
    """
```

## Input Validation Standards

### 1. Target Format Validation
```python
from tmux_orchestrator.utils.validation import validate_target_format

@click.argument('target')
def command_with_target(target: str):
    """Command that accepts session:window format."""
    validate_target_format(target)  # Raises ValidationError if invalid
    # Continue with validated target
```

### 2. Input Sanitization
```python
from tmux_orchestrator.utils.tmux import TMUXManager

def safe_command_execution(user_input: str):
    """Example of proper input sanitization."""
    tmux = TMUXManager()

    # Built-in validation and sanitization
    sanitized = tmux._sanitize_input(user_input)
    validated = tmux._validate_input(sanitized)

    # Safe execution
    return tmux.execute_command(['tmux', 'command', validated])
```

### 3. Required Validations
All commands MUST validate:
- Target format (session:window) where applicable
- File paths (prevent directory traversal)
- Agent names (alphanumeric + hyphens only)
- Session names (valid tmux session naming)
- JSON input structure

## Error Handling Standards

### 1. Consistent Error Types
```python
from tmux_orchestrator.cli.errors import (
    CLIError,
    ValidationError,
    TMUXError,
    AgentError
)

def handle_error(error: Exception, json: bool = False) -> None:
    """Standardized error handling."""
    if isinstance(error, ValidationError):
        error_type = "ValidationError"
        message = f"Invalid input: {error}"
    elif isinstance(error, TMUXError):
        error_type = "TMUXError"
        message = f"TMUX operation failed: {error}"
    elif isinstance(error, AgentError):
        error_type = "AgentError"
        message = f"Agent operation failed: {error}"
    else:
        error_type = "UnknownError"
        message = f"Unexpected error: {error}"

    if json:
        response = {
            "success": false,
            "error": message,
            "error_type": error_type,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        click.echo(json.dumps(response))
    else:
        console.print(f"[red]Error:[/red] {message}")

    sys.exit(1)
```

### 2. Graceful Degradation
```python
def robust_command_implementation():
    """Example of graceful degradation."""
    try:
        # Primary functionality
        return primary_operation()
    except TMUXError:
        # Fallback to alternative approach
        console.print("[yellow]Warning:[/yellow] Falling back to alternative method")
        return fallback_operation()
    except Exception as e:
        # Last resort graceful failure
        handle_error(e)
```

## Security Standards

### 1. Command Execution Security
```python
# ✅ CORRECT: Safe subprocess execution
import subprocess
import shlex

def safe_execution(command_args: List[str]):
    """Safe subprocess execution."""
    try:
        result = subprocess.run(
            command_args,  # List format prevents injection
            capture_output=True,
            text=True,
            timeout=30,  # Always set timeouts
            check=True
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        raise TMUXError("Command timed out")
    except subprocess.CalledProcessError as e:
        raise TMUXError(f"Command failed: {e.stderr}")

# ❌ INCORRECT: Shell injection vulnerability
def unsafe_execution(user_input: str):
    subprocess.run(f"tmux {user_input}", shell=True)  # NEVER DO THIS
```

### 2. Input Sanitization Requirements
```python
def sanitize_user_input(user_input: str) -> str:
    """Required sanitization for all user inputs."""
    # Remove null bytes
    sanitized = user_input.replace('\0', '')

    # Validate length
    if len(sanitized) > 1000:
        raise ValidationError("Input too long")

    # Validate characters (context-dependent)
    if not re.match(r'^[a-zA-Z0-9_-]+$', sanitized):
        raise ValidationError("Invalid characters in input")

    return sanitized
```

### 3. Output Sanitization
```python
def sanitize_output(output: str) -> str:
    """Sanitize output to prevent information leakage."""
    # Remove sensitive paths
    sanitized = re.sub(r'/home/[^/\s]+', '/home/USER', output)

    # Remove API keys or tokens
    sanitized = re.sub(r'sk-[a-zA-Z0-9]+', 'sk-***', sanitized)

    return sanitized
```

## Performance Standards

### 1. Response Time Requirements
- CLI commands MUST complete within 3 seconds for interactive use
- Long-running operations MUST provide progress indicators
- Operations over 10 seconds MUST be asynchronous with status checking

### 2. Resource Usage
```python
import resource
import time

def performance_monitored_command():
    """Example of performance monitoring."""
    start_time = time.time()
    start_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    try:
        result = operation()

        execution_time = time.time() - start_time
        memory_used = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss - start_memory

        # Log performance metrics
        if execution_time > 3.0:
            console.print(f"[yellow]Warning:[/yellow] Command took {execution_time:.2f}s")

        return result
    except Exception:
        # Always log timing even on failure
        execution_time = time.time() - start_time
        console.print(f"[red]Command failed after {execution_time:.2f}s[/red]")
        raise
```

## Testing Standards

### 1. Required Test Coverage
Every CLI command MUST have:
- Unit tests for business logic
- Integration tests with mocked TMUXManager
- JSON output validation tests
- Error handling tests
- Performance tests

### 2. Test Structure
```python
import pytest
from click.testing import CliRunner
from tmux_orchestrator.cli.command_module import command_name

class TestCommandName:
    def test_successful_execution(self):
        """Test successful command execution."""
        runner = CliRunner()
        result = runner.invoke(command_name, ['valid-arg'])

        assert result.exit_code == 0
        assert 'expected output' in result.output

    def test_json_output(self):
        """Test JSON output format."""
        runner = CliRunner()
        result = runner.invoke(command_name, ['valid-arg', '--json'])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['success'] is True
        assert 'data' in data

    def test_error_handling(self):
        """Test error handling."""
        runner = CliRunner()
        result = runner.invoke(command_name, ['invalid-arg'])

        assert result.exit_code != 0
        assert 'Error:' in result.output

    @pytest.mark.performance
    def test_performance(self):
        """Test command performance."""
        start_time = time.time()
        runner = CliRunner()
        result = runner.invoke(command_name, ['valid-arg'])
        execution_time = time.time() - start_time

        assert execution_time < 3.0
        assert result.exit_code == 0
```

## MCP Integration Standards

### 1. MCP Tool Generation
CLI commands automatically become MCP tools. Ensure:
- Help text is comprehensive (becomes tool description)
- Parameter descriptions are clear (become tool parameter descriptions)
- JSON output is well-structured (becomes tool response format)

### 2. MCP-Friendly Design
```python
@click.command()
@click.argument('target', metavar='SESSION:WINDOW')
@click.option('--briefing', help='Additional context to add to briefing')
@click.option('--json', is_flag=True, help='Output in JSON format')
def mcp_friendly_command(target: str, extend: str, json: bool):
    """
    MCP-friendly command with clear descriptions.

    This command does X, Y, and Z. It's useful when you need to
    accomplish specific goals in specific contexts.

    Args:
        target: Session and window in format session:window
        extend: Optional additional context string
        json: Return structured JSON response
    """
    # Implementation follows all standards above
```

## Code Quality Checklist

Before submitting CLI enhancements:

### Pre-Commit Checklist
- [ ] Command follows naming conventions
- [ ] Help text is comprehensive with examples
- [ ] JSON output follows standard format
- [ ] Input validation implemented
- [ ] Error handling follows standards
- [ ] Security considerations addressed
- [ ] Performance requirements met
- [ ] Tests written and passing
- [ ] Type hints added
- [ ] Docstrings complete

### Review Checklist
- [ ] No business logic in CLI layer
- [ ] Proper separation of concerns
- [ ] Consistent error handling
- [ ] Security validation present
- [ ] Performance within limits
- [ ] Test coverage adequate
- [ ] MCP integration friendly
- [ ] Documentation complete

## Tools and Automation

### 1. Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: cli-standards-check
        name: CLI Standards Check
        entry: python scripts/check-cli-standards.py
        language: python
        files: ^tmux_orchestrator/cli/.*\.py$
```

### 2. Performance Monitoring
```python
# Add to conftest.py for automatic performance testing
@pytest.fixture(autouse=True)
def monitor_cli_performance(request):
    """Automatically monitor CLI command performance."""
    if 'cli' in request.module.__name__:
        start_time = time.time()
        yield
        execution_time = time.time() - start_time
        if execution_time > 3.0:
            pytest.fail(f"CLI command exceeded 3s limit: {execution_time:.2f}s")
    else:
        yield
```

## Documentation Requirements

### 1. ADR Documentation
Significant CLI changes require Architecture Decision Records in `docs/architecture/`.

### 2. API Documentation
CLI reflection automatically generates API documentation. Ensure help text is:
- Comprehensive
- Example-rich
- Accurate
- User-friendly

This document serves as the foundation for maintaining high-quality, secure, and maintainable CLI enhancements in the Tmux Orchestrator project.
