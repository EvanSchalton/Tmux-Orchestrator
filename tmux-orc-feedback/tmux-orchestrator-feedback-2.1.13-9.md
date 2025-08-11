# PM Agent Creating New Sessions Instead of Managing Existing Team

## Issue: PM Agent Session Fragmentation and Poor Team Management

### Problem Description
PM agents are creating new agents in separate tmux sessions instead of managing their existing team members, leading to session fragmentation and resource waste.

### Observed Behavior Sequence

#### Initial State
```
kanban-project: 3 windows (PM, QA, Developer)
```

#### Problem Action - PM Creates New Session
When asked to assign dedicated frontend and backend developers, instead of:
- Using existing kanban-project:2 (Developer)
- Properly directing kanban-project:1 (QA)
- Managing the team they already have

The PM agent spawned an entirely new session:
```
kanban-dev-fullstack: 5 windows (orchestrator, PM, Frontend-Dev, Backend-Dev, Developer)
```

#### Result - Team Fragmentation
- **Original team**: kanban-project (PM, QA, unused Developer)
- **New team**: kanban-dev-fullstack (duplicate PM, new developers)
- **Resource waste**: 2 PMs, duplicate roles
- **Management confusion**: Which team is the "real" team?

### Root Cause Analysis

#### 1. PM Agent Behavior Pattern
PM agents appear to default to "create new resources" rather than "manage existing resources" when asked for team adjustments.

#### 2. Session Scope Confusion
PM agent doesn't understand that their role is to manage agents within their session, not create new sessions.

#### 3. Resource Management Failure
No awareness that creating duplicate roles (2 PMs) wastes resources and creates confusion.

### Expected vs Actual Behavior

#### What PM Should Have Done
1. **Assess existing team**: "I have QA and 1 Developer in my session"
2. **Reassign roles**: "Developer, focus on backend. QA, please document UI issues"
3. **Request additional resources**: "Orchestrator, I need 1 more developer for frontend"
4. **Manage within session**: Keep all team members in kanban-project session

#### What PM Actually Did
1. Created entirely new session with new agents
2. Duplicated PM role unnecessarily
3. Ignored existing team members
4. Fragmented team across multiple sessions

### Impact Assessment

#### Technical Impact
- **Resource waste**: 2 PM agents, duplicate developers
- **Session management complexity**: Multiple sessions to coordinate
- **Communication breakdown**: Team members isolated in different sessions

#### Workflow Impact
- **Confusion**: Which team is authoritative?
- **Inefficiency**: Managing multiple sessions instead of one team
- **Coordination failure**: Original team members abandoned

### Specific Instance Details

#### Session Before Issue
```bash
$ tmux list-sessions
kanban-project: 3 windows (PM, QA, Developer)
```

#### Session After PM Action
```bash
$ tmux list-sessions
kanban-project: 3 windows (PM, QA, Developer) 
kanban-dev-fullstack: 5 windows (orchestrator, PM, Frontend-Dev, Backend-Dev, Developer)
```

#### Windows in New Session
```
0: orchestrator
1: Project-Manager    # DUPLICATE PM
2: Frontend-Developer # Could have reassigned existing dev
3: Backend-Developer  # Could have requested 1 additional dev
4: Claude-developer   # ANOTHER duplicate
```

### Recommended Fixes

#### 1. PM Agent Training
PM agents should be trained to:
- **Inventory existing team** before creating new resources
- **Reassign roles** within existing team first
- **Request specific additions** rather than creating entire new teams
- **Manage within session boundaries**

#### 2. Session Management Constraints
- **Prevent PM from creating new sessions** without explicit approval
- **Force PM to work within assigned session**
- **Require justification** for additional agents

#### 3. Resource Management Awareness
- **Detect duplicate roles** and prevent them
- **Show resource utilization** to PM agent
- **Encourage efficient team management**

### Workaround Applied
1. **Manual intervention**: Killed the duplicate session
2. **Redirected PM**: Told them to use existing team
3. **Resource consolidation**: Forced back to single session management

### Long-term Solution
Need tmux-orchestrator features:
1. **Session boundaries**: PM agents should not create new sessions
2. **Resource limits**: Prevent duplicate role creation  
3. **Team management training**: Better PM agent behavior
4. **Resource visibility**: Show PM what team they already have

### Pattern Recognition
This is part of a broader pattern where AI agents:
- Default to "create new" rather than "manage existing"
- Don't understand resource constraints
- Lack organizational awareness
- Over-provision rather than optimize

---
*Reported: 2025-08-10*
*Version: tmux-orchestrator v2.1.13*
*Document: tmux-orchestrator-feedback-2.1.13-9*
*Priority: P1 - HIGH (resource waste and team fragmentation)*
*Status: Recurring pattern requiring manual intervention*