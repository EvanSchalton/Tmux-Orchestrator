# TMUX Orchestrator Running Guide

This guide covers day-to-day operations of the TMUX Orchestrator system.

## Quick Start Commands

### Deploy a Team
```bash
# Auto-detect team from task file
./references/Tmux-Orchestrator/bin/generic-team-deploy.sh tasks.md my-project

# Or use project-specific deployment (if available)
./scripts/tmux-deploy-team.sh tasks.md
```

### Restart Existing Team
```bash
# Simple restart
cd .tmux-orchestrator
./restart.sh

# Or restart specific project
./restart-my-project.sh
```

### Check Team Status
```bash
# Quick status
.tmux-orchestrator/commands/agent-status.sh

# PM schedule check
./references/Tmux-Orchestrator/pm-suite/pm-schedule-tracker.sh dashboard

# Full monitoring
.tmux-orchestrator/monitor-my-project-team.sh
```

## Core Operations

### 1. Team Deployment

#### Automatic Team Detection
The orchestrator analyzes your task file to determine required roles:

```bash
# Frontend indicators: react, vue, ui, component, html, css, javascript
# Backend indicators: api, service, endpoint, python, node, fastapi
# Database indicators: database, sql, postgres, migration, schema
# Always includes: Orchestrator, PM, QA
```

#### Manual Role Specification
```bash
# Deploy specific agents
.tmux-orchestrator/commands/deploy-agent.sh frontend developer
.tmux-orchestrator/commands/deploy-agent.sh backend developer
.tmux-orchestrator/commands/deploy-agent.sh database specialist
```

### 2. Agent Communication

#### Send Messages to Agents
```bash
# Quick message
tmux-message session:window "Your message here"

# Status update request
tmux-message my-project-frontend:0 "STATUS UPDATE: What's your current progress?"

# Task assignment
tmux-message my-project-backend:0 "TASK: Implement user authentication endpoints with JWT tokens"
```

#### Agent-to-Agent Coordination
```bash
# PM coordinating between agents
tmux-message my-project-frontend:0 "Frontend team: API endpoints are ready at /api/v1/"
tmux-message my-project-backend:0 "Backend team: Frontend needs pagination support"
```

### 3. Session Management

#### List Active Sessions
```bash
# All orchestrator sessions
tmux list-sessions | grep -E "(orchestrator|my-project)"

# Session details
tmux list-windows -t my-project-frontend
```

#### Attach to Sessions
```bash
# Attach to specific agent
tmux attach -t my-project-frontend

# Attach to orchestrator
tmux attach -t orchestrator

# Attach to PM
tmux attach -t my-project-my-project
```

#### Kill Sessions
```bash
# Kill specific session
tmux kill-session -t session-name

# Kill all project sessions
tmux list-sessions | grep "my-project" | cut -d: -f1 | xargs -I {} tmux kill-session -t {}
```

### 4. Monitoring & Status

#### Real-Time Monitoring
```bash
# Agent status dashboard
.tmux-orchestrator/commands/agent-status.sh

# Live session monitoring (updates every 5 seconds)
watch -n 5 ".tmux-orchestrator/commands/agent-status.sh"
```

#### PM Schedule Management
```bash
# Check upcoming PM tasks
./references/Tmux-Orchestrator/pm-suite/pm-schedule-tracker.sh next

# Full PM dashboard  
./references/Tmux-Orchestrator/pm-suite/pm-schedule-tracker.sh dashboard

# Manual PM check-in
./references/Tmux-Orchestrator/pm-suite/pm-monitor-status.sh
```

#### Progress Tracking
```bash
# Git activity monitoring
git log --oneline --since="1 hour ago"

# Recent commits by all agents
git log --pretty=format:"%h %an %s" --since="2 hours ago"
```

### 5. Quality Assurance

#### Test Execution
```bash
# Run automated tests
tmux-message my-project-testing:0 "Run full test suite and report results"

# Manual QA check
tmux-message my-project-testing:0 "STATUS: Test coverage report please"
```

#### Code Quality Checks
```bash
# Request linting
tmux-message my-project-frontend:0 "Run npm run lint and fix all issues"

# Type checking
tmux-message my-project-backend:0 "Run mypy type checking and resolve errors"
```

## Advanced Operations

### 1. Custom Team Configurations

#### Create Team Template
```bash
# .tmux-orchestrator/templates/web-app-team.yaml
team_name: "web-app"
roles:
  - orchestrator
  - pm
  - frontend_developer
  - backend_developer
  - qa_engineer
briefings:
  frontend: "Focus on React components with TypeScript"
  backend: "Implement FastAPI with PostgreSQL"
```

#### Deploy from Template
```bash
# Custom deployment script
./deploy-from-template.sh templates/web-app-team.yaml tasks.md
```

### 2. Integration Management

#### Git Automation
```bash
# Check for uncommitted changes across all agents
for session in $(tmux list-sessions -F "#{session_name}" | grep my-project); do
  tmux-message "$session:0" "git status - commit if needed"
done
```

#### Automated Reporting
```bash
# Daily progress report
./references/Tmux-Orchestrator/monitoring/daily-report.sh > daily-progress.md
```

### 3. Scheduling & Automation

