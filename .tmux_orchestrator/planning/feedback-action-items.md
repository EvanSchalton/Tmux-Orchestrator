# Feedback Action Items Summary

## ✅ Completed Items

1. **C-Enter vs Enter Issue** - Fixed in previous work
2. **Orchestrator Role Clarification** - Claude Code is the orchestrator
3. **Documentation Updates** - Workflow shows document-driven approach
4. **Context System** - Added `tmux-orc context` commands
5. **MCP Context Endpoints** - Added `/contexts/*` endpoints
6. **Pre-commit Hook** - Warns about outdated orchestrator context
7. **File Organization** - Moved agent-tasks to .tmux_orchestrator/planning

## ❌ High Priority - Still Need Implementation

### 1. Session Attach Command
**Issue**: No easy way to attach to tmux session containing all agents
**Solution**: Implement `tmux-orc session attach` with:
- Auto-discovery of sessions
- Default to most recent session
- `--list` flag to show menu
- No need to remember session names

### 2. Monitor Auto-Submit Fix
**Issue**: Monitor detects "idle with Claude interface" but doesn't submit
**Solution**: In monitor.py, when detecting idle Claude:
```python
if "idle with Claude interface" in status:
    tmux.send_keys(target, "Enter")  # Submit the message
    log.info(f"Auto-submitted stuck message for {target}")
```

### 3. Agent Discovery/Type Detection
**Issue**: Agents show as type "Unknown", list shows "No agents found"
**Solution**: Fix agent metadata storage and retrieval:
- Store agent type when spawning
- Fix list_agents() to properly detect sessions
- Show correct agent types in listings

## ❌ Medium Priority - Quality of Life

### 4. Bulk Agent Commands
Add `--all` flag to agent commands:
- `tmux-orc agent kill --all`
- `tmux-orc agent restart --all`
- `tmux-orc agent message --all "message"`

### 5. Remove/Deprecate team deploy
Since we're using document-driven workflow:
- Mark team deploy as deprecated
- Update docs to remove references
- Focus on individual agent spawning

## Implementation Priority

1. **Monitor Auto-Submit** - Critical for system to work at all
2. **Session Attach** - Core monitoring feature users desperately need
3. **Agent Discovery** - Makes system usable and debuggable
4. **Bulk Commands** - Nice to have for managing many agents
5. **Deprecate team deploy** - Cleanup task

## Notes

- All high priority items block effective use of the system
- Monitor auto-submit is the most critical - without it, nothing works
- Session attach is the most requested feature
- Agent discovery issues make debugging very difficult
