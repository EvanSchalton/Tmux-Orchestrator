# Context-Aware Crash Detection

*Implemented: 2025-08-16 (commit 381bf99)*

## Overview

The monitoring daemon now uses context-aware crash detection to prevent false positives when Project Managers (PMs) discuss errors, failures, or issues in their normal conversation flow.

## How It Works

### Safe Context Patterns

The system ignores crash indicators when they appear in these contexts:

1. **Test-Related Discussions**:
   - "test failed", "tests failed"
   - "unit test failed", "integration test failed"
   - "test suite failed", "test run failed"

2. **Build/Deployment Discussions**:
   - "deployment failed", "build failed"
   - "pipeline failed", "job failed"
   - "compilation failed", "release failed"

3. **Error Analysis**:
   - "error occurred", "error was"
   - "previous error", "fixed the error"
   - "debugging the error", "found the error"

4. **Status Reports**:
   - "reported killed", "was killed by"
   - "process was terminated", "service was stopped"

5. **Historical References**:
   - "previously failed", "had failed"
   - "which failed", "that failed earlier"

### Claude UI Detection

The system checks for active Claude conversation markers:
- "Human:", "Assistant:"
- "You:", "I'll", "I will", "Let me"
- UI elements: "╭─", "│", "╰─"
- Activity indicators: "Checking", "Running", "Executing"

## Configuration

### Grace Period
```python
pm_recovery_grace_period_minutes = 3  # Default: 3 minutes
```

PMs are protected from health checks for 3 minutes after recovery to allow initialization.

## Example Scenarios

### ✅ Will NOT Trigger Recovery
```
PM: "The tests failed with 3 errors. Let me investigate..."
PM: "I found that the deployment failed due to missing config"
PM: "The previous build failed, but I've fixed the issue"
```

### ❌ WILL Trigger Recovery
```
bash-5.2$
Segmentation fault (core dumped)
Killed
```

## Troubleshooting

### If False Positives Still Occur

1. Check if the PM output contains unusual patterns
2. Review `/var/log/tmux-orchestrator/monitor.log` for debug info
3. Report the issue with the exact PM output that triggered the false positive

### Adjusting Sensitivity

To add custom safe contexts, modify the `_should_ignore_crash_indicator()` method in `monitor.py`.

## Technical Details

- **Method**: `_should_ignore_crash_indicator()`
- **Location**: `tmux_orchestrator/core/monitor.py`
- **Tests**: `tests/test_context_aware_crash_detection.py`

The implementation uses regex pattern matching and presence detection of Claude UI elements to determine if crash indicators are part of normal conversation.
