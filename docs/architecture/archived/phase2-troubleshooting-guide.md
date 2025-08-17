# Phase 2 Troubleshooting Guide: Clean Slate MCP Implementation

## Overview

This guide addresses common issues and architectural conflicts encountered during Phase 2 MCP implementation, with special focus on resolving the manual tools vs. dynamic CLI introspection conflict.

## 🚨 Critical Architectural Issue: Manual vs Auto-Generation Conflict

### Problem Description

The current implementation has a **fundamental architectural conflict**:

1. **Manual Tools**: `tmux_orchestrator/mcp/tools/agent_management.py` contains manually implemented MCP tools
2. **Auto-Generation**: `tmux_orchestrator/mcp/auto_generator.py` exists but isn't being used
3. **Server Conflict**: `server.py` imports manual tools instead of using auto-generation
4. **Dual Registration**: This would cause tools to be registered twice with different implementations

### Solution: Clean Slate Approach

**RECOMMENDED**: Implement pure auto-generation architecture to fully embrace CLI introspection.

#### Step 1: Backup and Remove Manual Tools

```bash
# Backup existing manual tools
mkdir -p /tmp/mcp-backup
cp -r tmux_orchestrator/mcp/tools/ /tmp/mcp-backup/

# Remove manual tool implementations
rm tmux_orchestrator/mcp/tools/agent_management.py
rm tmux_orchestrator/mcp/tools/team_operations.py
rm tmux_orchestrator/mcp/tools/monitoring.py
```

#### Step 2: Update Server to Use Auto-Generation

Replace `tmux_orchestrator/mcp/server.py` with pure auto-generation:

```python
"""Dynamic MCP server for tmux-orchestrator using CLI introspection.

This module creates a FastMCP server that automatically generates tools
from tmux-orc CLI commands, eliminating dual-implementation maintenance.
"""

import asyncio
import logging
from fastmcp import FastMCP

# Import the auto-generator
from tmux_orchestrator.mcp.auto_generator import auto_generate_mcp_tools

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastMCP instance
mcp = FastMCP("tmux-orchestrator")

async def initialize_server():
    """Initialize server with auto-generated tools."""
    logger.info("Starting dynamic MCP tool generation...")

    # Auto-generate all tools from CLI introspection
    generated_tools = auto_generate_mcp_tools(mcp)

    logger.info(f"Successfully generated {len(generated_tools)} MCP tools from CLI")
    for tool_name in generated_tools.keys():
        logger.info(f"  - {tool_name}")

    return generated_tools

async def main():
    """Run the FastMCP server."""
    logger.info("Starting FastMCP tmux-orchestrator server with auto-generation...")

    # Initialize auto-generated tools
    await initialize_server()

    # Start the server
    await mcp.run_stdio_async()

if __name__ == "__main__":
    asyncio.run(main())

__all__ = ["mcp", "main"]
```

#### Step 3: Update CLI Integration

Ensure `tmux_orchestrator/cli/__init__.py` properly exposes the CLI for introspection:

```python
"""CLI module with proper introspection support."""

import click
from tmux_orchestrator.cli.commands import *

# Ensure the CLI group is properly accessible for introspection
@click.group()
def cli():
    """Tmux Orchestrator CLI."""
    pass

# Register all commands dynamically
# This ensures the auto_generator can introspect all available commands
def register_all_commands():
    """Register all CLI commands for introspection."""
    # Import and register all command modules
    from tmux_orchestrator.cli.commands import (
        agent_commands,
        team_commands,
        monitor_commands,
        # Add other command modules
    )

    # Each command module should register its commands with the main CLI group
    agent_commands.register_commands(cli)
    team_commands.register_commands(cli)
    monitor_commands.register_commands(cli)

# Initialize commands
register_all_commands()

__all__ = ["cli"]
```

## Common Phase 2 Issues and Solutions

### Issue 1: Tool Registration Conflicts

**Symptoms:**
- `RuntimeError: Tool 'spawn_agent' already registered`
- Duplicate tool definitions in MCP client
- Inconsistent tool behavior

