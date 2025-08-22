# Claude Code Instructions for This Project

## Tmux Orchestrator Integration

This project has Tmux Orchestrator installed for managing AI agent teams.

### Quick Start Commands

1. **Create PRD from description**:
   ```
   /create-prd project_description.md
   ```

2. **Generate tasks from PRD**:
   ```
   /generate-tasks
   ```

3. **Execute PRD with agent team**:
   - Via MCP: "Execute the PRD at ./prd.md"
   - Via CLI: `tmux-orc execute ./prd.md`

### Monitoring Agents

- View all agents: `tmux-orc list`
- Check team status: `tmux-orc team status <session>`
- View agent output: `tmux-orc read --session <session:window>`

### Task Management

All tasks are organized in `.tmux_orchestrator/projects/`:
- Master task list: `tasks.md`
- Agent tasks: `agents/{agent}-tasks.md`
- Status tracking: `status/summary.md`

### Available Slash Commands

- `/create-prd` - Generate PRD from feature description
- `/generate-tasks` - Create task list from PRD
- `/process-task-list` - Execute tasks systematically

## Project-Specific Instructions

[Add your project-specific Claude instructions here]
