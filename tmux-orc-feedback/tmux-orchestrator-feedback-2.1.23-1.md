# Tmux Orchestrator Feedback - Version 2.1.23

## Critical Issue: False Positive PM Crash Detection Loop

### Issue Description
The monitoring daemon is repeatedly killing and respawning healthy PMs due to false positive crash detection.

### Observed Behavior
1. PM is spawned successfully and is functional
2. Daemon detects "failed" keyword somewhere in the PM window
3. Daemon immediately kills the healthy PM
4. Daemon spawns replacement PM
5. Loop repeats every ~30 seconds

### Log Evidence
```
2025-08-16 02:14:14,180 - PM is healthy and ready for coordination
2025-08-16 02:14:16,099 - PM crash indicator found: 'failed' in kanban-v2:2
2025-08-16 02:14:16,100 - 🚨 PM crash detected in session kanban-v2
2025-08-16 02:14:16,108 - Successfully killed crashed PM window kanban-v2:2
2025-08-16 02:14:31,191 - Successfully spawned PM at kanban-v2:2
2025-08-16 02:14:36,201 - ✅ PM recovery SUCCESSFUL
2025-08-16 02:14:44,281 - PM is healthy and ready for coordination
2025-08-16 02:14:46,234 - PM crash indicator found: 'failed' in kanban-v2:2
[Loop continues...]
```

### Root Cause Analysis
The daemon appears to be detecting the word "failed" in the PM's normal output (possibly from error messages, test results, or status reports) and incorrectly interpreting this as a PM crash.

### Impact
- Prevents PM from completing any work
- Creates constant disruption
- Wastes resources on unnecessary recovery
- Makes the system unusable with monitoring enabled

### Suggested Fixes
1. **Improve crash detection logic**: Don't rely solely on keyword detection
   - Check for actual process status
   - Look for specific crash patterns (e.g., "command not found", exit codes)
   - Require multiple indicators before declaring a crash

2. **Add grace period**: Don't immediately kill on first detection
   - Wait and re-check after a delay
   - Require persistent failure indicators

3. **Whitelist normal error messages**:
   - Ignore "failed" in certain contexts (test results, status reports)
   - Look for more specific crash indicators

4. **Add manual override**:
   - Command to mark a PM as "do not auto-recover"
   - Ability to disable auto-recovery per session

### Workaround
Currently must run with monitoring disabled:
```bash
tmux-orc monitor stop
```

### Severity
**CRITICAL** - Makes the monitoring system counterproductive and prevents normal operation

### Version Information
- tmux-orc version: 2.1.23
- Environment: Linux container
- Date: 2025-08-16
