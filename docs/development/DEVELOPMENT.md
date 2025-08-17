# Development Guide

This project uses `invoke` for all development tasks. This ensures consistency between local development and CI/CD.

## Quick Start

```bash
# Install dependencies and setup
poetry run invoke install

# Run all CI/CD checks locally (identical to GitHub Actions)
poetry run invoke ci

# Quick check before committing
poetry run invoke quick
# or use the alias
poetry run invoke q
```

## 🚨 CLI Reflection Development - CRITICAL KNOWLEDGE

**EVERY CLI ENHANCEMENT AUTOMATICALLY IMPROVES AI AGENT CAPABILITIES**

The Tmux Orchestrator uses CLI Reflection architecture where CLI commands are the single source of truth for all functionality, including MCP tools used by Claude agents.

### **Knowledge Transfer Essentials**

#### **What This Means for Developers**
1. **CLI First**: Always implement in CLI commands, never manually create MCP tools
2. **Automatic MCP**: Every CLI command automatically becomes an MCP tool for Claude
3. **JSON Required**: All CLI commands MUST support `--json` flag for MCP compatibility
4. **Single Codebase**: No dual implementation - CLI changes automatically update AI capabilities

#### **Architecture Impact**
```
Your CLI Enhancement
    ↓
Automatic MCP Tool Update (via reflection)
    ↓
Enhanced Claude Agent Capabilities
    ↓
Improved AI Agent Collaboration
```

### **Mandatory CLI Command Patterns**

#### **1. JSON Output Support (REQUIRED)**
```python
@click.option('--json', 'json_output', is_flag=True, help='Output in JSON format')
def your_command(json_output):
    try:
        result = perform_operation()
        if json_output:
            click.echo(json.dumps({
                "success": True,
                "data": result,
                "timestamp": datetime.now().isoformat(),
                "command": "your-command"
            }))
        else:
            click.echo(f"Operation completed: {result}")
    except Exception as e:
        if json_output:
            click.echo(json.dumps({
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": datetime.now().isoformat(),
                "command": "your-command"
            }))
        else:
            click.secho(f"Error: {e}", fg='red')
        sys.exit(1)
```

#### **2. Discovery Commands (Use These, Never Hardcode)**
```bash
# ALWAYS use these to understand current CLI structure
tmux-orc reflect                    # Full CLI tree view
tmux-orc reflect --format json     # JSON structure for tools
tmux-orc [command] --help          # Specific command help

# NEVER hardcode CLI examples in docs or code
# CLI structure evolves, use reflection commands
```

#### **3. MCP Integration Testing**
```bash
# Test that your CLI enhancement works with MCP
tmux-orc server mcp-serve           # Start MCP server

# In Claude Code: Your new command is automatically available
# No additional MCP development required
```

#### **4. Comprehensive Help Text (Claude Uses This)**
```python
@click.command(
    help="""
    Clear description of what this command does.

    This becomes the MCP tool description that Claude sees.
    Be comprehensive and include examples.

    Examples:
        tmux-orc your-command arg1 arg2        # Basic usage
        tmux-orc your-command --option value   # With options
        tmux-orc your-command --json           # JSON output

    Use Cases:
        • When you need to...
        • For managing...
        • To automate...
    """,
    short_help="Brief description for tool listings"
)
```

### **Development Workflow**

#### **Before Writing Code**
```bash
# 1. Understand current CLI structure
tmux-orc reflect

# 2. Check if functionality already exists
tmux-orc [command] --help

# 3. Follow existing patterns
```

#### **While Developing**
```bash
# 1. Test CLI command manually
tmux-orc your-new-command --json

# 2. Verify JSON output format
# 3. Test error handling
```

#### **After Implementation**
```bash
# 1. Test MCP integration
tmux-orc server mcp-serve

# 2. Verify in Claude Code
# Your command should appear as MCP tool automatically

# 3. Test end-to-end AI agent usage
```

### **Critical Rules**

1. **NEVER create manual MCP tools** - CLI Reflection handles this automatically
2. **ALWAYS add `--json` support** - Required for MCP compatibility
3. **ALWAYS use `tmux-orc reflect`** - Never hardcode CLI structure
4. **ALWAYS test MCP integration** - Verify Claude can use your command
5. **FOCUS on CLI quality** - MCP tools inherit CLI behavior exactly

### **Knowledge Transfer Links**
- [CLI Enhancement Patterns](../architecture/cli-enhancement-patterns.md) - Detailed implementation patterns
- [CLI Reflection Architecture](../architecture/cli-reflection-mcp-architecture.md) - Complete architecture overview
- [MCP Integration Guide](../architecture/mcp-integration-complete.md) - MCP server setup and testing

## Available Tasks

### Core Development Tasks

| Command | Description | Alias |
|---------|-------------|-------|
| `invoke test` | Run all tests | `invoke t` |
| `invoke test --verbose --coverage` | Run tests with coverage report | |
| `invoke lint` | Run linting checks | `invoke l` |
| `invoke lint --fix` | Run linting with auto-fix | |
| `invoke format` | Format code | `invoke f` |
| `invoke format --check` | Check formatting without changes | |
| `invoke type-check` | Run MyPy type checking | |
| `invoke security` | Run Bandit security scan | |

### Workflow Commands

| Command | Description |
|---------|-------------|
| `invoke check` | Run all checks (lint, format, security, type, test) |
| `invoke ci` | Run exact CI/CD simulation locally |
| `invoke quick` | Quick checks before committing |
| `invoke full` | Clean, format, and run all checks |
| `invoke pre-commit` | Run pre-commit hooks on all files |

### Utility Commands

| Command | Description |
|---------|-------------|
| `invoke clean` | Clean up generated files |
| `invoke update-deps` | Update dependencies |
| `invoke show-errors` | Show current MyPy errors |
| `invoke serve-docs` | Serve documentation locally |
| `invoke test-component <component>` | Test specific component |

## Component Testing

Test specific components:
```bash
invoke test-component cli
invoke test-component core
invoke test-component server
invoke test-component sdk

# Test specific module
invoke test-component cli --module setup
```

## CI/CD Parity

The `invoke ci` command runs the exact same checks as GitHub Actions:
1. Ruff linting
2. Ruff formatting check
3. Bandit security scan
4. MyPy type checking
5. Pytest tests

This ensures your local environment produces identical results to CI/CD.

## Pre-commit Hooks

Pre-commit hooks are automatically installed with `invoke install`. They run:
- Ruff formatting
- Ruff linting
- MyPy type checking
- Bandit security scan
- General file checks (trailing whitespace, file size, etc.)

## Development Workflow

1. **Before starting work:**
   ```bash
   poetry run invoke install  # Ensure dependencies are up to date
   ```

2. **During development:**
   ```bash
   poetry run invoke quick   # Quick checks while coding
   poetry run invoke test-component <component>  # Test specific areas
   ```

3. **Before committing:**
   ```bash
   poetry run invoke check   # Run all checks
   # or
   poetry run invoke ci      # Match exact CI/CD behavior
   ```

4. **Formatting and fixes:**
   ```bash
   poetry run invoke format  # Auto-format code
   poetry run invoke lint --fix  # Auto-fix linting issues
   ```

## Tips

- Use short aliases (`t`, `f`, `l`, `q`) for frequently used commands
- Run `invoke --list` to see all available tasks
- Run `invoke --help <task>` for detailed help on any task
- The `invoke ci` command ensures your code will pass GitHub Actions

## MyPy Progress

Current MyPy status: ~4 errors remaining (down from 123!)
```bash
# Check current errors
poetry run invoke show-errors
```
