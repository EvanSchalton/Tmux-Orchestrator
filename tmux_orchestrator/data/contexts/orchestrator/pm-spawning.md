# PM Spawning Guide

> 💡 **CLI Discovery**: For current tmux-orc command syntax, run `tmux-orc reflect` or use `--help` flags

## 🚨 CRITICAL: Always Use tmux-orc Commands 🚨

**The #1 cause of PM spawning failures is using raw tmux commands!**

### ❌ WRONG (Messages Won't Submit):
```bash
# These commands will TYPE text but NOT submit it to Claude:
tmux new-session -d -s project
tmux send-keys -t project:1 "message"  # FAILS TO SUBMIT!
```

### ✅ CORRECT (Guaranteed Delivery):
```bash
# Use tmux-orc commands that handle message submission properly:
tmux-orc spawn pm --session project:1
tmux-orc agent send project:1 "message"
```

## PM Spawning Methods

### Method 1: spawn pm (Recommended)
```bash
# Simplest and most reliable
tmux-orc spawn pm --session project:1
```

### Method 2: context spawn
```bash
# Alternative if spawn pm fails
tmux-orc context spawn pm --session project:1
```

### Method 3: Manual with Instructions
```bash
# 1. Stop daemon first
tmux-orc monitor stop

# 2. Create tmux session and launch Claude
tmux new-session -d -s project
tmux rename-window -t project:1 "Claude-pm"
tmux send-keys -t project:1 "claude --dangerously-skip-permissions" Enter

# 3. Wait for Claude to initialize
sleep 8

# 4. Send PM instruction message
tmux-orc agent send project:1 "Welcome! You are being launched as the Project Manager (PM).

Please run the following command to load your PM context:

tmux-orc context show pm

This will provide you with your role, responsibilities, and workflow for managing agent teams.

After loading your context, review the team plan in:
.tmux_orchestrator/planning/[project-dir]/team-plan.md"

# 5. Wait for PM to spawn team, then restart daemon
# (PM will know to start daemon from their context)
```

## Critical Pre-Spawn Steps

### 1. Stop the Daemon
```bash
# ALWAYS stop daemon before spawning PM
tmux-orc monitor stop
```
**Why**: Prevents race conditions and false idle alerts during spawn

### 2. Kill Existing PMs
```bash
# MANDATORY: Remove any existing PM windows
SESSION_NAME="project"
tmux list-windows -t $SESSION_NAME 2>/dev/null | grep -i pm | cut -d: -f1 | xargs -I {} tmux kill-window -t $SESSION_NAME:{} 2>/dev/null || true
```
**Why**: Prevents multiple PM conflicts and ensures clean succession

### 3. Create or Verify Session
```bash
# Check if session exists
if ! tmux has-session -t project 2>/dev/null; then
    tmux new-session -d -s project
fi
```

## PM Initialization Sequence

### What Happens After Spawn:
1. Claude loads in tmux window
2. PM receives instruction message
3. PM runs `tmux-orc context show pm`
4. PM loads their context
5. PM locates and reads team plan
6. PM spawns required agents
7. PM starts monitoring daemon

### Typical Timeline:
- 0-10s: Claude initialization
- 10-30s: PM loads context
- 30-60s: PM reads team plan
- 1-3min: PM spawns team
- 3min+: Team operational

## Verification Steps

### Check PM Spawned:
```bash
# Verify PM window exists
tmux list-windows -t project | grep -i pm

# Check PM is active
tmux-orc agent status project:1
```

### Monitor PM Progress:
```bash
# Watch PM terminal
tmux capture-pane -t project:1 -p | tail -20

# Check if PM loaded context
tmux capture-pane -t project:1 -p | grep "tmux-orc context show pm"
```

## Common PM Spawning Issues

### Issue: PM Doesn't Know They're PM
**Symptom**: PM asks "what should I do?"
**Cause**: Didn't receive instruction message
**Fix**:
```bash
tmux-orc agent send project:1 "You are the PM. Please run: tmux-orc context show pm"
```

### Issue: Multiple PMs Spawn
**Symptom**: Windows named pm, pm1, pm2
**Cause**: Didn't kill existing PMs first
**Fix**:
```bash
# Kill all but the first PM
tmux kill-window -t project:2  # If pm is in window 2
tmux kill-window -t project:3  # If pm is in window 3
```

### Issue: PM Can't Find Team Plan
**Symptom**: "I don't see a team plan"
**Cause**: Wrong directory or path
**Fix**:
```bash
tmux-orc agent send project:1 "Team plan location: .tmux_orchestrator/planning/YYYY-MM-DDTHH-MM-SS-project/team-plan.md"
```

### Issue: Message Not Submitted
**Symptom**: Text appears but PM doesn't respond
**Cause**: Used raw tmux instead of tmux-orc
**Fix**:
```bash
# Clear the unsent message
tmux send-keys -t project:1 C-u

# Resend with tmux-orc
tmux-orc agent send project:1 "Your message here"
```

## PM Recovery Procedures

### If PM Crashes:
1. Stop daemon: `tmux-orc monitor stop`
2. Check for project-closeout.md (might be complete)
3. Kill crashed PM window
4. Spawn replacement PM with context:
   ```bash
   tmux-orc spawn pm --session project:1
   tmux-orc agent send project:1 "Previous PM crashed. Please load context and check team status."
   ```
5. Restart daemon after PM ready

### If PM Becomes Unresponsive:
1. Check if rate limited
2. Try sending a simple message
3. If no response, treat as crashed

## Best Practices

### DO:
- ✅ Always use tmux-orc commands
- ✅ Stop daemon before spawning
- ✅ Kill existing PMs first
- ✅ Wait for PM to fully initialize
- ✅ Verify PM loaded context
- ✅ Restart daemon after team ready

### DON'T:
- ❌ Use raw tmux send-keys
- ❌ Spawn PM with daemon running
- ❌ Allow multiple PMs
- ❌ Rush the initialization
- ❌ Skip verification steps

## Quick Reference Card

```bash
# Complete PM spawn sequence
tmux-orc monitor stop
SESSION="project"
tmux list-windows -t $SESSION 2>/dev/null | grep -i pm | cut -d: -f1 | xargs -I {} tmux kill-window -t $SESSION:{} 2>/dev/null || true
tmux-orc spawn pm --session $SESSION:1

# Wait for PM to spawn team (2-3 minutes)
# Then restart daemon (PM will handle this)
```

Remember: Patience during spawn prevents problems later!
