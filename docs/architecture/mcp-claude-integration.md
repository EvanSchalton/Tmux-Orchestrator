# MCP Server Claude Integration Guide

## 🎯 CRITICAL: Correct MCP Deployment Workflow

The MCP server must be registered with Claude using the proper integration pattern, NOT deployed as a standalone service.

## ✅ Correct Implementation Workflow

### **Step 1: Add MCP Server CLI Command**

The tmux-orchestrator CLI needs a command to start the MCP server:

```python
# In tmux_orchestrator/cli/commands/server.py

import click
import asyncio
from tmux_orchestrator.mcp_server import FreshCLIMCPServer

@click.group()
def server():
    """MCP server management commands."""
    pass

@server.command()
@click.option('--port', default=None, help='Port for HTTP mode (default: stdio)')
def start(port):
    """Start the MCP server for Claude integration.

    By default, runs in stdio mode for Claude Desktop.
    Use --port for HTTP mode (development/testing).
    """
    if port:
        click.echo(f"Starting MCP server on port {port}...")
        # HTTP mode for testing
        asyncio.run(start_http_server(port))
    else:
        # STDIO mode for Claude Desktop
        asyncio.run(start_stdio_server())

async def start_stdio_server():
    """Start MCP server in stdio mode for Claude."""
    server = FreshCLIMCPServer()
    await server.run()

async def start_http_server(port):
    """Start MCP server in HTTP mode for testing."""
    # Implementation for HTTP mode if needed
    pass
```

### **Step 2: Update Setup Command**

The `tmux-orc setup` command should register the MCP server with Claude:

```python
# In tmux_orchestrator/cli/commands/setup.py

import json
import os
from pathlib import Path

@click.command()
def setup():
    """Set up tmux-orchestrator and register MCP server with Claude."""

    # Existing setup logic...

    # Register MCP server with Claude
    register_mcp_with_claude()

def register_mcp_with_claude():
    """Register the MCP server with Claude Desktop."""

    # Claude Desktop config location (macOS)
    claude_config_dir = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"

    # Windows path
    if os.name == 'nt':
        claude_config_dir = Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"

    # Linux path
    elif os.name == 'posix' and not sys.platform == 'darwin':
        claude_config_dir = Path.home() / ".config" / "Claude" / "claude_desktop_config.json"

    # Ensure directory exists
    claude_config_dir.parent.mkdir(parents=True, exist_ok=True)

    # Load existing config or create new
    if claude_config_dir.exists():
        with open(claude_config_dir, 'r') as f:
            config = json.load(f)
    else:
        config = {}

    # Ensure mcpServers section exists
    if 'mcpServers' not in config:
        config['mcpServers'] = {}

    # Add tmux-orchestrator MCP server
    config['mcpServers']['tmux-orchestrator'] = {
        "command": "tmux-orc",
        "args": ["server", "start"],
        "env": {},
        "disabled": False
    }

    # Write updated config
    with open(claude_config_dir, 'w') as f:
        json.dump(config, f, indent=2)

    click.echo("✅ MCP server registered with Claude Desktop")
    click.echo(f"   Config: {claude_config_dir}")
    click.echo("   Command: tmux-orc server start")
    click.echo("\nRestart Claude Desktop to activate the MCP server.")
```

### **Step 3: Installation Workflow**

The correct installation and setup process:

```bash
# 1. Install tmux-orchestrator
pip install tmux-orchestrator

# 2. Run setup (registers MCP with Claude)
tmux-orc setup

# 3. Restart Claude Desktop
# The MCP server will be available in Claude
```

## 📋 Implementation Checklist

### **CLI Commands Needed**:
- [ ] `tmux-orc server start` - Start MCP server in stdio mode
- [ ] `tmux-orc server status` - Check if MCP server is registered
- [ ] `tmux-orc server test` - Test MCP server functionality

### **Setup Command Updates**:
- [ ] Detect Claude Desktop installation
- [ ] Update Claude config file with MCP registration
- [ ] Provide platform-specific paths (macOS, Windows, Linux)
- [ ] Handle existing config gracefully

### **MCP Server Requirements**:
- [ ] Must run in stdio mode by default
- [ ] Must handle Claude's initialization protocol
- [ ] Must provide proper capability advertisement

## 🔧 Technical Implementation Details

### **Claude Desktop Config Format**

```json
{
  "mcpServers": {
    "tmux-orchestrator": {
      "command": "tmux-orc",
      "args": ["server", "start"],
      "env": {
        // Optional environment variables
      },
      "disabled": false
    }
  }
}
```

### **STDIO Protocol Requirements**

The MCP server must:
1. Read from stdin for requests
2. Write to stdout for responses
3. Use stderr for logging only
4. Handle proper JSON-RPC communication

### **Server Lifecycle**

```
Claude Desktop starts
    ↓
Reads claude_desktop_config.json
    ↓
Finds tmux-orchestrator MCP server
    ↓
Executes: tmux-orc server start
    ↓
MCP server runs in stdio mode
    ↓
Claude communicates via stdin/stdout
```

## ⚠️ Common Issues and Solutions

### **Issue: MCP server not appearing in Claude**
- Ensure Claude Desktop is fully restarted
- Check config file location is correct for platform
- Verify tmux-orc is in PATH

### **Issue: Command not found**
- Ensure tmux-orchestrator is installed: `pip install tmux-orchestrator`
- Check PATH includes pip bin directory
- Try full path in config if needed

### **Issue: Server crashes immediately**
- Check logs in stderr output
- Ensure all dependencies installed
- Test with `tmux-orc server start` manually

## 🧪 Testing the Integration

### **Manual Test**:
```bash
# Test server starts correctly
tmux-orc server start

# Should see:
# INFO - Starting fresh CLI reflection MCP server...
# INFO - Discovered X CLI commands
# INFO - Generated MCP Tools: ...
```

### **Integration Test**:
1. Run `tmux-orc setup`
2. Restart Claude Desktop
3. In Claude, check available tools
4. Should see tmux-orchestrator tools available

## 📊 Migration from Incorrect Deployment

If the server was incorrectly deployed as a standalone service:

1. **Stop any running MCP server processes**
2. **Remove any systemd/Docker deployments**
3. **Run proper setup**: `tmux-orc setup`
4. **Update documentation** to reflect correct workflow

## 🎯 Key Points

1. **NO Docker deployment** - MCP runs as subprocess from Claude
2. **NO standalone service** - Claude manages server lifecycle
3. **YES Claude registration** - Via config file during setup
4. **YES CLI command** - `tmux-orc server start` for Claude to execute

This follows the standard Claude MCP integration pattern and ensures proper lifecycle management.
