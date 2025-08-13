# Test Organization Guidelines for Tmux-Orchestrator

## Overview
This document provides comprehensive guidelines for organizing and maintaining tests in the Tmux-Orchestrator project. These guidelines ensure consistency, maintainability, and effectiveness of our test suite.

## Core Principles

### 1. Test Structure Mirrors Code Structure
- Test directory structure must mirror the application code structure
- Example: `tmux_orchestrator/core/monitor.py` → `tests/test_core/monitor_test.py`
- This makes it easy to locate tests for any given module

### 2. One Test File Per Application File
- Each application code file should have exactly one corresponding test file
- Test file naming: `[module_name]_test.py` (not `test_[module_name].py`)
- Exception: Large test files can be split by functionality (see File Size Guidelines)

### 3. Function-Based Testing
- Use `def test_*()` functions, not `class Test*:`
- All test functions must have type hints: `def test_example() -> None:`
- Group related tests using clear naming patterns

## File Organization Standards

### Directory Structure
```
tests/
├── conftest.py                    # Shared fixtures only
├── test_cli/                      # Tests for CLI modules
│   ├── agent_test.py
│   ├── monitor_test.py
│   └── ...
├── test_core/                     # Tests for core modules
│   ├── monitor_test.py
│   ├── error_handler_test.py
│   └── test_recovery/            # Subdirectory for recovery module
│       ├── check_agent_health_test.py
│       └── ...
├── test_server/                   # Tests for server modules
│   ├── mcp_server_test.py
│   └── test_tools/               # Tests for server tools
│       ├── get_agent_status_test.py
│       └── ...
└── integration_*_test.py         # Integration tests at root level
```

### File Naming Conventions
- Test files: `module_name_test.py` (e.g., `monitor_test.py`, `agent_test.py`)
- Test directories: `test_module/` (e.g., `test_cli/`, `test_server/`)
- NO `__init__.py` files in test directories (pytest works better without them)

### File Size Guidelines
- **Target**: 300-400 lines per test file
- **Maximum**: 500 lines (split if larger)
- **Splitting Strategy**:
  - By functionality: `feature_basic_test.py`, `feature_edge_cases_test.py`, `feature_integration_test.py`
  - By component: `feature_models_test.py`, `feature_validation_test.py`, `feature_workflow_test.py`
  - By operation: `feature_create_test.py`, `feature_update_test.py`, `feature_delete_test.py`

## Test Writing Standards

### Type Hints (MANDATORY)
```python
# ✅ CORRECT
def test_agent_spawn() -> None:
    """Test agent spawning functionality."""
    pass

@pytest.fixture
def mock_tmux() -> Mock:
    """Create a mock TMUXManager."""
    return Mock(spec=TMUXManager)

# ❌ INCORRECT
def test_agent_spawn():  # Missing return type
    pass

@pytest.fixture
def mock_tmux():  # Missing return type
    return Mock(spec=TMUXManager)
```

### Test Function Naming
```python
# Pattern: test_[feature]_[scenario]_[expected_outcome]

def test_agent_spawn_valid_type_succeeds() -> None:
    """Test that spawning an agent with valid type succeeds."""

def test_agent_spawn_invalid_type_raises_error() -> None:
    """Test that spawning an agent with invalid type raises ValueError."""

def test_monitor_rate_limit_detection_pauses_execution() -> None:
    """Test that monitor pauses execution when rate limit is detected."""
```

### Fixture Usage
```python
# Shared fixtures go in conftest.py
@pytest.fixture
def cli_runner() -> CliRunner:
    """Provide a Click CLI test runner."""
    return CliRunner()

# Local fixtures in test files must have docstrings
@pytest.fixture
def sample_agent_data() -> dict[str, Any]:
    """Provide sample agent data for testing."""
    return {
        "session": "test-session:1",
        "type": "developer",
        "status": "active"
    }
```

