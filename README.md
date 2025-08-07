![Orchestrator Hero](/Orchestrator.png)

**Run AI agents 24/7 while you sleep** - The Tmux Orchestrator enables Claude agents to work autonomously, schedule their own check-ins, and coordinate across multiple projects without human intervention.

## 🚀 NEW: Version 2.0 - Enhanced Agent Communication & VS Code Integration

✅ **VS Code Integration** - Open all agents with one command in separate terminals  
✅ **Agent Communication** - PM and Orchestrator can message all team members  
✅ **PM Check-ins** - Off-cycle status checks when agents appear idle  
✅ **Auto-Submit Messages** - No manual Enter required for agent communication  
✅ **Enhanced Stability** - Fixed window indexing and tmux server crashes  
✅ **18 VS Code Tasks** - Complete orchestrator control through Command Palette  

## 🤖 Key Capabilities & Autonomous Features

- **Self-trigger** - Agents schedule their own check-ins and continue work autonomously
- **Coordinate** - Project managers assign tasks to engineers across multiple codebases  
- **Persist** - Work continues even when you close your laptop
- **Scale** - Run multiple teams working on different projects simultaneously

## 🏗️ Architecture

The Tmux Orchestrator uses a three-tier hierarchy to overcome context window limitations:

```
┌─────────────┐
│ Orchestrator│ ← You interact here
└──────┬──────┘
       │ Monitors & coordinates
       ▼
┌─────────────┐     ┌─────────────┐
│  Project    │     │  Project    │
│  Manager 1  │     │  Manager 2  │ ← Assign tasks, enforce specs
└──────┬──────┘     └──────┬──────┘
       │                   │
       ▼                   ▼
┌─────────────┐     ┌─────────────┐
│ Engineer 1  │     │ Engineer 2  │ ← Write code, fix bugs
└─────────────┘     └─────────────┘
```

### Why Separate Agents?
- **Limited context windows** - Each agent stays focused on its role
- **Specialized expertise** - PMs manage, engineers code
- **Parallel work** - Multiple engineers can work simultaneously
- **Better memory** - Smaller contexts mean better recall

## 🐳 Quick Setup for Devcontainer Projects

### One-Command Integration
```bash
# Download and run the setup script
curl -O https://raw.githubusercontent.com/your-repo/tmux-orchestrator/main/setup-devcontainer.sh
chmod +x setup-devcontainer.sh
./setup-devcontainer.sh my-project-name
```

This automatically:
- Copies all orchestrator files
- Updates `devcontainer.json` 
- Creates project-specific scripts
- Sets up environment variables

### Manual Integration
```bash
# 1. Copy orchestrator to your project
cp -r Tmux-Orchestrator references/

# 2. Create installation script  
cp references/Tmux-Orchestrator/install-template.sh scripts/install-tmux-orchestrator.sh

# 3. Update devcontainer.json
{
  "postCreateCommand": "bash scripts/install-tmux-orchestrator.sh",
  "remoteEnv": {
    "TMUX_ORCHESTRATOR_HOME": "/workspaces/my-project/.tmux-orchestrator",
    "TMUX_ORCHESTRATOR_REGISTRY": "/workspaces/my-project/.tmux-orchestrator/registry"
  }
}

# 4. Rebuild devcontainer and deploy team
./scripts/deploy-my-project-team.sh tasks.md
```

## 🎯 VS Code Integration - New in v2.0!

### One-Click Agent Access
Open all your agents instantly through VS Code's Command Palette:

```
Ctrl+Shift+P → Tasks: Run Task → Select:

🎭 Open ALL Agent Terminals        ← Opens all 5 agents at once!
🎯 Open Orchestrator Agent         ← Main coordinator  
👔 Open Project Manager Agent      ← Planning & quality
🎨 Open Frontend Agent            ← UI/UX development
⚙️ Open Backend Agent             ← API & server logic
🧪 Open QA Agent                  ← Testing & verification
```

### PM Team Management
Perfect for when you notice agents are idle:

```
👔 PM Check-in with All Agents     ← Comprehensive status check
💬 PM Custom Check-in with All     ← Custom message for specific situations
```

### Agent Communication Commands
Agents now know how to message each other:

```bash
# PM can coordinate the team
tmux-message orchestrator:1 "Priority update: Focus on auth issues"
tmux-message corporate-coach-frontend:2 "UI fixes needed for login flow"

# Check team status  
.tmux-orchestrator/commands/agent-status.sh
.tmux-orchestrator/commands/list-agents.sh
```

## 📸 Examples in Action

### Project Manager Coordination
![Initiate Project Manager](Examples/Initiate%20Project%20Manager.png)
*The orchestrator creating and briefing a new project manager agent*

### Status Reports & Monitoring
![Status Reports](Examples/Status%20reports.png)
*Real-time status updates from multiple agents working in parallel*

### Tmux Communication
![Reading TMUX Windows and Sending Messages](Examples/Reading%20TMUX%20Windows%20and%20Sending%20Messages.png)
*How agents communicate across tmux windows and sessions*

### Project Completion
![Project Completed](Examples/Project%20Completed.png)
*Successful project completion with all tasks verified and committed*

## 🎯 Quick Start (Any Project Type)

### Option 1: Generic Team Deployment
```bash
# Auto-detects needed roles from task content
./bin/generic-team-deploy.sh tasks.md my-project /workspaces
```

