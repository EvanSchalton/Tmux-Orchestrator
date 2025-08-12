# Monitor Daemon PM Notification Fix

## Issue Summary
The monitor daemon was failing to send PM notifications about idle agents due to two critical issues:
1. **Incorrect notification delivery method** - Using subprocess CLI calls instead of direct tmux communication
2. **Timing threshold too strict** - 2-minute idle requirement prevented notifications since agents naturally reset every 30-60 seconds

## Root Cause Analysis

### Primary Issue: Subprocess vs Direct Communication
- **Original Code**: Used `subprocess.run(["tmux-orc", "agent", "send", pm_target, message])`
- **Problem**: Subprocess calls were failing silently or timing out
- **Solution**: Direct `tmux.send_message(pm_target, message)` calls

### Secondary Issue: Timing Threshold
- **Original Code**: Required 2 minutes of continuous idle time before notifications
- **Problem**: Agents naturally become active every 30-60 seconds due to UI updates, preventing notifications
- **Solution**: Reduced threshold to 30 seconds

## Implementation Changes

### File: `tmux_orchestrator/core/monitor.py`

#### 1. Idle Threshold Reduction (Lines 793-796)
```python
# OLD: 2-minute threshold
if idle_duration < timedelta(minutes=2):

# NEW: 30-second threshold
if idle_duration < timedelta(seconds=30):  # Reduced from 2 minutes to 30 seconds for faster notifications
    logger.info(f"Agent {target} idle for {idle_duration.total_seconds():.1f}s, need 30s minimum")
```

#### 2. Direct TMux Communication (Lines 831-839)
```python
# OLD: Subprocess CLI calls
result = subprocess.run(
    ["tmux-orc", "agent", "send", pm_target, message],
    capture_output=True, text=True,
)

# NEW: Direct tmux.send_message() calls
logger.info(f"Sending idle notification to PM at {pm_target} about agent {target} (idle for {int(idle_duration.total_seconds())}s)")
success = tmux.send_message(pm_target, message)
```

#### 3. Enhanced Logging (Lines 805, 810, 832, 836)
- Added PM detection logging: "Looking for PM to notify about idle agent {target}"
- Added success confirmation: "Successfully notified PM at {pm_target} about idle agent {target}"
- Added detailed timing information in notifications

#### 4. Crash Notification Fix (Lines 765-771)
```python
# Also fixed crash notifications to use direct calls
success = tmux.send_message(pm_target, message)
```

## Test Results

### Verification Steps Performed
1. **Direct Message Testing**: Confirmed `tmux.send_message()` works correctly
2. **End-to-End Testing**: Monitored logs for actual notification delivery
3. **Timing Validation**: Verified 30-second threshold triggers notifications

### Log Evidence of Success
```
2025-08-11 00:14:45,749 - idle_monitor_daemon - INFO - Sending idle notification to PM at monitor-fixes:2 about agent monitor-fixes:4 (idle for 30s)
2025-08-11 00:14:49,794 - idle_monitor_daemon - INFO - Successfully notified PM at monitor-fixes:2 about idle agent monitor-fixes:4
```

## Impact

### Before Fix
- ❌ No PM notifications delivered
- ❌ Silent failures in notification system
- ❌ Agents could be idle indefinitely without PM awareness

### After Fix
- ✅ PM notifications delivered within 30 seconds
- ✅ Full logging of notification flow
- ✅ Reliable detection and communication of idle agents
- ✅ Enhanced crash detection and auto-restart capabilities

## Deployment Status
- **Status**: ✅ DEPLOYED
- **Commit**: `f6b7534` - "fix: Resolve PM notification system issues in monitor daemon"
- **Monitor Status**: Running with PID 32931
- **Active Since**: 2025-08-11 00:13:25

## Additional Improvements Delivered
As part of this fix, also implemented:
- **Agent crash detection** with automatic restart attempts
- **Enhanced idle detection** with 300ms polling
- **Comprehensive error handling** and logging
- **Cooldown mechanisms** to prevent notification spam

The monitor daemon now provides robust, reliable PM notifications with full visibility into the notification process.
