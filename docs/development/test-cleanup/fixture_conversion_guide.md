# Fixture Conversion Guide for Tmux Orchestrator Tests

## Overview
This guide provides specific patterns for converting the 21 setup/teardown methods found across 9 test files in the Tmux Orchestrator codebase.

## Common Setup Patterns Found

### 1. Mock TMux Manager Pattern
**Found in**: `monitor_crash_detection_test.py`, `monitor_pm_notifications_test.py`, `monitor_auto_recovery_test.py`

```python
# ❌ Current Pattern
class TestCrashDetectionReliability:
    def setup_method(self):
        self.mock_tmux = Mock(spec=TMUXManager)
        self.mock_monitor = Mock(spec=DaemonMonitor)
        self.test_session = "test-session:0"

# ✅ Converted to Fixtures
@pytest.fixture
def mock_tmux():
    """Mock TMUXManager for testing."""
    return Mock(spec=TMUXManager)

@pytest.fixture
def mock_monitor():
    """Mock DaemonMonitor for testing."""
    return Mock(spec=DaemonMonitor)

@pytest.fixture
def test_session():
    """Standard test session identifier."""
    return "test-session:0"

def test_crash_detection_reliability(mock_tmux, mock_monitor, test_session):
    # Use fixtures directly
    mock_tmux.read_pane.return_value = "bash$"
    # ... rest of test
```

### 2. Fixture File Management Pattern
**Found in**: `rate_limit_handling_test.py`, `monitor_crash_detection_test.py`

```python
# ❌ Current Pattern
class TestRateLimitDetection:
    def setup_method(self):
        self.fixtures_dir = Path(__file__).parent / "fixtures" / "rate_limit_examples"
        self.helper = RateLimitHelper()

# ✅ Converted to Fixtures
@pytest.fixture
def fixtures_dir():
    """Path to test fixtures directory."""
    return Path(__file__).parent / "fixtures" / "rate_limit_examples"

@pytest.fixture
def rate_limit_helper():
    """Rate limit helper instance."""
    return RateLimitHelper()

@pytest.fixture
def load_fixture(fixtures_dir):
    """Factory fixture for loading test files."""
    def _load(filename):
        return (fixtures_dir / filename).read_text()
    return _load

def test_rate_limit_detection(load_fixture, rate_limit_helper):
    content = load_fixture("standard_rate_limit.txt")
    assert rate_limit_helper.is_rate_limited(content)
```

### 3. State Storage Pattern
**Found in**: `monitor_pm_notifications_test.py`, `integration_combined_features_test.py`

```python
# ❌ Current Pattern
class TestPMNotificationDelivery:
    def setup_method(self):
        self.notifications_sent = []
        self.pm_messages = []
        self.mock_tmux = Mock(spec=TMUXManager)

        def capture_send(target, keys):
            if "pm:" in target:
                self.pm_messages.append(keys)

        self.mock_tmux.send_keys.side_effect = capture_send

# ✅ Converted to Fixtures
@pytest.fixture
def notification_tracker():
    """Track notifications and messages sent during tests."""
    class Tracker:
        def __init__(self):
            self.notifications_sent = []
            self.pm_messages = []

        def capture_send(self, target, keys):
            if "pm:" in target:
                self.pm_messages.append(keys)

    return Tracker()

@pytest.fixture
def mock_tmux_with_tracking(notification_tracker):
    """TMux mock that tracks PM messages."""
    mock = Mock(spec=TMUXManager)
    mock.send_keys.side_effect = notification_tracker.capture_send
    return mock

def test_pm_notification_delivery(mock_tmux_with_tracking, notification_tracker):
    # Use the tracking fixtures
    # ... perform test actions
    assert len(notification_tracker.pm_messages) == 1
```

### 4. Complex State Setup Pattern
**Found in**: `simplified_restart_system_test.py`, `monitor_auto_recovery_test.py`

```python
# ❌ Current Pattern
class TestSimplifiedRestartSystem:
    def setup_method(self):
        self.mock_tmux = Mock(spec=TMUXManager)
        self.recovery_coordinator = RecoveryCoordinator(self.mock_tmux)
        self.test_agents = [
            {"session": "test", "window": "0", "name": "agent1"},
            {"session": "test", "window": "1", "name": "agent2"}
        ]

# ✅ Converted to Fixtures
@pytest.fixture
def test_agents():
    """Standard test agent configurations."""
    return [
        {"session": "test", "window": "0", "name": "agent1"},
        {"session": "test", "window": "1", "name": "agent2"}
    ]

@pytest.fixture
def recovery_coordinator(mock_tmux):
    """Recovery coordinator with mock TMux."""
    return RecoveryCoordinator(mock_tmux)

@pytest.fixture
def configured_agents(mock_tmux, test_agents):
    """Pre-configured agents in mock TMux."""
    # Set up mock responses for agent discovery
    mock_tmux.list_windows.return_value = [
        f"{a['session']}:{a['window']}" for a in test_agents
    ]
    return test_agents

def test_simplified_restart_system(recovery_coordinator, configured_agents):
    # Use pre-configured fixtures
    result = recovery_coordinator.restart_agent(configured_agents[0])
    assert result.success
```

### 5. SetUpClass Pattern (Class-level Setup)
**Found in**: `monitor_fixtures_dynamic_test.py`