**Root Cause:**
Both manual tools and auto-generated tools trying to register the same tool names.

**Solution:**
```python
# Check for existing tools before registration
def safe_tool_registration(mcp_server, tool_name, tool_func):
    """Safely register MCP tools to avoid conflicts."""
    if hasattr(mcp_server, '_tools') and tool_name in mcp_server._tools:
        logger.warning(f"Tool '{tool_name}' already registered, skipping")
        return False

    # Register the tool
    mcp_server.tool(name=tool_name)(tool_func)
    return True
```

### Issue 2: CLI Command Discovery Failures

**Symptoms:**
- `AttributeError: 'NoneType' object has no attribute 'commands'`
- Auto-generator failing to find CLI commands
- Empty tool generation

**Root Cause:**
CLI group not properly initialized or circular import issues.

**Solution:**
```python
# Robust CLI discovery with error handling
def get_cli_group_safely():
    """Get CLI group with proper error handling."""
    try:
        from tmux_orchestrator.cli import cli as root_cli_group

        # Validate CLI group
        if not hasattr(root_cli_group, 'commands'):
            raise ImportError("CLI group missing commands attribute")

        if not root_cli_group.commands:
            logger.warning("CLI group has no registered commands")

        return root_cli_group

    except ImportError as e:
        logger.error(f"Failed to import CLI group: {e}")
        # Return a dummy group for graceful degradation
        return click.Group()
```

### Issue 3: Parameter Conversion Errors

**Symptoms:**
- `TypeError: Object of type 'click.Option' is not JSON serializable`
- MCP schema validation failures
- Parameter type mismatches

**Root Cause:**
Click parameter types not properly converted to JSON schema.

**Solution:**
```python
def convert_click_param_safely(param):
    """Safely convert Click parameters to JSON schema."""
    try:
        # Enhanced type mapping
        type_mapping = {
            click.types.StringParamType: "string",
            click.types.IntParamType: "integer",
            click.types.FloatParamType: "number",
            click.types.BoolParamType: "boolean",
            click.types.UUIDParamType: "string",
            click.types.DateTime: "string",
        }

        param_type = type(param.type)
        json_type = type_mapping.get(param_type, "string")

        schema = {
            "type": json_type,
            "description": param.help or f"Parameter: {param.name}"
        }

        # Handle special cases
        if isinstance(param.type, click.types.Choice):
            schema["enum"] = list(param.type.choices)

        if isinstance(param.type, click.types.Path):
            schema["format"] = "path"

        if param.default is not None and param.default != ():
            # Ensure default is JSON serializable
            try:
                import json
                json.dumps(param.default)
                schema["default"] = param.default
            except (TypeError, ValueError):
                logger.warning(f"Skipping non-serializable default for {param.name}")

        return schema

    except Exception as e:
        logger.error(f"Failed to convert parameter {param.name}: {e}")
        return {
            "type": "string",
            "description": f"Parameter: {param.name} (conversion failed)"
        }
```

### Issue 4: Subprocess Execution Failures

**Symptoms:**
- `subprocess.CalledProcessError: Command 'tmux-orc' returned non-zero exit status`
- Tool execution timeouts
- Missing JSON output from CLI commands

**Root Cause:**
CLI commands not properly supporting JSON output or subprocess environment issues.

