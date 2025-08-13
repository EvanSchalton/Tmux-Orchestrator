# TMUX Communications Guide

## Session Management

### Finding Your Current Session
```bash
tmux display-message -p '#S'
```

### Listing Windows in Current Session
```bash
SESSION_NAME=$(tmux display-message -p '#S')
tmux list-windows -t $SESSION_NAME -F "#{window_index}:#{window_name}"
```

## Agent Communication

**CRITICAL: Message Sending Protocol**

**NEVER use `tmux send-keys` directly** - messages won't be submitted!

ALWAYS use `tmux-orc agent send` which properly submits messages:
```bash
# CORRECT - Message sent AND submitted with Enter:
tmux-orc agent send test-cleanup:2 "Analyze the test directory structure"

# WRONG - Message queued but NOT submitted:
tmux send-keys -t test-cleanup:2 "Analyze the test directory structure"
```

The `tmux-orc agent send` command:
1. Sends your message text
2. Automatically adds Enter to submit
3. Confirms successful delivery

**⚠️ Message Sending Best Practices:**
- **Keep messages concise** - Very long messages may fail to send
- **Break up complex instructions** - Multiple smaller messages are more reliable
- **Avoid embedding files** - Don't use `$(cat file.md)` in messages
- **Use clear, simple formatting** - Avoid complex special characters
- **Test with a simple message first** - "Are you ready?" before sending complex instructions

If agents aren't responding, they may have queued messages. Fix with:
```bash
tmux send-keys -t session:window Enter
```

## Window Navigation

### Switch to a specific window
```bash
tmux select-window -t session:window
```

### Check if window exists
```bash
tmux list-windows -t session -F "#{window_index}" | grep -q "^${WINDOW_NUM}$"
```

## Agent Health Checks

### Check if Claude is running in a window
```bash
tmux capture-pane -t session:window -p | grep -q "Human:"
```

### List all agents in the system
```bash
tmux-orc agent list
```

## Daemon Management

### Stop daemon before spawning agents (prevents race conditions)
```bash
tmux-orc monitor stop
```

### Restart daemon after agents are ready
```bash
tmux-orc monitor start
```

**CRITICAL: Always stop the daemon before spawning agents and restart it only after all agents are fully initialized and ready.**

## Common Patterns

### Safe Agent Spawning
```bash
# 1. Stop daemon to prevent race conditions
tmux-orc monitor stop

# 2. Check your current session
SESSION_NAME=$(tmux display-message -p '#S')
echo "Spawning agent in session: $SESSION_NAME"

# 3. Spawn the agent
tmux-orc agent spawn $SESSION_NAME:2 developer --briefing "Your role..."

# 4. Wait for agent to be fully ready
sleep 8

# 5. Restart daemon
tmux-orc monitor start
```

### Handling Unresponsive Agents
1. First try sending Enter to submit any queued messages
2. If still unresponsive, check with `tmux capture-pane`
3. If crashed, use restart procedure from team plan

## Session Boundaries

- **NEVER** use `tmux attach-session` to switch sessions
- **NEVER** use `tmux new-session` - work within your assigned session
- All coordination happens within your current session
- Use `tmux kill-session -t $(tmux display-message -p '#S')` to terminate when complete
