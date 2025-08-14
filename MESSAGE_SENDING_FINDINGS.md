# Message Sending Investigation Report

## Executive Summary
The tmux message sending functionality has inconsistent implementations and conflicting documentation about whether to use Enter or Ctrl+Enter for message submission to Claude.

## Key Findings

### 1. Multiple Implementations Exist
- **TMUXManager.send_message()** (tmux_orchestrator/utils/tmux.py:92-157)
  - Uses regular Enter for submission
  - Has safety checks for Claude initialization
  - Includes timing delays and fallback method

- **agent send command** (tmux_orchestrator/cli/agent.py)
  - Bypasses TMUXManager.send_message()
  - Implements its own logic with Enter
  - Uses similar pattern but with customizable delays

### 2. Conflicting Documentation
- Code comments say "Claude Code uses Enter, not Ctrl+Enter"
- Development docs reference research showing Ctrl+Enter might be needed
- Legacy docs mention fixing escape sequences by removing End key

### 3. Current Implementation Analysis

#### TMUXManager.send_message() Flow:
1. Wait for Claude to be ready (checks for "│ >" or "Bypassing Permissions")
2. Press Ctrl+C to clear any existing input
3. Press Ctrl+U to clear the input line
4. Send message text as literal (properly escaped)
5. Wait 3+ seconds for processing
6. Press Enter to submit

#### Potential Issues:
1. **Enter vs C-Enter**: Documentation suggests C-Enter was tested but current code uses Enter
2. **Timing**: Fixed delays might not work for all scenarios
3. **State Detection**: Only checks for specific strings to determine Claude readiness
4. **No Verification**: Doesn't verify if message was actually submitted

### 4. Test Scripts Created
- `test_message_sending.py`: Tests various send methods and timing
- `test_message_submission.py`: Comprehensive test of submission methods including C-Enter

## Recommendations

### Immediate Actions:
1. **Test C-Enter**: The docs suggest it worked before, but code uses Enter
2. **Add Verification**: Check if message was actually submitted by monitoring pane content
3. **Dynamic Timing**: Adjust delays based on message length and system response

### Code Changes Needed:
1. Try C-Enter instead of Enter in send_message()
2. Add post-submission verification
3. Implement retry logic for failed submissions
4. Unify implementations between TMUXManager and agent send

### Testing Strategy:
1. Test with different Claude states (idle, busy, just started)
2. Test with various message types (short, long, special chars)
3. Verify submission with pane capture
4. Test both Enter and C-Enter systematically

## Critical Code Locations
- Main implementation: tmux_orchestrator/utils/tmux.py:92-157
- CLI override: tmux_orchestrator/cli/agent.py (send command)
- Test for unsubmitted messages: Look for has_unsubmitted_message() function

## Next Steps
1. Run the test scripts to determine which submission method works
2. Update send_message() based on test results
3. Add verification logic to ensure messages are submitted
4. Create unit tests for the working method