### Parametrized Tests
```python
# Use parametrize for testing multiple scenarios
@pytest.mark.parametrize(
    "agent_type,expected_context",
    [
        ("developer", "dev_context.md"),
        ("pm", "pm_context.md"),
        ("qa", "qa_context.md"),
    ],
)
def test_agent_context_loading(agent_type: str, expected_context: str) -> None:
    """Test that correct context is loaded for each agent type."""
    # Test implementation
```

## Test Categories

### 1. Unit Tests
- Test individual functions/methods in isolation
- Mock external dependencies
- Focus on single responsibility
- File suffix: `_test.py` (standard)

### 2. Integration Tests
- Test interaction between multiple components
- May use real dependencies where appropriate
- File prefix: `integration_` (e.g., `integration_rate_limit_test.py`)

### 3. Edge Case Tests
- Focus on boundary conditions and error handling
- When splitting files: `*_edge_cases_test.py`

### 4. Model/Validation Tests
- Test data models and validation logic
- When splitting files: `*_models_test.py` or `*_validation_test.py`

## Coverage Requirements

### Targets
- **Minimum**: 90% statement coverage
- **Goal**: 100% branch and statement coverage
- **Priority**: Cover all error paths and edge cases

### Running Coverage
```bash
# Run with coverage report
pytest --cov=tmux_orchestrator --cov-report=term-missing --cov-branch

# Generate HTML report
pytest --cov=tmux_orchestrator --cov-report=html --cov-branch
```

### Coverage Exclusions
Only exclude code that truly cannot be tested:
```python
if TYPE_CHECKING:  # pragma: no cover
    from typing import SomeType

# Platform-specific code that can't run in CI
if sys.platform == "win32":  # pragma: no cover
    # Windows-specific implementation
```

## Common Patterns and Anti-Patterns

### ✅ DO
- Write focused tests that test one thing
- Use descriptive test names that explain the scenario
- Keep test setup minimal and clear
- Use fixtures for reusable setup
- Test both success and failure paths
- Include docstrings for complex tests

### ❌ DON'T
- Don't test Python built-ins or standard library behavior
- Don't test basic Pydantic field assignment
- Don't create test classes (use functions)
- Don't use hardcoded paths or values (use fixtures)
- Don't write tests > 50 lines (split into multiple tests)
- Don't leave commented-out test code

## File Splitting Process

When a test file exceeds 500 lines:

1. **Analyze Current Structure**
   ```bash
   # Count test functions
   grep -c "^def test_" large_test_file.py

   # Identify logical groups
   grep "^def test_" large_test_file.py | cut -d'_' -f2-4 | sort | uniq -c
   ```

2. **Plan the Split**
   - Group by functionality or component
   - Ensure balanced file sizes
   - Maintain logical cohesion

3. **Execute the Split**
   ```bash
   # Create new files
   touch feature_basic_test.py feature_edge_cases_test.py

   # Move tests (manually or with careful scripting)
   # Update imports in each file
   ```

4. **Validate**
   ```bash
   # Run all tests
   pytest tests/test_module/

   # Check coverage didn't drop
   pytest tests/test_module/ --cov=module_name --cov-report=term
   ```

5. **Clean Up**
   - Remove the original large file
   - Update any documentation
   - Commit with clear message

## Maintenance Guidelines

### Regular Reviews
- Review test organization quarterly
- Monitor file sizes monthly
- Update guidelines as patterns emerge

### Continuous Improvement
- Refactor tests when touching related code
- Add type hints when modifying tests
- Split files proactively when approaching 400 lines

### Documentation
- Keep this guide updated with new patterns
- Document special cases in test files
- Share learnings from test refactoring

## Quick Reference Checklist

Before committing test changes, ensure:
- [ ] All test files end with `_test.py`
- [ ] All test functions have type hints (→ None)
- [ ] All fixtures have type hints and docstrings
- [ ] No test file exceeds 500 lines
- [ ] Test directory structure mirrors application structure
- [ ] No `__init__.py` files in test directories
- [ ] Coverage is maintained or improved
- [ ] All tests pass locally
- [ ] Clear, descriptive test names used
