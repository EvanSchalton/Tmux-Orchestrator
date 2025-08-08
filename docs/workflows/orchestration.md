# Orchestrated PRD-Driven Development Workflow with Dynamic Team Composition

## Overview

This workflow scales the successful single-agent PRD → Task List → Execution pattern to a multi-agent orchestrated system with flexible team composition and horizontal scaling across the stack with automated quality assurance.

**Key Principles**: 
- Human remains in the loop for PRD creation and survey to ensure proper context curation
- Team composition is dynamically determined based on project requirements
- PM executes autonomously with occasional human feedback/guidance

## Workflow Architecture

```
User Input (1-2 paragraphs)
    ↓
Orchestrator/PM Analysis
    ├→ PRD Creation (using /create-prd.md)
    ├→ Team Composition Planning (based on PRD)
    ├→ Task List Generation (using /generate-tasks.md)
    └→ Dynamic Team Deployment
         ├→ Custom Agent Roles (as needed)
         ├→ Specialized Developers
         └→ Quality & Testing Agents
              ↓
         Coordinated Execution
```

## Dynamic Team Composition

### Flexible Team Planning

Instead of fixed team structures, the orchestrator analyzes the PRD to determine optimal team composition:

#### Example Team Compositions

**API-Heavy Project**:
- 1 PM (coordination & quality)
- 1 API Designer (architecture)
- 2 Backend Developers (implementation)
- 1 Database Engineer (data layer)
- 1 Test Automation Engineer (API testing)

**CLI Tool Project**:
- 1 Technical Lead (PM + coding)
- 2 CLI Developers (interface & functionality)
- 1 Technical Writer (documentation)
- 1 QA Engineer (usability testing)

**Security-Critical Project**:
- 1 PM (compliance & coordination)
- 1 Security Engineer (threat modeling)
- 2 Backend Developers (secure implementation)
- 1 Security Tester (penetration testing)
- 1 DevOps Engineer (secure deployment)

### Team Composition Document

Each project includes `team-composition.md` that defines:
- Agent roles and specializations
- Interaction patterns (Mermaid diagram)
- Recovery information for crashes
- Communication protocols
- Quality standards per role

### Agent Templates

Reusable agent templates in `.tmux_orchestrator/agent-templates/`:
- `cli-developer.yaml` - Command-line specialist
- `api-designer.yaml` - API architecture expert
- `security-engineer.yaml` - Security specialist
- `technical-writer.yaml` - Documentation expert
- Plus standard roles (frontend, backend, QA, etc.)

## CLI/MCP Communication Layer

### Moving Beyond Shell Scripts

The system is transitioning from shell scripts to CLI commands and MCP server calls for agent communication:

#### CLI Publish/Subscribe Pattern
```bash
# Daemon publishes idle status
tmux-orc publish --group management "Agents frontend:0, backend:0 are idle"

# PM reads agent output
tmux-orc read --session frontend:0 --tail 100

# PM sends targeted message
tmux-orc publish --session frontend:0 "Please confirm all tests pass"

# QA broadcasts bug report
tmux-orc publish --group development --priority high "Critical bug in auth flow"

# Search for errors across all agents
tmux-orc search "error" --all-sessions
```

#### MCP Server Alternative
Agents can also use MCP server endpoints:
- `POST /agents/message` - Send messages
- `GET /monitor/status` - Get system status
- `POST /coordination/broadcast` - Broadcast to groups
- `GET /agents/{session}/output` - Read agent output

#### Fallback to Direct TMUX
When CLI/MCP unavailable, agents can fallback to:
```bash
tmux send-keys -t session:window "message" Enter
tmux capture-pane -t session:window -p | tail -50
```

## Phase 1: Project Initialization

### PM Briefing Template
```
You are the Project Manager for [PROJECT NAME]. You will follow our PRD-driven development workflow:

1. **PRD Creation**: Use /workspaces/Tmux-Orchestrator/.claude/commands/create-prd.md
2. **Task Generation**: Use /workspaces/Tmux-Orchestrator/.claude/commands/generate-tasks.md  
3. **Task Distribution**: Break the master list into chunks for dev agents
4. **Quality Enforcement**: Ensure all tests/linting/formatting pass before marking complete
5. **QA Coordination**: Create test plans from completed features
6. **Test Automation**: Guide Test Engineer to automate QA workflows

**Critical Requirements**:
- NO task moves forward with failing tests/linting/formatting
- Batch feedback to developers (don't micromanage)
- Maintain master task list visibility
- Coordinate horizontal scaling across stack

Your first task: Review the project description and create a PRD.
```

### Feature Input Format
```
**FEATURE REQUEST**: [Feature Name]

[1-2 paragraphs describing the feature, user needs, and expected behavior]

Key Requirements:
- [Requirement 1]
- [Requirement 2]
- [Requirement 3]

Technical Considerations:
- [Any specific tech/framework requirements]
- [Performance or security needs]
- [Integration requirements]
```

