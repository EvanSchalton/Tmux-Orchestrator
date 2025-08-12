# Directory Refactoring In Progress

## Overview
Using tmux-orchestrator to refactor its own directory structure through dogfooding.

## Why This Refactoring?
1. **Package data in wrong places** - Won't be included in pip installs
2. **Scattered resources** - Agent examples, contexts, templates all over
3. **Runtime vs Package confusion** - .tmux_orchestrator/ mixing both

## Team Deployed
- Session: `refactor`
- PM: Window 2 (managing the refactoring)
- Will spawn: Refactoring Engineer, DevOps Engineer

## Key Changes Being Made
1. Moving `/agent-examples/` → `/tmux_orchestrator/data/agent_examples/`
2. Moving `/.tmux_orchestrator/contexts/` → `/tmux_orchestrator/data/contexts/`
3. Updating all code references
4. Fixing pyproject.toml packaging
5. Cleaning up duplicate directories

## Monitor Status
The auto-submit fix is working! Already helped the PM continue when stuck.

## To Check Progress
```bash
tmux attach -t refactor
# or
tmux capture-pane -t refactor:2 -p | tail -30
```

The PM will coordinate the full refactoring and ensure all references are updated.
