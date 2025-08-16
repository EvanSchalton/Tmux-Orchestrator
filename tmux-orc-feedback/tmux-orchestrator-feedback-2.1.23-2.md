# Tmux Orchestrator Feedback - Version 2.1.23 (Issue #2)

## Critical Issue: Complete tmux Server Crash

### Issue Description
The entire tmux server crashed during normal agent operations, killing all sessions and agents.

### Timeline of Events
1. Spawned PM in session `kanban-final`
2. PM initialized successfully
3. Started monitoring daemon (PID: 80615)
4. Within 20 seconds, entire tmux server crashed
5. Error: "no server running on /tmp/tmux-1000/default"
6. All agents and sessions lost

### Impact
- **CATASTROPHIC** - Complete loss of all running agents
- No graceful recovery possible
- Work in progress lost
- Requires manual restart of entire system

### Possible Causes
1. Race condition between daemon and agent operations
2. Memory or resource exhaustion
3. Conflict in tmux command execution
4. Bug in tmux-orc's tmux interaction layer

### Related Issues
This crash occurred shortly after fixing the false-positive PM crash detection loop (see feedback file 2.1.23-1.md). The timing suggests possible correlation between:
- Monitoring daemon operations
- Agent spawning/management
- Rapid tmux command execution

### Recovery Steps Required
1. Stop monitoring daemon
2. Manually start new tmux server
3. Re-spawn all agents
4. Restart work from last known state

### Suggested Investigation
1. Check for memory leaks in daemon
2. Review tmux command frequency/throttling
3. Add tmux server health checks
4. Implement crash recovery for tmux server itself

### Workaround
Currently must operate very carefully:
- Avoid rapid agent operations
- Consider running without monitoring
- Save work frequently

### Severity
**CATASTROPHIC** - Complete system failure with no automatic recovery

### Environment
- tmux-orc version: 2.1.23
- tmux version: (system default)
- OS: Linux container
- Date: 2025-08-16
- Time since spawn to crash: ~20 seconds
