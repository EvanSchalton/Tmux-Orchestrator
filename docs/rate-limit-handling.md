# Rate Limit Handling

## Overview

The Tmux Orchestrator monitoring daemon now includes automatic rate limit detection and recovery. When Claude API rate limits are reached, the system will:

1. Detect the rate limit error message
2. Extract the reset time
3. Notify the PM about the rate limit
4. Pause monitoring until the rate limit resets
5. Resume monitoring automatically after the reset time

## How It Works

### Detection
The monitor detects rate limits by looking for these patterns in agent output:
- "Claude usage limit reached"
- "Your limit will reset at [TIME] (UTC)"

### Time Extraction
The system extracts the reset time from the error message using regex pattern matching. Supported time formats include:
- `4am`, `4pm` (simple hour format)
- `4:30am`, `11:59pm` (hour:minute format)
- Case-insensitive matching

### Sleep Calculation
The daemon calculates how long to sleep based on:
1. Current UTC time
2. Reset time from the error message
3. A 2-minute safety buffer to ensure the limit has fully reset

If the reset time has already passed today, it assumes the reset is tomorrow.

### PM Notification
Before pausing, the daemon sends a notification to the PM with:
- The rate limit status
- The reset time
- When monitoring will resume
- Instructions that all agents will be responsive after reset

### Automatic Resume
After the calculated sleep duration:
1. The daemon wakes up
2. Sends a notification to PM that monitoring has resumed
3. Continues normal monitoring operations

## Implementation Details

### New AgentState
A new `RATE_LIMITED` state has been added to the `AgentState` enum in `monitor_helpers.py`.

### Key Functions
- `extract_rate_limit_reset_time(content: str) -> Optional[str]`: Extracts reset time from error message
- `calculate_sleep_duration(reset_time_str: str, now: datetime) -> int`: Calculates seconds to sleep

### Monitoring Loop Changes
The monitoring loop in `monitor.py` now:
1. Checks all agents for rate limit messages before normal monitoring
2. If rate limit detected, pauses the entire monitoring cycle
3. Resumes after the sleep period

## Example Flow

```
1. Agent shows: "Claude usage limit reached. Your limit will reset at 4:30pm (UTC)."
2. Monitor detects rate limit at 2:00 PM UTC
3. Calculates sleep: 2.5 hours + 2 min buffer = 9,120 seconds
4. Notifies PM: "Rate limit reached, monitoring will pause until 4:32 PM UTC"
5. Daemon sleeps for 9,120 seconds
6. At 4:32 PM UTC, daemon wakes up
7. Notifies PM: "Rate limit reset! Monitoring resumed."
8. Normal monitoring continues
```

## Testing

Comprehensive tests are available in:
- `tests/test_rate_limit.py` - Core functionality tests
- `tests/test_monitor_daemon_resume.py` - Daemon resume behavior tests

## Error Handling

- Invalid time formats are logged but don't crash the daemon
- If PM notification fails (PM might also be rate limited), monitoring still pauses
- The daemon always resumes after the calculated duration

## Configuration

No configuration is required. The feature is automatically enabled and uses a 2-minute buffer for safety.

## Limitations

- Only detects Claude API rate limits (not other types of errors)
- Assumes rate limit messages follow the standard format
- All monitoring pauses during rate limit (not just the affected agent)
- Maximum sleep duration is effectively 24 hours (if reset time is same time next day)
