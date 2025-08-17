# Hierarchical MCP Implementation Plan

## Phase 2: Command Group Detection & Nesting

### Implementation Approach

#### 1. Enhanced CLI Structure Discovery
```python
def discover_hierarchical_structure(self) -> Dict[str, Any]:
    """Enhanced discovery that preserves group relationships."""
    structure = {
        "commands": {},  # Top-level commands
        "groups": {}     # Command groups with subcommands
    }

    # Get base structure
    cli_data = await self.discover_cli_structure()

    # Separate commands and groups
    for name, info in cli_data.items():
        if info.get('type') == 'command':
            structure['commands'][name] = info
        elif info.get('type') == 'group':
            # Discover subcommands for this group
            subcommands = await self.discover_group_subcommands(name)
            structure['groups'][name] = {
                'info': info,
                'subcommands': subcommands
            }

    return structure
```

#### 2. Modified Tool Generation
```python
def generate_hierarchical_mcp_tools(self) -> Dict[str, Any]:
    """Generate hierarchical tools instead of flat ones."""

    # Generate tools for top-level commands (unchanged)
    for cmd_name, cmd_info in self.structure['commands'].items():
        self._generate_simple_tool(cmd_name, cmd_info)

    # Generate ONE tool per group with action parameter
    for group_name, group_data in self.structure['groups'].items():
        self._generate_hierarchical_group_tool(
            group_name,
            group_data['info'],
            group_data['subcommands']
        )
```

#### 3. Smart Parameter Detection
- Parse subcommand help text for required/optional parameters
- Build conditional schemas based on action selection
- Support both positional and keyword arguments

### Coordination Points with LLM Optimizer

1. **Schema Simplicity**
   - Use clear, descriptive enum values for actions
   - Provide helpful descriptions for each parameter
   - Include examples in schema descriptions

2. **Error Messages**
   - Clear feedback when wrong action is selected
   - Suggest available actions in error responses
   - Validate parameters before execution

3. **Discovery Enhancement**
   - Tool descriptions should list all available actions
   - Consider adding an "actions" property that returns available operations
   - Support introspection for better LLM understanding

### Integration Strategy

1. **Backward Compatibility**
   - Keep existing flat tool generation as fallback
   - Add configuration flag for hierarchical mode
   - Gradual migration path

2. **Testing Approach**
   - Test each group independently
   - Verify all 92 operations still work
   - Measure LLM success rates

3. **Performance Optimization**
   - Cache subcommand discovery results
   - Lazy-load parameter schemas
   - Minimize subprocess calls

## Next Steps

1. Implement enhanced discovery method
2. Create hierarchical tool generator
3. Test with agent group as proof-of-concept
4. Coordinate with LLM Opt on schema optimization
5. Extend to all 16 command groups
