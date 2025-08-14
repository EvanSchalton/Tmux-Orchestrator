# Communication Protocols and Status Updates

## Standard Communication Formats

### STATUS UPDATE Format
All agents should use this format for status updates:
```
STATUS UPDATE:
- Current Task: [What you're working on]
- Progress: [X%]
- Blockers: [Any issues, or "None"]
- Next Steps: [What you'll do next]
- ETA: [Estimated completion time]
```

### TASK COMPLETE Format
When agents complete tasks:
```
TASK COMPLETE:
- Task: [What was completed]
- Location: [Files/directories affected]
- Tests: [Pass/Fail status]
- Coverage: [X%]
- Pre-commit: [Pass/Fail]
- Notes: [Any important information]
```

### BLOCKER Format
For reporting blockers:
```
BLOCKER:
- Task: [What you're trying to do]
- Issue: [What's blocking you]
- Tried: [What you've attempted]
- Need: [What would unblock you]
- Impact: [What this blocks]
```

## Communication Frequency

### Regular Updates
- **Status updates**: Every 30 minutes
- **Blocker reports**: Immediately when encountered
- **Completion reports**: As soon as task is done
- **Questions**: As they arise, don't wait

### Proactive Communication
Encourage agents to communicate:
- Before starting major changes
- When approach is uncertain
- If timeline will be exceeded
- When dependencies are discovered

## Team Coordination Messages

### Starting Collaborative Work
```bash
tmux-orc agent send project:2 "
COORDINATION: Auth Module
- I'll work on: models/user.py
- Please take: routes/auth.py
- Let's sync before integration
"
```

### Handoff Communication
```bash
tmux-orc agent send project:3 "
HANDOFF: User Model Ready
- Location: src/models/user.py
- Tests: tests/test_user_model.py
- Coverage: 95%
- Ready for: Integration testing
- Docs: Updated in docstrings
"
```

### Dependency Notification
```bash
tmux-orc agent send project:2 "
DEPENDENCY ALERT:
- Your task needs: Completed User model
- Status: QA is testing now
- ETA: 30 minutes
- Suggestion: Start on independent parts
"
```

## Upward Communication (PM to Orchestrator)

### Progress Reports
Every 30 minutes, summarize team status:
```
TEAM PROGRESS UPDATE:
- Sprint Goal: [Current objective]
- Progress: [Overall %]
- Active Tasks: [X]
- Completed: [Y]
- Blockers: [List or "None"]
- Team Health: [Good/Issues]
- ETA: [Sprint completion estimate]
```

### Escalation Format
When escalating issues:
```
ESCALATION REQUIRED:
- Issue: [Description]
- Impact: [What it affects]
- Attempted: [What you tried]
- Options: [Possible solutions]
- Recommendation: [Your suggested approach]
- Need: [What you need from orchestrator]
```

## Managing Information Flow

### Information Hierarchy
1. **Critical**: Blockers, failures, security issues → Immediate
2. **Important**: Completions, dependencies → Within 5 minutes
3. **Routine**: Status updates, progress → Every 30 minutes
4. **FYI**: Observations, suggestions → As appropriate

### Broadcast vs Targeted
- **Broadcast** (all agents): System-wide changes, process updates
- **Targeted** (specific agent): Task assignments, specific feedback
- **Paired** (two agents): Collaboration requests, handoffs

## Communication Best Practices

### Clarity Guidelines
- **Be specific**: "Fix login bug" → "Fix SQL injection in login.py line 45"
- **Include context**: Why this matters, what it affects
- **Set expectations**: Deadline, success criteria
- **Provide resources**: Links, examples, documentation

### Avoiding Communication Anti-patterns
- ❌ Vague requests: "Make it better"
- ❌ Missing context: "Fix the thing"
- ❌ No success criteria: "Do some testing"
- ❌ Information hoarding: Not sharing findings

### Effective Questioning
```bash
# ❌ Poor question
"Is the auth module done?"

# ✅ Good question
"Auth module status: What % complete? Any blockers? When will tests be ready?"
```

## Meeting Patterns

### Daily Standup Format
Every 2-3 hours, collect standups:
```bash
for window in 2 3 4; do
    tmux-orc agent send project:$window "
    STANDUP REQUEST:
    1. What did you complete?
    2. What are you working on?
    3. Any blockers?
    Please respond in 2 minutes.
    "
done
```

### Sprint Planning
When starting new work phase:
```
SPRINT PLANNING:
- Goal: [What we're building]
- Tasks: [Breakdown of work]
- Assignments: [Who does what]
- Timeline: [Expected duration]
- Success Criteria: [How we know we're done]
```

## Crisis Communication

### System Down
```
🚨 CRITICAL ISSUE:
- What: [System/component down]
- Since: [Time]
- Impact: [What's affected]
- Action: [What we're doing]
All hands to address this issue!
```

### Security Issue
```
🔒 SECURITY ALERT:
- Type: [Nature of issue]
- Severity: [Critical/High/Medium]
- Affected: [What components]
- Action Required: [Immediate steps]
Do not commit any code until resolved!
```

## Documentation of Communication

### Important Decisions
Document key decisions in the planning directory:
- Why we chose approach X
- Trade-offs considered
- Team consensus/disagreements
- Action items from discussions

### Lessons Learned
Capture for project closeout:
- Communication breakdowns
- Successful patterns
- Team dynamics
- Process improvements

Remember: Over-communication is better than under-communication in distributed teams!