## Phase 2: PRD Creation Process

### PM PRD Workflow
1. **Receive feature description**
2. **Use /create-prd.md command** to generate survey
3. **Answer survey questions** comprehensively
4. **Review generated PRD** for completeness
5. **Store PRD** in `/planning/prd-[feature-name].md`

### PRD Quality Checklist
- [ ] Clear problem statement
- [ ] Comprehensive user stories
- [ ] Technical requirements specified
- [ ] Success criteria defined
- [ ] Non-functional requirements included
- [ ] Dependencies identified

## Phase 3: Task List Generation

### PM Task Generation Workflow
1. **Use /generate-tasks.md** with the PRD
2. **Review generated task list** for completeness
3. **Categorize tasks** by stack layer:
   - Frontend tasks
   - Backend tasks
   - Shared/Infrastructure tasks
   - Testing tasks
4. **Add quality gates** to each task group
5. **Store master list** in `/planning/tasks-[feature-name].md`

### Task List Structure
```markdown
# Master Task List: [Feature Name]

## Frontend Tasks
- [ ] 1. [Task description]
  - Quality Gate: All tests pass, no linting errors
- [ ] 2. [Task description]
  - Quality Gate: Component tests cover all scenarios

## Backend Tasks
- [ ] 1. [Task description]
  - Quality Gate: API tests pass, 100% endpoint coverage
- [ ] 2. [Task description]
  - Quality Gate: Database migrations tested

## Integration Tasks
- [ ] 1. [Task description]
  - Quality Gate: E2E tests pass
```

## Phase 4: Task Distribution

### Creating Developer Sub-Lists

#### Frontend Developer Task List
```
**TASK LIST**: Frontend Implementation for [Feature]

Use /workspaces/Tmux-Orchestrator/.claude/commands/process-task-list.md

## Your Tasks:
[Copy relevant frontend tasks from master list]

## Quality Requirements:
- ALL tests must pass (npm test)
- NO linting errors (npm run lint)
- NO formatting issues (npm run format)
- Commit every 30 minutes

## Definition of Done:
- [ ] Feature implemented
- [ ] Unit tests written and passing
- [ ] Integration tests passing
- [ ] No console errors/warnings
- [ ] Accessibility standards met
- [ ] Responsive design verified

Report status after each task completion.
```

#### Backend Developer Task List
```
**TASK LIST**: Backend Implementation for [Feature]

Use /workspaces/Tmux-Orchestrator/.claude/commands/process-task-list.md

## Your Tasks:
[Copy relevant backend tasks from master list]

## Quality Requirements:
- ALL tests must pass (pytest)
- NO linting errors (ruff check)
- NO formatting issues (black)
- Type checking passes (mypy)
- Commit every 30 minutes

## Definition of Done:
- [ ] API endpoints implemented
- [ ] Unit tests >90% coverage
- [ ] API documentation updated
- [ ] Database migrations tested
- [ ] Performance benchmarks met
- [ ] Security best practices followed

Report status after each task completion.
```

## Phase 5: Quality Gate Management

### PM Quality Monitoring

#### Status Check Template
```
**STATUS CHECK**: Quality Gate Verification

Please run and report results:
1. Test suite: [command]
2. Linting: [command]
3. Formatting: [command]
4. Type checking: [command if applicable]

If any failures, fix them before proceeding to next task.
Do NOT skip tests or suppress warnings.
```

#### Batch Feedback Template
```
**FEEDBACK BATCH**: Issues Found

I've reviewed the implementation and found these issues:

Frontend:
1. [Issue description + console logs/screenshots]
2. [Issue description + console logs/screenshots]

Backend:
1. [Issue description + error logs]
2. [Issue description + error logs]

Please fix all issues and ensure:
- All tests still pass after fixes
- No new linting/formatting errors introduced
- Changes are committed

Report back when complete.
```

## Phase 6: QA Coordination

### Creating QA Task Lists

#### QA Test Plan Template
```
**QA TEST PLAN**: [Feature Name]

Based on completed development work, please test:

## User Flows to Test:
1. [Flow description with steps]
2. [Flow description with steps]

## Test Scenarios:
- Happy path: [description]
- Edge cases: [list]
- Error scenarios: [list]

## Tools Available:
- Manual browser testing
- Playwright MCP for automation assistance
- API testing tools

## Deliverables:
1. Test execution report
2. Bug list with reproduction steps
3. Screenshots/videos of issues
4. Recommendations for automated tests

Use batching: Test all flows, then report all issues together.
```

### QA Bug Report Format
```
**BUG REPORT BATCH**

## Critical Issues:
1. **[Bug Title]**
   - Steps to reproduce
   - Expected behavior
   - Actual behavior
   - Screenshots/logs

## Minor Issues:
1. **[Bug Title]**
   - Details as above

## Suggestions:
- [UI/UX improvements]
- [Performance observations]
```

## Phase 7: Test Automation

