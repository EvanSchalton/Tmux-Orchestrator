# Test Conversion Playbook
A practical guide based on successful conversions in Tmux Orchestrator

## Table of Contents
1. [Common Fixture Patterns](#common-fixture-patterns)
2. [Conversion Steps](#conversion-steps)
3. [Pattern Recognition Guide](#pattern-recognition-guide)
4. [Troubleshooting](#troubleshooting)

## Common Fixture Patterns

### 1. Three-Tier Mock Architecture
The most successful pattern observed across all conversions.

```python
# Tier 1: Base Mock (Foundation)
@pytest.fixture
def mock_tmux():
    """Create a mock TMUXManager for testing."""
    tmux = Mock(spec=TMUXManager)
    # Pre-configure with sensible defaults
    tmux.list_sessions.return_value = [
        {"name": "test-session", "windows": 2, "created": "2024-01-15"}
    ]
    tmux.list_windows.return_value = [
        {"index": "0", "name": "claude-pm", "active": True},
        {"index": "1", "name": "claude-dev", "active": False},
    ]
    return tmux

# Tier 2: Domain Object (Built on mock)
@pytest.fixture
def monitor(mock_tmux):
    """Create an IdleMonitor instance with mock tmux."""
    return IdleMonitor(mock_tmux)

# Tier 3: Test Utilities (Supporting fixtures)
@pytest.fixture
def logger():
    """Create a logger for testing."""
    return logging.getLogger("test_module")
```

### 2. Mock Response Patterns

#### Variable Response Mock
```python
@pytest.fixture
def mock_tmux_with_responses():
    """Mock with different responses based on input."""
    tmux = Mock(spec=TMUXManager)

    def capture_pane_response(target, lines=50):
        responses = {
            "test-session:0": "PM content...",
            "test-session:1": "Dev content...",
            "test-session:2": "QA content..."
        }
        return responses.get(target, "Default content")

    tmux.capture_pane.side_effect = capture_pane_response
    return tmux
```

#### Sequential Response Mock
```python
@pytest.fixture
def mock_tmux_sequential():
    """Mock that returns different values on each call."""
    tmux = Mock(spec=TMUXManager)

    call_count = 0
    def evolving_response(target, lines=50):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return "Initial state"
        elif call_count == 2:
            return "State after action"
        else:
            return "Final state"

    tmux.capture_pane.side_effect = evolving_response
    return tmux
```

### 3. Notification Tracking Pattern
```python
@pytest.fixture
def notification_tracker(mock_tmux):
    """Track notifications sent during tests."""
    notifications = []

    def capture_notification(target, message):
        notifications.append((target, message))
        return True

    mock_tmux.send_message.side_effect = capture_notification
    return notifications
```

### 4. Time Control Pattern
```python
@pytest.fixture
def frozen_time():
    """Control time for rate limit and scheduling tests."""
    with patch("datetime.datetime") as mock_datetime:
        test_time = datetime(2024, 1, 15, 2, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = test_time
        # Preserve normal datetime constructor
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        yield test_time
```

### 5. File Discovery Pattern
```python
@pytest.fixture(scope="module")  # Module scope for expensive operations
def fixture_files():
    """Discover test fixture files once per module."""
    fixtures_dir = Path(__file__).parent / "fixtures"
    return list(fixtures_dir.glob("**/*.txt"))
```

## Conversion Steps

### Step 1: Analyze Test Class Structure
```bash
# Use our analysis tool
python docs/development/test-cleanup/validate_test_classes.py tests/target_test.py
```

### Step 2: Identify Fixture Requirements
Look for:
- `setUp()` methods → Need fixtures
- `self.attribute` assignments → Become fixture returns
- Shared test data → Extract to fixtures

### Step 3: Create Fixtures Following Patterns

#### Converting setUp Method
```python
# BEFORE (Class-based)
class TestMonitor(unittest.TestCase):
    def setUp(self):
        self.tmux = Mock(spec=TMUXManager)
        self.monitor = IdleMonitor(self.tmux)
        self.logger = logging.getLogger("test")

# AFTER (Function-based)
@pytest.fixture
def mock_tmux():
    return Mock(spec=TMUXManager)

@pytest.fixture
def monitor(mock_tmux):
    return IdleMonitor(mock_tmux)

@pytest.fixture
def logger():
    return logging.getLogger("test")
```

### Step 4: Convert Test Methods to Functions

#### Simple Conversion
```python
# BEFORE
def test_something(self):
    self.monitor.check_status()
    self.assertTrue(self.tmux.called)

# AFTER
def test_something(monitor, mock_tmux):
    monitor.check_status()
    assert mock_tmux.called
```

#### With Parametrization
```python
# BEFORE
def test_multiple_cases(self):
    for input, expected in [("a", 1), ("b", 2)]:
        result = self.process(input)
        self.assertEqual(result, expected)

# AFTER
@pytest.mark.parametrize("input,expected", [
    ("a", 1),
    ("b", 2)
])
def test_multiple_cases(input, expected, processor):
    result = processor.process(input)
    assert result == expected
```

### Step 5: Handle Special Cases

#### Dynamic Test Generation
```python
# For files like monitor_fixtures_dynamic_test.py
def discover_and_generate_tests():
    """Generate test functions dynamically."""
    for fixture_file in fixture_files:
        # Create test function
        def test_func(file=fixture_file):
            # Test logic here
            pass

        # Register with pytest
        globals()[f"test_{fixture_file.stem}"] = test_func
```

#### Complex Mock Scenarios
```python
# Multiple mock coordination
@pytest.fixture
def mock_system(mock_tmux):
    """Coordinate multiple mocks."""
    mock_scheduler = Mock()
    mock_notifier = Mock()

    # Wire them together
    mock_tmux.scheduler = mock_scheduler
    mock_tmux.notifier = mock_notifier

    return {
        "tmux": mock_tmux,
        "scheduler": mock_scheduler,
        "notifier": mock_notifier
    }
```

## Pattern Recognition Guide

### Identifying Conversion Complexity

#### 🟢 Simple (5-10 mins)
- No setUp/tearDown
- Few test methods (<5)
- No inheritance
- Simple assertions

```python
class TestSimple:
    def test_basic(self):
        assert 1 + 1 == 2
```

#### 🟡 Moderate (15-20 mins)
- setUp method present
- 5-10 test methods
- Some shared state
- Mock usage

```python
class TestModerate(unittest.TestCase):
    def setUp(self):
        self.obj = SomeObject()

    def test_method(self):
        self.obj.do_something()
```

#### 🔴 Complex (20-30 mins)
- unittest.TestCase inheritance
- Complex setUp/tearDown
- Many test methods (>10)
- Nested mocks or patches

```python
class TestComplex(unittest.TestCase):
    def setUp(self):
        self.patcher = patch('module.something')
        self.mock = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
```

### Common Patterns to Fixtures

| Test Pattern | Fixture Solution |
|-------------|------------------|
| `self.mock = Mock()` | `@pytest.fixture def mock(): return Mock()` |
| `self.data = load_data()` | `@pytest.fixture def test_data(): return load_data()` |
| `with patch(...) as mock:` | `@pytest.fixture def patched(): with patch(...) as m: yield m` |
| Time-based tests | `@pytest.fixture def frozen_time(): ...` |
| Notification capture | `@pytest.fixture def notification_tracker(): ...` |

## Troubleshooting

### Issue: Test Count Changed
**Symptom**: Fewer tests after conversion
**Solution**: Check for:
- Dynamic test generation
- Parametrized tests not converted
- Tests inside helper methods

### Issue: Fixture Scope Errors
**Symptom**: `ScopeMismatch` error
**Solution**:
- Function-scoped fixtures can't use module-scoped
- Keep mocks at function scope
- Only use module scope for expensive, read-only operations

### Issue: Test Interference
**Symptom**: Tests pass alone, fail together
**Solution**:
- Ensure all fixtures are function-scoped
- Check for module-level state
- Look for missing mock resets

### Issue: Missing Coverage
**Symptom**: Coverage drops after conversion
**Solution**:
- Verify all test methods converted
- Check dynamic test generation still works
- Ensure parametrized tests expanded properly

## Quick Reference Card

```python
# 1. Basic fixture
@pytest.fixture
def thing():
    return Thing()

# 2. Dependent fixture
@pytest.fixture
def dependent(thing):
    return Process(thing)

# 3. Mock with defaults
@pytest.fixture
def mock_service():
    mock = Mock(spec=Service)
    mock.get.return_value = "default"
    return mock

# 4. Parametrized test
@pytest.mark.parametrize("input,expected", [
    ("a", 1),
    ("b", 2),
])
def test_cases(input, expected):
    assert process(input) == expected

# 5. Skip/Mark tests
@pytest.mark.skip(reason="Not implemented")
def test_future_feature():
    pass
```

## Conversion Checklist
- [ ] Run analysis tool on target file
- [ ] Identify all setUp/tearDown methods
- [ ] Create fixture hierarchy
- [ ] Convert test methods to functions
- [ ] Update assertions (self.assert* → assert)
- [ ] Run tests to verify
- [ ] Check test count preserved
- [ ] Verify coverage maintained
- [ ] Remove empty test class
- [ ] Clean up imports

This playbook will evolve as more conversions are completed. Each successful pattern should be added here for team reference.
