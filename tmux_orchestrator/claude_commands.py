"""Embedded Claude slash commands for tmux-orchestrator."""

SLASH_COMMANDS = {
    "create-prd.md": """# Create PRD from Feature Description

Generate a comprehensive Product Requirements Document (PRD) from a feature description file.

## Usage
```
/create-prd feature_description.md
```

## What it does
1. Reads your feature description from the specified file
2. Asks clarifying questions to understand requirements
3. Generates a structured PRD with:
   - Executive summary
   - User stories and personas
   - Functional requirements
   - Technical specifications
   - Success metrics
   - Timeline estimates

## Example

### Input file (feature_description.md):
```
We need a user authentication system that supports:
- Email/password login
- Social login (Google, GitHub)
- Two-factor authentication
- Password reset via email
- Remember me functionality
```

### Output
The command will generate a complete PRD that can be executed with:
```
tmux-orc execute ./generated-prd.md
```

## Tips
- Be specific about your requirements in the description file
- Include any technical constraints or preferences
- Mention target users and use cases
- Specify any integration requirements

## Next Steps
After generating the PRD:
1. Review and edit the generated PRD if needed
2. Run `/generate-tasks` to create the task breakdown
3. Execute with `tmux-orc execute ./generated-prd.md`
""",
    "generate-tasks.md": """# Generate Tasks from PRD

Break down a Product Requirements Document into executable tasks for the AI agent team.

## Usage
```
/generate-tasks
```

## Prerequisites
- Must have a PRD file in the current directory (usually `prd.md` or similar)
- PRD should follow the standard format from `/create-prd`

## What it does
1. Analyzes the current PRD
2. Identifies all deliverables and requirements
3. Creates a hierarchical task structure:
   - Epic-level tasks
   - Feature-level tasks
   - Implementation tasks
   - Testing tasks
   - Documentation tasks
4. Assigns priorities and dependencies
5. Estimates effort for each task
6. Suggests optimal agent assignments

## Output Format
```markdown
# Task List for [Project Name]

## Epic 1: Authentication System
### Task 1.1: Implement Login API
- **Priority**: High
- **Assigned to**: Backend Agent
- **Estimated effort**: 4 hours
- **Dependencies**: Database schema setup
- **Acceptance criteria**:
  - POST /api/auth/login endpoint
  - JWT token generation
  - Rate limiting implemented

### Task 1.2: Create Login UI Components
- **Priority**: High
- **Assigned to**: Frontend Agent
...
```

## Integration with Tmux Orchestrator
The generated task list is automatically formatted for:
- Distribution to appropriate agents via `tmux-orc tasks distribute`
- Progress tracking with `tmux-orc tasks status`
- Automatic task assignment based on agent expertise

## Next Steps
1. Review generated tasks
2. Run `tmux-orc execute [prd-file]` to deploy agents
3. Monitor progress with `tmux-orc tasks status`
""",
    "agent-status.md": """# Check Agent Status

Get real-time status of all active tmux orchestrator agents.

## Usage
```
/agent-status
```

## What it shows
- **Active Agents**: All running agent sessions
- **Agent Types**: Role of each agent (PM, Developer, QA, etc.)
- **Current Activity**: What each agent is working on
- **Health Status**: Idle, Active, Blocked, or Unresponsive
- **Session Info**: Tmux session and window details
- **Last Activity**: Timestamp of last meaningful action

## Status Indicators

### Health Status
- 🟢 **Active**: Currently working on tasks
- 🟡 **Idle**: Waiting for input or tasks
- 🔴 **Blocked**: Waiting on dependencies or facing errors
- ⚫ **Unresponsive**: No activity for extended period

### Agent Types
- **Orchestrator**: Main coordination agent
- **PM**: Project Manager - planning and quality control
- **Developer**: Implementation and coding
- **QA**: Testing and verification
- **DevOps**: Infrastructure and deployment
- **Reviewer**: Code review and security

## Example Output
```
🟢 project-alpha:orchestrator - Active
   Last: Coordinating backend API implementation (2 min ago)

🟢 project-alpha:pm - Active
   Last: Reviewing PR #42 for API endpoints (5 min ago)

🟡 project-alpha:frontend - Idle
   Last: Completed login component (15 min ago)

🔴 project-alpha:backend - Blocked
   Last: Waiting for database schema approval (45 min ago)
```

## Quick Actions
After checking status:
- Send message to specific agent: `tmux-orc agent send [session:window] "message"`
- Restart unresponsive agent: `tmux-orc agent restart [session:window]`
- View agent output: `tmux-orc monitor dashboard`

## Monitoring Best Practices
1. Check status regularly during active development
2. Address blocked agents promptly
3. Restart unresponsive agents
4. Ensure PM agent is coordinating effectively
""",
    "deploy-agent.md": """# Deploy Specialized Agent

Spawn a new Claude agent with a specific role in your project.

## Usage
```
/deploy-agent [role] [project-name]
```

## Available Roles
- **developer**: General development tasks
- **frontend**: UI/UX implementation
- **backend**: API and server development
- **pm**: Project management and coordination
- **qa**: Testing and quality assurance
- **devops**: Infrastructure and deployment
- **reviewer**: Code review and best practices
- **researcher**: Technical research and evaluation
- **docs**: Documentation writing

## Examples
```
/deploy-agent frontend my-app
/deploy-agent backend api-service
/deploy-agent pm team-alpha
```

## What happens
1. Creates new tmux session: `[project-name]-[role]`
2. Starts Claude with role-specific prompt
3. Sets up project directory context
4. Provides initial briefing based on role
5. Integrates with existing team

## Role-Specific Behaviors

### Developer Agent
- Focuses on implementation
- Follows coding standards
- Commits regularly
- Writes tests

### PM Agent
- Monitors team progress
- Enforces quality gates
- Schedules check-ins
- Manages task distribution

### QA Agent
- Writes and runs tests
- Verifies requirements
- Reports bugs
- Ensures coverage

## Team Composition
For different project types:

### Web Application
```
/deploy-agent pm my-app
/deploy-agent frontend my-app
/deploy-agent backend my-app
/deploy-agent qa my-app
```

### API Service
```
/deploy-agent pm api-service
/deploy-agent backend api-service
/deploy-agent devops api-service
/deploy-agent qa api-service
```

## Best Practices
1. Always deploy a PM agent first
2. Deploy QA agent early for TDD
3. Add specialized agents as needed
4. Use consistent project names

## Monitoring
After deployment:
- Check status: `/agent-status`
- View output: `tmux-orc monitor dashboard`
- Send tasks: `tmux-orc agent send [session:window] "task"`
""",
    "schedule-checkin.md": """# Schedule Agent Check-in

Schedule automated check-ins for your AI agents to maintain momentum.

## Usage
```
/schedule-checkin [interval] [message]
```

## Parameters
- **interval**: How often to check in (e.g., "30m", "1h", "2h")
- **message**: Optional custom check-in message

## Examples
```
/schedule-checkin 1h
/schedule-checkin 30m "Review PR status and continue implementation"
/schedule-checkin 2h "Check test results and fix any failures"
```

## Default Check-in Messages
If no message provided, agents receive role-specific prompts:

### PM Agent
- Review team progress
- Check for blocked tasks
- Update project status
- Plan next steps

### Developer Agent
- Continue current implementation
- Commit any pending changes
- Review and refactor code
- Start next task

### QA Agent
- Run test suites
- Update test coverage
- Document any issues
- Verify fixed bugs

## How it Works
1. Creates background scheduler
2. Sends wake-up message at specified intervals
3. Includes context about:
   - Current project state
   - Pending tasks
   - Team member status
   - Recent commits

## Check-in Message Format
```
🔔 Scheduled Check-in

Time for your scheduled review:
1. Check current task progress
2. Commit any pending changes
3. Review team member updates
4. Continue with: [specific task]

Current context:
- Project: [project-name]
- Sprint: Active
- Pending PRs: 2
- Tests: Passing ✓
```

## Managing Schedules
- View active schedules: `tmux-orc schedule list`
- Cancel schedule: `tmux-orc schedule cancel [id]`
- Modify interval: `tmux-orc schedule update [id] [new-interval]`

## Best Practices
1. **PM agents**: Schedule every 1-2 hours
2. **Dev agents**: Schedule every 30-60 minutes during active work
3. **QA agents**: Schedule after each feature completion
4. Include specific tasks in custom messages
5. Adjust intervals based on project phase

## Advanced Scheduling
```bash
# Schedule with specific tasks
/schedule-checkin 1h "Focus on: 1) API authentication 2) Error handling 3) Tests"

# Schedule for specific agent
tmux-orc schedule add project:pm --interval 2h --message "Team sync"

# Conditional scheduling
tmux-orc schedule add project:qa --interval 30m --if-idle 15m
```
""",
    "process-task-list.md": """# Process Task List

Execute a task list with progress tracking and agent coordination.

## Usage
```
/process-task-list [task-file]
```

## Prerequisites
- Task list file (usually from `/generate-tasks`)
- Active agent team or orchestrator

## What it does
1. Parses the task list
2. Assigns tasks to appropriate agents
3. Tracks progress in real-time
4. Manages dependencies
5. Reports completion status

## Task Assignment Logic
- **Frontend tasks** → Frontend agent
- **Backend/API tasks** → Backend agent
- **Testing tasks** → QA agent
- **Infrastructure** → DevOps agent
- **Documentation** → Docs agent
- **Coordination** → PM agent

## Progress Tracking
Creates `.tmux_orchestrator/projects/[name]/` with:
- `status/progress.md` - Real-time updates
- `status/completed.md` - Finished tasks
- `status/blocked.md` - Blocked tasks
- `agents/[agent]-tasks.md` - Per-agent assignments

## Example Workflow
```bash
# 1. Generate tasks from PRD
/generate-tasks

# 2. Review and edit tasks.md if needed

# 3. Process the task list
/process-task-list ./tasks.md

# 4. Monitor progress
tmux-orc tasks status my-project
```

## Task Status Updates
- ⬜ **Pending**: Not started
- 🔄 **In Progress**: Currently being worked on
- ✅ **Completed**: Finished and verified
- ❌ **Blocked**: Waiting on dependencies
- 🔍 **In Review**: Completed, pending review

## Handling Blocked Tasks
When tasks are blocked:
1. System identifies the blockage
2. Notifies the PM agent
3. PM coordinates resolution
4. Updates dependencies
5. Resumes blocked tasks

## Best Practices
1. Review generated task list before processing
2. Ensure all required agents are deployed
3. Monitor blocked tasks actively
4. Use PM agent for coordination
5. Keep task descriptions clear and atomic
""",
    "development-patterns.md": """# Tmux Orchestrator Development Patterns

Best practices and patterns for AI agent development with tmux-orchestrator.

## Team Composition Patterns

### 🌐 Full-Stack Web Application
```bash
tmux-orc team deploy my-app --type fullstack
```
Deploys: Orchestrator, PM, Frontend, Backend, QA

### 🔧 API Service
```bash
tmux-orc team deploy api-service --type backend
```
Deploys: Orchestrator, PM, Backend, DevOps, QA

### 🧪 Testing-Focused Team
```bash
tmux-orc team deploy test-suite --type testing
```
Deploys: Orchestrator, PM, QA, Test Engineer, Developer

## Communication Patterns

### 📢 Broadcast Pattern
For team-wide announcements:
```bash
tmux-orc team broadcast my-app "Switching to feature-auth branch"
```

### 🤝 Handoff Pattern
For task transitions:
```bash
# Backend to Frontend handoff
tmux-orc agent send backend:1 "API endpoints ready at /api/v1/auth"
tmux-orc agent send frontend:1 "Please integrate auth UI with new endpoints"
```

### 🔄 Round-Robin Review
For code review cycles:
```bash
# PM initiates review cycle
tmux-orc agent send pm:1 "Start code review for PR #42"
# Reviews flow: Developer → Reviewer → QA → PM
```

## Task Management Patterns

### 📋 Kanban Flow
```
TODO → IN_PROGRESS → REVIEW → TESTING → DONE
```

Track with:
```bash
tmux-orc tasks status --format kanban
```

### 🎯 Sprint Pattern
```bash
# Start sprint
tmux-orc tasks create sprint-1 --duration 2w

# Daily standup
tmux-orc team broadcast sprint-1 "Daily standup: Share progress and blockers"

# Sprint review
tmux-orc tasks export sprint-1 --format retrospective
```

## Quality Assurance Patterns

### ✅ Continuous Testing
```bash
# QA agent runs tests on every commit
tmux-orc agent send qa:1 "Monitor commits and run tests automatically"
```

### 🛡️ Quality Gates
```yaml
# .tmux_orchestrator/quality-gates.yml
pre-commit:
  - lint
  - format
  - type-check

pre-merge:
  - all-tests-pass
  - coverage > 80%
  - no-security-issues
```

## Recovery Patterns

### 🔄 Auto-Recovery
```bash
# Enable auto-recovery daemon
tmux-orc recovery start --auto-restart

# Configure recovery rules
tmux-orc recovery config --max-failures 3 --restart-delay 5m
```

### 📊 Health Monitoring
```bash
# Real-time dashboard
tmux-orc monitor dashboard

# Health checks
tmux-orc recovery test --comprehensive
```

## Git Workflow Patterns

### 🌿 Feature Branch Flow
```bash
# PM creates feature plan
tmux-orc agent send pm:1 "Plan feature: user-authentication"

# Agents work on feature branches
tmux-orc team broadcast my-app "Create branch: feature/user-auth"

# Regular integration
tmux-orc agent send pm:1 "Schedule: Merge to develop every 2 hours"
```

### 🔀 Parallel Development
```bash
# Split team for parallel work
tmux-orc agent send pm:1 "Assign: Frontend→UI, Backend→API, DevOps→Infrastructure"

# Coordinate integration points
tmux-orc schedule add pm:1 --interval 2h --message "Sync integration points"
```

## Scaling Patterns

### 📈 Horizontal Scaling
```bash
# Add more agents of same type
tmux-orc agent spawn additional-backend backend:2
tmux-orc agent spawn additional-frontend frontend:2

# Load balance tasks
tmux-orc tasks distribute --strategy round-robin
```

### 🎛️ Vertical Scaling
```bash
# Specialize agents
tmux-orc agent spawn api-specialist backend:2 --briefing "Focus on REST API design"
tmux-orc agent spawn ui-specialist frontend:2 --briefing "Focus on component library"
```

## Integration Patterns

### 🔌 CI/CD Integration
```yaml
# .github/workflows/ai-team.yml
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  ai-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: |
          tmux-orc agent send reviewer:1 "Review PR #${{ github.event.number }}"
          tmux-orc agent send qa:1 "Test PR #${{ github.event.number }}"
```

### 📊 Metrics Collection
```bash
# Track productivity metrics
tmux-orc metrics enable --output prometheus

# Custom metrics
tmux-orc metrics add custom.tasks_per_hour
tmux-orc metrics add custom.bugs_fixed
```

## Anti-Patterns to Avoid

### ❌ Agent Overload
```bash
# Bad: One agent doing everything
tmux-orc agent send developer:1 "Build frontend, backend, write tests, deploy"

# Good: Distribute responsibilities
tmux-orc tasks distribute ./tasks.md --max-per-agent 3
```

### ❌ Missing Coordination
```bash
# Bad: Agents working in isolation
# Good: Regular sync points
tmux-orc schedule add pm:1 --interval 1h --message "Team sync and coordination"
```

### ❌ Ignoring Failures
```bash
# Bad: Let agents stay stuck
# Good: Active monitoring
tmux-orc recovery start --auto-restart --notify-on-failure
```

## Advanced Patterns

### 🧠 Self-Improving Team
```bash
# Retrospective analysis
tmux-orc team broadcast my-app "Retrospective: What worked? What didn't?"

# Capture learnings
tmux-orc tasks export my-app --format lessons-learned >> .tmux_orchestrator/knowledge-base.md
```

### 🔄 Continuous Deployment
```bash
# Auto-deploy on tests passing
tmux-orc agent send devops:1 "Setup: Auto-deploy when all tests pass"

# Progressive rollout
tmux-orc agent send devops:1 "Configure: Canary deployment 10% → 50% → 100%"
```

## Pattern Templates

Access pre-configured patterns:
```bash
# List available patterns
tmux-orc patterns list

# Apply a pattern
tmux-orc patterns apply microservice my-service

# Create custom pattern
tmux-orc patterns create my-pattern --from-project my-app
```
""",
    "start-orchestrator.md": """# Start Tmux Orchestrator

Initialize the main orchestrator agent to coordinate your AI development team.

## Usage
```
/start-orchestrator [project-name]
```

## What it does
1. Creates orchestrator tmux session
2. Starts Claude with orchestrator role
3. Sets up project structure
4. Prepares for team deployment
5. Initializes monitoring

## Examples
```
/start-orchestrator my-webapp
/start-orchestrator backend-api
/start-orchestrator data-pipeline
```

## Orchestrator Responsibilities
- **Team Deployment**: Spawns specialized agents
- **Task Distribution**: Assigns work to team members
- **Coordination**: Manages inter-agent communication
- **Quality Control**: Enforces standards and gates
- **Progress Tracking**: Monitors project advancement

## First Steps After Starting
1. **Deploy your team**:
   ```
   tmux-orc team deploy [project] --type [frontend|backend|fullstack]
   ```

2. **Provide project context**:
   ```
   tmux-orc agent send orchestrator:1 "Project brief: [description]"
   ```

3. **Set quality standards**:
   ```
   tmux-orc agent send orchestrator:1 "Enforce: TDD, 80% coverage, PR reviews"
   ```

## Project Structure Created
```
.tmux_orchestrator/
├── projects/
│   └── [project-name]/
│       ├── prd.md
│       ├── tasks.md
│       ├── agents/
│       └── status/
└── logs/
```

## Monitoring the Orchestrator
- View output: `tmux attach -t [project-name]`
- Check status: `tmux-orc agent status`
- See decisions: `tmux-orc monitor dashboard`

## Best Practices
1. **Clear project names**: Use descriptive, unique names
2. **Early context**: Provide project details immediately
3. **Regular check-ins**: Schedule orchestrator reviews
4. **Resource limits**: Set max team size if needed

## Advanced Configuration
```bash
# Start with custom configuration
/start-orchestrator my-app --config advanced

# Options include:
# - Max team size
# - Auto-scaling rules
# - Quality thresholds
# - Communication patterns
```

## Troubleshooting
If orchestrator seems stuck:
1. Check status: `/agent-status`
2. Send wake-up: `tmux-orc agent send orchestrator:1 "Status update?"`
3. Review logs: `tmux-orc logs orchestrator`
4. Restart if needed: `tmux-orc agent restart orchestrator:1`
""",
    "cleanup-claude.md": """# Clean Up Claude Sessions

Clean up tmux sessions and orchestrator artifacts from completed or abandoned projects.

## Usage
```
/cleanup-claude [project-name|--all]
```

## Examples
```
/cleanup-claude my-app
/cleanup-claude --all
/cleanup-claude --inactive 24h
```

## What it cleans
1. **Tmux sessions**: Terminates specified sessions
2. **Task files**: Archives to `.tmux_orchestrator/archive/`
3. **Logs**: Compresses and stores
4. **Git branches**: Lists (but doesn't delete) feature branches
5. **Temporary files**: Removes work artifacts

## Cleanup Process
1. **Confirmation**: Lists what will be cleaned
2. **Graceful shutdown**: Sends exit to agents
3. **Archive creation**: Saves important data
4. **Session termination**: Kills tmux sessions
5. **Report generation**: Summary of cleanup

## Archive Structure
```
.tmux_orchestrator/archive/
└── [project-name]-[date]/
    ├── prd.md
    ├── tasks/
    ├── logs/
    ├── commits.log
    └── summary.md
```

## Selective Cleanup
```bash
# Clean only tmux sessions
/cleanup-claude my-app --sessions-only

# Clean only old logs
/cleanup-claude --logs-older-than 7d

# Dry run to see what would be cleaned
/cleanup-claude my-app --dry-run
```

## Safety Features
- **No code deletion**: Never deletes source code
- **Archive first**: Always archives before removing
- **Confirmation required**: Shows what will be removed
- **Recovery possible**: Archives can be restored

## When to Clean Up
- Project completed and deployed
- Project abandoned or cancelled
- Before starting similar project
- Regular maintenance (weekly/monthly)

## Post-Cleanup Actions
1. **Review archive**: Check important data was saved
2. **Update documentation**: Note project completion
3. **Extract learnings**: Save useful patterns
4. **Free resources**: Verify memory/CPU freed

## Automation
```bash
# Schedule weekly cleanup of inactive projects
crontab -e
0 0 * * 0 tmux-orc cleanup --inactive 7d --auto-confirm

# Clean up after successful deployment
tmux-orc cleanup my-app --if-deployed
```

## Recovery
If you need to restore:
```bash
# List archives
ls .tmux_orchestrator/archive/

# Restore project
tmux-orc restore my-app-20240115

# Selective restore
tmux-orc restore my-app-20240115 --tasks-only
```
""",
    "enrich-tasks.md": """# Enrich Task Descriptions

Add technical details and implementation hints to task descriptions for better agent execution.

## Usage
```
/enrich-tasks [task-file]
```

## What it does
1. Analyzes existing task descriptions
2. Adds technical specifications
3. Includes implementation hints
4. Suggests design patterns
5. Links related documentation
6. Identifies potential pitfalls

## Example Enhancement

### Before:
```markdown
Task: Implement user login
```

### After:
```markdown
Task: Implement user login
- Technical: REST endpoint POST /api/auth/login
- Accept: JSON {email, password}
- Return: JWT token, user profile
- Security: Rate limit (5 attempts/min), bcrypt passwords
- Database: users table with email index
- Validation: Email format, password min 8 chars
- Error codes: 401 (invalid), 429 (rate limit)
- Tests: Unit (validation), Integration (DB), E2E (flow)
- References: RFC 7519 (JWT), OWASP Auth guidelines
```

## Enrichment Categories

### 🏗️ Architecture
- Design patterns to use
- Component structure
- Data flow diagrams
- Integration points

### 🔧 Implementation
- Code examples
- Library suggestions
- Performance considerations
- Edge cases

### 🧪 Testing
- Test scenarios
- Coverage requirements
- Mock data needs
- Verification steps

### 📚 Documentation
- API documentation format
- Code comments needed
- README updates
- User guides

## Customization
```bash
# Focus on specific aspects
/enrich-tasks tasks.md --focus security

# Add project-specific context
/enrich-tasks tasks.md --context "Using React, TypeScript, Node.js"

# Include code snippets
/enrich-tasks tasks.md --include-examples
```

## Best Practices
1. Run after `/generate-tasks`
2. Review enrichments before distribution
3. Keep enrichments relevant to tech stack
4. Update based on project evolution
5. Share enriched tasks with team

## Integration
Enriched tasks work seamlessly with:
- `tmux-orc tasks distribute` - Better agent understanding
- `tmux-orc execute` - Faster implementation
- `tmux-orc monitor` - Clearer progress tracking
""",
}
