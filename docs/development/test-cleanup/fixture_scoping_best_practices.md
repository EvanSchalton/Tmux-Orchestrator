# Fixture Scoping Best Practices - Tmux Orchestrator

## Observed Patterns from Conversions

### 1. Function Scope (Default) - Most Common
**When to use**: Mocks, test data, anything that could have state

```python
@pytest.fixture  # Default is function scope
def mock_tmux():
    """Fresh mock for each test."""
    return Mock(spec=TMUXManager)

@pytest.fixture
def test_data():
    """Mutable data structure - new instance per test."""
    return {"key": "value"}
```

**Why**: Prevents test interference, ensures clean state

### 2. Module Scope - Expensive Setup
**When to use**: File discovery, expensive computations

```python
@pytest.fixture(scope="module")
def all_fixtures():
    """Discover fixture files once per test module."""
    fixtures = {}
    for path in Path("fixtures").iterdir():
        fixtures[path.name] = list(path.glob("*.txt"))
    return fixtures
```

**Example from monitor_fixtures_dynamic_test.py**:
- File discovery happens once
- Read-only data structure
- Significant performance benefit

### 3. Session Scope - Rarely Needed
**When to use**: Database connections, external services

```python
@pytest.fixture(scope="session")
def database():
    """Shared database for entire test run."""
    db = setup_test_database()
    yield db
    db.teardown()
```

**Note**: Not seen in conversions yet - be very careful with session scope

## Scoping Rules Observed

### ✅ DO: Use Function Scope for
- All mocks (TMUXManager, Logger, etc.)
- Mutable data structures
- Objects with state
- Anything that tests might modify

### ✅ DO: Use Module Scope for
- Expensive read-only operations
- File system discovery
- Static configuration
- Immutable data used by many tests

### ❌ DON'T: Common Mistakes to Avoid
```python
# BAD: Module-scoped mock
@pytest.fixture(scope="module")
def mock_tmux():
    return Mock()  # Shared state between tests!

# GOOD: Function-scoped mock
@pytest.fixture
def mock_tmux():
    return Mock()  # Fresh instance
```

## Fixture Dependencies and Scoping

### Rule: Fixture scope must be compatible with dependencies

```python
# ✅ GOOD: Same or wider scope
@pytest.fixture(scope="module")
def config():
    return {"timeout": 30}

@pytest.fixture  # function scope can use module scope
def client(config):
    return Client(config)

# ❌ BAD: Narrower scope dependency
@pytest.fixture  # function scope
def connection():
    return connect()

@pytest.fixture(scope="module")  # ERROR!
def database(connection):  # Can't use function-scoped in module-scoped
    return Database(connection)
```

## Patterns from Successful Conversions

### 1. Mock Configuration Pattern
```python
@pytest.fixture
def mock_tmux():
    """Configure mock with common responses."""
    tmux = Mock(spec=TMUXManager)
    # Setup default behavior
    tmux.list_sessions.return_value = [...]
    tmux.list_windows.return_value = [...]
    return tmux
```
**Scope**: Always function - mocks should be fresh

### 2. Fixture Composition Pattern
```python
@pytest.fixture
def monitor(mock_tmux):  # Dependency injection
    """Monitor with mock tmux."""
    return IdleMonitor(mock_tmux)
```
**Scope**: Inherits function scope from mock_tmux

### 3. Discovery Pattern
```python
@pytest.fixture(scope="module")
def test_files():
    """Discover test files once."""
    return list(Path("tests").glob("*_test.py"))
```
**Scope**: Module - expensive operation, read-only result

## Quick Decision Guide

Ask yourself:
1. **Does it have state?** → Function scope
2. **Could tests interfere?** → Function scope
3. **Is it expensive to create?** → Consider module scope
4. **Is it read-only?** → Can use module scope
5. **Is it a mock?** → Always function scope

## Real Examples from Tmux Orchestrator

### Function Scope (Majority)
- `mock_tmux` - Mock object
- `logger` - Might capture logs
- `monitor` - Stateful object
- `notification_tracker` - Accumulates data

### Module Scope (Rare)
- `all_fixtures` - File discovery
- `discovered_fixtures` - Static file list

### Never Seen (Good!)
- Session-scoped fixtures
- Class-scoped fixtures (pytest-deprecated)

## Conclusion

The Backend Dev is following best practices:
- Default to function scope (safest)
- Module scope only for expensive, read-only operations
- Clear fixture dependencies
- No over-scoping of mocks or stateful objects
