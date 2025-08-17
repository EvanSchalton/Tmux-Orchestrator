# Hierarchical MCP Tools: User Guide

## Quick Start: What's Changed?

The MCP tools have been reorganized from 92 individual tools to ~20 hierarchical tools. This guide shows exactly how to update your usage with clear before/after examples.

## Visual Overview

### Before: 92 Flat Tools
```
tmux-orc_agent_spawn      tmux-orc_monitor_start    tmux-orc_team_deploy
tmux-orc_agent_status     tmux-orc_monitor_stop     tmux-orc_team_status
tmux-orc_agent_kill       tmux-orc_monitor_status   tmux-orc_team_list
tmux-orc_agent_restart    tmux-orc_monitor_metrics  tmux-orc_team_update
... (82 more tools)
```

### After: ~20 Hierarchical Tools
```
tmux-orc_agent     → actions: spawn, status, kill, restart, logs, etc.
tmux-orc_monitor   → actions: start, stop, status, metrics, export, etc.
tmux-orc_team      → actions: deploy, status, list, update, cleanup
tmux-orc_pubsub    → actions: send, broadcast, subscribe, publish, etc.
... (16 more entity-based tools)
```

## Common Tasks: Before & After

### Task 1: Spawn a Developer Agent

**❌ OLD WAY (Flat Tool):**
```json
{
  "tool": "tmux-orc_agent_spawn",
  "arguments": {
    "agent_type": "developer",
    "session_window": "myproject:1",
    "--context": "Build user authentication API"
  }
}
```

**✅ NEW WAY (Hierarchical):**
```json
{
  "tool": "tmux-orc_agent",
  "arguments": {
    "action": "spawn",
    "type": "developer",
    "session_window": "myproject:1",
    "context": "Build user authentication API"
  }
}
```

**Key Changes:**
- Tool name: Just `tmux-orc_agent` (not `tmux-orc_agent_spawn`)
- Added: `"action": "spawn"` parameter
- Removed: `--` prefix from optional parameters
- Parameter: `agent_type` → `type`

### Task 2: Check Agent Status

**❌ OLD WAY:**
```json
{
  "tool": "tmux-orc_agent_status",
  "arguments": {
    "session_window": "myproject:1"
  }
}
```

**✅ NEW WAY:**
```json
{
  "tool": "tmux-orc_agent",
  "arguments": {
    "action": "status",
    "session_window": "myproject:1"
  }
}
```

### Task 3: Start Monitoring

**❌ OLD WAY:**
```json
{
  "tool": "tmux-orc_monitor_start",
  "arguments": {
    "session_window": "control:0",
    "--interval": "30",
    "--verbose": true
  }
}
```

**✅ NEW WAY:**
```json
{
  "tool": "tmux-orc_monitor",
  "arguments": {
    "action": "start",
    "session_window": "control:0",
    "interval": 30,
    "verbose": true
  }
}
```

**Key Changes:**
- No more `--` prefixes
- Numeric values don't need quotes
- Boolean values are proper booleans (not strings)

### Task 4: Deploy a Team

**❌ OLD WAY:**
```json
{
  "tool": "tmux-orc_team_deploy",
  "arguments": {
    "config": "backend-team.yaml"
  }
}
```

**✅ NEW WAY:**
```json
{
  "tool": "tmux-orc_team",
  "arguments": {
    "action": "deploy",
    "config": "backend-team.yaml"
  }
}
```

### Task 5: Send a Message

**❌ OLD WAY:**
```json
{
  "tool": "tmux-orc_pubsub_send",
  "arguments": {
    "target": "backend:1",
    "message": "Update API endpoints",
    "--priority": "high"
  }
}
```

**✅ NEW WAY:**
```json
{
  "tool": "tmux-orc_pubsub",
  "arguments": {
    "action": "send",
    "target": "backend:1",
    "message": "Update API endpoints",
    "priority": "high"
  }
}
```

## Complete Workflows: Before & After

### Workflow: Deploy and Monitor a Backend Team

**❌ OLD WAY (Multiple Flat Tools):**
```python
# Step 1: Deploy team
{
  "tool": "tmux-orc_team_deploy",
  "arguments": {"config": "backend.yaml"}
}

# Step 2: Check deployment
{
  "tool": "tmux-orc_team_status",
  "arguments": {"name": "backend-team"}
}

# Step 3: Start monitoring
{
  "tool": "tmux-orc_monitor_start",
  "arguments": {"session_window": "backend:0", "--interval": "30"}
}

# Step 4: Configure alerts
{
  "tool": "tmux-orc_monitor_configure",
  "arguments": {"--alert-threshold": "error", "--session": "backend"}
}
```

**✅ NEW WAY (Hierarchical Tools):**
```python
# Step 1: Deploy team
{
  "tool": "tmux-orc_team",
  "arguments": {
    "action": "deploy",
    "config": "backend.yaml"
  }
}

# Step 2: Check deployment
{
  "tool": "tmux-orc_team",
  "arguments": {
    "action": "status",
    "name": "backend-team"
  }
}

# Step 3: Start monitoring
{
  "tool": "tmux-orc_monitor",
  "arguments": {
    "action": "start",
    "session_window": "backend:0",
    "interval": 30
  }
}

# Step 4: Configure alerts
{
  "tool": "tmux-orc_monitor",
  "arguments": {
    "action": "configure",
    "alert_threshold": "error",
    "session": "backend"
  }
}
```

## Quick Reference Table

