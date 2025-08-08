# Claude Code Instructions

## Task List Checkbox States

When working on tasks in markdown task lists, use these checkbox states:

- `[ ]` - Not started
- `[-]` - In progress
- `[x]` - Completed

This helps track which tasks are actively being worked on versus completed.

## Task Implementation Protocol

### One Sub-task at a Time

- Complete one sub-task fully before moving to the next

### Completion Protocol

1. When finishing a **sub-task**, immediately mark it as completed `[x]`
2. If **all** subtasks under a parent task are complete, mark the **parent task** as `[x]`
3. Update the task list file after any significant work

### Task List Maintenance

- **Relevant Files Section**: Maintain an accurate list of all created/modified files with descriptions
- **Add New Tasks**: As implementation reveals new requirements, add them to the task list
- **Regular Updates**: Update the task list file frequently to reflect current progress

## Development Standards

### Code Organization

- **One function/class per file**: Each business logic function should be in its own file
- **Type hints everywhere**: All functions, methods, variables, and parameters need type hints
- **SQL in separate files**: Store SQL queries in `*.sql` files within a `sql/` directory

### Testing Requirements

- **100% coverage target**: Aim for complete branch and statement coverage
- **Test structure mirrors code**: Test directory structure should match application code
- **One test file per code file**: Each code file should have a corresponding test file
- **Use pytest**: All tests must be in the `tests/` directory with proper naming

### Quality Checks Before Task Completion

- Run `mypy` for type checking
- Run `ruff` for code quality
- Run `pytest` with coverage reporting
- Only mark tasks complete when all checks pass without errors

### Dependency Management

- **Use Poetry**: All dependencies managed through Poetry, not pip
- `poetry add <package>` for runtime dependencies
- `poetry add --group dev <package>` for development dependencies

## SOLID Principles Application

### Single Responsibility (SRP)

- Each function handles one specific operation
- Each service handles one bounded context
- Each file contains one main function or class

### Open/Closed (OCP)

- Use dependency injection for extensibility
- Prefer composition over inheritance

### Interface Segregation (ISP)

- Create focused, client-specific interfaces
- Services expose only needed operations

### Dependency Inversion (DIP)

- Depend on abstractions, not concrete implementations
- Use dependency injection for external services

## Working with PRDs and Tasks

### PRD Workflow

1. Create survey from project description
2. Generate PRD from completed survey
3. Create task list from PRD
4. Implement tasks following the protocol above

### File Locations

- PRDs: `/tasks/prd-[feature-name].md`
- Task Lists: `/tasks/tasks-prd-[feature-name].md`
- Surveys: `prd-survey.md` (in current directory)

## Tmux Orchestrator Integration

This project includes Tmux Orchestrator for managing multiple Claude agents working in parallel. The orchestrator enables 24/7 development with autonomous agents handling different components.

### Quick Start

1. **Install (first time only)**: Run `/workspaces/corporate-coach/scripts/install-tmux-orchestrator.sh`
2. **Start orchestrator**: `/start-orchestrator`
3. **Deploy agents**: `/deploy-agent frontend developer` and `/deploy-agent backend developer`
4. **Monitor progress**: `/agent-status`
5. **Schedule check-ins**: `/schedule-checkin 30 orchestrator:0 "Review progress"`

### Available Commands

- `/start-orchestrator [session-name]` - Initialize the orchestrator
- `/deploy-agent <component> [role]` - Deploy a new agent
  - Components: `frontend`, `backend`, `database`, `docs`
  - Roles: `developer`, `pm`, `qa`, `reviewer`
- `/agent-status` - Check all agent statuses
- `/schedule-checkin <minutes> <target> "<note>"` - Schedule future check-ins

### Agent Communication

Send messages to agents using `tmux-message`:
```bash
tmux-message corporate-coach-frontend:0 "Please update the markdown editor tests"
tmux-message orchestrator:0 "Status update on Neo4j integration?"
```

### Git Discipline for Agents

All agents MUST follow these practices:
- **Commit every 30 minutes** - No exceptions
- **Feature branches** - Create branches for new features
- **Meaningful messages** - Describe what changed and why
- **Tag stable versions** - Before major changes

### Agent Hierarchy

```
Orchestrator (Oversight & Coordination)
    ├── Frontend Team
    │   ├── Developer
    │   ├── PM
    │   └── QA
    ├── Backend Team
    │   ├── Developer
    │   ├── PM
    │   └── QA
    └── Database Team
        ├── Developer
        └── QA
```

### Best Practices

1. **Start orchestrator first** - It coordinates all other agents
2. **Deploy PMs early** - They maintain quality standards
3. **Regular check-ins** - Every 15-30 minutes for orchestrator
4. **Clear communication** - Use structured message formats
5. **Monitor progress** - Use `/agent-status` frequently

### Orchestrator Responsibilities

- Deploy and coordinate agent teams
- Monitor system health and progress
- Resolve cross-component dependencies
- Ensure git discipline is maintained
- Make architectural decisions
- Schedule regular check-ins

### Reference Documentation

Full Tmux Orchestrator documentation: `/workspaces/corporate-coach/references/Tmux-Orchestrator/CLAUDE.md`
Setup guide: `/workspaces/corporate-coach/docs/development/tmux-orchestrator-setup.md`
