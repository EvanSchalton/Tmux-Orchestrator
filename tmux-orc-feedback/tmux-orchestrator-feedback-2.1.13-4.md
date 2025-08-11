# TMUX Orchestrator Feedback

## Issue 1: Agent List Inconsistency
**Problem**: When using `deploy_team`, the agents are spawned successfully but don't always appear in `list_agents` output immediately.

**Example**:
- Deployed "kanban-testing" team with 3 agents
- `list_agents` only showed the PM agent, not the testing team
- Running `tmux ls` confirmed the session exists with 4 windows

**Workaround**: Use direct `spawn_agent` calls instead of `deploy_team` for better visibility.

## Issue 2: Session Naming Convention
**Problem**: The `deploy_team` function creates sessions with concatenated names like "kanban-testing-testing" which is redundant.

**Suggestion**: Simplify naming to just use the team_name parameter.

## Issue 3: Agent Type Detection
**Problem**: Some agents show type as "Frontend" when they should be "QA" or other types.

**Example**: kanban-frontend-test session shows type "Frontend" instead of "QA"

## Issue 4: Window Indexing
**Problem**: Windows are indexed starting from 0, but when spawning multiple agents in the same session, the window numbers increment correctly but can be confusing for coordination.

**Suggestion**: Consider using named windows consistently instead of numeric indices.

## Positive Feedback
- The `spawn_agent` function works reliably when specifying session names
- The briefing_message parameter is excellent for providing context
- Being able to spawn agents in existing sessions is very useful for team coordination

## Recommended Improvements
1. Add a `get_agent_output` function to retrieve what an agent has been doing
2. Add a `wait_for_agent_ready` function to ensure agent is fully initialized
3. Improve `list_agents` to always reflect current state accurately
4. Add session cleanup commands for removing finished agents
5. Consider adding agent status beyond just "Active" (e.g., "Working", "Idle", "Error")