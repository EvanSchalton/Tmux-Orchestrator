# MCP Server Integration Notes

## Overview
This document provides integration guidance for merging the hierarchical tool generation into `mcp_server.py`.

## Integration Strategy

### 1. Phased Rollout
```python
# Add configuration flag in mcp_server.py
class FreshCLIToMCPServer:
    def __init__(self, server_name: str = "tmux-orchestrator-fresh",
                 hierarchical_mode: bool = True):
        self.hierarchical_mode = hierarchical_mode
        self.hierarchical_generator = OptimizedHierarchicalToolGenerator() if hierarchical_mode else None
```

### 2. Modified Tool Generation Flow

Replace the current `generate_all_mcp_tools()` method:

```python
def generate_all_mcp_tools(self) -> Dict[str, Any]:
    """Generate MCP tools with hierarchical optimization."""

    if not self.hierarchical_mode:
        # Fall back to flat generation
        return self._generate_flat_tools()

    # Extract commands and groups
    commands = {k: v for k, v in self.cli_structure.items()
               if isinstance(v, dict) and v.get('type') == 'command'}
    groups = {k: v for k, v in self.cli_structure.items()
             if isinstance(v, dict) and v.get('type') == 'group'}

    logger.info(f"Generating hierarchical tools: {len(commands)} commands, {len(groups)} groups")

    # Generate individual command tools (unchanged)
    for cmd_name, cmd_info in commands.items():
        self._generate_tool_for_command(cmd_name, cmd_info)

    # Generate hierarchical group tools
    for group_name, group_info in groups.items():
        # Discover subcommands
        subcommands = self._discover_group_subcommands(group_name)

        # Generate single hierarchical tool
        tool_def = self.hierarchical_generator.generate_hierarchical_tool(
            group_name, group_info, subcommands
        )

        # Register with FastMCP
        self._register_hierarchical_tool(tool_def)

    return self.generated_tools
```

### 3. Hierarchical Tool Registration

```python
def _register_hierarchical_tool(self, tool_def: Dict[str, Any]) -> None:
    """Register a hierarchical tool with FastMCP."""

    tool_function = tool_def['function']

    # FastMCP registration with enhanced metadata
    try:
        decorated_tool = self.mcp.tool(
            name=tool_def['name'],
            description=tool_def['description']
        )(tool_function)

        self.generated_tools[tool_def['name']] = {
            "type": "hierarchical",
            "command_name": tool_def['name'],
            "description": tool_def['description'],
            "actions": tool_def['subcommands'],
            "examples": tool_def.get('examples', []),
            "function": decorated_tool
        }

        logger.info(f"Registered hierarchical tool: {tool_def['name']} with {len(tool_def['subcommands'])} actions")

    except Exception as e:
        logger.error(f"Failed to register hierarchical tool {tool_def['name']}: {e}")
```

### 4. Import Requirements

Add to imports section:
```python
from tmux_orchestrator.mcp_hierarchical_optimized import (
    OptimizedHierarchicalToolGenerator,
    LLMOptimizedSchemaBuilder,
    LLMFriendlyErrorFormatter
)
```

### 5. Subcommand Discovery Enhancement

```python
def _discover_group_subcommands(self, group_name: str) -> List[Dict[str, Any]]:
    """Enhanced subcommand discovery with metadata."""
    try:
        # Get help text
        result = subprocess.run(
            ["tmux-orc", group_name, "--help"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return []

        # Parse subcommands
        subcommand_names = self._parse_subcommands_from_help(result.stdout)

        # Build subcommand info with descriptions
        subcommands = []
        for name in subcommand_names:
            # Try to get individual subcommand help
            subcmd_help = self._get_subcommand_help(group_name, name)
            subcommands.append({
                "name": name,
                "help": subcmd_help,
                "group": group_name
            })

        return subcommands

    except Exception as e:
        logger.error(f"Failed to discover subcommands for {group_name}: {e}")
        return []
```

### 6. Configuration Options

Add to server initialization:
```python
# Environment variable support
hierarchical_mode = os.environ.get('MCP_HIERARCHICAL_MODE', 'true').lower() == 'true'

# Or command line argument
parser.add_argument('--flat-mode', action='store_true',
                    help='Use flat tool generation (legacy mode)')
```

## Testing Strategy

### 1. A/B Testing
- Run both modes in parallel initially
- Compare LLM success rates
- Monitor performance metrics

### 2. Gradual Migration
```python
# Start with specific groups
HIERARCHICAL_GROUPS = ['agent', 'monitor', 'team']  # Expand gradually

def should_use_hierarchical(group_name: str) -> bool:
    return self.hierarchical_mode and group_name in HIERARCHICAL_GROUPS
```

### 3. Metrics Collection
```python
# Add metrics tracking
self.metrics = {
    "flat_tools_generated": 0,
    "hierarchical_tools_generated": 0,
    "total_actions": 0,
    "generation_time": 0
}
```

## Rollback Plan

If issues arise:
1. Set `hierarchical_mode=False`
2. Restart MCP server
3. All tools revert to flat structure

## Performance Considerations

1. **Startup Time**: Hierarchical generation is faster (fewer tools)
2. **Memory Usage**: Reduced by ~60% (fewer function objects)
3. **Execution Speed**: Identical (same CLI calls)

## Migration Checklist

- [ ] Add hierarchical imports
- [ ] Implement configuration flag
- [ ] Update tool generation logic
- [ ] Add hierarchical registration
- [ ] Test with sample groups
- [ ] Monitor LLM success rates
- [ ] Document changes
- [ ] Update tests
- [ ] Deploy with monitoring

## Expected Outcomes

- **Tool Count**: 92 → ~20 (78% reduction)
- **LLM Accuracy**: Target 95%+ success rate
- **Generation Time**: <2 seconds
- **Memory Usage**: 60% reduction
- **Maintenance**: Easier with grouped structure
