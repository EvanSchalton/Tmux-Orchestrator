# Tmux-Orchestrator Feature Request: Interactive Tmux Monitoring

## Feature Request: Session-Level Attach Command

### Current Gap
There's no tmux-orc command to attach to the entire tmux session (not individual agents). Users want to:
1. Attach to the tmux session containing all agents
2. Use native tmux controls to switch between agent windows (Ctrl+B then 0,1,2,etc)
3. See all agents in one tmux session interface

Currently, users must:
- Remember the session name (e.g., "Tmux-Orchestrator-fullstack")
- Use raw `tmux attach -t SESSION_NAME`
- There's no tmux-orc equivalent like `tmux-orc session attach`

### Proposed Solutions

#### Solution 1: `tmux-orc session attach` Command
Add a simple command to attach to orchestrator sessions:
```bash
tmux-orc session attach                    # Attach to default/most recent session
tmux-orc session attach fullstack          # Attach to specific team session
tmux-orc session attach --list             # Show menu of available sessions
```

This would be equivalent to `tmux attach -t SESSION_NAME` but with:
- Auto-discovery of orchestrator sessions
- No need to remember exact session names
- Integration with tmux-orc workflow

#### Solution 2: Enhanced VS Code Integration
Add VS Code tasks for monitoring:
```json
{
  "label": "🖥️ Monitor All Agents (Tmux)",
  "type": "shell",
  "command": "tmux-orc",
  "args": ["agent", "attach", "--all"],
  "detail": "Open tmux terminal to toggle between all agents"
}
```

With keyboard shortcut support:
- `Ctrl+Shift+P` > "Monitor TMux"
- Opens integrated terminal with tmux session
- Provides instructions for navigation

#### Solution 3: `tmux-orc agent attach --all`
Extend the existing attach command:
```bash
tmux-orc agent attach --all        # Attach to session with all agents
tmux-orc agent attach --list       # Show menu to select agent
tmux-orc agent attach --monitor    # Create monitoring dashboard in tmux
```

### Benefits
1. **Easier Monitoring**: No need to remember session names or window numbers
2. **Better Visibility**: See all agents at once or quickly switch between them
3. **VS Code Integration**: Use Command Palette for quick access
4. **Improved Workflow**: Faster debugging and monitoring of multi-agent systems

### Current Workaround
Users must manually:
1. Run `tmux ls` to find sessions
2. Run `tmux attach -t SESSION_NAME`
3. Use `Ctrl+B` + window number to switch
4. Remember which window has which agent

### Priority
High - This is a core monitoring feature that would significantly improve the developer experience when working with multiple agents.

## CRITICAL BUG: Monitor Detects But Doesn't Submit Unsubmitted Messages

### The Problem
The monitor daemon correctly detects when agents have unsubmitted messages:
```
Agent Tmux-Orchestrator-fullstack:1 is idle with Claude interface
```

BUT it does NOT automatically submit these messages. This leaves agents stuck indefinitely with typed but unsubmitted prompts.

### Evidence
From monitor logs:
- Detects "idle with Claude interface" every 30 seconds
- Takes no action to submit the message
- Agents remain stuck for hours with unsubmitted text

### Expected Behavior
When monitor detects "idle with Claude interface":
1. Should attempt to submit the message (send Enter key)
2. Log the submission attempt
3. Notify PM if submission fails repeatedly
4. Track how long messages have been unsubmitted

### Current Impact
- Agents appear to be working but are actually stuck
- Messages sent via `tmux-orc agent message` are typed but not submitted
- Entire teams can be idle while appearing active
- No automatic recovery mechanism

### Proposed Fix
```python
if "idle with Claude interface" in status:
    # Try to submit the message
    tmux.send_keys(target, "Enter")
    log.info(f"Auto-submitted message for {target}")
    # Track submission attempts
    if attempts > 3:
        notify_pm(f"Agent {target} may be stuck")
```

### Priority: CRITICAL
This breaks the entire orchestration system - agents receive instructions but never execute them.

## Additional Missing Features

### 1. Session Naming Control
Currently `team deploy` creates sessions with fixed names like `Tmux-Orchestrator-fullstack`. Should support:
```bash
tmux-orc team deploy fullstack --name kanban-project
```

### 2. Bulk Agent Management
Missing commands for managing all agents at once:
```bash
tmux-orc agent kill --all          # Kill all agents
tmux-orc agent restart --all       # Restart all agents
tmux-orc agent message --all "msg" # Broadcast to all agents
```

### 3. Agent Discovery Issues
- `tmux-orc agent list` often shows "No agents found" even when sessions exist
- Agents show as type "Unknown" instead of their actual type
- Monitor daemon can't detect agents properly (sees sessions but not agents)

---
*Documented: 2025-08-10*
*Version: tmux-orchestrator v2.1.10*
