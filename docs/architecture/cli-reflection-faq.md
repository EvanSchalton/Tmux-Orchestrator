# CLI Reflection Architecture - FAQ

## 🤔 Frequently Asked Questions

### **Q: How do CLI commands become MCP tools?**

**A**: The CLI reflection MCP server automatically discovers all CLI commands using `tmux-orc reflect --format json` and generates an MCP tool for each command. The process is:

1. Server starts → Runs `tmux-orc reflect --format json`
2. Parses CLI structure → Finds all commands
3. Generates MCP tool → Creates tool with same functionality
4. Command name mapping → `quick-deploy` becomes `quick_deploy` tool

**No manual coding required!**

### **Q: What happens when I add a new CLI command?**

**A**: Simply restart the MCP server and your new command automatically becomes an MCP tool:

```bash
# 1. Add new CLI command
# In tmux_orchestrator/cli/commands/team.py
@click.command()
def team_status():
    """Get team status."""
    # Your implementation

# 2. Restart MCP server
python -m tmux_orchestrator.mcp_server

# 3. New tool available!
# MCP tool "team_status" now exists
```

### **Q: How do I make my CLI command work well with MCP?**

**A**: Follow these key patterns:

1. **Add `--json` support**:
   ```python
   @click.option('--json', is_flag=True, help='Output in JSON format')
   def my_command(json):
       if json:
           click.echo(json.dumps({"success": True, "data": result}))
       else:
           click.echo("Human readable output")
   ```

2. **Use clear help text** (becomes MCP tool description):
   ```python
   @click.command(help="Clear description of what this command does")
   ```

3. **Handle errors consistently**:
   ```python
   if error and json:
       click.echo(json.dumps({"success": False, "error": str(error)}))
       sys.exit(1)
   ```

### **Q: Where did all the manual MCP tool code go?**

**A**: It's been removed! The architecture has completely changed:

- **OLD**: Manual tool implementations in `/mcp/tools/` (deleted)
- **NEW**: CLI commands auto-generate tools via reflection

All the old manual code is archived and no longer needed.

### **Q: How do MCP tool arguments work?**

**A**: MCP tools accept arguments in a flexible format:

```json
{
  "args": ["positional", "arguments"],
  "options": {
    "flag-name": true,
    "option-name": "value"
  }
}
```

The server converts these to CLI arguments:
- `args` → Positional arguments
- `options` → `--flag-name --option-name value`

### **Q: Do I need to update imports after the cleanup?**

**A**: Yes, if your code imported old MCP modules:

```python
# OLD - Remove these
from tmux_orchestrator.mcp.tools.agent_management import spawn_agent
from tmux_orchestrator.mcp.handlers.team_handlers import TeamHandlers

# NEW - Use CLI directly or MCP server
from tmux_orchestrator.mcp_server import FreshCLIMCPServer
# Or just use CLI commands directly via subprocess
```

### **Q: How do I test my CLI enhancements?**

**A**: Test at three levels:

1. **CLI Level**:
   ```bash
   tmux-orc my-command --json
   # Should output valid JSON
   ```

2. **MCP Tool Generation**:
   ```python
   # Verify tool is generated
   from tmux_orchestrator.mcp_server import FreshCLIMCPServer
   server = FreshCLIMCPServer()
   await server._generate_all_tools()
   assert "my_command" in server.generated_tools
   ```

3. **MCP Tool Execution**:
   ```python
   # Test tool execution
   result = await server._execute_cli_command("my-command", {"options": {"json": True}})
   assert result["success"]
   ```

### **Q: What if my command needs complex arguments?**

**A**: Design your CLI to accept simple arguments that work well with the args/options pattern:

```python
# GOOD - Simple, clear arguments
@click.command()
@click.argument('target')
@click.option('--format', type=click.Choice(['json', 'yaml']))
@click.option('--timeout', type=int, default=30)

# AVOID - Complex nested structures
# Use multiple options instead of complex JSON arguments
```

### **Q: How do I debug when a tool isn't working?**

**A**: Follow this debugging path:

1. **Test CLI directly**:
   ```bash
   tmux-orc my-command --json
   # Does it work?
   ```

2. **Check tool generation**:
   ```python
   # Is tool being generated?
   python -m tmux_orchestrator.mcp_server
   # Look for your tool in the list
   ```

3. **Test execution manually**:
   ```python
   # Debug execution
   server = FreshCLIMCPServer()
   result = await server._execute_cli_command("my-command", {})
   print(result)  # Check error messages
   ```

### **Q: What about performance?**

**A**: The CLI reflection approach has minimal overhead:

- **Tool Generation**: Once at server startup (~1-2 seconds)
- **Tool Execution**: Direct subprocess call (same as running CLI)
- **No middleware**: No translation layers or complex routing

Average execution time: 2-3 seconds per tool call.

### **Q: Can I still use the old manual approach?**

**A**: No, and you shouldn't want to! The CLI reflection approach is:
- ✅ Zero maintenance
- ✅ Always in sync with CLI
- ✅ Automatically tested when you test CLI
- ✅ No dual implementation

The old approach required maintaining two separate implementations.

### **Q: What if I need a complex MCP tool that doesn't map to CLI?**

**A**: Create a CLI command for it! If it's useful as an MCP tool, it's probably useful as a CLI command too. This ensures:
- Single implementation
- Available via both CLI and MCP
- Consistent behavior
- Easier testing

### **Q: How do subcommands work?**

**A**: Click subcommands become MCP tools with underscore naming:

```python
@click.group()
def agent():
    """Agent commands."""

@agent.command()
def status():
    """Get agent status."""

# Becomes MCP tool: "agent_status"
```

### **Q: What about backward compatibility?**

**A**: MCP tool names follow CLI command structure:
- `list` → `list` (same)
- `quick-deploy` → `quick_deploy` (underscore)
- `agent status` → `agent_status` (subcommand)

Update any tool references to use new names.

### **Q: Where can I find more help?**

**A**: Reference documents:
- **Architecture**: `/docs/architecture/cli-reflection-mcp-architecture.md`
- **CLI Patterns**: `/docs/architecture/cli-enhancement-patterns.md`
- **Troubleshooting**: `/docs/architecture/cli-reflection-troubleshooting.md`
- **Team Plan**: `/.tmux_orchestrator/planning/2025-08-16T16-30-00-mcp-server-completion/`

### **Q: What's the #1 thing to remember?**

**A**: 🎯 **Enhance CLI = Enhance MCP Tools Automatically**

Every improvement to CLI commands automatically improves the MCP tools. Focus all effort on making great CLI commands with JSON support, and the MCP tools take care of themselves!
