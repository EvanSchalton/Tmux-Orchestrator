# Directory Reorganization Plan

## Problem
- Agent examples, contexts, and templates are scattered across root and .tmux_orchestrator
- These files won't be packaged with pip install
- Confusing duplication between agent-examples/ and examples/

## Current Issues
1. `/agent-examples/` - In root, won't be packaged
2. `/.tmux_orchestrator/agent-templates/` - Runtime dir, won't be packaged
3. `/.tmux_orchestrator/contexts/` - Runtime dir, won't be packaged
4. `/examples/` - Mixed with agent examples, unclear purpose

## Proposed Solution

### 1. Create Package Data Structure
```
tmux_orchestrator/
├── data/
│   ├── agent_examples/      # From /agent-examples/
│   ├── contexts/            # From /.tmux_orchestrator/contexts/
│   └── templates/           # Merge with existing templates/
```

### 2. Update Code References
- `context.py` to use package data
- Any other code referencing these paths

### 3. Keep Runtime Directory Clean
`.tmux_orchestrator/` should only contain:
- Runtime data (logs, planning docs, etc.)
- User-created content
- NOT package resources

### 4. Clean Up Examples
- Keep `/examples/` for full project examples
- Move agent briefings to package data

## Benefits
- All package data ships with pip install
- Clear separation of package vs runtime data
- No confusion about where to find resources
