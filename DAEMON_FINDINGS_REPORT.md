# Daemon Message Detection Issue - Investigation Report

## To: Project Manager (msgfix:1)
## From: Daemon Specialist (msgfix:3)
## Date: 2025-08-14

### Executive Summary
I've identified the root cause of the daemon not detecting agent messages properly. The issue is in the `detect_claude_state()` function which incorrectly prioritizes "fresh agent" detection over "message queued" detection.

### Key Findings

#### 1. **Order of Detection Problem**
The `detect_claude_state()` function in `monitor_helpers.py` checks patterns in the wrong order:

```python
# Current flow (INCORRECT):
1. Check for fresh patterns (e.g., "Welcome to Claude Code")
2. Check for unsubmitted messages
3. Check for active conversation
```

This causes agents with typed messages to be incorrectly classified as "fresh" if the terminal still contains "Welcome to Claude Code" text anywhere in the buffer.

#### 2. **Overly Broad Pattern Matching**
The fresh pattern `r'Try ".*" for more information'` is too broad and matches user input like `Try "fix lint errors"`, causing false positives.

#### 3. **Test Failures Confirm Issue**
Running the message detection tests revealed:
- `terminal_with_update_error.txt`: Has message "Try 'fix lint errors'" but detected as FRESH
- `agent_simple_prompt_with_message.txt`: Has message "Test message to see if monitor detects stuck messages" but detected as FRESH

### Technical Details

The issue occurs in this code flow:

1. **monitor.py:609** - Calls `detect_claude_state(content)`
2. **monitor_helpers.py:183-205** - Checks fresh patterns BEFORE checking for messages
3. **Result**: Returns "fresh" even when there's an unsubmitted message

### Impact
- Agents with typed messages are not getting auto-submit assistance
- PM is being notified about "fresh agents" that actually have pending work
- Idle detection is compromised because message state is misidentified

### Recommended Fix
The `detect_claude_state()` function needs to be reordered:

```python
def detect_claude_state(content: str) -> str:
    # 1. FIRST check for actual unsubmitted content
    if has_unsubmitted_message(content):
        return "unsubmitted"

    # 2. THEN check for fresh Claude patterns
    # (with more specific patterns to avoid false positives)

    # 3. Finally check for active conversation
```

### Next Steps
1. Fix the order of detection in `detect_claude_state()`
2. Make fresh patterns more specific to avoid false positives
3. Add test coverage for edge cases
4. Verify fix resolves the daemon detection issues

This fix is critical for proper daemon monitoring functionality.
