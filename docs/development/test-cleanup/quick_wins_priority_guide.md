# Quick Wins Priority Guide for Backend Dev

🎉 **MILESTONE ACHIEVED: All 9/9 setUp/tearDown files converted!**

Now tackling the 7 "quick win" files in optimal order for maximum efficiency.

## ⚡ Recommended Conversion Order

### **BATCH 1: Warmup (15 minutes)**
Start with the simplest file to establish momentum:

#### 1. `tests/compaction_detection_test.py` ⏱️ 15 mins
- **Why first**: Single class, 4 functions, very straightforward
- **Classes**: 1 (TestCompactionDetection)
- **Pattern**: Basic class → function conversion
- **No setUp/tearDown**: Just convert methods to functions

```python
# Current pattern:
class TestCompactionDetection:
    def test_compacting_keyword_detection(self):
        # Simple assertions

# Convert to:
def test_compacting_keyword_detection():
    # Same logic, no self references
```

### **BATCH 2: CLI Tests (40 minutes)**
Group these together - they follow similar patterns:

#### 2. `tests/test_cli/errors_test.py` ⏱️ 20 mins
- **Classes**: 1 (TestCLIErrors)
- **Functions**: 12
- **Pattern**: Mock CLI arguments and error handling

#### 3. `tests/test_cli/vscode_setup_test.py` ⏱️ 20 mins
- **Classes**: 1 (TestVSCodeSetup)
- **Functions**: 12
- **Pattern**: Mock file system operations

**CLI Batch Tips**:
- Both likely mock argparse and file operations
- Create fixtures for mock CLI arguments
- Follow the three-tier pattern: mock → CLI object → utilities

### **BATCH 3: Recovery Tests (90 minutes)**
These are related and can share fixture patterns:

#### 4. `tests/test_core/test_recovery/check_agent_health_test.py` ⏱️ 30 mins
- **Classes**: 1 (TestCheckAgentHealth)
- **Functions**: 6
- **Pattern**: Mock agent health states

#### 5. `tests/test_core/test_recovery/discover_agents_test.py` ⏱️ 30 mins
- **Classes**: 2 (TestDiscoverAgents)
- **Functions**: 11
- **Pattern**: Mock tmux discovery operations

#### 6. `tests/test_core/test_recovery/restore_context_test.py` ⏱️ 30 mins
- **Classes**: 2 (TestRestoreContext)
- **Functions**: 9
- **Pattern**: Mock file system and context restoration

**Recovery Batch Tips**:
- All use similar tmux mocking patterns
- Agent discovery fixtures can be shared
- Mock file operations for context restoration

### **BATCH 4: Daemon Test (20 minutes)**

#### 7. `tests/monitor_daemon_resume_test.py` ⏱️ 20 mins
- **Classes**: 1 (TestMonitorDaemonResume)
- **Functions**: 4
- **Pattern**: Basic daemon restart testing

## Fixture Patterns for Quick Wins

### CLI Tests Pattern
```python
@pytest.fixture
def mock_args():
    """Mock CLI arguments."""
    args = Mock()
    args.verbose = False
    args.config = "/tmp/test"
    return args

@pytest.fixture
def cli_runner(mock_args):
    """CLI runner with mock args."""
    return CLIRunner(mock_args)
```

### Recovery Tests Pattern
```python
@pytest.fixture
def mock_agent_health():
    """Mock agent health responses."""
    return {
        "session:1": "healthy",
        "session:2": "crashed",
        "session:3": "unresponsive"
    }

@pytest.fixture
def recovery_manager(mock_tmux, mock_agent_health):
    """Recovery manager with mock dependencies."""
    manager = RecoveryManager(mock_tmux)
    manager.agent_health = mock_agent_health
    return manager
```

## Conversion Checklist for Each File

For each quick win file:
- [ ] Remove class definition(s)
- [ ] Convert methods to functions
- [ ] Add fixtures at top of file
- [ ] Replace `self.x` with fixture parameter `x`
- [ ] Update assertions (self.assert* → assert)
- [ ] Run tests to verify
- [ ] Check test count preserved
- [ ] Clean up imports if needed

## Expected Outcomes

After completing all 7 quick wins:
- **Total progress**: 33/56 files (59%)
- **Classes eliminated**: 11 fewer classes
- **Time invested**: ~3 hours
- **Patterns established**: CLI and recovery test fixtures
- **Momentum built**: Ready for medium complexity files

## Success Metrics

✅ **All 7 files should**:
- Convert without test loss
- Follow established fixture patterns
- Pass all tests after conversion
- Complete within estimated timeframes

## Next Steps After Quick Wins

Once these 7 are complete, recommend:
1. **Server Tools Batch** (16 files) - Similar patterns, can be batch converted
2. **Medium Priority** (remaining files) - Apply established patterns
3. **Final Complex Files** - Use all learned patterns

Let me know which file you're starting with, and I'll monitor your progress!

🚀 **Ready to knock out these quick wins efficiently!**
