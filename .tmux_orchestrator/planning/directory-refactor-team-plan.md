# Team Plan: Directory Structure Refactoring

## Project Overview
Refactor the tmux-orchestrator directory structure to properly organize package data, fix packaging issues, and create a clean, maintainable layout.

## Current Problems
1. Agent examples and contexts scattered across multiple directories
2. Package data in .tmux_orchestrator/ won't be included in pip installs
3. Confusing duplication between /agent-examples/ and /examples/
4. References throughout codebase point to wrong locations
5. No clear separation between package data and runtime data

## Team Composition

### Required Agents

1. **Project Manager** (Window 1)
   - Coordinate the refactoring effort
   - Ensure all references are updated
   - Verify packaging works correctly
   - Update documentation

2. **Senior Refactoring Engineer** (Window 2)
   - Move files to correct locations
   - Update all code references
   - Fix import statements
   - Ensure backwards compatibility

3. **DevOps Engineer** (Window 3)
   - Update pyproject.toml for proper packaging
   - Test pip install with new structure
   - Verify all data files are included
   - Update CI/CD if needed

## Proposed New Structure

```
/workspaces/Tmux-Orchestrator/
├── examples/                    # Keep for full project examples
├── tmux_orchestrator/          # Main package
│   ├── data/                   # Package data (included in pip)
│   │   ├── agent_examples/     # Agent briefing examples
│   │   ├── contexts/           # System role contexts
│   │   └── templates/          # Other templates
│   └── [other code...]
└── .tmux_orchestrator/         # Runtime data only
    ├── logs/
    ├── planning/
    └── projects/
```

## Agent Briefings

### Project Manager Briefing
```
You are the Project Manager for refactoring tmux-orchestrator's directory structure.

Current Issues:
1. Package data scattered in wrong locations
2. Files in .tmux_orchestrator/ won't ship with pip install
3. Confusing duplication of examples
4. Code references point to wrong paths

Your responsibilities:
1. Read the full plan and current issues
2. Spawn the refactoring team
3. Coordinate file movements and code updates
4. Ensure all references are updated
5. Verify packaging works correctly
6. Update documentation

Key directories to reorganize:
- /agent-examples/ → /tmux_orchestrator/data/agent_examples/
- /.tmux_orchestrator/contexts/ → /tmux_orchestrator/data/contexts/
- /.tmux_orchestrator/agent-templates/ → /tmux_orchestrator/data/agent_examples/

Remember to clean up agents when work is complete.
```

### Senior Refactoring Engineer Briefing
```
You are a Senior Refactoring Engineer fixing the directory structure.

Your tasks:
1. Create new directory structure under tmux_orchestrator/data/
2. Move files from scattered locations to package data
3. Update all Python code references:
   - tmux_orchestrator/cli/context.py
   - Any other files referencing old paths
4. Search for hardcoded paths and fix them
5. Ensure imports work correctly
6. Add __init__.py files where needed

Key moves:
- /agent-examples/* → /tmux_orchestrator/data/agent_examples/
- /.tmux_orchestrator/contexts/* → /tmux_orchestrator/data/contexts/
- Update CONTEXTS_DIR in context.py to use pkg_resources

Use grep to find all references before changing them.
```

### DevOps Engineer Briefing
```
You are a DevOps Engineer ensuring proper packaging.

Your tasks:
1. Update pyproject.toml to include data files:
   ```toml
   include = [
       { path = "tmux_orchestrator/data/**/*", format = ["sdist", "wheel"] }
   ]
   ```
2. Test packaging with: poetry build
3. Verify data files are included in wheel/sdist
4. Update MANIFEST.in if needed
5. Test pip install in fresh environment
6. Document any packaging changes

Ensure all data files ship with the package.
```

## Success Criteria
- All package data in tmux_orchestrator/data/
- No package resources in .tmux_orchestrator/
- All code references updated
- Packaging includes all data files
- Documentation reflects new structure
- Clean separation of package vs runtime data

## Cleanup Note
When complete, kill all agents to avoid monitoring waste:
```bash
tmux-orc agent kill refactor:2  # Refactoring Engineer
tmux-orc agent kill refactor:3  # DevOps
# Then exit PM
```
