# Test Structure README Outline

## Proposed Structure for tests/README.md

### 1. Overview
- Brief description of test organization philosophy
- Key principles: pytest-first, function-based, fixture-driven
- Coverage goals and standards

### 2. Test Organization

#### 2.1 Directory Structure
```
tests/
├── fixtures/                    # Test data and mock responses
│   └── monitor_states/         # Terminal state fixtures
├── test_cli/                   # CLI command tests
├── test_core/                  # Core functionality tests
│   ├── test_recovery/         # Recovery system tests
│   └── test_team_operations/  # Team management tests
├── test_integration/          # End-to-end integration tests
└── test_server/               # MCP server tests
    └── test_tools/           # Individual tool tests
```

#### 2.2 Naming Conventions
- Test files: `*_test.py` (NOT `test_*.py`)
- Test functions: `test_<description>`
- Fixtures: Descriptive names without `test_` prefix
- One primary test function per file (with helpers as needed)

### 3. Testing Patterns

#### 3.1 Fixture Architecture
- **Three-tier pattern**: Base Mock → Domain Object → Utilities
- **Scoping rules**: Function scope for mocks, module scope for discovery
- **Common fixtures**: Listed with examples

#### 3.2 Mock Patterns
- Pre-configured mocks with sensible defaults
- Variable response mocks for different scenarios
- Sequential response mocks for state changes
- Notification tracking pattern

#### 3.3 Parametrization
- When to use `@pytest.mark.parametrize`
- Dynamic test generation patterns
- Examples from the codebase

### 4. Writing Tests

#### 4.1 Test Structure
```python
# Standard test structure
def test_feature_behavior(mock_dependency, fixture_obj):
    """Test that feature behaves correctly under condition."""
    # Arrange
    mock_dependency.return_value = "expected"

    # Act
    result = fixture_obj.do_something()

    # Assert
    assert result == "expected"
    mock_dependency.assert_called_once()
```

#### 4.2 Common Patterns
- Testing async behavior
- Testing error conditions
- Testing tmux interactions
- Testing rate limits and timeouts

### 5. Running Tests

#### 5.1 Basic Commands
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/monitor_helpers_test.py

# Run with coverage
pytest --cov=tmux_orchestrator --cov-report=html

# Run specific test function
pytest tests/monitor_helpers_test.py::test_specific_function
```

#### 5.2 Test Markers
- `@pytest.mark.slow` - Tests that take >1s
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.parametrize` - Data-driven tests

### 6. Test Coverage

#### 6.1 Coverage Standards
- Target: 100% coverage (with justified exceptions)
- Branch coverage required
- Integration tests for critical paths

#### 6.2 Coverage Reports
- How to generate HTML reports
- Understanding coverage gaps
- Excluding unreachable code

### 7. Fixtures Reference

#### 7.1 Common Fixtures
| Fixture | Scope | Purpose |
|---------|-------|---------|
| `mock_tmux` | function | Mock TMUXManager |
| `monitor` | function | IdleMonitor with mock tmux |
| `logger` | function | Test logger |
| `frozen_time` | function | Time control for tests |
| `notification_tracker` | function | Capture notifications |

#### 7.2 Creating New Fixtures
- Fixture naming conventions
- Scope selection guide
- Composition patterns

### 8. Integration Testing

#### 8.1 Feature Integration Tests
- Rate limit + compaction detection
- Multi-agent scenarios
- Recovery system tests

#### 8.2 End-to-End Tests
- Full system workflow tests
- Performance benchmarks
- Stress testing patterns

### 9. Debugging Tests

#### 9.1 Common Issues
- Fixture scope mismatches
- Test interference
- Mock configuration errors
- Dynamic test discovery issues

#### 9.2 Debugging Tools
- pytest debugging flags
- Print debugging in tests
- Using pdb in tests

### 10. Contributing

#### 10.1 Adding New Tests
- Follow the one-function-per-file pattern
- Use existing fixtures when possible
- Ensure tests are deterministic
- Document complex test logic

#### 10.2 Modifying Tests
- Maintain test coverage
- Update related integration tests
- Run full test suite before submitting

### 11. Test Maintenance

#### 11.1 Keeping Tests Fast
- Mock external dependencies
- Use appropriate fixture scoping
- Avoid sleep() in tests
- Profile slow tests

#### 11.2 Test Quality
- Tests should be readable
- One logical assertion per test
- Clear test names
- Minimal test setup

### 12. Migration Guide

#### 12.1 From unittest to pytest
- Quick reference for common conversions
- Fixture conversion patterns
- Assertion updates

### Appendices

#### A. Pytest Configuration
- pytest.ini settings
- Coverage configuration
- Plugin requirements

#### B. Test Data Management
- Fixture file organization
- Test data best practices
- Mock response templates

#### C. Performance Testing
- Benchmark patterns
- Load testing approaches
- Profiling test execution
