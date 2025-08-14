# Session Management Guidelines

## ⚠️ CRITICAL: Session Management

**YOU MUST SPAWN ALL AGENTS IN YOUR CURRENT SESSION**

Common mistake to avoid:
- ❌ NEVER create new sessions with `tmux new-session`
- ✅ ALWAYS spawn agents as new windows in YOUR current session

To find your session name: `tmux display-message -p '#S'`
Example: If you're in 'project:1', spawn agents as 'project:2', 'project:3', etc.

## MANDATORY PRE-SPAWN CHECKS

Before spawning any agent, you MUST run these validation checks:

### 1. Check your current session:
```bash
SESSION_NAME=$(tmux display-message -p '#S')
echo "Current session: $SESSION_NAME"
```

### 2. Check existing windows to prevent duplicates:
```bash
tmux list-windows -t $SESSION_NAME -F "#{window_index}:#{window_name}"
```

### 3. Validate no duplicate roles exist:
- Never spawn multiple agents with the same role (e.g., two "Developer" agents)
- Each role should have only ONE agent per session
- Check window names for role conflicts before spawning

## 🚨 CRITICAL: Kill existing PM windows before spawning new PM

```bash
# MANDATORY: Kill any existing PM windows first
tmux list-windows -t $SESSION_NAME | grep -i pm | cut -d: -f1 | xargs -I {} tmux kill-window -t $SESSION_NAME:{} 2>/dev/null || true
```
**This prevents multiple PM conflicts and ensures clean PM succession!**

## SESSION BOUNDARY ENFORCEMENT

- YOU ARE CONFINED TO YOUR SESSION - Never access other sessions
- All team coordination must happen within your assigned session
- Session name format: `{project-name}` (you are window 1, spawn others as 2, 3, etc.)
- NEVER use `tmux attach-session` or switch to other sessions

## Window Numbering Convention

1. **Window 1**: Always the PM (you)
2. **Window 2+**: Team agents in order of importance
   - Window 2: Lead Developer or Architect
   - Window 3: Secondary Developer or QA
   - Window 4+: Supporting roles

## Agent Spawning Best Practices

### Before Spawning
```bash
# Full pre-spawn validation
SESSION_NAME=$(tmux display-message -p '#S')
echo "=== Pre-spawn validation for $SESSION_NAME ==="

# List current windows
echo "Current windows:"
tmux list-windows -t $SESSION_NAME -F "#{window_index}:#{window_name}"

# Check for daemon
if tmux-orc monitor status | grep -q "running"; then
    echo "✓ Daemon is running"
else
    echo "⚠ Daemon not running - start it after spawning agents"
fi
```

### Spawning Pattern
```bash
# Always use explicit session:window format
tmux-orc spawn agent developer $SESSION_NAME:2 --briefing "..."
tmux-orc spawn agent qa-engineer $SESSION_NAME:3 --briefing "..."
```

### Post-Spawn Verification
```bash
# Verify agents spawned correctly
tmux-orc agent list | grep $SESSION_NAME
```

## Common Session Management Errors

### ❌ Creating New Sessions
```bash
# WRONG - Creates isolated session
tmux new-session -d -s other-project
```

### ❌ Switching Sessions
```bash
# WRONG - Abandons your team
tmux switch-client -t other-session
```

### ❌ Attaching to Other Sessions
```bash
# WRONG - Violates session boundaries
tmux attach-session -t different-project
```

### ✅ Correct Approach
```bash
# RIGHT - All work in current session
SESSION_NAME=$(tmux display-message -p '#S')
tmux-orc spawn agent developer $SESSION_NAME:2 --briefing "..."
```

Remember: One session, one team, one project!
