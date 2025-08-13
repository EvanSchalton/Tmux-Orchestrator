# Phase 2 Test Class Conversion Priorities

## Executive Summary
- **39 files** need class-to-function conversion
- **21 setup/teardown methods** require fixture conversion
- **2 files** use unittest.TestCase inheritance (most complex)
- **11 files** rated as "hard" difficulty

## 🔴 High Priority - Complex Cases

### 1. Files with unittest.TestCase Inheritance (Need Special Care)
These require the most careful conversion as they use unittest patterns:

1. **`tests/monitor_fixtures_dynamic_test.py`**
   - Uses `unittest.TestCase`
   - Has `setUpClass` method
   - Needs conversion from unittest assertions to pytest

2. **`tests/monitor_message_detection_test.py`**
   - Uses `unittest.TestCase`
   - Needs assertion method conversions

### 2. Files with Setup/Teardown Methods (9 files, 21 methods)
These need conversion to pytest fixtures:

**Most Complex (multiple setup methods):**
1. **`tests/monitor_crash_detection_test.py`** - 4 classes with setup_method
2. **`tests/monitor_pm_notifications_test.py`** - 4 classes with setup_method
3. **`tests/rate_limit_handling_test.py`** - 3 classes with setup_method
4. **`tests/monitor_auto_recovery_test.py`** - 3 classes with setup_method
5. **`tests/simplified_restart_system_test.py`** - 3 classes with setup_method

**Single Setup Methods:**
6. `tests/integration_rate_limit_test.py`
7. `tests/integration_compaction_test.py`
8. `tests/integration_combined_features_test.py`
9. `tests/monitor_fixtures_dynamic_test.py` (setUpClass)

## 🟡 Medium Priority - Large Classes

### Files with Most Test Classes (Top 5)
1. **`tests/monitor_helpers_test.py`** - 10 classes, 46 test methods
2. **`tests/rate_limit_handling_test.py`** - 7 classes, 25 test methods
3. **`tests/test_server/test_tools/report_activity_test.py`** - 6 classes, 34 test methods
4. **`tests/test_server/test_tools/get_agent_status_test.py`** - 5 classes, 30 test methods
5. **`tests/monitor_crash_detection_test.py`** - 4 classes, 16 test methods

### Files with Largest Single Classes (>15 methods)
1. **`tests/test_server/test_tools/create_team_test.py`** - TestCreateTeam has 23 methods
2. **`tests/test_server/test_tools/handoff_work_test.py`** - TestHandoffWork has 21 methods
3. **`tests/test_server/test_tools/track_task_status_test.py`** - TestTrackTaskStatus has 21 methods
4. **`tests/test_server/test_tools/run_quality_checks_test.py`** - TestRunQualityChecks has 20 methods
5. **`tests/test_server/test_tools/get_agent_status_test.py`** - TestGetAgentStatus has 20 methods

## 🟢 Lower Priority - Simple Cases

### Easy Conversions (5 files)
Simple classes with no special methods or inheritance:
- Basic test classes with only test methods
- No setup/teardown
- No inheritance
- Small number of methods per class

## Recommended Conversion Order

### Phase 2.1 - Foundation (Week 1)
1. Start with **easy files** to establish patterns
2. Document conversion patterns for the team

### Phase 2.2 - Setup/Teardown (Week 1-2)
1. Convert files with `setup_method` to pytest fixtures
2. Start with single setup method files
3. Move to complex multi-setup files

### Phase 2.3 - Inheritance (Week 2)
1. Convert `unittest.TestCase` files carefully
2. Replace unittest assertions with pytest assertions
3. Convert `setUpClass` to class-scoped fixtures

### Phase 2.4 - Large Classes (Week 2-3)
1. Split large test classes (>15 methods)
2. Group by functionality
3. Consider creating separate test files

## Conversion Patterns Reference

### Setup Method → Fixture
```python
# Before
class TestFeature:
    def setup_method(self):
        self.data = create_test_data()

    def test_something(self):
        assert self.data.value == expected

# After
@pytest.fixture
def test_data():
    return create_test_data()

def test_feature_something(test_data):
    assert test_data.value == expected
```

### unittest.TestCase → pytest
```python
# Before
class TestFeature(unittest.TestCase):
    def setUp(self):
        self.value = 42

    def test_something(self):
        self.assertEqual(self.value, 42)

# After
@pytest.fixture
def value():
    return 42

def test_feature_something(value):
    assert value == 42
```

## Validation Command
After each file conversion:
```bash
cd /workspaces/Tmux-Orchestrator
python docs/development/test-cleanup/phase2_conversion_monitor.py validate tests/converted_file_test.py
```