### Option 2: Traditional Setup
```bash
# 1. Create a project spec
cat > project_spec.md << 'EOF'
PROJECT: My Web App
GOAL: Add user authentication system

CONSTRAINTS:
- Use existing database schema
- Follow current code patterns  
- Commit every 30 minutes
- Write tests for new features

DELIVERABLES:
1. Login/logout endpoints
2. User session management
3. Protected route middleware
EOF

# 2. Start orchestrator
tmux new-session -s orchestrator
claude

# 3. Deploy team
"You are the Orchestrator. Deploy a team for the authentication project using project_spec.md"
```

## ✨ Enhanced Features

### 🔄 Advanced PM Suite
- **Smart Scheduling** - PM agents schedule their own follow-ups
- **Idle Detection** - Automatically detects stuck agents
- **Team Coordination** - Cross-team communication patterns
- **Quality Gates** - Automated quality checks

```bash
# PM management commands
./pm-schedule-tracker.sh dashboard
./pm-auto-monitor.sh 
./pm-coordination-tools.sh
```

### 👥 Auto-Detecting Team Deployment
The orchestrator analyzes your task file and automatically deploys appropriate agents:

- **Frontend indicators**: react, vue, ui, component, html, css, javascript
- **Backend indicators**: api, service, endpoint, python, node, fastapi  
- **Database indicators**: database, sql, postgres, migration, schema
- **Always includes**: Orchestrator, PM, QA

### 💾 Enhanced Git Integration
- **Smart commits** every 30 minutes with meaningful messages
- **Feature branch** workflows
- **Quality gates** before merging
- **Automated tagging** of stable versions

### 📊 Real-Time Monitoring
```bash
# Multiple monitoring options
.tmux-orchestrator/commands/agent-status.sh
./monitor-project-team.sh  
./pm-schedule-tracker.sh dashboard
```

## 📚 Comprehensive Documentation

- **[SETUP.md](SETUP.md)** - Complete setup guide for any project
- **[RUNNING.md](RUNNING.md)** - Day-to-day operations and troubleshooting  
- **[CLAUDE.md](CLAUDE.md)** - Agent behavior instructions and best practices
- **[devcontainer-integration.md](devcontainer-integration.md)** - DevContainer integration guide
- **[INTEGRATION-COMPLETE.md](INTEGRATION-COMPLETE.md)** - Summary of all enhancements

## 🛠️ Project Templates

### Web Application Stack
- Orchestrator + PM + Frontend + Backend + QA
- Auto-detects React, Vue, Angular frontends
- Supports Node.js, Python, Java backends

### API-Only Project  
- Orchestrator + PM + Backend + Database + QA
- Focus on API development and testing
- Database migration support

### Data Pipeline
- Orchestrator + PM + Data Engineer + Backend + QA  
- ETL/ELT workflow support
- Data validation and quality checks

## 📋 Best Practices

### Writing Effective Task Files
```markdown
PROJECT: E-commerce Checkout
GOAL: Implement multi-step checkout process

CONSTRAINTS:
- Use existing cart state management
- Follow current design system
- Maximum 3 API endpoints
- Commit after each step completion

DELIVERABLES:
1. Shipping address form with validation
2. Payment method selection (Stripe integration)
3. Order review and confirmation page
4. Success/failure handling

SUCCESS CRITERIA:
- All forms validate properly
- Payment processes without errors  
- Order data persists to database
- Emails send on completion
```

### Git Safety Rules
1. **Feature branches** for all work
2. **Commits every 30 minutes** with descriptive messages  
3. **Quality gates** before merging
4. **Stable tags** for working versions

## 🚨 Common Pitfalls & Solutions

| Pitfall | Consequence | Solution |
|---------|-------------|----------|
| Vague task descriptions | Agent drift, wasted compute | Write clear, specific task files |
| No git commits | Lost work, frustrated devs | Enforce 30-minute commit rule |
| Too many agents | Context overload, confusion | Use auto-detection or templates |
| Missing specifications | Unpredictable results | Always start with written specs |
| No monitoring | Agents stop working | Use provided monitoring tools |

## 🔧 Advanced Usage

### Multi-Project Orchestration
```bash
# Deploy multiple project teams
./bin/generic-team-deploy.sh frontend-tasks.md frontend-app
./bin/generic-team-deploy.sh backend-tasks.md api-service  
./bin/generic-team-deploy.sh data-tasks.md analytics-pipeline
```

### Custom Agent Briefings
```bash
# Customize the deployment script briefings
# Edit bin/generic-team-deploy.sh to add project-specific instructions
```

### Integration Hooks
```bash
# Add custom quality gates
echo "npm run lint && npm run test" > .tmux-orchestrator/qa/quality-gates.sh

# Add Slack notifications
echo "curl -X POST $SLACK_WEBHOOK ..." > .tmux-orchestrator/integrations/slack.sh
```

## 📄 Core Files

- **`setup-devcontainer.sh`** - One-click devcontainer integration
- **`bin/generic-team-deploy.sh`** - Universal team deployment
- **`install-template.sh`** - Customizable installation template
- **`send-claude-message.sh`** - Simplified agent communication
- **`schedule_with_note.sh`** - Self-scheduling functionality
- **PM Suite** - Advanced project management tools
- **Monitoring Tools** - Real-time team monitoring

## 🤝 Contributing & Evolution

The orchestrator evolves through community use and feedback:

1. **Test in your projects** and report what works
2. **Submit improvements** for team deployment patterns  
3. **Share novel use cases** and coordination strategies
4. **Contribute project templates** for common stacks
5. **Enhance monitoring** and quality gate systems

## 📄 License

MIT License - Use freely across all your projects.

---

*"The future of development is autonomous teams working while you sleep"*