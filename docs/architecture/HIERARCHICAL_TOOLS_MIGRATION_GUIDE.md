# Migration Guide: From 92 Flat Tools to 20 Hierarchical Tools

## Executive Summary

This guide facilitates the transition from the current 92 flat MCP tools to a streamlined hierarchical structure of approximately 20 tools. The new structure reduces cognitive load while maintaining all functionality through intelligent parameter routing.

## Migration Timeline

### Phase 1: Current State (Completed)
- 92 auto-generated flat tools from CLI reflection
- Pattern: `tmux-orc_[group]_[action]`
- Example: `tmux-orc_agent_spawn`, `tmux-orc_monitor_start`

### Phase 2: Transition Period (Upcoming)
- Both flat and hierarchical tools available
- Deprecation warnings on flat tools
- Automatic forwarding to hierarchical equivalents

### Phase 3: Future State
- ~20 hierarchical tools only
- Pattern: `tmux-orc_[entity]` with action parameter
- Example: `tmux-orc_agent(action="spawn", ...)`

## Tool Consolidation Map

### Before: 92 Flat Tools
```
tmux-orc_agent_spawn
tmux-orc_agent_status
tmux-orc_agent_kill
tmux-orc_agent_restart
tmux-orc_agent_health-check
tmux-orc_agent_quality-check
tmux-orc_agent_logs
tmux-orc_agent_list
tmux-orc_agent_pause
tmux-orc_agent_resume
... (82 more tools)
```

### After: ~20 Hierarchical Tools

| Hierarchical Tool | Consolidates | Action Parameters |
|-------------------|--------------|-------------------|
| `tmux-orc_agent` | 10 agent tools | spawn, status, kill, restart, health-check, quality-check, logs, list, pause, resume |
| `tmux-orc_monitor` | 10 monitor tools | start, stop, status, health-check, metrics, configure, list, pause, resume, export |
| `tmux-orc_team` | 5 team tools | deploy, status, list, update, cleanup |
| `tmux-orc_pm` | 6 PM tools | spawn, status, restart, coordinate, delegate, report |
| `tmux-orc_pubsub` | 8 pubsub tools | send, broadcast, subscribe, publish, history, ack, list, clear |
| `tmux-orc_daemon` | 5 daemon tools | start, stop, status, restart, configure |
| `tmux-orc_context` | 4 context tools | get, set, update, list |
| `tmux-orc_orchestrator` | 7 orchestrator tools | init, plan, execute, status, coordinate, verify, cleanup |
| `tmux-orc_setup` | 7 setup tools | claude-code, mcp, verify, configure, reset, export, import |
| `tmux-orc_recovery` | 4 recovery tools | trigger, status, history, configure |
| `tmux-orc_session` | 2 session tools | create, manage |
| `tmux-orc_tasks` | 7 task tools | create, assign, status, update, complete, list, report |
| `tmux-orc_errors` | 4 error tools | list, analyze, clear, report |
| `tmux-orc_server` | 5 server tools | start, status, tools, setup, toggle |
| `tmux-orc_execute` | Top-level | Direct execution with options |
| `tmux-orc_spawn` | 3 spawn variants | Unified spawning interface |
| `tmux-orc_system` | 5 system tools | status, list, reflect, quick-deploy, info |

## Detailed Migration Examples

### Example 1: Agent Management

**Current (Flat):**
```json
// Spawn an agent
{
  "tool": "tmux-orc_agent_spawn",
  "arguments": {
    "agent_type": "developer",
    "session_window": "project:1",
    "--context": "Build API"
  }
}

// Check status
{
  "tool": "tmux-orc_agent_status",
  "arguments": {
    "session_window": "project:1"
  }
}

// Kill agent
{
  "tool": "tmux-orc_agent_kill",
  "arguments": {
    "session_window": "project:1"
  }
}
```

**Future (Hierarchical):**
```json
// Spawn an agent
{
  "tool": "tmux-orc_agent",
  "arguments": {
    "action": "spawn",
    "type": "developer",
    "session_window": "project:1",
    "context": "Build API"
  }
}

// Check status
{
  "tool": "tmux-orc_agent",
  "arguments": {
    "action": "status",
    "session_window": "project:1"
  }
}

// Kill agent
{
  "tool": "tmux-orc_agent",
  "arguments": {
    "action": "kill",
    "session_window": "project:1"
  }
}
```

### Example 2: Monitoring Operations

