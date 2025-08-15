# Monitor Daemon Fix v2.1.7

## Fixed Issues

### 1. ✅ Monitor Not Running Loop
**Problem**: Daemon only logged startup, never entered monitoring loop
**Root Cause**: `window_info["id"]` doesn't exist - should be `window_info["index"]`
**Fix**:
- Corrected window index access in `_discover_agents`
- Added cycle counting and logging
- Enhanced error handling

### 2. ✅ No Activity Logging
**Problem**: No monitoring cycles logged despite daemon "running"
**Fix**:
- Added comprehensive logging at each stage
- Logs discovery results, cycle times, and agent counts
- Added warning when no agents found with session list

### 3. ✅ Crashed Agent Detection
**New Feature**: Enhanced monitor detects:
- Empty panes (crashed agents)
- Error messages in output
- Idle agents (no output changes)
- Proper state tracking

### 4. ✅ Debug Mode
**New Feature**: Set `TMUX_ORC_DEBUG=true` for verbose logging

## Quick Start

### Option 1: Use Fixed Built-in Monitor
```bash
# The built-in monitor is now fixed
tmux-orc monitor start --interval 30

# Check logs
tail -f /tmp/tmux-orchestrator-idle-monitor.log
```

### Option 2: Use Enhanced Monitor (Recommended)
```bash
# Quick start with debug logging
./start_enhanced_monitor.sh

# Or manually
export TMUX_ORC_DEBUG=true
python -m tmux_orchestrator.core.monitor_enhanced 30

# View logs
tail -f /tmp/tmux-orchestrator-enhanced-monitor.log
```

### Option 3: Test Diagnostics
```bash
# Run comprehensive diagnostics
python test_monitor_daemon.py
```

## What the Enhanced Monitor Does

1. **Proper Daemon Creation**: Double-fork for true daemon process
2. **Agent Discovery**:
   - Finds all tmux sessions
   - Identifies Claude agents by content/window name
   - Handles errors gracefully
3. **Status Monitoring**:
   - Tracks content changes to detect idle agents
   - Detects empty panes (crashed agents)
   - Monitors error indicators
4. **Reporting**:
   - Alerts PM about crashed/idle agents
   - Comprehensive logging of all activities

## Log Output Example

With the fix, you'll now see:
```
2025-08-10 12:00:00 - enhanced_monitor - INFO - Starting monitoring cycle #1
2025-08-10 12:00:00 - enhanced_monitor - INFO - Found 4 agents to monitor
2025-08-10 12:00:00 - enhanced_monitor - DEBUG - Agent backend:0 is active
2025-08-10 12:00:00 - enhanced_monitor - WARNING - Agent frontend:0 is idle
2025-08-10 12:00:00 - enhanced_monitor - ERROR - Agent qa:0 has crashed!
2025-08-10 12:00:30 - enhanced_monitor - INFO - Starting monitoring cycle #2
```

## Debugging Tips

1. **No Agents Found?**
   - Check window names contain "Claude" or agent indicators
   - Run `test_monitor_daemon.py` for discovery diagnostics
   - Ensure agents are actually running

2. **Daemon Still Exiting?**
   - Check `/tmp/monitor-daemon-error.log` for exceptions
   - Use enhanced monitor for better error handling
   - Run in foreground: `python -m tmux_orchestrator.core.monitor_enhanced 30`

3. **Not Detecting Crashes?**
   - Enhanced monitor checks for empty panes
   - Also looks for error messages in output
   - Tracks state across multiple cycles

## Configuration

Enhanced monitor supports:
- `TMUX_ORC_DEBUG=true` - Enable debug logging
- Custom intervals via command line
- Configurable idle thresholds (3 cycles or 2 minutes)

## Known Limitations

1. **PM Notifications**: Still subject to Claude message submission issues
2. **Auto-Recovery**: Not implemented
3. **Config File**: No persistent configuration yet

## Test Results

Successfully tested both monitors with the test script:
- ✅ Standard monitor: Running cycles every 5s, proper logging
- ✅ Enhanced monitor: Running cycles, debug logging working
- ✅ Daemon persistence: Both daemons stay running (not exiting)
- ✅ Error handling: Gracefully handles no agents scenario
- ✅ Cycle logging: Shows each monitoring cycle with timing

## Next Steps

The enhanced monitor provides a solid foundation for:
- Auto-recovery of crashed agents
- Performance metrics collection
- Team coordination improvements
- Health check APIs
