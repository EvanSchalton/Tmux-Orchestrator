# Indentation Fix for monitor_pm_notifications_test.py

## Issues Found

The file has 4 functions that should be class methods but are at the wrong indentation level:

### 1. Line 244: `test_full_idle_detection_to_notification_flow`
- Should be a method of `TestIntegratedNotificationFlow` class
- Currently at module level (no indent)
- Needs to be indented to be inside the class

### 2. Line 289: `test_idle_pm_receives_idle_agent_notifications`
- Should be a method of `TestPMIdleNotificationBugFix` class
- Currently at module level (no indent)
- Needs to be indented to be inside the class

### 3. Line 329: `test_pm_self_notification_prevention_still_works`
- Should be a method of `TestPMIdleNotificationBugFix` class
- Currently at module level (no indent)
- Needs to be indented to be inside the class

## Quick Fixes

### For Backend Dev - Two Options:

#### Option 1: Fix Indentation (Keep Classes)
```python
# Line 244 - Indent this entire function by 4 spaces
    def test_full_idle_detection_to_notification_flow(self):
        """Test complete flow from idle detection to PM notification."""
        # Add self parameter and use self.mock_tmux, self.monitor, self.logger

# Line 289 - Indent this entire function by 4 spaces
    def test_idle_pm_receives_idle_agent_notifications(self):
        """CRITICAL: Test that idle PMs receive notifications..."""
        # Add self parameter and use self.mock_tmux, self.monitor, self.logger

# Line 329 - Indent this entire function by 4 spaces
    def test_pm_self_notification_prevention_still_works(self):
        """Test that the bug fix doesn't break..."""
        # Add self parameter and use self.mock_tmux, self.monitor, self.logger
```

#### Option 2: Convert to Functions (Recommended)
Since you're converting to pytest anyway, just convert these to standalone functions with fixtures:

```python
# Remove the class definitions and convert all methods to functions
# The problematic functions are already written as functions with fixtures!

# Line 244 - This is already correct for pytest!
def test_full_idle_detection_to_notification_flow(mock_tmux, monitor, logger):
    # This function is ready, just needs the class above it removed

# Line 289 - This is already correct for pytest!
def test_idle_pm_receives_idle_agent_notifications(mock_tmux, monitor, logger):
    # This function is ready, just needs the class above it removed

# Line 329 - This is already correct for pytest!
def test_pm_self_notification_prevention_still_works(mock_tmux, monitor, logger):
    # This function is ready, just needs the class above it removed
```

## Root Cause

Someone started converting these specific test methods to functions but forgot to:
1. Remove the class definitions
2. Convert the other methods in those classes
3. The last 3 test functions are already in pytest style!

## Recommended Solution

Since the file is being converted to pytest anyway:
1. Convert all the class methods to functions
2. Remove all class definitions
3. The last 3 functions are already correct - they just need the empty classes removed
4. Add the standard fixtures at the top:

```python
@pytest.fixture
def mock_tmux():
    return Mock()

@pytest.fixture
def monitor(mock_tmux):
    return IdleMonitor(mock_tmux)

@pytest.fixture
def logger():
    return Mock()
```

This file is actually partially converted already - it just needs to be finished!