### Test Engineer Briefing
```
**AUTOMATION REQUEST**: [Feature Name]

The QA Engineer has completed manual testing. Please automate their test workflows:

## QA Test Workflows:
[Copy QA's test scenarios]

## Automation Requirements:
1. Create Playwright/Cypress tests for user flows
2. Create API tests for backend endpoints
3. Ensure tests are maintainable and documented
4. Tests should run in CI/CD pipeline

## Quality Standards:
- Tests must be deterministic (no flaky tests)
- Use page object pattern for UI tests
- Clear test descriptions and assertions
- Handle async operations properly
```

## Phase 8: PM Orchestration Patterns

### Daily Workflow

#### Morning Standup
```
**MORNING SYNC**

Checking status across all agents:

Frontend Dev: What's your current task and any blockers?
Backend Dev: What's your current task and any blockers?
QA: What features are ready for testing?
Test Engineer: What automation is in progress?

Based on responses, I'll update task assignments.
```

#### Task Progression Management
```
Developer completes tasks → PM verifies quality gates → Tasks marked complete
    ↓
PM creates QA test plan → QA executes tests → QA reports issues
    ↓
PM creates fix tasks for devs → Devs fix issues → PM verifies fixes
    ↓
PM requests test automation → Test Engineer creates automated tests
    ↓
Cycle continues with next feature chunk
```

### Handling Common Scenarios

#### Failing Tests/Linting
```
"I see tests are failing. Please:
1. Run [test command] and share the full output
2. Fix all failing tests - do not skip or disable them
3. Run [lint command] and fix all issues
4. Run [format command] to ensure consistency
5. Commit fixes and report back

We cannot proceed until all quality gates pass."
```

#### Cross-Team Dependencies
```
"Frontend team needs the following from Backend:
- API endpoint for [feature]
- Response schema documentation
- Test data for development

Backend team, please prioritize this and share when ready."
```

#### Scope Creep
```
"This request is outside our current PRD scope. Let's:
1. Complete current tasks first
2. Document this as a new feature request
3. Create a separate PRD after current sprint

Please continue with the original task list."
```

## Tools and Commands Reference

### PM Commands
- `/workspaces/Tmux-Orchestrator/.claude/commands/create-prd.md` - Create PRD from description
- `/workspaces/Tmux-Orchestrator/.claude/commands/generate-tasks.md` - Generate tasks from PRD
- `/workspaces/Tmux-Orchestrator/.claude/commands/process-task-list.md` - Execute task list

### Quality Commands
```bash
# Frontend
npm test          # Run all tests
npm run lint      # Check linting
npm run format    # Fix formatting

# Backend (Python)
pytest           # Run all tests
ruff check      # Check linting
black .         # Fix formatting
mypy .          # Type checking

# Backend (Go)
go test ./...   # Run all tests
golangci-lint run  # Linting
go fmt ./...    # Formatting
```

### Git Discipline
```bash
# Every 30 minutes or task completion
git add -A
git commit -m "feat: [specific description of changes]"

# Before switching tasks
git status  # Ensure clean working directory
git commit -m "checkpoint: [current progress description]"
```

## Success Metrics

### PM Performance Indicators
- **Task Completion Rate**: % of tasks completed vs assigned
- **Quality Gate Pass Rate**: First-time pass rate for tests/linting
- **Bug Discovery Rate**: Bugs found by QA vs escaped to production
- **Test Automation Coverage**: % of QA tests automated
- **Cycle Time**: Time from task assignment to completion

### Team Health Indicators
- **Agent Responsiveness**: Time to acknowledge PM requests
- **Cross-team Collaboration**: Dependency resolution time
- **Code Quality Trends**: Linting/test failures over time
- **Commit Frequency**: Adherence to 30-minute rule

## Troubleshooting Guide

### Common Issues and Solutions

#### "Tests are passing locally but failing in CI"
1. Check for environment differences
2. Verify all dependencies are committed
3. Look for timing/async issues
4. Check for hardcoded paths/values

#### "Frontend and Backend integration failing"
1. Verify API contracts match
2. Check CORS configuration
3. Ensure consistent data formats
4. Test with actual API, not mocks

#### "QA finding too many bugs"
1. Increase developer testing requirements
2. Add pre-QA checklist for developers
3. Improve task descriptions/acceptance criteria
4. Consider pair programming for complex features

## Continuous Improvement

### Sprint Retrospective Template
```
**SPRINT RETROSPECTIVE**

## What Went Well:
- [Smooth handoffs between teams]
- [Quality gates prevented bugs]
- [Good test automation coverage]

## What Could Improve:
- [Communication delays]
- [Unclear requirements]
- [Testing bottlenecks]

## Action Items:
1. [Specific improvement with owner]
2. [Process change to implement]
3. [Tool or automation to add]
```

### Process Evolution
- Regularly review and update this workflow
- Collect feedback from all agents
- Measure success metrics and adjust
- Share learnings across projects
- Build reusable templates and tools