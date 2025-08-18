# Project Status and Completion Checking

> 💡 **CLI Discovery**: For current tmux-orc command syntax, run `tmux-orc reflect` or `tmux-orc --help`

## 📋 Checking Project Completion Status

**When asked "Did the team complete or crash?", follow this procedure:**

### 1. Check for project-closeout.md
```bash
# Find closeout reports in planning directories
find .tmux_orchestrator/planning -name "project-closeout.md" -mtime -7

# Or search for specific project
find .tmux_orchestrator/planning -name "*project-name*" -type d -exec ls -la {} \;
```

### 2. Interpretation
- **Closeout file exists** = Team completed successfully ✅
- **No closeout file** = Team likely crashed or is still running ❌

### 3. If no closeout found, check if session still exists:
```bash
tmux list-sessions | grep [project-name]
```

### 4. Status Matrix

| Closeout | Session | Status | Action |
|----------|---------|--------|--------|
| ✅ Exists | ❌ Gone | **Success** - Project completed properly | Report success to human |
| ✅ Exists | ✅ Exists | **PM Crashed** - After creating closeout | Check closeout, kill session |
| ❌ None | ✅ Exists | **Still Running** - Or crashed without closeout | Check agent status |
| ❌ None | ❌ Gone | **Crashed** - No proper completion | Plan recovery |

## Recovery Procedures

### If Team Crashed (No Closeout)
1. **Stop monitoring**: `tmux-orc monitor stop`
2. **Create recovery plan** with context about previous attempt
3. **Spawn new PM** with recovery briefing:
   ```bash
   tmux-orc spawn pm --session recovery:1
   tmux-orc agent send recovery:1 "Previous team crashed working on [project]. Please review planning dir and continue work."
   ```
4. **Include crash context** in new team plan

### Recovery Briefing Template
```markdown
# Recovery Team Plan - [Project Name]

## Previous Attempt Summary
- Started: [Timestamp]
- Crashed: [Estimated time]
- Progress: [What was completed]
- Issue: [Why it likely crashed]

## Recovery Objectives
1. Assess previous progress
2. Complete remaining tasks
3. Ensure proper closeout

## Special Instructions
- Check git log for previous commits
- Review any partial work
- Verify test status
- Complete missing documentation
```

## Checking Active Project Status

### Quick Status Check
```bash
# See all active sessions
tmux list-sessions

# Check specific session health
SESSION="project"
echo "=== Windows in $SESSION ==="
tmux list-windows -t $SESSION -F "#{window_index}:#{window_name}"

echo "=== Agent Status ==="
tmux-orc agent list | grep $SESSION
```

### Detailed Status Check
```bash
# Check PM status
tmux capture-pane -t project:1 -p | tail -30

# Check if agents are active
for window in 1 2 3 4; do
    echo "=== Window $window ==="
    tmux capture-pane -t project:$window -p | tail -10
done

# Check daemon status
tmux-orc monitor status
```

## Project Closeout Validation

### Good Closeout Indicators
✅ Contains "Executive Summary"
✅ Lists completed objectives
✅ Shows quality metrics (tests, coverage)
✅ Documents team performance
✅ Identifies any remaining work

### Example Closeout Structure
```markdown
# Project Closeout - [Project Name]

**Date**: YYYY-MM-DD
**PM**: Claude-PM
**Status**: ✅ COMPLETE

## Executive Summary
[What was accomplished]

## Objectives Met
- [x] Objective 1
- [x] Objective 2
- [x] Objective 3

## Technical Details
[What was implemented/changed]

## Quality Metrics
- Tests: All passing
- Coverage: 85%
- Pre-commit: Clean
- Documentation: Updated

## Team Performance
[How each agent performed]

## Next Steps
[Any follow-up work identified]
```

## Session Health Indicators

### Healthy Session Signs
- ✅ All windows have "Claude-" prefix
- ✅ Agents responding to messages
- ✅ Regular commit activity
- ✅ No error messages in terminals
- ✅ PM providing regular updates

### Unhealthy Session Signs
- ❌ Windows showing bash prompts
- ❌ "command not found" errors
- ❌ No activity for >10 minutes
- ❌ Rate limit messages
- ❌ Missing PM window

## Project Timeline Expectations

### Typical Project Durations
- **Small fix**: 30 min - 1 hour
- **Feature add**: 1 - 3 hours
- **Major feature**: 3 - 6 hours
- **Refactoring**: 2 - 4 hours

### Warning Signs (Check Status)
- No updates for 30+ minutes
- Project exceeding 2x estimated time
- Multiple agent crashes reported
- PM escalation messages

## Status Reporting to Humans

### Success Report Template
```
✅ Project completed successfully!

Team created comprehensive closeout report:
- Location: .tmux_orchestrator/planning/[timestamp]/project-closeout.md
- Objectives: All met
- Quality: All tests passing, 85% coverage
- Duration: 2.5 hours

The session has been properly terminated.
```

### In-Progress Report Template
```
🔄 Project still in progress

Current status:
- Duration: 1.5 hours
- Active agents: 4/4
- Last update: 5 minutes ago
- Progress: Approximately 60% complete
- Health: All systems normal

Estimated completion: 1 hour
```

### Failure Report Template
```
❌ Project team crashed

Crash details:
- Last activity: 45 minutes ago
- Likely cause: [Rate limit/PM crash/Unknown]
- Progress saved: ~40% complete
- Git commits: 3 saved

Recommended: Spawn recovery team with crash context
```

## Monitoring Best Practices

1. **Check status every 30-60 minutes** for long projects
2. **Look for closeout immediately** when session disappears
3. **Trust the closeout** - PMs are required to create it
4. **Plan recovery quickly** - Fresh context helps
5. **Learn from crashes** - Update team plans

Remember: The presence of project-closeout.md is the definitive success indicator!
