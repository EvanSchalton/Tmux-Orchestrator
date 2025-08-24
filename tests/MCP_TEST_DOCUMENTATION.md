# MCP Server Unit Tests Documentation

## Overview

This test suite provides comprehensive unit testing for the Tmux Orchestrator MCP server using FastMCP's in-memory testing patterns. The tests ensure the MCP server maintains 100% CLI parity and validates all critical fixes.

## Test Structure

### 1. Core Test Files

#### `test_mcp_server.py`
- **Purpose**: Core MCP server functionality and infrastructure
- **Coverage**:
  - Server initialization and configuration
  - CLI structure discovery and caching
  - Hierarchical tool generation
  - Kwargs string parsing
  - Error handling
  - Performance optimizations

#### `test_mcp_commands.py`
- **Purpose**: Command-specific behavior validation
- **Coverage**: All 20 hierarchical command groups:
  - Agent commands (list, status, deploy, kill, restart, send)
  - Team commands (list, status, deploy, broadcast)
  - Spawn commands (agent, pm, orchestrator)
  - Monitor commands (status, dashboard, logs)
  - Session commands (list, attach, detach)
  - And 15 more command groups...

#### `test_mcp_fixes.py`
- **Purpose**: Focused validation of the 5 critical fixes
- **Coverage**:
  - Fix #1: Empty kwargs handling
  - Fix #2: Multi-word message parsing
  - Fix #3: Force flag for interactive commands
  - Fix #4: Selective JSON flag logic
  - Fix #5: Daemon command detection

## Testing Approach

### FastMCP In-Memory Testing
Following FastMCP's recommended patterns, all tests run in-memory without requiring:
- MCP server deployment
- External processes
- Network connections
- File system operations

### Key Testing Patterns

1. **Mock-based Testing**
   ```python
   with patch('subprocess.run') as mock_run:
       mock_run.return_value = Mock(returncode=0, stdout='{"status": "ok"}')
       result = await tool(kwargs='action=status')
   ```

2. **Fixture-based Setup**
   ```python
   @pytest.fixture
   def mcp_server(self):
       server = EnhancedCLIToMCPServer("test-server")
       return server
   ```

3. **Parametrized Testing**
   ```python
   @pytest.mark.parametrize("command,expected", test_cases)
   async def test_command_execution(self, command, expected):
       # Test implementation
   ```

## Running the Tests

### Basic Test Execution
```bash
# Run all MCP tests
pytest tests/test_mcp_server.py tests/test_mcp_commands.py tests/test_mcp_fixes.py -v

# Run specific test file
pytest tests/test_mcp_server.py -v

# Run specific test class
pytest tests/test_mcp_fixes.py::TestFix1EmptyKwargsHandling -v

# Run with coverage
pytest tests/test_mcp_*.py --cov=tmux_orchestrator.mcp_server --cov-report=html
```

### Performance Testing
```bash
# Run with timing information
pytest tests/test_mcp_server.py --durations=10

# Run performance-specific tests
pytest tests/test_mcp_server.py::TestPerformanceOptimizations -v
```

### Debugging Failed Tests
```bash
# Run with detailed output
pytest tests/test_mcp_fixes.py -vv -s

# Run with pdb on failure
pytest tests/test_mcp_server.py --pdb

# Run specific test with full traceback
pytest tests/test_mcp_commands.py::TestAgentCommands::test_agent_list -vv --tb=long
```

## Test Coverage Requirements

### Target: 90%+ Coverage

The test suite aims for comprehensive coverage of:
- All 20 hierarchical command groups
- All 5 critical fixes
- Error handling paths
- Edge cases and boundary conditions
- Performance-critical code paths

### Coverage Report Generation
```bash
# Generate HTML coverage report
pytest tests/test_mcp_*.py --cov=tmux_orchestrator.mcp_server --cov-report=html

# View coverage in terminal
pytest tests/test_mcp_*.py --cov=tmux_orchestrator.mcp_server --cov-report=term-missing

# Generate XML for CI/CD
pytest tests/test_mcp_*.py --cov=tmux_orchestrator.mcp_server --cov-report=xml
```

## CI/CD Integration

### GitHub Actions Configuration
The tests are designed to run in GitHub Actions with:
- Python 3.11+ environment
- Poetry dependency management
- Parallel test execution
- Coverage reporting
- Performance benchmarks

### Example GitHub Actions Workflow
```yaml
name: MCP Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install Poetry
        run: pip install poetry
      - name: Install dependencies
        run: poetry install
      - name: Run MCP tests
        run: poetry run pytest tests/test_mcp_*.py -v --cov=tmux_orchestrator.mcp_server
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Test Maintenance

### Adding New Tests

1. **For new commands**: Add test methods to appropriate class in `test_mcp_commands.py`
2. **For new fixes**: Create new test class in `test_mcp_fixes.py`
3. **For new features**: Add to `test_mcp_server.py` or create new test file

### Test Naming Conventions
- Test files: `test_mcp_*.py`
- Test classes: `Test<Feature>` (e.g., `TestAgentCommands`)
- Test methods: `test_<specific_behavior>` (e.g., `test_agent_list_with_json`)

### Mock Best Practices
1. Mock at the subprocess boundary (subprocess.run, subprocess.Popen)
2. Return realistic data structures
3. Test both success and failure paths
4. Verify command construction, not just results

## Common Test Scenarios

### Testing Command Execution
```python
async def test_command_execution(self, tool):
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"result": "success"}',
            stderr=""
        )

        result = await tool(kwargs='action=list')

        assert result["success"] == True
        cmd_args = mock_run.call_args[0][0]
        assert cmd_args == ["tmux-orc", "agent", "list", "--json"]
```

### Testing Error Handling
```python
async def test_error_handling(self, tool):
    result = await tool(kwargs='action=invalid')

    assert result["success"] == False
    assert "Invalid action" in result["error"]
    assert "valid_actions" in result
```

### Testing Daemon Commands
```python
async def test_daemon_command(self, tool):
    with patch('subprocess.Popen') as mock_popen:
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        result = await tool(kwargs='action=dashboard')

        assert result["command_type"] == "daemon"
        assert result["pid"] == 12345
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure tmux_orchestrator is in PYTHONPATH
2. **Async Test Failures**: Use `@pytest.mark.asyncio` decorator
3. **Mock Not Called**: Check command name and argument matching
4. **Coverage Gaps**: Look for untested error paths and edge cases

### Debug Tips
- Use `pytest.set_trace()` for breakpoints
- Add `-s` flag to see print statements
- Use `mock_obj.call_args_list` to inspect all calls
- Check `result` dictionary for unexpected keys

## Future Enhancements

1. **Property-based Testing**: Add hypothesis tests for kwargs parsing
2. **Integration Tests**: Test with real CLI in isolated environment
3. **Performance Benchmarks**: Add timing assertions
4. **Mutation Testing**: Ensure test quality with mutmut
5. **Contract Testing**: Validate MCP protocol compliance
