# Daemon Management and Notifications

> 💡 **CLI Discovery**: For current tmux-orc command syntax, run `tmux-orc reflect` or `tmux-orc --help`

## 🤖 Working with the Monitoring Daemon

The monitoring daemon is your automated assistant, detecting idle/crashed agents and alerting you. Learn to work WITH it, not against it.

## Daemon Basics

### Check Daemon Status
```bash
# Always verify daemon is running
tmux-orc monitor status

# Start if not running
tmux-orc monitor start

# View daemon logs
tmux-orc monitor logs -f
```

### Daemon Responsibilities
- **Detects idle agents** (no activity for ~1 minute)
- **Identifies crashed agents** (Claude not responding)
- **Monitors rate limits** (API usage limits)
- **Sends PM notifications** (via monitoring system)
- **Auto-recovers crashed PMs** (spawns replacement)

## 📋 CRITICAL: How to Handle Daemon Notifications

**When you receive idle agent notifications, follow this MANDATORY workflow:**

### ✅ CORRECT Response to Idle Notifications:
1. **READ THE AGENT'S TERMINAL FIRST** before taking any action:
   ```bash
   tmux capture-pane -t session:window -p | tail -20
   ```

2. **UNDERSTAND WHY they're idle**:
   - Waiting for instructions? → Assign tasks
   - Completed their work? → Verify and assign next task
   - Having issues? → Provide help
   - Rate limited? → Wait for reset

3. **TAKE APPROPRIATE ACTION** using tmux-orc commands:
   ```bash
   tmux-orc agent send session:window "Great work! Here's your next task..."
   ```

### ❌ WRONG Response to Idle Notifications:
- Immediately sending "why are you idle?" without checking
- Ignoring the notification
- Telling them to "keep working" without checking if they're done
- Asking them to restart Claude

## Common Daemon Notification Patterns

### 1. Agent Idle Notification
```
🚨 IDLE AGENT DETECTED: project:2 (Agent project:2)
Agent has been idle - no terminal activity detected.
Please check agent status and assign work if needed.
```
**Action**: Check terminal, understand status, assign work

### 2. Rate Limit Notification
```
🚨 RATE LIMIT REACHED: All Claude agents are rate limited.
Will reset at 4am UTC.
```
**Action**: Wait for reset, plan non-Claude work

### 3. Team-Wide Idle Alert
```
⚠️ IDLE TEAM ALERT (3 min)
Your entire team is idle and waiting for task assignments.
```
**Action**: Review team plan, distribute tasks immediately

### 4. Missing Agent Alert
```
🚨 MISSING AGENT DETECTED: project:3
Agent project:3 (qa-engineer) has disappeared from session
```
**Action**: Investigate and respawn if needed

## Managing Daemon Notifications

### Notification Cooldowns
- **Idle agents**: 5-minute cooldown between notifications
- **Crashed agents**: 5-minute cooldown
- **Missing agents**: 30-minute cooldown

### Working with the Daemon Cycle
The daemon checks every 10 seconds:
1. Discovers all agents in your session
2. Checks each agent's status
3. Collects notifications
4. Sends batch notification to PM
5. Applies 60-second cooldown after any notification

### Preventing Notification Spam
- **Respond promptly** to notifications
- **Keep agents busy** with clear task queues
- **Check terminals** before assigning new work
- **Use structured task lists** for agents

## Daemon Stop/Start During Operations

### When to Stop the Daemon
```bash
# Stop before bulk agent spawning
tmux-orc monitor stop

# Spawn your agents...

# Restart after all agents ready
tmux-orc monitor start
```

### When to Keep Daemon Running
- During normal operations
- When agents are working
- During code reviews
- While monitoring progress

## Troubleshooting Daemon Issues

### Daemon Not Detecting Agents
```bash
# Check if agents are properly named
tmux list-windows -t $SESSION_NAME -F "#{window_index}:#{window_name}"

# Windows should be named like "Claude-developer", "Claude-qa"
```

### Too Many Notifications
- Check if agents are actually idle
- Ensure you're responding to notifications
- Verify agents have clear tasks

### No Notifications When Expected
```bash
# Check daemon is running
tmux-orc monitor status

# Check daemon logs
tmux-orc monitor logs -n 50
```

## Best Practices

1. **Start daemon after initial team spawn**
2. **Respond to notifications within 2 minutes**
3. **Use daemon logs for debugging**
4. **Trust daemon's idle detection**
5. **Let daemon handle PM recovery**

Remember: The daemon is your friend, helping you manage a large team efficiently!
