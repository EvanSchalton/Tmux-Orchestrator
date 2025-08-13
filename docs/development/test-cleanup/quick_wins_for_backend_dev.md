# Quick Win Test Conversions - Backend Dev

Hi Backend Dev! Based on my analysis, here are 7 "quick win" files that can be converted rapidly (~3 hours total). These have minimal complexity and low risk.

## ⚡ Quick Wins List (Estimated: 2.75 hours total)

### 1. **tests/compaction_detection_test.py** ⏱️ 15 mins
- **Classes**: 1 (TestCompactionDetection)
- **Functions**: 4
- **Complexity**: Low - Single test class with simple assertions
- **Pattern**: Basic class → function conversion

### 2. **tests/monitor_daemon_resume_test.py** ⏱️ 20 mins
- **Classes**: 1 (TestMonitorDaemonResume)
- **Functions**: 4
- **Complexity**: Low - Basic daemon tests
- **Pattern**: Simple setUp → fixture

### 3. **tests/test_cli/errors_test.py** ⏱️ 20 mins
- **Classes**: 1 (TestCLIErrors)
- **Functions**: 12
- **Complexity**: Low - CLI error handling
- **Pattern**: Mock CLI setup → fixture

### 4. **tests/test_cli/vscode_setup_test.py** ⏱️ 20 mins
- **Classes**: 1 (TestVSCodeSetup)
- **Functions**: 12
- **Complexity**: Low - VSCode integration tests
- **Pattern**: Mock file system → fixture

### 5. **tests/test_core/test_recovery/check_agent_health_test.py** ⏱️ 30 mins
- **Classes**: 1 (TestCheckAgentHealth)
- **Functions**: 6
- **Complexity**: Medium-Low - Some setUp complexity
- **Pattern**: Mock agent states → fixtures

### 6. **tests/test_core/test_recovery/restore_context_test.py** ⏱️ 30 mins
- **Classes**: 2 (TestRestoreContext)
- **Functions**: 9
- **Complexity**: Medium-Low - File operations
- **Pattern**: Mock file system → fixtures

### 7. **tests/test_core/test_recovery/discover_agents_test.py** ⏱️ 30 mins
- **Classes**: 2 (TestDiscoverAgents)
- **Functions**: 11
- **Complexity**: Medium-Low - Agent discovery
- **Pattern**: Mock tmux discovery → fixtures

## Why These Are Quick Wins

1. **Minimal setUp/tearDown** - Most have simple or no setUp methods
2. **Low interdependencies** - Self-contained test logic
3. **Clear patterns** - Similar to files you've already converted
4. **Low risk** - Won't break critical functionality
5. **Good test/class ratio** - Fewer classes to convert

## Suggested Conversion Order

1. Start with `compaction_detection_test.py` (warmup - 15 mins)
2. Batch the CLI tests together (similar patterns - 40 mins)
3. Batch the recovery tests together (related functionality - 90 mins)

## Conversion Tips

### For compaction_detection_test.py:
```python
# Current pattern in file
class TestCompactionDetection:
    def setup_method(self):
        self.helper = MonitorHelper()

# Convert to:
@pytest.fixture
def monitor_helper():
    return MonitorHelper()
```

### For CLI tests:
- They likely mock CLI arguments and filesystem
- Use fixtures for mock argument parsing
- Consider parametrizing error scenarios

### For recovery tests:
- They mock tmux and agent states
- Follow the three-tier fixture pattern
- Pre-configure agent health states in fixtures

## After Quick Wins

Once these 7 files are done:
- 11 fewer classes to convert
- Good patterns established for CLI and recovery tests
- Ready to tackle higher complexity files

Let me know which one you're starting with, and I'll monitor your progress!
