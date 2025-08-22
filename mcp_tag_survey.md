# MCP Documentation Tag Survey Report

## Summary

This report provides a comprehensive survey of all CLI commands in the tmux-orchestrator project and their MCP documentation tags.

## Methodology

1. Scanned all CLI module files in `/workspaces/Tmux-Orchestrator/tmux_orchestrator/cli/`
2. Counted total commands (using `@click.command`, `@cli.command`, or `@group.command` decorators)
3. Identified commands with MCP tags (pattern: `<mcp>...</mcp>` in help strings)
4. Listed commands missing MCP tags

## Overall Statistics
