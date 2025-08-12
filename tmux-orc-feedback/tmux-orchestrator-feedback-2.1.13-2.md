# Tmux-Orchestrator Session Management Issues

## Issue: Zombie Sessions and Agent Fragmentation

### Problem Description
Agents are being spawned across multiple disconnected tmux sessions, creating "zombie" sessions that:
- Fragment the team across different session namespaces
- Make coordination difficult
- Leave orphaned agents that aren't properly managed

### Observed Behavior
When deploying agents, the system created:
- `kanban-project` - Main session with PM, QA, and Developer
- `kanban-loadtest` - Isolated developer
- `kanban-frontend-test` - Another isolated frontend agent
- `kanban-qa` - Separate QA agent
- `kanban-testing-testing` - Another testing session with 4 windows

### Expected Behavior
Agents should be:
- Consolidated in logical session groupings
- Easy to manage as a cohesive team
- Properly namespaced to avoid confusion

### Workaround Applied
1. Manually killed zombie sessions using `tmux kill-session`
2. Redeployed team using `deploy_team` command with proper naming
3. Created consolidated `kanban-dev-fullstack` session

### Suggested Improvements
1. **Session naming convention**: Enforce consistent naming patterns
2. **Session cleanup**: Auto-cleanup orphaned sessions before deploying new teams
3. **Session consolidation**: Provide command to merge agents from multiple sessions
4. **Session status**: Show session health/activity in list_agents output
5. **Prevent duplicates**: Check for existing agents before creating new ones

### Impact
- Medium severity - causes confusion but has workarounds
- Affects team coordination and orchestration efficiency
- Manual cleanup required frequently

---
*Reported: 2025-08-10*
*Version: tmux-orchestrator v2.1.13*
*Document: tmux-orchestrator-feedback-2.1.13-2*
*Priority: P1 - HIGH*