**Current (Flat):**
```json
// Start monitoring
{
  "tool": "tmux-orc_monitor_start",
  "arguments": {
    "session_window": "control:0",
    "--interval": "30"
  }
}

// Get metrics
{
  "tool": "tmux-orc_monitor_metrics",
  "arguments": {
    "--session": "backend",
    "--format": "json"
  }
}

// Export data
{
  "tool": "tmux-orc_monitor_export",
  "arguments": {
    "--from": "2024-01-01",
    "--output": "report.json"
  }
}
```

**Future (Hierarchical):**
```json
// Start monitoring
{
  "tool": "tmux-orc_monitor",
  "arguments": {
    "action": "start",
    "session_window": "control:0",
    "interval": 30
  }
}

// Get metrics
{
  "tool": "tmux-orc_monitor",
  "arguments": {
    "action": "metrics",
    "session": "backend",
    "format": "json"
  }
}

// Export data
{
  "tool": "tmux-orc_monitor",
  "arguments": {
    "action": "export",
    "from": "2024-01-01",
    "output": "report.json"
  }
}
```

### Example 3: Team Deployment

**Current (Flat):**
```json
// Deploy team
{
  "tool": "tmux-orc_team_deploy",
  "arguments": {
    "config": "backend-team.yaml"
  }
}

// Check status
{
  "tool": "tmux-orc_team_status",
  "arguments": {
    "name": "backend-team"
  }
}

// Update team
{
  "tool": "tmux-orc_team_update",
  "arguments": {
    "name": "backend-team",
    "--add-agent": "qa-engineer:3"
  }
}
```

**Future (Hierarchical):**
```json
// Deploy team
{
  "tool": "tmux-orc_team",
  "arguments": {
    "action": "deploy",
    "config": "backend-team.yaml"
  }
}

// Check status
{
  "tool": "tmux-orc_team",
  "arguments": {
    "action": "status",
    "name": "backend-team"
  }
}

// Update team
{
  "tool": "tmux-orc_team",
  "arguments": {
    "action": "update",
    "name": "backend-team",
    "add_agent": "qa-engineer:3"
  }
}
```

## Parameter Mapping Rules

### 1. Action Parameter
- First positional argument becomes `action` parameter
- Maps directly to the original command suffix
- Example: `agent_spawn` → `action: "spawn"`

### 2. Common Parameters
These parameters are standardized across all hierarchical tools:

| Old Format | New Format | Notes |
|------------|------------|-------|
| `session_window` | `session_window` | No change |
| `--context` | `context` | Remove `--` prefix |
| `--force` | `force: true` | Boolean flag |
| `--format` | `format` | Remove `--` prefix |
| `--output` | `output` | Remove `--` prefix |
| `--verbose` | `verbose: true` | Boolean flag |

### 3. Entity-Specific Parameters
Maintained within each hierarchical tool:

**Agent Tool:**
- `type` (for spawn action)
- `preserve_context` (for restart action)
- `include_logs` (for status action)

**Monitor Tool:**
- `interval` (for start action)
- `threshold` (for configure action)
- `from`, `to` (for export action)

**Team Tool:**
- `config` (for deploy action)
- `add_agent`, `remove_agent` (for update action)
- `force` (for cleanup action)

## Migration Strategy

### Phase 1: Preparation (Weeks 1-2)
1. **Audit Current Usage**
   ```json
   {
     "tool": "tmux-orc_system",
     "arguments": {
       "action": "audit-tools",
       "output": "tool-usage-report.json"
     }
   }
   ```

2. **Identify High-Usage Tools**
   - Focus migration efforts on most-used tools
   - Create specific migration guides for common workflows

3. **Update Documentation**
   - Add deprecation notices to flat tool docs
   - Create hierarchical tool reference

### Phase 2: Dual Support (Weeks 3-6)
1. **Enable Hierarchical Tools**
   - Deploy new hierarchical tool handlers
   - Flat tools remain functional

2. **Add Migration Helpers**
   ```json
   {
     "tool": "tmux-orc_migrate",
     "arguments": {
       "action": "suggest",
       "old_tool": "tmux-orc_agent_spawn",
       "show_equivalent": true
     }
   }
   ```

3. **Implement Forwarding**
   - Flat tools automatically forward to hierarchical
   - Log deprecation warnings

### Phase 3: Transition (Weeks 7-8)
1. **Deprecation Warnings**
   - All flat tool usage shows migration message
   - Provide exact hierarchical equivalent

2. **Migration Validation**
   ```json
   {
     "tool": "tmux-orc_migrate",
     "arguments": {
       "action": "validate",
       "test_workflows": true
     }
   }
   ```

