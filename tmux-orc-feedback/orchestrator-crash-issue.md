# TMUX Orchestrator Critical Issue Report

## Version
Unable to determine version (tmux-orc --version not available)

## Critical Issue: Agent Crashes Not Detected

### Problem Description
Agents are crashing silently without detection by the orchestrator daemon. This is causing critical development delays.

### Observed Behavior
1. Developer agent at kanban-project:2 crashed twice today
2. No error messages or notifications from orchestrator
3. Manual restart required each time
4. Work blocked until manual intervention

### Impact
- Development work stopped unexpectedly
- Frontend team blocked waiting for backend auth
- Manual monitoring required (inefficient)

### Current Workaround
Created `/workspaces/agent-kanban/monitor-agents.sh` script that:
- Checks agent health by looking for Claude prompt
- Lists dead agents
- Can restart dead agents with --restart flag

### Requested Features
1. **Automatic crash detection** - Monitor agent health every 30 seconds
2. **Auto-restart capability** - Restart crashed agents automatically
3. **Crash notifications** - Alert PM when agent crashes
4. **Health endpoint** - API to check agent status
5. **Crash logs** - Capture last output before crash

### Reproduction Steps
1. Spawn agent with tmux-orchestrator
2. Agent crashes after ~30-60 minutes of work
3. Orchestrator doesn't detect or report crash
4. Manual intervention required

### Temporary Solution
Running monitor script every 5 minutes via cron:
```bash
*/5 * * * * /workspaces/agent-kanban/monitor-agents.sh --restart >> /tmp/agent-monitor.log 2>&1
```

### Priority
CRITICAL - Blocking development progress

---
*Report Date: Aug 10, 2025*
*Affected Version: Unknown (need version command)*
*Workaround: monitor-agents.sh script*