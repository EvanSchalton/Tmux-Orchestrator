# Deploy Claude Agent

Spawns a new Claude agent based on a team planning document.

## Usage
```
/deploy-agent <session:window> <agent-name> --briefing "<briefing>"
```

### Parameters
- **session:window** (required): Target tmux location (e.g., `project:2`)
- **agent-name** (required): Descriptive name for the agent
- **--briefing** (required): Full agent briefing from team plan

## Document-Driven Approach

Agents should be spawned based on a team plan document that defines:
- Required agents and their expertise
- Individual briefings with full context
- Interaction patterns between agents
- Recovery instructions

## Examples from Team Plans

```bash
# From API project team plan:
/deploy-agent api-project:2 backend-dev --briefing "You are a backend developer specializing in FastAPI..."

# From CLI tool team plan:
/deploy-agent cli-tool:2 cli-engineer --briefing "You are a CLI specialist focused on user experience..."

# Custom agent types:
/deploy-agent content:2 technical-writer --briefing "You are a technical writer creating user guides..."
/deploy-agent research:2 ml-researcher --briefing "You are researching latest ML techniques..."
```

## Examples
```
/deploy-agent frontend
/deploy-agent backend developer
/deploy-agent frontend pm
/deploy-agent database qa
```

## What it does

1. **Creates/uses session** - Sets up tmux session for the component
2. **Creates agent window** - New window with descriptive name
3. **Starts Claude** - Launches Claude in the agent window
4. **Sends role briefing** - Provides role-specific instructions
5. **Returns access info** - Shows how to attach to the session

## Role-Specific Briefings

### Developer
- Focus on implementing features per PRD
- Maintain code quality
- Commit every 30 minutes
- Use meaningful commit messages

### Project Manager (PM)
- Maintain high quality standards
- Coordinate work between team members
- Ensure proper testing coverage
- No shortcuts or compromises

### QA Engineer
- Test thoroughly
- Create comprehensive test plans
- Verify functionality meets requirements
- Report bugs and issues

### Code Reviewer
- Review for security vulnerabilities
- Check performance implications
- Ensure best practices
- Verify project standards compliance

## Session Structure

Each component gets its own session:
- `corporate-coach-frontend`
- `corporate-coach-backend`
- `corporate-coach-database`
- `corporate-coach-docs`

Windows are named by role:
- `Claude-developer`
- `Claude-pm`
- `Claude-qa`
- `Claude-reviewer`

## Example Output
```
📦 Creating session for frontend...
🪟 Creating window for developer...
🤖 Starting Claude agent...
📋 Briefing developer agent...
✅ developer agent deployed for frontend!
Access with: tmux attach -t corporate-coach-frontend
```

## Communication

Send messages to deployed agents:
```bash
tmux-message corporate-coach-frontend:Claude-developer "Please update the tests"
```

## Best Practices

1. **Start orchestrator first** - Use `/start-orchestrator` before deploying agents
2. **Deploy PM early** - Project managers help coordinate multiple developers
3. **Component isolation** - Each component has its own session
4. **Regular check-ins** - Agents should report progress frequently

## Related Commands

- `/start-orchestrator` - Initialize the orchestrator
- `/agent-status` - Check all agent statuses
- `/schedule-checkin` - Schedule agent check-ins
