# Repository Cleanup Migration Guide

This guide documents the repository reorganization performed to improve maintainability and discoverability.

## Major Changes

### Directory Consolidation
- `.tmux-orchestrator/` → Removed (legacy)
- `.tmux_orchestrator/` → Kept (active task management system)
- `Examples/` → Merged into `examples/`
- All documentation moved to `docs/`
- Essential scripts moved to `scripts/`

### Documentation Reorganization

#### Setup & Installation
- `SETUP.md` → `docs/setup/installation.md`
- `QUICKSTART.md` → `docs/setup/quickstart.md`
- `CLI_QUICKSTART.md` → `docs/setup/cli-quickstart.md`

#### Workflows
- `end-to-end-workflow.md` → `docs/workflows/end-to-end.md`
- `orchestration-workflow.md` → `docs/workflows/orchestration.md`
- `PM-QUICKSTART.md` → `docs/workflows/pm-guide.md`
- `TASK_MANAGEMENT.md` → `docs/workflows/task-management.md`

#### Features
- `IDLE_DETECTION_V2.md` → `docs/features/idle-detection.md`
- `coordination.md` → `docs/features/coordination.md`
- `devcontainer-integration.md` → `docs/features/devcontainer.md`
- Dynamic team composition → `docs/features/team-composition.md`

#### Development
- `DEVELOPMENT.md` → `docs/development/contributing.md`
- `ARCHITECTURE.md` → `docs/development/architecture.md`
- `LEARNINGS.md` → `docs/development/learnings.md`

### Script Changes

#### Deprecated Scripts (Use CLI Instead)
- `commands/deploy-agent.sh` → Use `tmux-orc agent deploy`
- `commands/agent-status.sh` → Use `tmux-orc agent status`
- `commands/list-agents.sh` → Use `tmux-orc list`
- `commands/start-orchestrator.sh` → Use `tmux-orc orchestrator start`
- `commands/recover-agents.sh` → Use `tmux-orc recovery check`

#### Essential Scripts (Moved to scripts/)
- `send-claude-message.sh` → `scripts/send-claude-message.sh`
- `schedule_with_note.sh` → `scripts/schedule-with-note.sh`
- `commands/idle-monitor-daemon.sh` → `scripts/idle-monitor-daemon.sh`

### Removed Files
- `README_NEW.md` - Content merged into main README
- `END_TO_END_QUICKSTART.md` - Duplicate of workflow docs
- `IDLE_DETECTION_IMPROVEMENTS.md` - Superseded by V2
- `INTEGRATION-COMPLETE.md` - Historical, not needed
- `RUNNING.md` - Outdated, use CLI docs

## For Users Upgrading

### If You Were Using Shell Scripts

Replace these commands in your workflows:

```bash
# Old way
./commands/deploy-agent.sh frontend developer

# New way
tmux-orc agent deploy frontend --role developer
```

```bash
# Old way
./commands/agent-status.sh

# New way
tmux-orc agent status
```

### If You Were Following Documentation

All documentation has moved to the `docs/` directory:
- Quick start guides are in `docs/setup/`
- Workflow guides are in `docs/workflows/`
- Feature documentation is in `docs/features/`

### Essential Scripts Location

The following scripts are still needed and have moved:
- Message sending: `scripts/send-claude-message.sh`
- Scheduling: `scripts/schedule-with-note.sh`
- Monitoring: `scripts/idle-monitor-daemon.sh`

Update any references to use the new paths.

## New Features Since Cleanup

### Dynamic Team Composition
- Teams are now composed based on project needs
- See `docs/features/team-composition.md`
- Use `tmux-orc team compose` command

### Task Management System
- Centralized in `.tmux_orchestrator/`
- See `docs/workflows/task-management.md`
- Use `tmux-orc tasks` commands

### Enhanced CLI
- `tmux-orc setup-claude-code` - Install slash commands
- `tmux-orc execute <prd>` - Execute PRD with custom team
- `tmux-orc tasks` - Complete task management
- `tmux-orc team compose` - Plan custom teams

## Getting Help

If you encounter issues after the cleanup:
1. Check this migration guide
2. Run `tmux-orc --help` for CLI documentation
3. See `docs/setup/quickstart.md` for getting started
4. Report issues on GitHub