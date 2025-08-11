# CRITICAL: Monitoring Daemon Complete Failure

## Severity: CRITICAL - System Unusable Without Manual Intervention

### Problem Summary
The monitoring daemon is completely non-functional. It fails to detect:
1. Agents without Claude running (just bash prompts)
2. Crashed/exited Claude sessions
3. Any form of agent health issues

### Evidence Collected

#### Test 1: New Team Deployment
- Deployed fullstack team via `deploy_team` command
- Result: All 3 agents created with only bash prompts, NO Claude
- Monitoring daemon: No detection, no alerts, no PM notification

#### Test 2: Message Delivery to Dead Agents
- Sent briefing messages to kanban-dev-fullstack agents
- Messages delivered to bash prompts (visible in tmux capture)
- Agents received messages as bash commands, causing errors
- Example: "Backend: command not found"

#### Test 3: Existing Session Check
- kanban-project:0 (PM) - Has Claude running ✓
- kanban-dev-fullstack:0,1,2 - NO Claude, just bash ✗
- No monitoring alerts for any failed agents

### Critical Impact
1. **Silent Failures**: Agents appear "Active" but are dead
2. **Wasted Resources**: Orchestrator sends messages to dead agents
3. **No Recovery**: No automatic restart or notification
4. **False Status**: `list_agents` shows all as "Active"
5. **Team Dysfunction**: Entire teams can be non-functional without detection

### Root Cause Indicators
- Daemon only logs startup, never logs checks
- 30-second interval should produce ~14 logs in 7 minutes, produces 0
- Likely issue: Main monitoring loop never executes
- Possible: Thread/process starts but immediately exits/blocks

### Immediate Workaround Needed
```bash
# Manual health check script
for session in $(tmux list-sessions -F '#{session_name}'); do
  for window in $(tmux list-windows -t $session -F '#{window_index}'); do
    if tmux capture-pane -t $session:$window -p | grep -q '^>.*shortcuts$'; then
      echo "✓ $session:$window has Claude"
    else
      echo "✗ $session:$window MISSING Claude"
    fi
  done
done
```

### Recommended Fix Priority
1. **P0 - Critical**: Fix monitoring loop execution
2. **P0 - Critical**: Add health check endpoint
3. **P1 - High**: Auto-restart dead agents
4. **P1 - High**: Alert mechanism for failures
5. **P2 - Medium**: Status accuracy in list_agents

### Business Impact
- **100% failure rate** for automated orchestration
- Requires constant manual intervention
- Makes multi-agent coordination impossible
- Defeats purpose of orchestration tool

---
*Reported: 2025-08-10*
*Version: tmux-orchestrator v2.1.13*
*Document: tmux-orchestrator-feedback-2.1.13-1*
*Priority: P0 - CRITICAL*
*Status: BLOCKING - Cannot proceed with automated workflows*