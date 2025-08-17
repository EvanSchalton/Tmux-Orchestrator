# ADR-006: CLI Reflection for MCP Tool Generation

**Status**: Accepted
**Date**: 2025-08-17
**Decision Makers**: Software Architect, Development Team
**Implementation**: Complete

## Context and Problem Statement

The Tmux Orchestrator project required Model Context Protocol (MCP) tools to enable AI agents to interact with the system. Additionally, the project needed a simple deployment model that would work seamlessly with Claude Desktop's MCP integration.

**Problems with initial approaches**:
- Manual MCP tools: Duplicate implementation of every CLI command
- Container deployment: Complex infrastructure for what should be a simple tool
- Synchronization issues between CLI and MCP interfaces
- 2x maintenance effort for every feature
- Complex deployment pipeline vs pip-installable simplicity
- Risk of behavioral divergence between interfaces

## Decision Drivers

1. **Deployment Simplicity**: Standard pip installation workflow
2. **Maintenance Efficiency**: Minimize code duplication and maintenance burden
3. **Claude Integration**: Seamless MCP registration with Claude Desktop
4. **Consistency**: Ensure CLI and MCP behaviors are always synchronized
5. **Developer Velocity**: Enable rapid feature development with standard Python tooling
6. **Architectural Simplicity**: Pure CLI tool, no infrastructure complexity
7. **User Experience**: Two-command setup (pip install + setup)

## Considered Options

### Option 1: Containerized Service with Manual MCP Tools
- **Pros**: Full control, separate deployment
- **Cons**: Complex infrastructure, Docker dependencies, dual implementation

### Option 2: Manual MCP Tool Implementation (CLI-based)
- **Pros**: Fine-grained control, no containers
- **Cons**: Massive duplication, maintenance nightmare, synchronization issues

### Option 3: Code Generation from CLI
- **Pros**: Reduced duplication, semi-automated
- **Cons**: Complex build process, generation drift, still requires templates

### Option 4: CLI Reflection with Pip-Only Deployment (Chosen)
- **Pros**: Zero duplication, automatic sync, simple deployment, Claude integration
- **Cons**: Requires CLI to support structured output (JSON)

### Option 5: Shared Business Logic Library
- **Pros**: Reusable logic, some reduction in duplication
- **Cons**: Still requires dual interface implementation, complex abstraction

## Decision

**We will use CLI Reflection with Pip-Only Deployment** to automatically create MCP tools from CLI commands with maximum simplicity.

### Implementation Details

1. **Pip Installation**: `pip install tmux-orchestrator` - standard Python package
2. **Setup Command**: `tmux-orc setup` registers MCP server with Claude Desktop
3. **CLI Discovery**: MCP server uses `tmux-orc reflect --format json` to discover commands
4. **Dynamic Tool Generation**: Each CLI command automatically becomes an MCP tool
5. **Direct Execution**: MCP tools execute CLI commands via subprocess
6. **Structured Output**: CLI commands support `--json` flag for structured responses
7. **Claude Integration**: Claude runs `tmux-orc server start` when MCP tools needed

```python
# Simplified architecture
class FreshCLIMCPServer:
    async def discover_cli_structure(self):
        # Run: tmux-orc reflect --format json
        # Parse command structure

    def generate_all_mcp_tools(self):
        # For each CLI command:
        # Create MCP tool with same name/description

    async def execute_cli_command(self, command, args):
        # Run: tmux-orc [command] [args] --json
        # Return structured result
```

## Consequences

### Positive Consequences

1. **Ultra-Simple Deployment**: Two commands: `pip install` + `tmux-orc setup`
2. **Zero Infrastructure**: No Docker, services, or complex deployment
3. **Standard Python Workflow**: Familiar pip/setuptools development
4. **Zero Dual Implementation**: CLI is the single source of truth
5. **Automatic Feature Parity**: New CLI commands instantly available as MCP tools
6. **Reduced Codebase**: Eliminated ~2000 lines of manual tool implementations
7. **Simplified Testing**: Test CLI once, MCP tools work automatically
8. **Consistent Behavior**: MCP tools behave exactly like CLI commands
9. **Claude Integration**: Standard MCP registration, no custom setup
10. **Cross-Platform**: Works anywhere Python + tmux available

### Negative Consequences

1. **CLI Dependency**: All commands must support structured output
2. **Performance Overhead**: Subprocess execution adds ~0.5s latency
3. **Limited MCP-Specific Features**: Tools limited to CLI capabilities
4. **Python Requirement**: Users must have Python environment

### Mitigation Strategies

1. **Structured Output Standard**: All CLI commands must support `--json` flag
2. **Performance Optimization**: Consider process pooling for frequent commands
3. **CLI Enhancement Focus**: Invest in rich CLI features that benefit both interfaces

## Implementation Requirements

### CLI Command Standards

1. **JSON Output Support**:
```python
@click.option('--json', is_flag=True, help='Output in JSON format')
def command(json):
    if json:
        click.echo(json.dumps({"success": True, "data": result}))
```

2. **Consistent Error Handling**:
```python
if error and json:
    click.echo(json.dumps({"success": False, "error": str(error)}))
    sys.exit(1)
```

3. **Rich Help Text**:
```python
@click.command(help="Clear, comprehensive description for MCP tool")
```

### MCP Server Requirements

1. **CLI Discovery**: Must handle dynamic command discovery
2. **Flexible Arguments**: Support args/options pattern
3. **Error Propagation**: Pass through CLI errors appropriately

## Validation and Rollback

### Success Metrics
- ✅ All CLI commands available as MCP tools
- ✅ Zero manual tool maintenance required
- ✅ Average tool execution under 3 seconds
- ✅ 100% behavioral consistency between interfaces

### Rollback Plan
If critical issues arise:
1. Restore legacy `mcp_server.py` from backup
2. Re-enable manual tool imports
3. Document specific failures for resolution

## Examples

### Before (Manual Implementation)
```python
# mcp/tools/agent_management.py
@mcp.tool()
async def spawn_agent(session_name: str, agent_type: str):
    """Manually implemented MCP tool."""
    # Duplicate logic from CLI command
    # Complex parameter handling
    # Direct tmux manipulation
    # Custom response formatting
    # ~200 lines of code

# cli/commands/agent.py
@click.command()
def spawn(session_name, agent_type):
    """CLI command with same logic."""
    # Original implementation
    # Different parameter handling
    # Different response format
    # ~150 lines of code
```

### After (CLI Reflection)
```python
# cli/commands/agent.py (ONLY implementation)
@click.command()
@click.option('--json', is_flag=True)
def spawn(session_name, agent_type, json):
    """CLI command - single source of truth."""
    # Single implementation
    # Structured output support
    # ~150 lines of code

# MCP tool "spawn" automatically generated!
```

## Related Decisions

- **ADR-002**: Dependency Injection Pattern - Supports clean CLI structure
- **ADR-004**: Async-First Design - CLI commands can be async
- **Future ADR**: CLI Enhancement Standards - Formal CLI requirements

## Notes

This architectural decision represents a paradigm shift in how we approach multi-interface systems. By treating the CLI as the primary interface and deriving other interfaces from it, we achieve unprecedented simplicity and maintainability.

The success of this approach validates the principle: **"Build one interface well, derive others automatically."**

## References

- [CLI Reflection Architecture](/docs/architecture/cli-reflection-mcp-architecture.md)
- [CLI Enhancement Patterns](/docs/architecture/cli-enhancement-patterns.md)
- [Implementation PR](#) - TODO: Add PR link
- [Original MCP Specification](https://modelcontextprotocol.io)