```python
# ❌ Current Pattern
class TestMonitorFixturesDynamic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures_base = Path(__file__).parent / "fixtures" / "monitor_states"
        cls.all_fixtures = cls._discover_fixtures()

# ✅ Converted to Module Fixture
@pytest.fixture(scope="module")
def fixtures_base():
    """Base path for monitor state fixtures."""
    return Path(__file__).parent / "fixtures" / "monitor_states"

@pytest.fixture(scope="module")
def all_fixtures(fixtures_base):
    """Discover all fixture files once per module."""
    def _discover_fixtures():
        fixtures = {}
        for category in fixtures_base.iterdir():
            if category.is_dir():
                fixtures[category.name] = list(category.glob("*.txt"))
        return fixtures

    return _discover_fixtures()

def test_monitor_fixtures_dynamic(all_fixtures):
    # Use module-scoped fixtures
    assert "crashed" in all_fixtures
    assert len(all_fixtures["crashed"]) > 0
```

## Conversion Patterns by Type

### Pattern A: Simple State Setup
```python
# Before
def setup_method(self):
    self.value = 42
    self.data = {"key": "value"}

# After
@pytest.fixture
def test_value():
    return 42

@pytest.fixture
def test_data():
    return {"key": "value"}
```

### Pattern B: Mock with Configuration
```python
# Before
def setup_method(self):
    self.mock = Mock()
    self.mock.method.return_value = "result"

# After
@pytest.fixture
def configured_mock():
    mock = Mock()
    mock.method.return_value = "result"
    return mock
```

### Pattern C: Cleanup Required
```python
# Before
def setup_method(self):
    self.temp_file = create_temp_file()

def teardown_method(self):
    self.temp_file.unlink()

# After
@pytest.fixture
def temp_file():
    file = create_temp_file()
    yield file
    file.unlink()
```

### Pattern D: Shared Test Utilities
```python
# Before (repeated in multiple test classes)
def setup_method(self):
    self.assert_notification = lambda msg: msg in self.notifications

# After (in conftest.py)
@pytest.fixture
def assert_notification():
    def _assert(msg, notifications):
        assert msg in notifications
    return _assert
```

## Best Practices for Conversion

### 1. Fixture Scoping
```python
# Session scope - expensive setup, shared across all tests
@pytest.fixture(scope="session")
def database_connection():
    return setup_database()

# Module scope - shared within a test module
@pytest.fixture(scope="module")
def api_client():
    return create_api_client()

# Function scope (default) - fresh for each test
@pytest.fixture
def mock_response():
    return Mock()
```

### 2. Fixture Composition
```python
@pytest.fixture
def base_config():
    return {"timeout": 30, "retries": 3}

@pytest.fixture
def extended_config(base_config):
    config = base_config.copy()
    config["debug"] = True
    return config
```

### 3. Parametrized Fixtures
```python
# Convert multiple similar test classes
@pytest.fixture(params=["crashed", "idle", "active"])
def agent_state(request):
    return request.param

def test_agent_monitoring(agent_state, mock_tmux):
    # Test runs for each agent state
    result = monitor_agent(mock_tmux, agent_state)
    assert result.needs_intervention == (agent_state != "active")
```

## Migration Checklist

For each file with setup/teardown:

- [ ] Identify all `setup_method`, `teardown_method`, `setUp`, `tearDown` methods
- [ ] Extract shared state into fixtures
- [ ] Check if cleanup is needed (use yield fixtures)
- [ ] Determine appropriate fixture scope
- [ ] Move common fixtures to `conftest.py`
- [ ] Update test methods to use fixture parameters
- [ ] Remove `self` references
- [ ] Verify all tests still pass
- [ ] Check test isolation (no shared state)

## Common Pitfalls to Avoid

### ❌ Mutable Fixture State
```python
# Bad - mutable state shared between tests
@pytest.fixture
def data():
    return []  # This list is shared!

# Good - fresh instance each time
@pytest.fixture
def data():
    return []  # New list for each test
```

### ❌ Over-Scoping Fixtures
```python
# Bad - module scope for mutable data
@pytest.fixture(scope="module")
def mock_api():
    return Mock()  # Shared mock can cause test interference

# Good - function scope for mocks
@pytest.fixture
def mock_api():
    return Mock()  # Fresh mock for each test
```

### ❌ Hidden Dependencies
```python
# Bad - fixture depends on test order
@pytest.fixture
def counter():
    return next(global_counter)  # Depends on external state

# Good - self-contained fixture
@pytest.fixture
def counter():
    return itertools.count(1)  # Independent counter
```

## File-Specific Conversion Notes

### `monitor_crash_detection_test.py`
- 4 setup methods all follow similar pattern
- Can share mock fixtures across all test functions
- Consider module-level fixture for crash scenarios

### `rate_limit_handling_test.py`
- Fixture file loading is common pattern
- Create parametrized fixture for different rate limit examples
- Helper instance can be session-scoped

### `monitor_pm_notifications_test.py`
- Message tracking pattern is complex
- Consider factory fixture for different tracking scenarios
- Notification cooldown tests may need time mocking

### `monitor_fixtures_dynamic_test.py`
- Uses unittest.TestCase - needs assertion conversion too
- File discovery should be module-scoped
- Consider parametrizing over fixture files

## Validation Commands

After converting setup/teardown in a file:

```bash
# 1. Verify no setup/teardown methods remain
grep -n "def setup\|def teardown\|def setUp\|def tearDown" tests/converted_file_test.py

# 2. Check fixtures are used
grep -n "@pytest.fixture" tests/converted_file_test.py

# 3. Run tests with fixture visibility
poetry run pytest tests/converted_file_test.py -v --fixtures

# 4. Validate conversion
python docs/development/test-cleanup/phase2_conversion_monitor.py validate tests/converted_file_test.py
```
