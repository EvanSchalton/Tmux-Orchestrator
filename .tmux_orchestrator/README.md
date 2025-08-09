# Tmux Orchestrator Task Management

This directory contains all task management files for the Tmux Orchestrator system, organizing PRDs, task lists, and agent sub-tasks.

## Directory Structure

```
.tmux_orchestrator/
├── projects/              # Active project task management
│   └── {project-name}/    # Per-project organization
│       ├── prd.md         # Product Requirements Document
│       ├── tasks.md       # Master task list
│       ├── agents/        # Agent-specific task lists
│       │   ├── frontend-tasks.md
│       │   ├── backend-tasks.md
│       │   ├── qa-tasks.md
│       │   └── test-tasks.md
│       └── status/        # Progress tracking
│           ├── daily/     # Daily status reports
│           └── summary.md # Overall progress
├── templates/             # Reusable templates
│   ├── prd-template.md
│   ├── tasks-template.md
│   └── agent-tasks-template.md
└── archive/               # Completed projects

```

## File Naming Conventions

### Projects Directory
- Project folders: `{project-name}` (lowercase, hyphens for spaces)
- PRD files: `prd.md` (always named the same for consistency)
- Task lists: `tasks.md` (master list)
- Agent tasks: `{agent-type}-tasks.md` (e.g., `frontend-tasks.md`)

### Status Reports
- Daily reports: `YYYY-MM-DD-status.md`
- Agent updates: `YYYY-MM-DD-{agent}-update.md`

## Task List Format

### Master Task List (`tasks.md`)
```markdown
# Project: {Project Name}
Generated from: prd.md
Date: YYYY-MM-DD

## Task Summary
Total Tasks: X
Completed: Y
In Progress: Z
Pending: A

## Relevant Files
- `path/to/file.ts` - Description
- `path/to/test.ts` - Test file

## Tasks
- [ ] 1.0 Major Feature Area
  - [ ] 1.1 Sub-task
  - [ ] 1.2 Sub-task
- [ ] 2.0 Another Feature Area
  - [ ] 2.1 Sub-task
```

### Agent Task Lists (`agents/{agent}-tasks.md`)
```markdown
# {Agent Type} Tasks - {Project Name}
Assigned: YYYY-MM-DD
PM: {PM Session}

## Current Sprint
- [ ] Task from master list
- [ ] Another task

## Quality Requirements
- All tests must pass
- No linting errors
- Commits every 30 minutes

## Status Updates
### YYYY-MM-DD HH:MM
- Completed: Task description
- Current: What I'm working on
- Blocked: Any issues
```

## CLI Integration

Task management commands:
```bash
# Create new project structure
tmux-orc tasks create <project-name>

# Import PRD and generate tasks
tmux-orc tasks import-prd <project-name> <prd-file>

# Distribute tasks to agents
tmux-orc tasks distribute <project-name>

# Check task status
tmux-orc tasks status <project-name>

# Archive completed project
tmux-orc tasks archive <project-name>
```

## Workflow

1. **Project Creation**
   - Create project directory: `.tmux_orchestrator/projects/{project-name}/`
   - Copy PRD to `prd.md`
   - Generate master task list as `tasks.md`

2. **Task Distribution**
   - PM analyzes master task list
   - Creates agent-specific task lists in `agents/`
   - Each agent receives their `{agent}-tasks.md` file

3. **Progress Tracking**
   - Agents update their task files with `[-]` (in progress) and `[x]` (complete)
   - PM aggregates status to `status/summary.md`
   - Daily reports saved to `status/daily/`

4. **Completion**
   - All tasks marked complete
   - Final summary generated
   - Project moved to `archive/` with timestamp

## Best Practices

1. **Atomic Updates**: Update task files immediately after completing work
2. **Clear Descriptions**: Each task should be self-contained and clear
3. **Regular Syncs**: PM should sync agent tasks with master list daily
4. **Version Control**: Commit task updates frequently
5. **Status Format**: Use consistent status update format across all agents

## Integration with Agent Prompts

When briefing agents, include:
```
Your tasks are located at:
/workspaces/Tmux-Orchestrator/.tmux_orchestrator/projects/{project}/agents/{agent}-tasks.md

Update this file as you work:
- Mark starting tasks with [-]
- Mark completed tasks with [x]
- Add notes about blockers or issues
```
