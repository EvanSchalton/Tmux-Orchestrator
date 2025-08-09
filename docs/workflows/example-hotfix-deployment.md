# Example: Emergency Hotfix Workflow

This example demonstrates how to rapidly deploy a team to fix a critical production issue using TMUX Orchestrator.

## Scenario

Your production API is returning 500 errors for user authentication. You need to deploy a team immediately to diagnose and fix the issue.

## Step 1: Rapid Team Deployment

```bash
# Deploy emergency response team
tmux-orc quick-deploy backend 3 --project-name auth-hotfix

# Creates:
# - 1 Senior Backend Developer
# - 1 DevOps Engineer
# - 1 Project Manager
```

## Step 2: Brief the Team

```bash
# Send emergency briefing to all agents
tmux-orc team broadcast auth-hotfix "CRITICAL: Auth service returning 500 errors.
Users cannot log in. Started 10 minutes ago.
Logs show 'connection pool exhausted' errors.
Priority: Fix immediately."

# Share error logs
tmux-orc agent send auth-hotfix:0 "$(tail -n 100 /var/log/auth-service/error.log)"
```

## Step 3: Coordinate Investigation

The PM automatically coordinates the team:

```
PM > "Critical issue identified. Assigning investigation tasks:
  - Backend Dev: Check auth service code for connection leaks
  - DevOps: Monitor database connections and system resources
  - I'll coordinate findings and customer communication"
```

## Step 4: Real-Time Monitoring

```bash
# Monitor team activity
tmux-orc monitor dashboard --session auth-hotfix --refresh 5

# Watch team communications
tmux-orc agent messages auth-hotfix --follow
```

## Step 5: Implement Fix

Once the issue is identified:

```bash
# Backend developer implements fix
Backend Dev > "Found issue: DB connections not being released in error cases"
Backend Dev > "Implementing fix in auth_handler.py line 234"

# Create hotfix branch
tmux-orc agent send auth-hotfix:0 "git checkout -b hotfix/auth-connection-leak"
```

## Step 6: Fast-Track Testing

```bash
# Run minimal test suite for hotfix
tmux-orc pm quality-check auth-hotfix --fast

# Only runs:
# - Auth-related unit tests
# - Critical integration tests
# - Basic smoke tests
```

## Step 7: Emergency Deployment

```bash
# Create emergency PR
tmux-orc pm create-pr auth-hotfix \
  --branch hotfix/auth-connection-leak \
  --base main \
  --emergency

# DevOps prepares deployment
DevOps > "Preparing rollout plan:
  1. Deploy to canary (5% traffic)
  2. Monitor for 5 minutes
  3. Full deployment if stable"
```

## Timeline Example

**T+0 minutes**: Issue detected
```bash
tmux-orc quick-deploy backend 3 --project-name auth-hotfix
```

**T+2 minutes**: Team briefed and investigating
```
Backend Dev > "Examining auth service logs..."
DevOps > "DB connections at 98% capacity"
PM > "Notifying stakeholders of ongoing issue"
```

**T+10 minutes**: Root cause identified
```
Backend Dev > "Found it! Connection leak in error handler"
DevOps > "Confirmed: connections spiking on each failed auth"
```

**T+15 minutes**: Fix implemented
```
Backend Dev > "Fix implemented and tested locally"
PM > "Running emergency quality checks"
```

**T+20 minutes**: PR created and approved
```
PM > "PR #1234 created with emergency approval"
DevOps > "Deploying to canary environment"
```

**T+25 minutes**: Issue resolved
```
DevOps > "Canary stable. Rolling out to production"
PM > "Auth service recovered. Preparing incident report"
```

## Error Recovery During Hotfix

If an agent crashes during the emergency:

```bash
# Enable auto-recovery for critical agents
tmux-orc recovery start --emergency --session auth-hotfix

# Manually recover if needed
tmux-orc agent restart auth-hotfix:0 --restore-context
```

## Post-Incident Actions

```bash
# Generate incident report
tmux-orc pm report auth-hotfix --type incident

# Archive team communications
tmux-orc agent messages auth-hotfix --export > incident-log.txt

# Schedule post-mortem
tmux-orc team broadcast auth-hotfix "Post-mortem scheduled for tomorrow 2pm"
```

## Emergency Command Reference

### Rapid Deployment
```bash
tmux-orc quick-deploy backend 3 --project-name emergency
tmux-orc team add emergency "Security Expert" --role security
```

### Crisis Communication
```bash
tmux-orc team broadcast emergency "UPDATE: ..."
tmux-orc agent send-all emergency "New information: ..."
```

### Fast Validation
```bash
tmux-orc pm quality-check emergency --fast --critical-only
tmux-orc execute test emergency --smoke-only
```

### Emergency PR
```bash
tmux-orc pm create-pr emergency --emergency --skip-full-tests
```

## Best Practices for Emergencies

1. **Speed Over Perfection**: Get a working fix out quickly
2. **Minimal Team**: 3-4 agents maximum for fast coordination
3. **Clear Communication**: Use broadcasts for critical updates
4. **Focused Testing**: Run only essential tests
5. **Document Everything**: All actions are logged for post-mortem

## Common Emergency Scenarios

### Database Outage
```bash
tmux-orc quick-deploy backend 2 --project-name db-recovery
tmux-orc team add db-recovery "Database Expert" --role dba
```

### Security Breach
```bash
tmux-orc quick-deploy backend 4 --project-name security-incident
tmux-orc agent send security-incident:0 "PRIORITY: Disable user registration immediately"
```

### Performance Crisis
```bash
tmux-orc quick-deploy backend 3 --project-name perf-crisis
tmux-orc monitor performance --session perf-crisis --analyze
```

## Recovery Success Metrics

A successful emergency response shows:
- ⏱️ Time to Deploy: < 2 minutes
- 🔍 Time to Root Cause: < 15 minutes
- 🔧 Time to Fix: < 30 minutes
- ✅ Time to Resolution: < 45 minutes
- 📊 Customer Impact: Minimized
