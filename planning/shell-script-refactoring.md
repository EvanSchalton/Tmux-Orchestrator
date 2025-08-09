# Shell Script Refactoring Plan

## Overview
Most shell scripts have Python CLI equivalents but some functionality is missing or scripts are still referenced.

## Scripts Analysis

### ✅ Already Refactored
1. **send-claude-message.sh** → `tmux-orc agent send`
2. **schedule_with_note.sh** → `tmux-orc orchestrator schedule`
3. **idle-monitor-daemon.sh** → `tmux-orc monitor start` (needs enhancement)
4. **tmux-deploy-team.sh** → `tmux-orc team deploy` / `tmux-orc execute`

### 🔧 Need Refactoring/Enhancement

#### 1. **idle-monitor-daemon.sh** → Enhance `monitor start`
Missing features in Python implementation:
- [ ] Claude crash detection
- [ ] Auto-submit unsubmitted messages
- [ ] PM notification for idle agents
- [ ] Cooldown period for notifications
- [ ] Crashed agent recovery instructions

#### 2. **generic-restart.sh** → Already in `agent restart`
- [ ] Remove script and update references

#### 3. **generic-team-deploy.sh** → Already in `team deploy`
- [ ] Remove script and update references

#### 4. **handler.sh** (in commands/)
- [ ] Check what this does and refactor if needed

#### 5. **setup-project-tasks.sh**
- [ ] Integrate into `tasks create` or `setup` command

### 🗑️ Scripts to Remove (already implemented in Python)

1. `/workspaces/Tmux-Orchestrator/scripts/send-claude-message.sh`
2. `/workspaces/Tmux-Orchestrator/scripts/schedule_with_note.sh`
3. `/workspaces/Tmux-Orchestrator/bin/generic-restart.sh`
4. `/workspaces/Tmux-Orchestrator/bin/generic-team-deploy.sh`
5. `/workspaces/Tmux-Orchestrator/bin/tmux-deploy-team.sh`

### 📝 Scripts to Keep (build/dev related)
1. `.devcontainer/post-create.sh` - DevContainer setup
2. `scripts/package.sh` - Build script
3. `scripts/run-tests.sh` - Test runner
4. `scripts/setup-devcontainer.sh` - Dev setup
5. `scripts/test-bootstrap.sh` - Test setup
6. `docs/templates/install-template.sh` - Installation template

## Action Items

1. **Enhance monitor start command** with missing idle-monitor-daemon.sh features
2. **Remove redundant shell scripts** that have Python equivalents
3. **Update all references** in documentation and code to use Python CLI commands
4. **Add deprecation notices** to shell scripts before removal
5. **Update CLAUDE.md** to reference only Python CLI commands

## Migration Guide

### For Users
```bash
# Old way
./scripts/send-claude-message.sh myproject:0 "Hello"
# New way
tmux-orc agent send myproject:0 "Hello"

# Old way
./scripts/schedule_with_note.sh 30 "Check progress" myproject:0
# New way
tmux-orc orchestrator schedule 30 myproject:0 "Check progress"

# Old way
./scripts/idle-monitor-daemon.sh 15
# New way
tmux-orc monitor start --interval 15
```

### For Documentation
Replace all references to shell scripts with their Python CLI equivalents.