| Task | Old Tool | New Tool | New Action |
|------|----------|----------|------------|
| Spawn agent | `tmux-orc_agent_spawn` | `tmux-orc_agent` | `spawn` |
| Kill agent | `tmux-orc_agent_kill` | `tmux-orc_agent` | `kill` |
| Agent status | `tmux-orc_agent_status` | `tmux-orc_agent` | `status` |
| Start monitor | `tmux-orc_monitor_start` | `tmux-orc_monitor` | `start` |
| Stop monitor | `tmux-orc_monitor_stop` | `tmux-orc_monitor` | `stop` |
| Deploy team | `tmux-orc_team_deploy` | `tmux-orc_team` | `deploy` |
| Send message | `tmux-orc_pubsub_send` | `tmux-orc_pubsub` | `send` |
| System status | `tmux-orc_status` | `tmux-orc_system` | `status` |

## Parameter Changes Cheat Sheet

### 1. Remove `--` Prefixes
```json
// ❌ OLD
"--context": "value"
"--force": true
"--interval": "30"

// ✅ NEW
"context": "value"
"force": true
"interval": 30
```

### 2. Use Proper Types
```json
// ❌ OLD
"--interval": "30"      // String
"--verbose": "true"     // String
"--count": "5"          // String

// ✅ NEW
"interval": 30          // Number
"verbose": true         // Boolean
"count": 5              // Number
```

### 3. Renamed Parameters
| Old Parameter | New Parameter | Notes |
|---------------|---------------|-------|
| `agent_type` | `type` | When spawning agents |
| `--alert-threshold` | `alert_threshold` | Underscores, not hyphens |
| `session_name` + `window` | `session_window` | Combined format |

## Common Mistakes to Avoid

### ❌ Mistake 1: Using Old Tool Names
```json
// WRONG
{
  "tool": "tmux-orc_agent_spawn",  // Old flat tool name
  "arguments": {...}
}
```

### ✅ Correct: Use Entity Tool with Action
```json
// RIGHT
{
  "tool": "tmux-orc_agent",
  "arguments": {
    "action": "spawn",
    ...
  }
}
```

### ❌ Mistake 2: Forgetting the Action Parameter
```json
// WRONG - Missing action
{
  "tool": "tmux-orc_agent",
  "arguments": {
    "type": "developer",
    "session_window": "dev:1"
  }
}
```

### ✅ Correct: Always Include Action
```json
// RIGHT
{
  "tool": "tmux-orc_agent",
  "arguments": {
    "action": "spawn",  // Required!
    "type": "developer",
    "session_window": "dev:1"
  }
}
```

### ❌ Mistake 3: Using String Booleans
```json
// WRONG
{
  "tool": "tmux-orc_monitor",
  "arguments": {
    "action": "start",
    "verbose": "true"  // String instead of boolean
  }
}
```

### ✅ Correct: Use Proper Boolean
```json
// RIGHT
{
  "tool": "tmux-orc_monitor",
  "arguments": {
    "action": "start",
    "verbose": true  // Proper boolean
  }
}
```

## Discovering Available Actions

### Method 1: List All Actions
```json
{
  "tool": "tmux-orc_agent",
  "arguments": {
    "action": "help"
  }
}
// Returns: ["spawn", "status", "kill", "restart", "logs", ...]
```

### Method 2: Get Help for Specific Action
```json
{
  "tool": "tmux-orc_agent",
  "arguments": {
    "action": "spawn",
    "help": true
  }
}
// Returns: Required and optional parameters for spawn action
```

### Method 3: Use System Reflection
```json
{
  "tool": "tmux-orc_system",
  "arguments": {
    "action": "reflect",
    "entity": "agent"
  }
}
// Returns: Complete information about agent tool
```

## Tool Categories Quick Reference

### 🤖 Agent Management
```json
{
  "tool": "tmux-orc_agent",
  "arguments": {
    "action": "spawn|status|kill|restart|logs|health-check|quality-check|list|pause|resume",
    // ... action-specific parameters
  }
}
```

### 📊 Monitoring
```json
{
  "tool": "tmux-orc_monitor",
  "arguments": {
    "action": "start|stop|status|metrics|configure|health-check|list|pause|resume|export",
    // ... action-specific parameters
  }
}
```

### 👥 Team Operations
```json
{
  "tool": "tmux-orc_team",
  "arguments": {
    "action": "deploy|status|list|update|cleanup",
    // ... action-specific parameters
  }
}
```

### 💬 Communication (PubSub)
```json
{
  "tool": "tmux-orc_pubsub",
  "arguments": {
    "action": "send|broadcast|subscribe|publish|history|ack|list|clear",
    // ... action-specific parameters
  }
}
```

### 🎯 Project Manager
```json
{
  "tool": "tmux-orc_pm",
  "arguments": {
    "action": "spawn|status|restart|coordinate|delegate|report",
    // ... action-specific parameters
  }
}
```

## Getting Help

### 1. General Help
```json
{
  "tool": "tmux-orc_system",
  "arguments": {
    "action": "help"
  }
}
```

### 2. Entity-Specific Help
```json
{
  "tool": "tmux-orc_agent",
  "arguments": {
    "action": "help"
  }
}
```

### 3. Action-Specific Help
```json
{
  "tool": "tmux-orc_agent",
  "arguments": {
    "action": "spawn",
    "help": true
  }
}
```

### 4. Migration Help
```json
{
  "tool": "tmux-orc_system",
  "arguments": {
    "action": "migrate-help",
    "old_tool": "tmux-orc_agent_spawn"
  }
}
```

## Summary

The hierarchical tool structure simplifies MCP usage by:
1. Reducing 92 tools to ~20 entity-based tools
2. Using consistent `action` parameter pattern
3. Removing confusing `--` prefixes
4. Using proper JSON types (numbers, booleans)
5. Providing better organization and discoverability

Remember: **Entity → Action → Parameters**
