# Git Hooks

This directory contains git hooks for the tmux-orchestrator project.

## Setup

To use these hooks, configure git to use this directory:

```bash
git config core.hooksPath .githooks
```

## Available Hooks

### pre-commit

Warns if the orchestrator context file may need updating when system files are modified.

This hook:
- Checks if CLI, server, core, or documentation files have been modified
- Compares modification times with the orchestrator context
- Shows a warning if the context might be outdated
- Does NOT block commits - just provides a helpful reminder

The orchestrator context (`.tmux_orchestrator/contexts/orchestrator.md`) should be kept up-to-date with:
- New CLI commands
- Changed workflows
- New MCP endpoints
- System behavior changes

## Notes

- Hooks are advisory only - they won't block commits
- The pre-commit hook helps maintain documentation accuracy
- Run `git config core.hooksPath .githooks` in each clone of the repository
