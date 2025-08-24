# MCP Integration Testing Framework

## Overview

This testing framework validates the MCP server integration between tmux-orchestrator and Claude Code CLI. It covers the complete user workflow and provides automated validation tools.

## Test Files

### 1. `test_mcp_integration.py`
Comprehensive unit tests for MCP integration functionality:
- **TestEnhancedSetupCommand**: Tests for the enhanced `tmux-orc setup all` command
- **TestClaudeCodeMCPIntegration**: Tests for Claude Code CLI MCP integration
- **TestAgentMCPAccess**: Tests for agent MCP server access validation

### 2. `test_mcp_validation_tools.py`
Standalone validation tools for testing MCP integration:
- **MCPValidationTools**: Complete validation suite with CLI interface
- Validates setup command, Claude integration, server functionality, and agent access
- Provides JSON output and comprehensive reporting

### 3. `test_workflow_integration.py`
End-to-end workflow testing:
- **WorkflowIntegrationTests**: Unit tests for complete user workflow
- **WorkflowValidationRunner**: Standalone workflow validation
- Tests the complete flow: install → setup → spawn → verify

### 4. `test_reflect_filter.py`
Existing CLI reflection and filtering tests (already present)

## Usage

### Running Individual Test Suites

```bash
# Run MCP integration unit tests
python tests/test_cli/test_mcp_integration.py

# Run specific test categories
python tests/test_cli/test_mcp_integration.py setup      # Setup command tests
python tests/test_cli/test_mcp_integration.py integration # Claude integration tests
python tests/test_cli/test_mcp_integration.py agents      # Agent access tests

# Run workflow integration tests
python tests/test_cli/test_workflow_integration.py --unit-tests

# Run workflow validation
python tests/test_cli/test_workflow_integration.py
```

### Using Validation Tools

```bash
# Run comprehensive MCP validation
python tests/test_cli/test_mcp_validation_tools.py

# Run specific validation tests
python tests/test_cli/test_mcp_validation_tools.py --test setup
python tests/test_cli/test_mcp_validation_tools.py --test claude
python tests/test_cli/test_mcp_validation_tools.py --test server
python tests/test_cli/test_mcp_validation_tools.py --test agents

# Get JSON output
python tests/test_cli/test_mcp_validation_tools.py --json

# Specify Claude config directory
python tests/test_cli/test_mcp_validation_tools.py --config-dir /path/to/.claude
```

## Test Coverage

### Enhanced Setup Command Testing
- ✅ Creates Claude config directory structure
- ✅ Generates proper mcp.json configuration
- ✅ Handles existing MCP configurations (merge, don't overwrite)
- ✅ Validates tmux-orc availability
- ✅ Ensures idempotent operation
- ✅ Provides proper error handling

### Claude Code CLI Integration Testing
- ✅ Verifies `claude mcp list` shows tmux-orchestrator
- ✅ Tests `claude mcp get tmux-orchestrator` functionality
- ✅ Validates MCP server configuration format
- ✅ Checks server startup and accessibility

### Agent MCP Access Testing
- ✅ Validates spawned agents can access MCP server
- ✅ Tests MCP tool availability to agents
- ✅ Verifies session management functionality
- ✅ Checks agent-to-server communication

### Workflow Integration Testing
- ✅ Complete user workflow: install → setup → spawn → verify
- ✅ Error handling and recovery scenarios
- ✅ Configuration persistence across restarts
- ✅ Idempotency validation

## Expected Test Results

### Before Fix (Current State)
- ❌ Claude MCP Integration tests fail: "No MCP servers configured"
- ❌ Setup command tests fail: Interactive mode, incomplete configuration
- ⚠️  Some workflow tests pass with mocked behavior

### After Fix (Target State)
- ✅ All MCP integration tests pass
- ✅ Enhanced setup command creates proper configuration
- ✅ Claude Code CLI recognizes tmux-orchestrator server
- ✅ Agents have full MCP server access
- ✅ Complete workflow functions end-to-end

## Key Test Scenarios

### 1. Fresh Installation Test
```bash
# Simulates new user experience
rm -rf .claude/config/mcp.json
tmux-orc setup all
claude mcp list  # Should show tmux-orchestrator
```

### 2. Configuration Merge Test
```bash
# Tests that existing MCP servers aren't overwritten
# Setup creates config with multiple servers
tmux-orc setup all  # Should preserve existing + add tmux-orchestrator
```

### 3. Agent Spawn and Access Test
```bash
# Tests complete agent workflow
tmux-orc setup all
tmux-orc spawn orc
# Verify orchestrator has MCP access
```

### 4. Restart Persistence Test
```bash
# Tests configuration survives Claude Code restart
tmux-orc setup all
# Restart Claude Code CLI
claude mcp list  # Should still show configuration
```

## Integration with CI/CD

The test framework is designed to integrate with automated testing:

```bash
# Run all MCP tests and exit with proper codes
python tests/test_cli/test_mcp_validation_tools.py && \
python tests/test_cli/test_workflow_integration.py && \
python -m unittest tests.test_cli.test_mcp_integration
```

## Troubleshooting Test Issues

### Common Test Failures

1. **"tmux-orc command not found"**
   - Ensure tmux-orchestrator is installed: `pip install -e .`
   - Check PATH includes tmux-orc binary

2. **"Claude Code CLI not found"**
   - Install Claude Code CLI
   - Ensure `claude` command is available

3. **"Permission denied on .claude/config/"**
   - Check file permissions
   - Ensure test has write access to config directory

4. **"MCP server not starting"**
   - Check tmux-orc server implementation
   - Verify MCP server dependencies

### Mock Behavior

Tests use mocking for external dependencies:
- Claude Code CLI commands are mocked for reliability
- Tmux operations are mocked to avoid session conflicts
- Network operations are mocked for speed

## Development Notes

### Adding New Tests

1. **Unit Tests**: Add to appropriate test class in `test_mcp_integration.py`
2. **Validation Tools**: Extend `MCPValidationTools` class
3. **Workflow Tests**: Add to `WorkflowIntegrationTests` class

### Test Data

Tests use temporary directories and mock configurations to avoid affecting real systems.

### Performance Considerations

- Tests run in parallel where possible
- Mocking reduces external dependencies
- Timeout protection prevents hanging tests

## Related Documentation

- **Planning Documents**: `.tmux_orchestrator/planning/2025-08-19T19-20-18-mcp-server-setup-fix/`
- **MCP Integration Guide**: `MCP_SERVER_INTEGRATION_GUIDE.md`
- **Troubleshooting Guide**: `MCP_TROUBLESHOOTING_GUIDE.md`

---

**Status**: Testing framework complete and ready for validation during implementation phase.
