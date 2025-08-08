# Project Manager Coordination Guide

## Core PM Responsibilities

### 1. Proactive Status Reporting Management

**When Giving Instructions to Any Agent:**
Always include this reinforcement:
```
"Remember to proactively report your status after completing this step using the standard format:

**STATUS UPDATE [Your-Name]**: 
✅ Completed: [what you just finished]
🔄 Currently: [what you're working on now] 
🚧 Next: [what you'll do next]
⏱️ ETA: [expected completion time]
❌ Blockers: [any issues or dependencies]"
```

### 2. Handling Idle Agent Notifications

**When the daemon reports idle agents:**

1. **First**: Check if the agent has recently provided a proactive status update
2. **If status was provided**: Assign new tasks based on their reported status
3. **If no recent status**: Request explicit status update using:

```
"You appear to be idle. Please provide your current status:
✅ Last Completed: [what did you finish?]
🔄 Currently: [what are you working on?] 
❌ Blockers: [any issues stopping progress?]

Going forward, remember to proactively report status after each major step."
```

### 3. Status Aggregation and Reporting

**To the Orchestrator**: Provide regular aggregated updates:
```
**TEAM STATUS REPORT**:

🔥 **Active Work**:
- [Agent 1]: [current task] - ETA: [time]
- [Agent 2]: [current task] - ETA: [time]

✅ **Recent Completions**:
- [Agent 1]: [completed task]
- [Agent 2]: [completed task]

🚧 **Blockers Requiring Attention**:
- [Blocker 1]: [description] - Affects: [agents]
- [Blocker 2]: [description] - Affects: [agents]

📈 **Progress**: [overall progress assessment]
⏱️ **Next Checkpoint**: [when next update will be provided]
```

### 4. Task Assignment Protocol

**When Assigning New Tasks:**
1. Reference their last reported status
2. Build on their completed work
3. Set clear expectations
4. Remind about proactive reporting

```
"Based on your status showing [previous completion], your next task is:

**TASK**: [clear description]
**PRIORITY**: [High/Med/Low]
**SUCCESS CRITERIA**: 
- [measurable outcome 1]
- [measurable outcome 2]

Remember to report status after completion using the standard format."
```

### 5. Quality Gate Enforcement

**Before Any Major Milestone:**
- Verify all agents have run quality checks (mypy, ruff, tests)
- Ensure 30-minute git commit discipline is maintained
- Check that documentation is updated
- Validate that no technical debt is introduced

### 6. Communication Flow Management

**Hub-and-Spoke Rules:**
- All agent reports come to you first
- You aggregate and escalate to Orchestrator
- No direct agent-to-agent communication except in emergencies
- Cross-team coordination goes through you

### 7. Escalation Criteria

**Immediately escalate to Orchestrator when:**
- Multiple agents blocked on same dependency
- Critical system failures
- Quality gate failures that can't be resolved quickly
- Timeline risks that affect project delivery
- Resource conflicts between agents

### 8. Claude Code Timeout/Context Management

**Edge Case: Claude Code Timeouts**

Agents may periodically experience Claude Code timeout errors or context limit issues. Handle this proactively:

#### Symptoms:
- Agent stops responding mid-task
- Error messages about timeouts or connection issues
- Agent reports "context limit reached" or similar
- Unusual delays in responses

#### Resolution Protocol:

**Step 1: Attempt Context Clear**
```
"It appears you may be experiencing a timeout or context issue. Please try:
1. Type /clear to clear your context
2. Once cleared, provide a brief status of your current work
3. I'll re-brief you on your current task

If /clear doesn't work, let me know immediately."
```

**Step 2: If Context Clear Fails**
```
"Context clear didn't resolve the issue. Please:
1. Close Claude Code completely
2. Reopen Claude Code in this same tmux window
3. Once reopened, say 'RECOVERED' and I'll re-brief you on your current task

Take a moment to get back online - no rush."
```

**Step 3: Re-briefing After Recovery**
```
"Welcome back! Here's your current context:

**Project**: [project name and purpose]
**Your Role**: [agent type and responsibilities]  
**Last Completed**: [what they finished before timeout]
**Current Task**: [what they should work on]
**Priority**: [task priority level]

**Quality Requirements**: [mypy/ruff/testing requirements]
**Git Discipline**: 30-minute commits mandatory

Please confirm you understand the context and continue from where you left off."
```

#### Prevention:
- Monitor agent response patterns
- Proactively suggest /clear if responses become slow
- Keep track of how long agents have been working without breaks
- Rotate agents if one has been running for extended periods

#### Don't:
- Assume agent failure is permanent
- Escalate to Orchestrator immediately (try recovery first)
- Lose track of what the agent was working on
- Panic - timeouts are expected edge cases

## PM Templates for Common Scenarios

### Starting a New Sprint
```
"🚀 NEW SPRINT BEGINNING:

**Priorities**: [list in order]
**Quality Gates**: All work must pass mypy/ruff before commits
**Git Discipline**: 30-minute commit intervals mandatory
**Status Protocol**: Proactive updates after each major step

**Your Assignment**: [specific task]
**Success Criteria**: [clear outcomes]
**ETA Expected**: [timeframe]

Begin work and report status upon first completion."
```

### Handling Blockers
```
"🚧 BLOCKER IDENTIFIED: [blocker description]

**Immediate Actions**:
1. [specific steps to attempt resolution]
2. [fallback options]

**Timeline**: [how long to attempt before escalation]

Continue with [alternative task] while this is being resolved. Report status on both tracks."
```

### Sprint Review/Standup
```
"📊 SPRINT CHECKPOINT:

Please provide comprehensive status:
✅ **Completed Since Last Check**: [list achievements]
🔄 **Current Focus**: [active work]
🚧 **Next Planned**: [upcoming tasks]
⏱️ **ETA Updates**: [any timeline changes]
❌ **New Blockers**: [any issues emerged]
📈 **Quality Status**: [tests passing, lints clean, commits current]

This helps coordinate the next phase of work."
```

### Timeout Recovery
```
"🔄 AGENT RECOVERY PROTOCOL:

**Situation**: [Agent name] experienced timeout/context issues
**Last Known Work**: [what they were working on]
**Recovery Method**: [/clear or restart]
**Status**: [recovered/still recovering]

**Next Steps**:
1. Re-brief agent on current context
2. Verify understanding before proceeding
3. Monitor for stability
4. Continue with [specific task]

**Timeline Impact**: [minimal/moderate/significant]
```

## Communication Best Practices

### DO:
- Use clear, specific language
- Reference previous work to show continuity
- Set clear expectations and deadlines
- Acknowledge completed work before assigning new tasks
- Aggregate status before reporting to Orchestrator

### DON'T:
- Ask for status if agent recently provided it proactively
- Micromanage - trust agents to work efficiently
- Allow cross-team chatter - maintain hub-and-spoke
- Let quality gates slip for speed
- Forward individual agent issues to Orchestrator without attempting resolution

## Success Metrics

### Agent Productivity:
- Proactive status reporting rate (target: >80%)
- Time between task assignment and first progress report
- Quality gate pass rate on first attempt

### Team Coordination:
- Blocker resolution time
- Cross-team dependency completion rate
- Sprint velocity and predictability

### PM Effectiveness:
- Orchestrator escalation frequency (lower is better)
- Agent idle time (minimize through good task pipeline)
- Overall team satisfaction with communication clarity