#### Schedule Regular Check-ins
```bash
# Schedule PM review
tmux-schedule 60 "PM: Review all agent progress and update status" orchestrator:0

# Schedule git commits
for agent in frontend backend testing; do
  tmux-schedule 30 "Commit your current work with descriptive message" my-project-$agent:0
done
```

#### Automated Quality Gates
```bash
# Before each commit
./references/Tmux-Orchestrator/qa/pre-commit-check.sh

# Before deployment
./references/Tmux-Orchestrator/qa/deployment-check.sh
```

## Troubleshooting Operations

### 1. Stuck or Unresponsive Agents

```bash
# Check agent status
tmux capture-pane -t my-project-frontend:0 -p | tail -20

# Send wake-up message
tmux-message my-project-frontend:0 "ATTENTION: Please provide status update - are you stuck?"

# Restart specific agent
tmux kill-window -t my-project-frontend:Claude-developer
.tmux-orchestrator/commands/deploy-agent.sh frontend developer
```

### 2. Communication Issues

```bash
# Verify message delivery
echo "Testing message delivery..." | tmux-message my-project-frontend:0

# Check tmux session integrity
tmux list-sessions -F "#{session_name}: #{session_created}"

# Recreate communication channels
sudo ln -sf .tmux-orchestrator/scripts/send-claude-message.sh /usr/local/bin/tmux-message
```

### 3. Session Recovery

```bash
# Save current session states
.tmux-orchestrator/commands/save-session-logs.sh

# Recover from logs
.tmux-orchestrator/commands/recover-from-logs.sh session-backup-20231201.tar.gz
```

### 4. Performance Issues

```bash
# Check system resources
top -p $(pgrep -f tmux)

# Monitor tmux server performance
tmux info | grep -E "(sessions|windows|panes)"

# Optimize session count
./clean-idle-sessions.sh
```

## Best Practices

### 1. Daily Operations
- Start with team status check: `.tmux-orchestrator/commands/agent-status.sh`
- Review PM schedule: `pm-schedule-tracker.sh dashboard`
- Check git activity: `git log --oneline --since="yesterday"`
- End with progress commit: Ensure all agents committed work

### 2. Communication Patterns
- **Status Updates**: Request every hour from active agents
- **Task Assignment**: Always include clear success criteria
- **Coordination**: Use PM as central hub for cross-team communication
- **Escalation**: Route blockers to orchestrator level

### 3. Quality Maintenance
- Run tests before major changes
- Enforce 30-minute commit rule
- Use feature branches for all work
- Regular code review through QA agent

### 4. Session Hygiene
- Clean up completed sessions daily
- Save important logs before cleanup
- Monitor session count (recommend <10 active)
- Regular restart of long-running sessions

## Monitoring Dashboards

### System Health Dashboard
```bash
#!/bin/bash
# .tmux-orchestrator/dashboards/health.sh

echo "🏥 TMUX Orchestrator Health Dashboard"
echo "======================================"
echo "Time: $(date)"
echo ""

echo "📊 System Resources:"
echo "  Memory: $(free -h | grep '^Mem:' | awk '{print $3 "/" $2}')"
echo "  CPU: $(uptime | awk -F'[a-z]:' '{print $2}' | awk '{print $1 $2 $3}')"

echo ""
echo "🎭 Active Sessions:"
tmux list-sessions | wc -l | awk '{print "  Total: " $1}'
tmux list-sessions | grep -c orchestrator | awk '{print "  Orchestrators: " $1}'

echo ""
echo "⏰ Recent Activity:"
find .tmux-orchestrator/registry/logs -name "*.log" -mmin -60 | wc -l | awk '{print "  Active in last hour: " $1}'
```

### Progress Dashboard
```bash
#!/bin/bash  
# .tmux-orchestrator/dashboards/progress.sh

echo "📈 Development Progress Dashboard"
echo "================================="
echo ""

echo "📝 Git Activity (Last 24h):"
git log --oneline --since="24 hours ago" | wc -l | awk '{print "  Commits: " $1}'
git log --pretty=format:"%an" --since="24 hours ago" | sort | uniq -c | awk '{print "  " $2 ": " $1 " commits"}'

echo ""
echo "🎯 Task Progress:"
# Parse task file for completion indicators
grep -c "✅\|DONE\|COMPLETE" tasks.md 2>/dev/null | awk '{print "  Completed: " $1}'
grep -c "🔄\|IN PROGRESS\|WORKING" tasks.md 2>/dev/null | awk '{print "  In Progress: " $1}'
```

## Emergency Procedures

### Total System Reset
```bash
#!/bin/bash
# emergency-reset.sh - Use only when system is completely broken

echo "🚨 EMERGENCY RESET - This will kill ALL tmux sessions!"
read -p "Continue? (yes/no): " confirm

if [ "$confirm" = "yes" ]; then
  # Kill all tmux sessions
  tmux kill-server
  
  # Clean up orphaned processes
  pkill -f claude
  
  # Restart fresh
  .tmux-orchestrator/restart.sh
  
  echo "✅ Emergency reset complete"
fi
```

### Data Recovery
```bash
# Recover lost work from tmux logs
.tmux-orchestrator/commands/recover-session-data.sh

# Restore from git
git reflog --all | head -20
git checkout -b recovery-branch <commit-hash>
```

This guide provides comprehensive operational coverage for running the TMUX Orchestrator effectively in day-to-day development workflows.