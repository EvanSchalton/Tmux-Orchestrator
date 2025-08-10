# PRD: Fix Critical Tmux-Orchestrator Issues from User Feedback

## Overview
Address critical issues and feature requests identified in user feedback (v3, v4, v5) to improve system reliability and usability.

## Priority Issues to Fix

### 1. CRITICAL: Monitor Auto-Submit Stuck Messages
**Problem**: Monitor detects "idle with Claude interface" but doesn't submit stuck messages
**Solution**: When detecting idle Claude interface, send Enter key to submit the message
**File**: `tmux_orchestrator/core/monitor.py`
**Priority**: P0 - System is unusable without this

### 2. HIGH: Add Session-Level Attach Command  
**Problem**: No easy way to attach to tmux session containing all agents
**Solution**: Add `tmux-orc session attach` command with auto-discovery
**Files**: Create `tmux_orchestrator/cli/session.py`
**Priority**: P0 - Core monitoring feature

### 3. HIGH: Fix Agent Spawning Reliability
**Problem**: Agents fail to spawn, crash silently, or show as "Unknown" type
**Solution**: 
  - Add retry logic with backoff
  - Verify Claude started successfully
  - Store agent metadata properly
**Files**: `tmux_orchestrator/utils/tmux.py`, `tmux_orchestrator/core/agent_lifecycle.py`
**Priority**: P0 - Can't deploy teams reliably

### 4. MEDIUM: Clarify Orchestrator Role
**Problem**: Window 0 "orchestrator" is just empty bash, no Claude
**Solution**: Either:
  - Remove orchestrator window entirely (recommended)
  - OR install Claude and make it functional
  - Update documentation to clarify human vs agent orchestrator
**Files**: `tmux_orchestrator/core/team_operations/deploy_team.py`
**Priority**: P1 - Confusing but not blocking

### 5. MEDIUM: Add Bulk Agent Commands
**Problem**: Can't manage all agents at once
**Solution**: Add --all flag to agent commands:
  - `tmux-orc agent kill --all`
  - `tmux-orc agent restart --all`  
  - `tmux-orc agent message --all "message"`
**Files**: `tmux_orchestrator/cli/agent.py`
**Priority**: P1 - Quality of life improvement

### 6. MEDIUM: Session Naming Control
**Problem**: Can't customize session names during team deploy
**Solution**: Add --name option to team deploy command
**Files**: `tmux_orchestrator/cli/team_compose.py`
**Priority**: P1 - Better project organization

## Task Breakdown

### Task 1: Fix Monitor Auto-Submit (Backend-Dev)
1. Locate idle detection in monitor.py
2. Add logic to send Enter when "idle with Claude interface" detected
3. Add logging for auto-submission attempts
4. Test with stuck messages

### Task 2: Add Session Attach Command (Backend-Dev)
1. Create new CLI module session.py
2. Implement attach subcommand with:
   - Default: attach to most recent orchestrator session
   - --list: show menu of sessions
   - Specific session name support
3. Update CLI to register new command group
4. Add tests

### Task 3: Fix Agent Spawning (Backend-Dev)
1. Add retry logic to spawn_agent
2. Verify Claude process starts successfully
3. Store agent metadata (type, briefing) properly
4. Fix agent type detection in list_agents
5. Add health check after spawn

### Task 4: Clarify Orchestrator Role (PM to decide approach)
1. Review current orchestrator implementation
2. Decide: remove or make functional?
3. If removing: update deploy_team to skip window 0
4. If keeping: add Claude installation
5. Update documentation either way

### Task 5: Add Bulk Commands (Backend-Dev)
1. Add --all flag to kill, restart, message commands
2. Implement logic to iterate over all agents
3. Add confirmation prompt for destructive operations
4. Test with multiple agents

### Task 6: Session Naming (Backend-Dev)  
1. Add --name parameter to team deploy
2. Use custom name instead of auto-generated
3. Validate name (no spaces, special chars)
4. Update session discovery to handle custom names

## Success Criteria
- Monitor automatically submits stuck messages
- Users can easily attach to tmux sessions
- Agent spawning succeeds reliably (>95% success rate)
- Orchestrator role is clear and consistent
- Bulk operations work on all agents
- Custom session names are supported

## Testing Plan
1. Deploy test team and verify agents spawn correctly
2. Send message that gets stuck, verify monitor auto-submits
3. Test session attach with multiple sessions
4. Test bulk commands with 5+ agents
5. Deploy team with custom name
6. Verify orchestrator changes work as intended

## Timeline
- Day 1-2: Fix critical issues (monitor auto-submit, agent spawning)
- Day 3: Add session attach command
- Day 4: Implement bulk commands and session naming
- Day 5: Clarify orchestrator role and update docs
- Day 6: Testing and bug fixes