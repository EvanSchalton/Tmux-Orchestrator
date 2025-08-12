# Tmux-Orchestrator v2.0.0 Feedback - Continued Issues

## Previous Issues (from v2 feedback)
1. Monitoring daemon not detecting or logging
2. Agent sessions crash silently
3. Message delivery partially fixed

## New Issue: Agent Spawn Inconsistencies

**Problem**: Agent spawning behavior is highly inconsistent, particularly with briefing messages.

**Observed Behavior**:
- `deploy_team` command reports success ("Successfully deployed fullstack team with 3 agents")
- However, `list_agents` immediately returns empty list
- `get_agent_status` fails with "Agent not found"
- Individual `spawn_agent` calls have mixed results:
  - Backend developer with long briefing: SUCCESS
  - Frontend developer with same long briefing: FAILED ("Failed to start Claude command")
  - Frontend developer with short briefing: FAILED
  - QA engineer with long briefing: FAILED
  - QA engineer with short briefing: FAILED

**Error Pattern**:
- No clear correlation between briefing length and success
- Same error message regardless of input variations
- Suggests underlying command execution issue rather than input validation

**Impact**:
- Cannot reliably deploy teams for projects
- Manual spawning is unpredictable
- Blocks automated orchestration workflows

## Workaround Discovered

Successfully spawned backend developer suggests possible workaround:
1. Try spawning without briefing first
2. Use `send_message` to provide instructions after spawn
3. May need to spawn agents one at a time with delays

## Critical Issue: Monitor Cannot Detect Agents

**Problem**: The monitor daemon cannot detect agents even when they exist in tmux sessions.

**Evidence**:
```
2025-08-10 02:35:35,811 - Agent discovery complete: found 0 agents
2025-08-10 02:35:35,811 - WARNING - No agents found to monitor
2025-08-10 02:35:35,817 - Available sessions: ['agent-kanban-fullstack', 'kanban-backend', 'kanban-frontend', 'kanban-qa']
```

**Root Cause**:
- Monitor sees tmux sessions but reports 0 agents
- The `list_agents` MCP tool also returns agents with status "Active" but type "Unknown"
- Agent detection logic appears broken - it can see sessions but not identify them as containing agents
- Spawned agents crash/exit but sessions remain, leaving empty shells

**Impact**:
- No idle detection possible
- No automatic recovery when agents fail
- No PM notifications about issues
- Manual intervention required to detect crashed agents

## Recommendations for v2.1.0

1. **Logging**: Add verbose logging for spawn command construction and execution
2. **Error Messages**: Provide specific error details (command that failed, exit code, stderr)
3. **Validation**: Pre-validate briefing messages before attempting spawn
4. **Retry Logic**: Implement automatic retry with exponential backoff
5. **Health Check**: Add immediate health check after spawn to verify agent is running

## Test Case for Reproduction

```bash
# This sequence reproduces the issue
tmux-orc team deploy agent-kanban fullstack  # Reports success
tmux-orc agent list                          # Shows empty
tmux-orc agent spawn kanban-frontend developer /workspaces/agent-kanban --briefing "Test"  # Fails
```

---
*Documented: 2025-08-10*
*Version: tmux-orchestrator v2.0.0*
