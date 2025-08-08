# Tmux Orchestrator Cleanup Analysis

## Current State Assessment

### Duplicate Directories
1. **`.tmux_orchestrator/` vs `.tmux-orchestrator/`**
   - `.tmux_orchestrator/` - NEW, contains task management system
   - `.tmux-orchestrator/` - OLD, contains legacy commands
   - **Action**: Keep `.tmux_orchestrator/`, remove `.tmux-orchestrator/`

2. **`examples/` vs `Examples/`**
   - `examples/` - Code examples and scripts
   - `Examples/` - Screenshots/images
   - **Action**: Merge into single `examples/` directory

### Shell Scripts Analysis

#### Critical Scripts to Keep
1. **`send-claude-message.sh`** - Core messaging utility with critical timing
2. **`schedule_with_note.sh`** - Orchestrator self-scheduling
3. **`commands/idle-monitor-daemon.sh`** - Idle detection + crash recovery (no CLI replacement yet)

#### Scripts to Convert to CLI
1. **`bootstrap.sh`** - Should become `tmux-orc init`
2. **`install.sh`** - Standard pip install
3. **`setup-devcontainer.sh`** - Could be `tmux-orc setup devcontainer`

#### Scripts Already Replaced by CLI
1. **`commands/deploy-agent.sh`** → `tmux-orc agent deploy`
2. **`commands/agent-status.sh`** → `tmux-orc agent status`
3. **`commands/list-agents.sh`** → `tmux-orc list`
4. **`commands/start-orchestrator.sh`** → `tmux-orc orchestrator start`
5. **`commands/recover-agents.sh`** → `tmux-orc recovery check/restart`
6. **`scripts/open-all-agents.sh`** → VS Code task

### Markdown Files Organization

#### Root Directory Docs to Move to `docs/`
1. **Setup & Installation**
   - `SETUP.md` → `docs/setup/installation.md`
   - `QUICKSTART.md` → `docs/setup/quickstart.md`
   - `CLI_QUICKSTART.md` → `docs/setup/cli-quickstart.md`

2. **Workflows**
   - `end-to-end-workflow.md` → `docs/workflows/end-to-end.md`
   - `orchestration-workflow.md` → `docs/workflows/orchestration.md`
   - `PM-QUICKSTART.md` → `docs/workflows/pm-guide.md`
   - `TASK_MANAGEMENT.md` → `docs/workflows/task-management.md`

3. **Development**
   - `DEVELOPMENT.md` → `docs/development/contributing.md`
   - `ARCHITECTURE.md` → `docs/development/architecture.md`
   - `LEARNINGS.md` → `docs/development/learnings.md`

4. **Features**
   - `IDLE_DETECTION_V2.md` → `docs/features/idle-detection.md`
   - `coordination.md` → `docs/features/coordination.md`
   - `devcontainer-integration.md` → `docs/features/devcontainer.md`

5. **Keep in Root**
   - `README.md` - Main documentation
   - `CHANGELOG.md` - Version history
   - `CLAUDE.md` - Agent instructions

#### Duplicate/Outdated Files to Remove
- `README_NEW.md` - Merge into README.md
- `IDLE_DETECTION_IMPROVEMENTS.md` - Outdated by V2
- `INTEGRATION-COMPLETE.md` - Historical, not needed
- `RUNNING.md` - Outdated by CLI
- `END_TO_END_QUICKSTART.md` - Duplicate of workflow

### Other Consolidations

#### agent-prompts.yaml vs templates/
- `agent-prompts.yaml` - Static prompts for recovery
- `.tmux_orchestrator/agent-templates/` - Dynamic team composition
- **Action**: Keep both, they serve different purposes

#### Commands Directory
- Many `.sh` scripts replaced by CLI
- Keep only essential scripts not yet in CLI
- Move remaining to `scripts/` directory

## Proposed New Structure

```
tmux-orchestrator/
├── README.md
├── CHANGELOG.md
├── CLAUDE.md
├── LICENSE
├── pyproject.toml
├── .claude/                    # Claude slash commands
│   └── commands/
├── .tmux_orchestrator/         # Task management system
│   ├── agent-templates/
│   ├── projects/
│   ├── templates/
│   └── archive/
├── docs/                       # All documentation
│   ├── setup/
│   │   ├── installation.md
│   │   ├── quickstart.md
│   │   └── cli-reference.md
│   ├── workflows/
│   │   ├── end-to-end.md
│   │   ├── orchestration.md
│   │   ├── pm-guide.md
│   │   └── task-management.md
│   ├── features/
│   │   ├── idle-detection.md
│   │   ├── coordination.md
│   │   ├── team-composition.md
│   │   └── devcontainer.md
│   ├── development/
│   │   ├── contributing.md
│   │   ├── architecture.md
│   │   └── learnings.md
│   └── api/
│       └── cli-reference.md
├── examples/                   # All examples
│   ├── screenshots/
│   ├── prd-examples/
│   └── team-compositions/
├── scripts/                    # Essential scripts
│   ├── send-claude-message.sh
│   ├── schedule-with-note.sh
│   └── idle-monitor-daemon.sh
├── tmux_orchestrator/          # Python package
│   ├── cli/
│   ├── core/
│   ├── server/
│   └── utils/
└── tests/

```

## Migration Steps

1. **Backup Current State**
   ```bash
   git checkout -b pre-cleanup-backup
   git push origin pre-cleanup-backup
   ```

2. **Create New Branch**
   ```bash
   git checkout -b feature/repository-cleanup
   ```

3. **Execute Cleanup**
   - Create docs/ structure
   - Move markdown files
   - Consolidate examples
   - Remove deprecated scripts
   - Update references in code
   - Update README with new structure

4. **Create Migration Guide**
   - Document what moved where
   - Update any hardcoded paths
   - Provide upgrade instructions

5. **Test Everything**
   - Verify CLI commands work
   - Check documentation links
   - Test examples
   - Ensure CI/CD passes

## Impact on Users

### Breaking Changes
- Script locations changed
- Some scripts removed (use CLI instead)
- Documentation reorganized

### Migration Guide Needed
- Map old locations to new
- Provide CLI equivalents for removed scripts
- Update any tutorials/guides

## Benefits After Cleanup

1. **Clearer Organization**: Logical structure for all files
2. **No Duplication**: Single source of truth
3. **Better Discoverability**: Easy to find documentation
4. **Maintainability**: Clear what's current vs legacy
5. **Professional**: Clean repository structure