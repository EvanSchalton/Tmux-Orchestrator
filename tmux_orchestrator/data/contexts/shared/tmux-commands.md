# TMUX Command Guidelines

> 💡 **CLI Discovery**: For current tmux-orc command syntax, run `tmux-orc reflect` or use `--help` flags

## 🚨 **ALWAYS USE TMUX-ORC COMMANDS - NEVER RAW TMUX!** 🚨

**CORRECT**: `tmux-orc agent send session:window "message"`
**WRONG**: `tmux send-keys -t session:window "message"`

The daemon auto-submits raw tmux messages, which bypasses your instructions!

## Why This Matters

- **Raw tmux commands** only TYPE text but don't submit it to Claude
- **tmux-orc commands** handle proper message submission with C-Enter
- **The daemon** may auto-submit queued messages, creating race conditions

## Quick Reference

### ✅ CORRECT Commands
```bash
# Send message to agent (guaranteed delivery)
tmux-orc agent send project:2 "Please implement the login feature"

# Spawn new agent with context
tmux-orc spawn agent developer project:2 --briefing "You are a backend developer..."

# Check agent status
tmux-orc agent status project:2

# List all agents
tmux-orc agent list
```

### ❌ WRONG Commands (Will Fail)
```bash
# These only TYPE but don't SUBMIT:
tmux send-keys -t project:2 "message"
tmux send -t project:2 "message"
```

## Common Scenarios

### Sending Instructions to Agents
```bash
# Always use agent send for messaging
tmux-orc agent send project:2 "STATUS UPDATE: Task completed successfully"
```

### Spawning New Team Members
```bash
# Use spawn commands with proper briefings
tmux-orc spawn agent qa-engineer project:3 --briefing "..."
```

### Checking Agent Health
```bash
# Use agent commands for monitoring
tmux-orc agent status project:2
```

Remember: When in doubt, if the command starts with `tmux-orc`, it's probably correct!
