# Task Management Guide

The Tmux Orchestrator provides comprehensive task management for PRD-driven development, organizing all project artifacts in a centralized location.

## Directory Structure

All task management files are stored in `.tmux_orchestrator/`:

```
.tmux_orchestrator/
├── projects/              # Active projects
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
└── archive/               # Completed projects
```

## Quick Start

### 1. Create a New Project

```bash
# Create with template PRD
tmux-orc tasks create my-feature --template

# Import existing PRD
tmux-orc tasks create my-feature --prd ./existing-prd.md

# Quick setup script
./commands/setup-project-tasks.sh my-feature
```

### 2. Generate Tasks from PRD

After creating the project, edit the PRD and use the Claude command:
```
/workspaces/Tmux-Orchestrator/.claude/commands/generate-tasks.md
```

Save the generated tasks to:
```
.tmux_orchestrator/projects/{project-name}/tasks.md
```

### 3. Distribute Tasks to Agents

```bash
# Default distribution
tmux-orc tasks distribute my-feature

# Custom distribution
tmux-orc tasks distribute my-feature --frontend 4 --backend 3 --qa 2
```

### 4. Monitor Progress

```bash
# Overall status
tmux-orc tasks status my-feature

# Specific agent status
tmux-orc tasks status my-feature --agent frontend

# Tree view
tmux-orc tasks status my-feature --tree
```

### 5. Export Reports

```bash
# Markdown report
tmux-orc tasks export my-feature

# JSON for integration
tmux-orc tasks export my-feature --format json --output report.json

# HTML for stakeholders
tmux-orc tasks export my-feature --format html --output report.html
```

### 6. Archive Completed Projects

```bash
# Archive with confirmation
tmux-orc tasks archive my-feature

# Force archive
tmux-orc tasks archive my-feature --force
```

## PM Workflow

### Initial Setup
1. Receive feature description from user
2. Create PRD using `/workspaces/Tmux-Orchestrator/.claude/commands/create-prd.md`
3. Set up project: `tmux-orc tasks create feature-name --prd ./prd.md`
4. Generate tasks from PRD
5. Distribute to team: `tmux-orc tasks distribute feature-name`

### Task Distribution Message Template
```
Your tasks are located at:
/workspaces/Tmux-Orchestrator/.tmux_orchestrator/projects/{project}/agents/{agent}-tasks.md

Please:
1. Review all assigned tasks
2. Use /workspaces/Tmux-Orchestrator/.claude/commands/process-task-list.md
3. Update task file as you work ([-] for in progress, [x] for complete)
4. Report status after each task completion
5. Commit code every 30 minutes

Quality gates must pass before marking tasks complete.
```

### Progress Monitoring
```bash
# Check all agents
tmux-orc tasks status project-name

# View specific agent work
tmux-orc read --session frontend:0 --tail 50

# Search for issues
tmux-orc search "error" --all-sessions
```

## Agent Instructions

When briefing agents, include:

```
Your task list is located at:
/workspaces/Tmux-Orchestrator/.tmux_orchestrator/projects/{project}/agents/{agent}-tasks.md

Update this file as you work:
- Mark starting tasks with [-]
- Mark completed tasks with [x]
- Add notes about blockers
- Include daily status updates

Use the quality checklist in your task file before marking anything complete.
```

## Task File Format

### Master Task List (`tasks.md`)
- Contains all project tasks
- Organized by feature area
- Includes relevant files section
- Tracks overall progress

### Agent Task Lists (`agents/*-tasks.md`)
- Subset of master tasks
- Includes quality checklist
- Space for daily status logs
- Agent-specific instructions

## Integration with CLI

All task operations are available via CLI:
```bash
tmux-orc tasks --help           # See all commands
tmux-orc tasks create --help    # Create project help
tmux-orc tasks status --help    # Status options
```

## Best Practices

1. **Consistent Updates**: Agents should update task files immediately
2. **Clear Task Descriptions**: Each task should be self-contained
3. **Regular Syncing**: PM syncs agent tasks with master daily
4. **Progress Tracking**: Use status commands frequently
5. **Quality Gates**: Never mark tasks complete with failing tests

## Troubleshooting

### Missing Task Files
```bash
# Recreate from template
cp .tmux_orchestrator/templates/agent-tasks-template.md \
   .tmux_orchestrator/projects/{project}/agents/{agent}-tasks.md
```

### Sync Issues
```bash
# Export current state
tmux-orc tasks export project-name

# Review and redistribute
tmux-orc tasks distribute project-name
```

### Recovery
```bash
# List all projects
tmux-orc tasks list

# Check archive
tmux-orc tasks list --archived
```