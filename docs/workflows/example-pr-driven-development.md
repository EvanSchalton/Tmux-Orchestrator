# Example: PRD-Driven Development Workflow

This example demonstrates the complete workflow for implementing a new feature using the TMUX Orchestrator's PRD-driven development approach.

## Scenario

Your team needs to implement a new "User Profile Management" feature for a web application.

## Step 1: Create Feature Request

First, create a feature request document:

```markdown
# Feature Request: User Profile Management

## Overview
Add comprehensive user profile management to allow users to customize their account settings, upload avatars, and manage preferences.

## Requirements
- Profile information editing (name, bio, location)
- Avatar upload with image cropping
- Email notification preferences
- Privacy settings
- Account deletion capability

## Technical Constraints
- Must integrate with existing auth system
- Avatar images limited to 5MB
- GDPR compliance required
- Mobile-responsive design

## Success Criteria
- Users can successfully update all profile fields
- Avatar upload works on all supported browsers
- All changes are persisted correctly
- No regression in existing functionality
```

## Step 2: Generate PRD from Feature Request

```bash
# Generate PRD using the execute command
tmux-orc execute feature-to-prd ./feature-request-profile.md

# This creates a comprehensive PRD with:
# - Detailed specifications
# - Task breakdown
# - Testing requirements
# - Deployment plan
```

## Step 3: Deploy Development Team

```bash
# Deploy a fullstack team for the implementation
tmux-orc team deploy user-profile fullstack 5

# This creates:
# - 1 Project Manager (PM)
# - 1 Frontend Developer
# - 1 Backend Developer
# - 1 QA Engineer
# - 1 UI/UX Specialist
```

## Step 4: Execute PRD with Team

```bash
# PM reads and distributes the PRD
tmux-orc execute prd ./prd-user-profile.md --session user-profile

# The PM will:
# 1. Parse the PRD into actionable tasks
# 2. Assign tasks to appropriate team members
# 3. Set up task tracking
# 4. Monitor progress
```

## Step 5: Monitor Development Progress

```bash
# Start monitoring daemon
tmux-orc monitor start --interval 30

# View real-time dashboard
tmux-orc monitor dashboard --session user-profile

# Check task status
tmux-orc tasks status --session user-profile
```

## Step 6: Quality Assurance

```bash
# Run automated quality checks
tmux-orc pm quality-check user-profile

# This runs:
# - Unit tests
# - Integration tests
# - Linting
# - Type checking
# - Security scans
```

## Step 7: Create Pull Request

```bash
# PM creates PR when all tasks complete
tmux-orc pm create-pr user-profile \
  --branch feature/user-profile \
  --base main

# Automatically includes:
# - Task completion summary
# - Test results
# - Quality check status
```

## Example Task Flow

Here's what happens behind the scenes:

### PM Activity
```
PM > "I've received the PRD for User Profile Management. Breaking down into tasks..."
PM > "Task assignments:
  - PROFILE-001: Create profile API endpoints → Backend Developer
  - PROFILE-002: Design profile UI components → UI/UX Specialist
  - PROFILE-003: Implement profile form → Frontend Developer
  - PROFILE-004: Add avatar upload → Frontend + Backend
  - PROFILE-005: Write integration tests → QA Engineer"
```

### Developer Communication
```
Backend Dev > "Starting PROFILE-001. Creating REST endpoints for profile CRUD operations."
Frontend Dev > "Waiting for API specs from PROFILE-001 before starting form implementation."
QA Engineer > "Setting up test framework for profile management features."
```

### Task Updates
```
# Developers report progress
Backend Dev > "PROFILE-001 completed. API docs available at /docs/api/profile"
Frontend Dev > "PROFILE-003 in progress. Implementing form validation."
QA Engineer > "PROFILE-005 blocked. Need API endpoints to test against."
```

## Monitoring and Recovery

If an agent becomes unresponsive:

```bash
# Check agent health
tmux-orc agent status user-profile:1

# Restart if needed
tmux-orc agent restart user-profile:1

# Recovery daemon automatically:
# - Detects idle agents
# - Attempts recovery
# - Restores context
# - Notifies PM of issues
```

## Best Practices

1. **PRD Quality**: The better your PRD, the smoother the execution
2. **Team Size**: 4-6 agents is optimal for most features
3. **Monitoring**: Always run monitoring for production work
4. **Communication**: Use the broadcast feature for team-wide updates
5. **Quality Gates**: Never skip automated checks before PR creation

## Command Reference

```bash
# Team management
tmux-orc team status user-profile
tmux-orc team broadcast user-profile "Daily standup in 5 minutes"

# Task tracking
tmux-orc tasks list --status in-progress
tmux-orc tasks assign PROFILE-003 user-profile:2

# Progress monitoring
tmux-orc pm report user-profile
tmux-orc monitor performance --session user-profile

# Error handling
tmux-orc errors recent --session user-profile
tmux-orc errors summary
```

## Troubleshooting

### Agent Not Responding
```bash
tmux-orc agent check-health user-profile:1
tmux-orc recovery manual user-profile:1
```

### Task Blocked
```bash
tmux-orc tasks update PROFILE-005 --status blocked --reason "Waiting for API"
tmux-orc pm coordinate user-profile
```

### Quality Check Failures
```bash
tmux-orc pm quality-check user-profile --detailed
tmux-orc agent send user-profile:2 "Please fix linting errors in ProfileForm.tsx"
```

## Results

When complete, you'll have:
- ✓ Fully implemented feature matching PRD specifications
- ✓ Comprehensive test coverage
- ✓ Clean, well-documented code
- ✓ Ready-to-merge pull request
- ✓ Complete audit trail of development process
