# Orchestrator Workflow

> 💡 **CLI Discovery**: For current tmux-orc command syntax, run `tmux-orc reflect` or use `--help` flags

## Complete Workflow Process

### 1. Receive Requirements
When a human provides a request, your first step is to understand and document it properly.

### 2. Create Project Directory
**🚨 CRITICAL: Use ISO timestamp format**
```bash
# Create directory with ISO timestamp
TIMESTAMP=$(date -u +"%Y-%m-%dT%H-%M-%S")
PROJECT_NAME="descriptive-name"
PLANNING_DIR=".tmux_orchestrator/planning/${TIMESTAMP}-${PROJECT_NAME}"
mkdir -p "$PLANNING_DIR"
```

**Format Rules:**
- ✅ CORRECT: `2025-01-14T16-30-00-daemon-fixes`
- ❌ WRONG: `daemon-fixes-2025-01-14` or `code-review-2025-01-14`

### 3. Create Requirements Briefing
Save the human's request as `briefing.md` for permanent record:
```bash
cat > "$PLANNING_DIR/briefing.md" << 'EOF'
# Project Briefing

**Date**: [ISO Date]
**Requested by**: Human operator
**Project**: [Project Name]

## Original Request
[Exact copy of human's request]

## Interpreted Requirements
[Your understanding of what needs to be done]

## Success Criteria
[How we'll know the project is complete]
EOF
```

### 4. Create Team Plan
Generate `team-plan.md` based on requirements:
```bash
cat > "$PLANNING_DIR/team-plan.md" << 'EOF'
# Team Plan - [Project Name]

## Project Overview
[Brief description of the project goals]

## Team Composition
- **PM**: Window 1 - Overall coordination
- **[Role]**: Window 2 - [Specific responsibility]
- **[Role]**: Window 3 - [Specific responsibility]

## Task Breakdown
1. [Major task 1]
2. [Major task 2]
3. [Major task 3]

## Agent Briefings
[Specific context for each agent role]

## Success Metrics
[How we measure completion]
EOF
```

### 5. Stop Monitoring Daemon
**Prevent race conditions during team spawn:**
```bash
# Discover monitor commands: tmux-orc reflect --filter "monitor.*stop"
tmux-orc monitor stop
```

### 6. Kill Existing PM Windows
**🚨 CRITICAL: Prevent multiple PM conflicts**
```bash
# Clean up any existing PMs
SESSION_NAME="your-project-session"
tmux list-windows -t $SESSION_NAME 2>/dev/null | grep -i pm | cut -d: -f1 | xargs -I {} tmux kill-window -t $SESSION_NAME:{} 2>/dev/null || true
```

### 7. Spawn PM
**🚨 CRITICAL: Spawn PM using proper method**

#### Method 1: Using spawn pm (Recommended)
```bash
# Discover spawn command: tmux-orc reflect --filter "spawn.*pm"
tmux-orc spawn pm --session project:1
```

#### Method 2: Using context spawn
```bash
# Alternative method: tmux-orc reflect --filter "context.*spawn"
tmux-orc context spawn pm --session project:1
```

#### Method 3: Manual spawn with instructions
```bash
# Create session and launch Claude
tmux new-session -d -s project
tmux rename-window -t project:1 "Claude-pm"
tmux send-keys -t project:1 "claude --dangerously-skip-permissions" Enter

# Wait for Claude to initialize
sleep 8

# Send PM instruction message
# Discover messaging: tmux-orc reflect --filter "agent.*send"
tmux-orc agent send project:1 "Welcome! You are being launched as the Project Manager (PM).

Please run the following command to load your PM context:

# Show context: tmux-orc reflect --filter "context.*show"
tmux-orc context show pm

This will provide you with your role, responsibilities, and workflow for managing agent teams.

After loading your context, review the team plan in:
.tmux_orchestrator/planning/[project-dir]/team-plan.md"
```

### 8. Wait for PM Initialization
- PM loads their context
- PM reviews team plan
- PM spawns initial team members
- PM confirms all agents ready

### 9. Restart Monitoring Daemon
**Only after all agents are spawned:**
```bash
# Discover monitor start: tmux-orc reflect --filter "monitor.*start"
tmux-orc monitor start
```

### 10. Monitor Progress
- Check for PM updates
- Handle escalations
- Track milestone completion
- Ensure quality gates

### 11. Handle Completion
When PM creates `project-closeout.md`:
- Verify objectives met
- Check session terminated
- Report results to human
- Archive project materials

## Workflow Timing Guidelines

- **Steps 1-4**: 5-10 minutes (planning)
- **Steps 5-8**: 5 minutes (PM spawn)
- **Step 9**: Immediate
- **Step 10**: Ongoing until completion
- **Step 11**: 5 minutes (wrap-up)

## Common Workflow Issues

### PM Not Loading Context
If PM doesn't run context show pm (use `tmux-orc reflect --filter "context.*show"`):
```bash
# Use discovered messaging command
tmux-orc agent send project:1 "Please start by running context show pm (see tmux-orc reflect --filter context.show)"
```

### Daemon Starting Too Early
If daemon starts before agents ready:
- Stop daemon
- Wait for PM to finish spawning
- Restart daemon

### Multiple PMs Spawned
If you see multiple PM windows:
- Stop daemon
- Kill duplicate PMs
- Ensure only one PM per project

## Workflow Checklist

Before spawning PM:
- [ ] Created planning directory with ISO timestamp
- [ ] Created briefing.md
- [ ] Created team-plan.md
- [ ] Stopped monitoring daemon
- [ ] Killed any existing PMs

After spawning PM:
- [ ] PM loaded context
- [ ] PM reviewed team plan
- [ ] PM spawned team
- [ ] Restarted daemon
- [ ] Monitoring progress

Remember: Follow this workflow precisely for reliable results!
