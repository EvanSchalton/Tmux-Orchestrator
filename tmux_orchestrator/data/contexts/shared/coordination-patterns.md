# Cross-Session Coordination Patterns

## Administrative Assistant Pattern

**Use Case**: When a PM needs to govern work across multiple sessions without directly interrupting technical teams.

### Problem Solved
- PM working alone becomes idle (no daemon monitoring)
- Need visibility into other sessions' progress
- Direct communication interrupts focused technical work
- Coordination bottlenecks when PM waits for updates

### Solution: Administrative Assistant Agent

Spawn an assistant agent in the governing PM's session that:

1. **Passive Monitoring**: Uses `tmux capture-pane -t other-session:window` to read terminal content
2. **Status Reporting**: Summarizes progress and reports back to PM
3. **Non-Intrusive**: Never interrupts the technical team's work
4. **Activity Generation**: Keeps PM session active for daemon monitoring

### Implementation Example
```bash
# In governing PM session:
tmux-orc spawn agent admin-assistant session:2 --briefing "
You are an Administrative Assistant monitoring cross-session work.

Your responsibilities:
1. Monitor external sessions using: tmux capture-pane -t session:window -p (full buffer)
2. Analyze and summarize findings - don't copy terminal output
3. Work continuously - no sleep timers (daemon handles activity)
4. Provide executive summaries with insights
5. PM will read your terminal when updates needed

Example output format:
[03:45] Project: Daemon Singleton - Executive Summary
- Current Focus: Developer implementing PID validation with atomic operations
- Key Decisions: Chose PID+process check over socket approach
- Progress: Core logic 40% complete, working on exception handling
- Blockers: None identified
- Next Steps: QA preparing concurrent daemon test fixtures
"
```

### PM Reading Assistant Updates
```bash
# PM checks assistant status when needed:
tmux capture-pane -t cleanout:2 -p | tail -20
```

### Benefits
- **Continuous Oversight**: PM maintains visibility without micromanaging
- **Daemon Monitoring**: Assistant activity keeps PM from appearing idle
- **Scalable**: Pattern works for multiple sessions under one coordinator
- **Documentation**: Assistant can maintain progress logs
- **Non-Blocking**: Technical teams work without interruption

### When to Use
- PM coordinating multiple sessions
- Long-running technical implementations
- Need for progress visibility without interruption
- Systematic project management across teams

### Variations
- **Multiple Assistants**: One per external session being monitored
- **Specialized Assistants**: QA assistant, deployment assistant, etc.
- **Escalation Assistants**: Monitor for specific keywords/patterns requiring PM attention

---

**Pattern Origin**: Discovered during cleanout-past project coordination with daemon-singleton-check implementation (2025-08-15)