**Solution:**
```python
async def execute_cli_command_robust(command_parts, timeout=60):
    """Execute CLI commands with robust error handling."""
    try:
        import subprocess
        import shutil
        import os

        # Verify tmux-orc is available
        if not shutil.which("tmux-orc"):
            return {
                "success": False,
                "error": "tmux-orc command not found in PATH",
                "suggestion": "Ensure tmux-orchestrator is properly installed"
            }

        # Prepare environment
        env = os.environ.copy()
        env["PYTHONPATH"] = os.getcwd()  # Ensure module can be found

        # Add --json flag if not present and command supports it
        if "--json" not in command_parts and _command_supports_json(command_parts[1]):
            command_parts = command_parts + ["--json"]

        # Execute with timeout
        result = subprocess.run(
            command_parts,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            cwd=os.getcwd()
        )

        # Parse result
        output_data = {}
        if result.stdout:
            try:
                import json
                output_data = json.loads(result.stdout)
            except json.JSONDecodeError:
                # Fallback to plain text
                output_data = {"output": result.stdout}

        return {
            "success": result.returncode == 0,
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "parsed_output": output_data
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"Command timed out after {timeout} seconds",
            "suggestion": "Try increasing timeout or check for hanging processes"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }

def _command_supports_json(command_name):
    """Check if a command supports JSON output."""
    json_supported_commands = {
        "list", "status", "reflect", "spawn", "send", "kill",
        "team-status", "monitor-status", "agent-status"
    }
    return command_name in json_supported_commands
```

### Issue 5: Dependency Injection Failures

**Symptoms:**
- `ValueError: tmux must be TMUXManager instance`
- Service container resolution failures
- Missing dependency instances

**Root Cause:**
Handlers expecting dependency injection but getting None or wrong types.

**Solution:**
```python
def create_service_container():
    """Create properly configured service container."""
    from tmux_orchestrator.core.monitoring.service_container import ServiceContainer
    from tmux_orchestrator.utils.tmux import TMUXManager
    from tmux_orchestrator.core.config import Config

    container = ServiceContainer()

    # Register core services with validation
    try:
        tmux_manager = TMUXManager()
        container.register(TMUXManager, lambda: tmux_manager)

        config = Config.load()
        container.register(Config, lambda: config)

        logger = logging.getLogger(__name__)
        container.register(logging.Logger, lambda: logger)

        return container

    except Exception as e:
        logger.error(f"Failed to create service container: {e}")
        raise RuntimeError(f"Service container initialization failed: {e}")

# Use in handlers
def get_handler_with_dependencies():
    """Get handler instance with proper dependencies."""
    container = create_service_container()

    return TeamHandlers(
        tmux=container.resolve(TMUXManager),
        config=container.resolve(Config),
        logger=container.resolve(logging.Logger)
    )
```

## Migration Strategy: Manual to Auto-Generation

### Phase 1: Assessment
```bash
# Check current tool registrations
python -c "
from tmux_orchestrator.mcp.server import mcp
print('Currently registered tools:')
for tool_name in getattr(mcp, '_tools', {}):
    print(f'  - {tool_name}')
"

# Test CLI introspection
python -c "
from tmux_orchestrator.cli import cli
print('Available CLI commands:')
for cmd_name in cli.commands:
    print(f'  - {cmd_name}')
"
```

### Phase 2: Parallel Testing
```python
# Create test script to compare implementations
def compare_manual_vs_auto():
    """Compare manual tools vs auto-generated tools."""

    # Test manual implementation
    from tmux_orchestrator.mcp.tools.agent_management import spawn_agent as manual_spawn

    # Test auto-generated implementation
    from tmux_orchestrator.mcp.auto_generator import auto_generate_mcp_tools
    from fastmcp import FastMCP

    test_mcp = FastMCP("test")
    auto_tools = auto_generate_mcp_tools(test_mcp)

    # Compare results
    print("Manual vs Auto-Generated Comparison:")
    print(f"Manual tools: {len(['spawn_agent', 'send_message', 'get_agent_status', 'kill_agent'])}")
    print(f"Auto-generated tools: {len(auto_tools)}")

    return auto_tools
```

### Phase 3: Cutover
```python
# Migration script
def migrate_to_auto_generation():
    """Migrate from manual to auto-generation."""

    # 1. Backup manual implementations
    backup_manual_tools()

    # 2. Update server configuration
    update_server_to_auto_generation()

    # 3. Test auto-generated tools
    test_results = test_auto_generated_tools()

    # 4. Rollback if issues found
    if not test_results["success"]:
        rollback_to_manual()
        raise RuntimeError(f"Migration failed: {test_results['error']}")

    print("Successfully migrated to auto-generation!")
```

