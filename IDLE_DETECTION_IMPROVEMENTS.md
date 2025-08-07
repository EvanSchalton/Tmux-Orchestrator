# Idle Detection Improvements - Activity-Based Strategy

## Problem Statement

The original idle detection strategy used pattern matching to identify idle agents, but this approach was unreliable:
- Agents showing as "active" when they were actually sitting idle at prompts
- Pattern matching couldn't catch all variations of idle states
- False negatives causing PM to not be notified of truly idle agents

## Solution: Activity-Based Detection

### New Strategy
Instead of pattern matching, we now detect agent activity by monitoring terminal changes:

1. **Take Multiple Snapshots**: Capture 4 terminal snapshots over 300ms
2. **Compare Changes**: If all snapshots are identical, agent is idle
3. **Claude Prompt Detection**: Also check for Claude prompt indicators
4. **Two-Pass Operation**: First check for unsubmitted messages, then idle detection

### Implementation Details

#### Activity Detection Function
```bash
is_agent_idle() {
    local session=$1
    local window=$2
    local agent_name=$3
    
    # Take 4 snapshots over 300ms to detect activity
    local snapshot1=$(tmux capture-pane -t "$session:$window" -p -S -10 2>/dev/null | tail -5 || echo "")
    sleep 0.1
    local snapshot2=$(tmux capture-pane -t "$session:$window" -p -S -10 2>/dev/null | tail -5 || echo "")
    sleep 0.1
    local snapshot3=$(tmux capture-pane -t "$session:$window" -p -S -10 2>/dev/null | tail -5 || echo "")
    sleep 0.1
    local snapshot4=$(tmux capture-pane -t "$session:$window" -p -S -10 2>/dev/null | tail -5 || echo "")
    
    # If all snapshots are identical, agent is idle
    if [ "$snapshot1" = "$snapshot2" ] && [ "$snapshot2" = "$snapshot3" ] && [ "$snapshot3" = "$snapshot4" ]; then
        return 0  # Idle (no terminal activity)
    fi
    
    # Also check if at Claude prompt
    if echo "$snapshot4" | grep -q "│ >"; then
        return 0  # At prompt, likely idle
    fi
    
    return 1  # Not idle (terminal changed)
}
```

## Results

### Before (Pattern Matching)
- Frequent false negatives
- Logs showing "All agents are active" when agents were idle
- Unreliable PM notifications

### After (Activity-Based Detection)
- Accurate idle detection
- Successful PM notifications: "Found idle agents: orchestrator:1 (Orchestrator),corporate-coach-backend:2 (Backend), etc."
- Reliable cooldown mechanism preventing spam
- Two-pass operation catches unsubmitted messages

### Sample Log Output
```
[2025-08-07 20:42:34] Starting Idle Agent Monitor Daemon (interval: 10s)
[2025-08-07 20:42:36] Found idle agents: orchestrator:1 (Orchestrator),corporate-coach-backend:2 (Backend),corporate-coach-corporate-coach:2 (Backend),corporate-coach-frontend:2 (Frontend),corporate-coach-testing:2 (QA),
[2025-08-07 20:42:36] PM is idle, sending notification
[2025-08-07 20:42:44] Notified PM about idle agents: orchestrator:1 (Orchestrator),corporate-coach-backend:2 (Backend),corporate-coach-corporate-coach:2 (Backend),corporate-coach-frontend:2 (Frontend),corporate-coach-testing:2 (QA),
```

## Technical Benefits

1. **Reliable Detection**: Terminal snapshots accurately reflect agent activity
2. **Fast Response**: 300ms detection window provides near real-time monitoring
3. **Robust**: Works regardless of agent output patterns or text content
4. **Efficient**: Minimal overhead with short sleep intervals
5. **Dual Strategy**: Combines activity detection with Claude prompt recognition

## Configuration

- **Detection Window**: 300ms (4 snapshots, 0.1s apart)
- **Terminal Capture**: Last 10 lines, tail -5 for comparison
- **Cooldown**: 5 minutes between notifications per agent
- **Check Interval**: 10 seconds (configurable)

## Future Considerations

This activity-based approach provides a solid foundation for:
- CLI implementation with real-time monitoring
- MCP server integration for programmatic agent management
- Enhanced dashboard with live activity indicators
- Statistical analysis of agent productivity patterns