3. **Team Training**
   - Update all automation scripts
   - Train team on new structure

### Phase 4: Completion (Week 9)
1. **Remove Flat Tools**
   - Clean removal with clear error messages
   - Point to hierarchical alternatives

2. **Final Validation**
   - Ensure all workflows function
   - Performance benchmarking

## Common Migration Patterns

### Pattern 1: Batch Operations
**Old:**
```python
tools = [
    "tmux-orc_agent_status",
    "tmux-orc_monitor_status",
    "tmux-orc_daemon_status"
]
for tool in tools:
    call_tool(tool, {"session": "prod"})
```

**New:**
```python
entities = ["agent", "monitor", "daemon"]
for entity in entities:
    call_tool(f"tmux-orc_{entity}", {
        "action": "status",
        "session": "prod"
    })
```

### Pattern 2: Conditional Actions
**Old:**
```python
if need_restart:
    tool = "tmux-orc_agent_restart"
else:
    tool = "tmux-orc_agent_status"
call_tool(tool, args)
```

**New:**
```python
action = "restart" if need_restart else "status"
call_tool("tmux-orc_agent", {
    "action": action,
    **args
})
```

### Pattern 3: Tool Discovery
**Old:**
```python
# List all agent-related tools
tools = [t for t in all_tools if t.startswith("tmux-orc_agent_")]
```

**New:**
```python
# Get all actions for agent tool
{
  "tool": "tmux-orc_agent",
  "arguments": {
    "action": "help"  # Lists all available actions
  }
}
```

## Benefits of Hierarchical Structure

### 1. Reduced Cognitive Load
- 78% reduction in tool count (92 → ~20)
- Logical grouping by entity
- Consistent action patterns

### 2. Improved Discoverability
- Find all agent actions in one tool
- Natural categorization
- Self-documenting structure

### 3. Better Error Messages
- Context-aware error handling
- Suggested actions for typos
- Clear parameter validation

### 4. Enhanced Flexibility
- Easy to add new actions
- Consistent parameter handling
- Simplified tool routing

## Troubleshooting Guide

### Issue: "Unknown tool" Error
**Cause:** Using flat tool name with hierarchical system
**Solution:**
```json
// Instead of:
{"tool": "tmux-orc_agent_spawn", ...}

// Use:
{"tool": "tmux-orc_agent", "arguments": {"action": "spawn", ...}}
```

### Issue: "Invalid action" Error
**Cause:** Action not available for entity
**Solution:** Check available actions:
```json
{
  "tool": "tmux-orc_agent",
  "arguments": {
    "action": "help"
  }
}
```

### Issue: Parameter Mismatch
**Cause:** Using old parameter format
**Solution:** Remove `--` prefixes and update format:
```json
// Old: "--context": "value"
// New: "context": "value"
```

### Issue: Missing Required Parameters
**Cause:** Parameters changed between versions
**Solution:** Check parameter requirements:
```json
{
  "tool": "tmux-orc_agent",
  "arguments": {
    "action": "spawn",
    "help": true  // Shows required parameters
  }
}
```

## Migration Checklist

### For Developers
- [ ] Review tool usage in codebase
- [ ] Update all tool calls to hierarchical format
- [ ] Test critical workflows
- [ ] Update error handling for new structure
- [ ] Document any custom patterns

### For DevOps
- [ ] Update automation scripts
- [ ] Modify CI/CD pipelines
- [ ] Update monitoring alerts
- [ ] Test deployment workflows
- [ ] Update documentation

### For Users
- [ ] Learn new tool structure
- [ ] Update personal scripts
- [ ] Practice with common workflows
- [ ] Report any issues
- [ ] Share feedback

## Support Resources

### Documentation
- Hierarchical Tool Reference (coming soon)
- Interactive Migration Tool
- Video Tutorials
- FAQ Document

### Tools
- Migration validator: `tmux-orc_migrate`
- Tool converter: Automatic in transition period
- Usage analyzer: Built into system tool

### Help
- Migration support channel
- Office hours for questions
- Automated migration assistance
- Legacy tool lookup service

## Conclusion

The migration from 92 flat tools to ~20 hierarchical tools represents a significant improvement in usability and maintainability. While the transition requires updating existing integrations, the benefits of reduced complexity, improved discoverability, and enhanced flexibility make this a worthwhile evolution. The phased approach ensures minimal disruption while providing ample time for teams to adapt to the new structure.
