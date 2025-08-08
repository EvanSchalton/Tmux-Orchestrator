# PM Quick Start Guide - PRD-Driven Orchestration

## Overview
This guide helps Project Managers implement the PRD-driven development workflow with horizontal scaling across development teams.

**Important**: Human remains in the loop for PRD creation and survey to ensure proper context curation.

## Quick Command Reference

### Modern CLI Commands (Preferred)
```bash
# Send messages
tmux-orc publish --session frontend:0 "Run tests please"
tmux-orc publish --group development "Code freeze at 3pm"
tmux-orc publish --session qa:0 --priority high --tag bug "P0 bug found"

# Read agent output  
tmux-orc read --session backend:0 --tail 100
tmux-orc read --session frontend:0 --since "2024-01-01T10:00:00"

# Search across agents
tmux-orc search "error" --all-sessions
tmux-orc search "test" --group development

# System status
tmux-orc status
tmux-orc pubsub status
tmux-orc list
```

### Legacy Commands (Fallback)
```bash
# Check your team status
tmux-orc pm status

# Monitor all agents
tmux-orc monitor dashboard

# Send message (old way)
tmux-orc agent message <session:window> "message"

# View agent output (old way)
tmux capture-pane -t <session:window> -p | tail -50
```

### PRD Workflow Commands (Use these in your Claude session)
1. `/workspaces/Tmux-Orchestrator/.claude/commands/create-prd.md` - Generate PRD from feature description
2. `/workspaces/Tmux-Orchestrator/.claude/commands/generate-tasks.md` - Create task list from PRD
3. `/workspaces/Tmux-Orchestrator/.claude/commands/process-task-list.md` - Give to devs for execution

### Task Management Directories
Projects are organized in `.tmux_orchestrator/projects/{project-name}/`:
- `prd.md` - Product Requirements Document
- `tasks.md` - Master task list
- `agents/` - Agent-specific task lists
  - `frontend-tasks.md`
  - `backend-tasks.md`
  - `qa-tasks.md`
  - `test-tasks.md`
- `status/` - Progress tracking
  - `daily/` - Daily status reports
  - `summary.md` - Overall progress

## Step-by-Step Workflow

### 1. Receive Feature Request
User provides 1-2 paragraphs describing a feature. Example:
```
"We need user authentication with email/password, secure sessions, and password reset..."
```

### 2. Create PRD
```
Please use /workspaces/Tmux-Orchestrator/.claude/commands/create-prd.md to create a PRD for this feature:

[Paste feature description]
```

### 3. Generate Master Task List
```
Please use /workspaces/Tmux-Orchestrator/.claude/commands/generate-tasks.md with the PRD we just created to generate a comprehensive task list.
```

### 4. Distribute Tasks to Developers

First, use the CLI to organize tasks:
```bash
# Create project structure
tmux-orc tasks create user-auth --prd ./prd.md

# Generate and distribute tasks
tmux-orc tasks distribute user-auth --frontend 3 --backend 3 --qa 1
```

#### For Frontend Developer:
```
Here's your task list located at:
/workspaces/Tmux-Orchestrator/.tmux_orchestrator/projects/user-auth/agents/frontend-tasks.md

Use /workspaces/Tmux-Orchestrator/.claude/commands/process-task-list.md to execute.

Requirements:
- ALL tests must pass (npm test)
- NO linting errors (npm run lint)
- Commit every 30 minutes
- Update task file as you complete work
```

#### For Backend Developer:
```
Here's your task list. Use /workspaces/Tmux-Orchestrator/.claude/commands/process-task-list.md to execute:

## Backend Tasks:
- [ ] 1. Create user model and migrations
- [ ] 2. Implement authentication endpoints
[etc...]

Requirements:
- ALL tests must pass (pytest)
- NO linting errors (ruff check)
- Commit every 30 minutes
```

### 5. Monitor Progress & Enforce Quality

