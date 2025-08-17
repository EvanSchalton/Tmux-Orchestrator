# Obsolete Files Audit - Phase 1.0 Project Cleanup

## Analysis Date: 2025-08-16
## Audit Purpose: Identify obsolete/duplicate functionality before MCP Server Completion

## Files Requiring Action

### 1. Shell Scripts to Archive/Replace

**Issue**: The package.sh script references several shell scripts that don't exist in the current codebase:
- `send-claude-message.sh` (referenced in package.sh:27) - NOT FOUND
- `schedule_with_note.sh` (referenced in package.sh:28) - NOT FOUND
- `install.sh` (referenced in package.sh:30) - NOT FOUND
- `bootstrap.sh` (referenced in package.sh:31) - NOT FOUND

**Analysis**: These missing files suggest the packaging script is outdated and references a previous version of the project structure.

**Action**: Update packaging script to reference current CLI commands instead.

### 2. VS Code Tasks Script Replacement

**Current**: `/commands/update-vscode-tasks.py`
**Future**: Will be replaced by `tmux-orc setup-vscode` CLI command (Task 6.0)

**Analysis**:
- The update script creates VS Code tasks dynamically based on running agents
- References `tmux-message` command which is the current implementation in `/bin/tmux-message`
- Should be preserved until CLI replacement is fully implemented

**Action**: Mark for future replacement, keep functional for now.

### 3. Documentation Files with Outdated Content

**Files Requiring Review**:
- `/docs/MIGRATION_GUIDE.md` - May reference obsolete commands
- `/docs/CLEANUP_SUMMARY.md` - Previous cleanup, may conflict with current
- `/examples/agent-cli-usage.md` - May have outdated CLI examples

**Action**: Review and update after CLI implementation is complete.

### 4. Duplicate Monitoring Implementations

**Current Structure**: Multiple monitoring implementations exist:
- `/tmux_orchestrator/core/monitor.py`
- `/tmux_orchestrator/core/monitor_async.py`
- `/tmux_orchestrator/core/monitor_enhanced.py`
- `/tmux_orchestrator/core/monitor_fix.py`
- `/tmux_orchestrator/core/monitor_modular.py`
- `/tmux_orchestrator/core/monitoring/` (modular system)

**Analysis**: The new modular monitoring system in `/core/monitoring/` appears to be the current implementation. Other monitor files may be legacy.

**Action**: Review with Senior Python Developer to confirm which monitoring files are obsolete.

### 5. Test Artifacts and Coverage Files

**Current State**:
- `/htmlcov/` directory contains HTML coverage reports
- `/coverage.xml` contains coverage data
- Various `__pycache__` directories

**Action**: Ensure these are in .gitignore and clean up existing artifacts.

## Files That Should NOT Be Removed

### 1. Core Message Sending Infrastructure
- `/bin/tmux-message` - Currently used by the system and referenced in VS Code tasks
- This implements the `send-claude-message.sh` functionality in the current project

### 2. Existing CLI Implementation
- All files in `/tmux_orchestrator/cli/` - These are the foundation being built upon
- All files in `/tmux_orchestrator/core/` - Core business logic
- All files in `/tmux_orchestrator/server/` - MCP server implementation

### 3. Configuration and Data
- All files in `/tmux_orchestrator/data/` - Agent contexts and examples
- `/tmux_orchestrator/templates/` - VS Code templates

## Next Steps

1. **Immediate**: Update package.sh to reference current file structure
2. **Before Task 2.0**: Confirm monitoring file consolidation needs
3. **After Task 6.0**: Replace commands/update-vscode-tasks.py with CLI
4. **During Task 8.0**: Update documentation files

## Key Findings

1. **No major obsolete shell scripts found** - The system has already been largely migrated to CLI
2. **Packaging script needs updating** - References non-existent legacy files
3. **Monitoring system may have legacy files** - Needs confirmation from team
4. **VS Code integration has working fallback** - Current Python script works while CLI is being built

## Confidence Level: High
The audit shows a well-maintained codebase with minimal obsolete functionality. Most "legacy" files appear to be intentional fallbacks or different implementation approaches rather than true obsolete code.
