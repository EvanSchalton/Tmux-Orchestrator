# Project Completion Protocol

## 🚨 MANDATORY PROJECT COMPLETION PROTOCOL 🚨

**AFTER PROJECT CLOSEOUT, YOU MUST IMMEDIATELY SHUTDOWN YOUR SESSION!**

Once you create `project-closeout.md`, you MUST run this exact command:
```bash
tmux kill-session -t $(tmux display-message -p '#S')
```

**THIS IS NOT OPTIONAL - FAILURE TO SHUTDOWN = SYSTEM ASSUMES YOU CRASHED!**

- ✅ Project complete + Session terminated = Success signal to orchestrator
- ❌ Project complete + Session still running = Crash/hang detection
- 🚨 No shutdown after closeout = Monitoring alerts + resource waste

**REMEMBER: Session termination disconnects you from tmux entirely - this is expected and correct!**

## Project Closeout Requirements

Before shutting down, you MUST create a comprehensive `project-closeout.md` in the planning directory:

### Required Sections
1. **Executive Summary** - Brief overview of what was accomplished
2. **Objectives Met** - List of completed objectives from the original plan
3. **Technical Details** - What was implemented/changed
4. **Quality Metrics** - Test results, linting status, coverage
5. **Team Performance** - How each agent performed
6. **Next Steps** - Any follow-up work identified

### Closeout File Location
```bash
# Find your planning directory
PLANNING_DIR=$(find .tmux_orchestrator/planning -name "*$(tmux display-message -p '#S')*" -type d | head -1)

# Create closeout
echo "Creating project closeout in: $PLANNING_DIR"
# ... write your closeout content ...
```

## Complete Shutdown Sequence

1. **Finish all work** - Ensure all tasks are complete
2. **Run final quality checks** - Tests, linting, formatting
3. **Create project-closeout.md** - Comprehensive summary
4. **Kill all agent windows** - Clean up your team
5. **Kill your session** - Final step, disconnects you

```bash
# Complete shutdown sequence
SESSION_NAME=$(tmux display-message -p '#S')

# 1. Kill all agent windows (except yours)
for window in $(tmux list-windows -t $SESSION_NAME -F "#{window_index}" | grep -v "^1$"); do
    tmux kill-window -t $SESSION_NAME:$window
done

# 2. Give a moment for cleanup
sleep 2

# 3. Kill the entire session (including yourself)
tmux kill-session -t $SESSION_NAME
```

## Why This Protocol Exists

The orchestrator uses session existence to determine project status:
- **Session exists + no closeout** = Project still running
- **Session gone + closeout exists** = Project completed successfully
- **Session exists + closeout exists** = PM crashed after completion
- **Session gone + no closeout** = Project crashed/failed

This clear signal prevents resource waste and ensures accurate project tracking.