#### Regular Check-in:
```
Status check: What task are you on and have you run tests/linting?

If not passing, please fix all issues before continuing.
```

#### When Dev Reports Task Complete:
```
Great! Please confirm:
1. All tests passing? (show output of test command)
2. No linting errors? (show output of lint command)
3. Changes committed?

If all yes, please proceed to next task.
```

### 6. QA Handoff (When Dev Tasks Complete)

Create QA task list:
```
**QA TESTING REQUIRED**

The following features are ready for testing:
1. User registration flow
2. Login/logout functionality
3. Password reset flow

Please test all flows and report issues in batches. Include:
- Steps to reproduce
- Screenshots of issues
- Console errors
- Suggestions for automated tests
```

### 7. Bug Fix Coordination

When QA reports issues:
```
**BUG FIXES NEEDED**

QA has identified these issues:

Frontend bugs:
1. [Issue with reproduction steps]
2. [Issue with reproduction steps]

Backend bugs:
1. [Issue with reproduction steps]

Please fix all issues, ensure tests still pass, then report back.
```

### 8. Test Automation Request

After manual QA:
```
**AUTOMATION REQUEST**

Please create automated tests for these QA workflows:
1. User registration happy path
2. Login with invalid credentials
3. Password reset flow

Use Playwright for UI tests and pytest for API tests.
```

## Common PM Scenarios

### Scenario: Developer Says "Tests are passing locally but failing in CI"
```
Let's debug this:
1. Show me the exact error from CI
2. Run 'git status' - any uncommitted files?
3. Check your local node/python version matches CI
4. Are you using any environment variables not in CI?
```

### Scenario: "I'm blocked waiting for the backend API"
```
Let me coordinate with the backend team. In the meantime:
1. Create mock data for the API responses
2. Build the UI with the mocks
3. Write tests using the mocks
4. We'll integrate once API is ready
```

### Scenario: "The requirements aren't clear"
```
Let's clarify. Looking at the PRD:
[Quote relevant section]

This means we need:
1. [Specific requirement]
2. [Specific requirement]

Does this help? What specific part needs clarification?
```

## Quality Gate Checklist

Before marking ANY task complete:
- [ ] Tests passing (no skipped tests)
- [ ] Linting passing (no warnings)
- [ ] Formatting correct
- [ ] Code committed
- [ ] No console errors/warnings
- [ ] Feature actually works as intended

## PM Communication Templates

### Morning Sync
```
Good morning team! Quick sync:
- Frontend: Current task and any blockers?
- Backend: Current task and any blockers?
- QA: Any features ready for testing?
- Test Engineer: Any automation in progress?
```

### End of Day
```
End of day check:
- Please commit any work in progress
- Share what you completed today
- What's first task tomorrow?
- Any blockers I should address?
```

### Task Completion
```
Excellent work! I've verified:
✓ Tests passing
✓ Linting clean
✓ Feature working

Moving this to QA. Your next task is: [next task]
```

## Red Flags to Watch For

1. **"I'll fix the tests later"** → No, fix them now
2. **"The linter is being too strict"** → No, follow the rules
3. **"It works on my machine"** → Then let's fix your environment
4. **"I committed everything at once"** → Review commit, ensure 30-min rule going forward
5. **"QA is being too picky"** → Quality matters, fix all issues

## Success Metrics to Track

- Tasks completed per day
- First-time quality pass rate
- Time from task start to completion
- Bugs found by QA vs users
- Test automation coverage %

## When to Escalate to Orchestrator

- Multiple teams blocked on same issue
- Major architectural decision needed
- Timeline at risk
- Resource conflicts
- Quality standards being compromised

## Remember

You are the quality gatekeeper and process enforcer. It's better to deliver fewer features that work perfectly than many features with bugs. The PRD-driven workflow ensures clarity, the task distribution enables parallelism, and your quality enforcement ensures excellence.