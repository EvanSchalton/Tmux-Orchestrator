# Escape Sequence Fix

## Issue
After sending messages to Claude agents, the escape sequence `[27;5;13~` would appear in the input box without being submitted. This escape sequence represents a modified function key (Shift+F3 or similar).

## Root Cause
The `send_message` implementation was using the `End` key to move the cursor to the end of the line before submitting with `C-Enter`. The `End` key was being interpreted differently by some terminals, producing escape sequences.

## Solution
Removed the `End` key press from the message sending sequence. Since we're already sending the full message and then immediately submitting with `C-Enter`, moving to the end of the line is unnecessary.

### Changes Made
1. **tmux_orchestrator/utils/tmux.py**:
   - Removed `self.send_keys(target, "End")` from `send_message()`
   - Removed `self.send_keys(target, "End")` from `_send_message_fallback()`

2. **tmux_orchestrator/cli/agent.py**:
   - Removed `tmux.send_keys(target, "End")` from the `send` command
   - Simplified to just use `C-Enter` for submission

## Testing
Created test script `test_escape_sequence_fix.py` to verify that no escape sequences appear in the output after sending messages.

## Result
Messages are now sent cleanly without any escape sequences appearing in the Claude input box.
