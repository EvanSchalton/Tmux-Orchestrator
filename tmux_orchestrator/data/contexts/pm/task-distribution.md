# Task Distribution and Agent Coordination

## Core Task Management Principles

As PM, you are responsible for keeping all agents productive and coordinated. This requires proactive task management and clear communication.

## Task Distribution Strategy

### 1. Understand Agent Expertise
Before assigning tasks, know your team:
- **Developer**: Implementation, bug fixes, refactoring
- **QA Engineer**: Testing, test writing, quality validation
- **DevOps**: CI/CD, deployment, infrastructure
- **Architect**: Design decisions, code structure
- **Documentation**: README updates, API docs

### 2. Task Prioritization
Order tasks by:
1. **Blockers** - Tasks blocking other work
2. **Critical Path** - Tasks on the main delivery path
3. **Parallel Work** - Tasks that can run simultaneously
4. **Nice-to-Have** - Improvements and optimizations

### 3. Load Balancing
- Keep all agents busy but not overwhelmed
- Distribute tasks based on complexity and agent skill
- Monitor completion rates and adjust

## Task Assignment Templates

### Clear Task Structure
```bash
tmux-orc agent send project:2 "
TASK: Implement user authentication
PRIORITY: High
REQUIREMENTS:
- JWT-based authentication
- Login/logout endpoints
- Session management
- Comprehensive tests (>80% coverage)
DELIVERABLES:
- Working implementation in src/auth/
- Tests in tests/test_auth.py
- Updated README with auth setup
DEADLINE: Please complete within 2 hours
"
```

### Bug Fix Assignment
```bash
tmux-orc agent send project:3 "
BUG FIX NEEDED:
Issue: Login fails with special characters in password
File: src/auth/login.py
Steps to reproduce:
1. Try login with password containing '@#$'
2. Observe 500 error
Expected: Successful login
Please fix and add regression test
"
```

### Research Task
```bash
tmux-orc agent send project:2 "
RESEARCH TASK:
Investigate optimal caching strategy for our API
Consider:
- Redis vs in-memory
- Cache invalidation patterns
- Performance implications
Deliver: Technical recommendation with pros/cons
"
```

## Coordinating Parallel Work

### Preventing Conflicts
```bash
# Before assigning overlapping work
tmux-orc agent send project:2 "
Working on auth module - files: src/auth/*.py
Please work on user profiles - files: src/profiles/*.py
This avoids merge conflicts
"
```

### Managing Dependencies
```bash
# When work has dependencies
tmux-orc agent send project:2 "Dev2: Please implement the User model first"
tmux-orc agent send project:3 "QA: User model in progress, will notify when ready for testing"

# Later...
tmux-orc agent send project:3 "QA: User model complete! Please begin testing src/models/user.py"
```

## Task Tracking

### Maintain a Task List
Keep track of:
- Assigned tasks per agent
- Task status (pending/in-progress/complete)
- Blockers and dependencies
- Time estimates vs actual

### Regular Status Checks
```bash
# Every 30 minutes, check progress
tmux-orc agent send project:2 "STATUS UPDATE: How's the auth implementation going?"
```

### Task Completion Verification
```bash
# When agent reports completion
tmux-orc agent send project:2 "
Great! Before we move on:
1. Are all tests passing?
2. Is coverage above 80%?
3. Did pre-commit hooks pass?
Please run: pre-commit run --all-files && pytest
"
```

## Handling Common Scenarios

### Agent Reports "Done" But Idle
1. Verify completion quality
2. Check if they need the next task
3. Have follow-up work ready

### Agent Stuck on Task
1. Check for blockers
2. Offer assistance or pair programming
3. Consider reassigning if truly blocked

### Multiple Agents Need Same Resource
1. Coordinate access schedule
2. Have one agent complete first
3. Use branching strategy to avoid conflicts

## Communication Patterns

### Broadcast Announcements
```bash
# To all agents - manually send to each
for window in 2 3 4; do
    tmux-orc agent send project:$window "TEAM NOTICE: Main branch updated, please pull latest"
done
```

### Agent Pairing
```bash
tmux-orc agent send project:2 "Please pair with QA (window 3) on test strategy"
tmux-orc agent send project:3 "Dev (window 2) will pair with you on test strategy"
```

## Using Agent Work Products

### 📊 CRITICAL: Leveraging Agent Outputs

**When agents provide summaries or analysis, USE THAT INFORMATION to task other agents!**

Example workflow:
1. **QA completes test audit** → Reports 3 failing tests
2. **You assign to Developer**: "Please fix the 3 failing tests QA identified in auth_test.py"
3. **Architect reviews code** → Suggests refactoring in user.py
4. **You assign to Developer**: "Please implement the refactoring suggested by architect"

**Key principle**: Agent outputs are INPUTS for tasking other agents. Don't let valuable analysis go unused!

## Red Flags in Task Management

- ❌ Agents idle for >5 minutes
- ❌ Vague task assignments
- ❌ No follow-up on "completed" tasks
- ❌ Ignoring agent blockers
- ❌ Not using agent findings to drive work

## Task Distribution Checklist

Before each task assignment:
- [ ] Is the task clear and specific?
- [ ] Are success criteria defined?
- [ ] Are dependencies resolved?
- [ ] Is the timeline reasonable?
- [ ] Will this conflict with other work?

Remember: Busy agents are happy agents. Keep the work flowing!
