# {Agent Type} Tasks - {Project Name}

Assigned: YYYY-MM-DD HH:MM
PM Session: {pm-session}
Master Task List: ../{project}/tasks.md

## Instructions

1. **Update Status**: Mark tasks as you work
   - `[ ]` - Not started
   - `[-]` - In progress
   - `[x]` - Completed

2. **Quality Gates**: Before marking complete
   - All tests passing
   - No linting errors
   - Code committed
   - PM notified

3. **Communication**: Report status after EACH task using:
   ```
   tmux-orc publish --session {pm-session} "STATUS UPDATE {Agent}:
   ✅ Completed: {task}
   🔄 Current: {current task}
   🚧 Next: {next task}
   ⏱️ ETA: {time estimate}
   ❌ Blockers: {any issues}"
   ```

## Current Sprint Tasks

### Priority 1 - Critical Path
- [ ] Task from master list (ref: 2.1)
- [ ] Another critical task (ref: 2.3)

### Priority 2 - Important
- [ ] Secondary task (ref: 3.1)
- [ ] Related work (ref: 3.2)

### Priority 3 - Nice to Have
- [ ] Enhancement (ref: 4.1)

## Completed Tasks
_Move tasks here when complete_

- [x] Example completed task (ref: 1.1) - Completed YYYY-MM-DD HH:MM

## Notes & Blockers

### Current Blockers
- None

### Dependencies
- Waiting on: Backend API for user endpoints
- Blocks: Frontend can't test auth flow

### Technical Decisions
- Using Redux for state management
- Chose Playwright over Cypress for E2E tests

## Quality Checklist

Before marking ANY task complete:
- [ ] Tests written and passing
- [ ] Linting clean (`npm run lint` or `ruff check`)
- [ ] Type checking passes (`tsc` or `mypy`)
- [ ] Code reviewed (self-review minimum)
- [ ] Changes committed to git
- [ ] Documentation updated if needed
- [ ] PM notified of completion

## Daily Status Log

### YYYY-MM-DD HH:MM
**Completed Today:**
- Implemented user authentication component
- Added unit tests (15 test cases)
- Fixed responsive design issues

**Currently Working On:**
- Integration with backend auth API

**Plan for Tomorrow:**
- Complete auth integration
- Start on user profile component

**Blockers:**
- None currently

---

### YYYY-MM-DD HH:MM
**Completed Today:**
- [Previous day's work]

**Currently Working On:**
- [Current focus]

**Plan for Tomorrow:**
- [Next steps]

**Blockers:**
- [Any issues]