## Testing and Validation

### Auto-Generation Testing
```python
# Test auto-generation functionality
def test_auto_generation():
    """Comprehensive test of auto-generation system."""

    from tmux_orchestrator.mcp.auto_generator import ClickToMCPGenerator
    from fastmcp import FastMCP

    # Create test MCP server
    test_mcp = FastMCP("test-server")
    generator = ClickToMCPGenerator(test_mcp)

    # Generate tools
    tools = generator.generate_all_tools()

    # Validate generation
    assert len(tools) > 0, "No tools generated"

    # Test specific tool generation
    required_tools = ["spawn", "send", "status", "kill"]
    for tool in required_tools:
        assert any(tool in name for name in tools.keys()), f"Missing {tool} tool"

    # Test tool execution (mock)
    for tool_name, tool_info in tools.items():
        assert "function" in tool_info, f"Tool {tool_name} missing function"
        assert "input_schema" in tool_info, f"Tool {tool_name} missing schema"

    print(f"✅ Auto-generation test passed: {len(tools)} tools generated")
    return True
```

### CLI Integration Testing
```python
def test_cli_integration():
    """Test CLI integration with MCP tools."""

    # Test CLI reflection
    import subprocess
    result = subprocess.run(["tmux-orc", "reflect", "--format", "json"],
                          capture_output=True, text=True)

    assert result.returncode == 0, f"CLI reflection failed: {result.stderr}"

    # Parse CLI structure
    import json
    cli_structure = json.loads(result.stdout)

    # Validate CLI structure
    assert "commands" in cli_structure, "CLI structure missing commands"
    assert len(cli_structure["commands"]) > 0, "No CLI commands found"

    print(f"✅ CLI integration test passed: {len(cli_structure['commands'])} commands found")
    return True
```

## Performance Optimization

### Tool Generation Caching
```python
class CachedMCPGenerator:
    """Cached version of MCP tool generator for better performance."""

    def __init__(self, mcp_server, cache_duration=300):  # 5 min cache
        self.mcp = mcp_server
        self.cache_duration = cache_duration
        self._cache = {}
        self._cache_timestamp = 0

    def generate_all_tools(self):
        """Generate tools with caching."""
        import time

        current_time = time.time()

        # Check cache validity
        if (current_time - self._cache_timestamp) < self.cache_duration and self._cache:
            logger.info("Using cached MCP tools")
            return self._cache

        # Generate fresh tools
        generator = ClickToMCPGenerator(self.mcp)
        tools = generator.generate_all_tools()

        # Update cache
        self._cache = tools
        self._cache_timestamp = current_time

        logger.info(f"Generated and cached {len(tools)} MCP tools")
        return tools
```

## Monitoring and Debugging

### Enable Debug Logging
```python
import logging

# Enable detailed logging for troubleshooting
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Enable specific loggers
loggers = [
    'tmux_orchestrator.mcp.auto_generator',
    'tmux_orchestrator.mcp.server',
    'tmux_orchestrator.cli',
    'fastmcp'
]

for logger_name in loggers:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
```

### Health Check Script
```python
def health_check():
    """Comprehensive health check for MCP implementation."""

    checks = {
        "CLI Available": check_cli_available(),
        "Auto-Generator Working": check_auto_generator(),
        "MCP Server Starting": check_mcp_server(),
        "Tool Generation": check_tool_generation(),
        "No Conflicts": check_no_conflicts()
    }

    print("🏥 MCP Health Check Results:")
    for check_name, result in checks.items():
        status = "✅" if result["success"] else "❌"
        print(f"  {status} {check_name}: {result['message']}")

    overall_health = all(check["success"] for check in checks.values())
    print(f"\n🎯 Overall Health: {'HEALTHY' if overall_health else 'ISSUES FOUND'}")

    return overall_health
```

This troubleshooting guide provides comprehensive solutions for the architectural conflicts and common issues in Phase 2 MCP implementation, with special emphasis on the clean slate approach using dynamic CLI introspection.
