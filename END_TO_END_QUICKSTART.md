# End-to-End Quickstart Guide

This guide walks through the complete workflow from initial setup to PRD execution with AI agent teams.

## Prerequisites

- Docker dev container or local development environment
- Tmux installed and working
- Claude Code installed (optional but recommended)
- VS Code (optional)

## Step 1: Install Tmux Orchestrator

```bash
# Clone and install from GitHub
git clone https://github.com/your-org/tmux-orchestrator.git
cd tmux-orchestrator
pip install -e .
```

## Step 2: Setup Claude Code Integration

```bash
# Install slash commands and MCP server
tmux-orc setup-claude-code

# This will:
# - Install slash commands for PRD creation
# - Configure MCP server for agent control
# - Create CLAUDE.md in your workspace
```

**Important**: Restart Claude Code after setup to load slash commands.

## Step 3: Setup VS Code Integration (Optional)

```bash
# Add VS Code tasks for monitoring
tmux-orc setup-vscode

# This creates tasks for:
# - Opening agent windows
# - Viewing daemon logs
# - Quick team deployment
```

## Step 4: Create Your Feature Description

Create a file describing what you want to build:

```bash
cat > project_description.md << 'EOF'
# User Authentication System

I need a complete user authentication system with:
- Email/password registration and login
- Secure session management
- Password reset functionality
- User profile management
- Role-based access control

The system should use modern security practices and be production-ready.
EOF
```

## Step 5: Generate PRD Using Claude

In Claude Code, run:
```
/create-prd project_description.md
```

Claude will:
1. Create a PRD survey with clarifying questions
2. Wait for you to complete the survey
3. Generate a comprehensive PRD

Save the PRD as `prd-user-auth.md` (or similar).

## Step 6: Execute the PRD

You have three options:

### Option A: Ask Claude (MCP)
In Claude Code:
```
Execute the PRD at ./prd-user-auth.md
```

### Option B: Use CLI
```bash
tmux-orc execute ./prd-user-auth.md --project-name user-auth
```

### Option C: Manual Orchestration
```bash
# Create project
tmux-orc tasks create user-auth --prd ./prd-user-auth.md

# Deploy team
tmux-orc team deploy fullstack 5 --project-name user-auth

# Brief PM (in tmux)
tmux attach -t user-auth
# Send PRD location and instructions to PM
```

## Step 7: Monitor Progress

### View All Agents
```bash
# List active agents
tmux-orc list

# Check team status
tmux-orc team status user-auth

# View task progress
tmux-orc tasks status user-auth
```

### Watch Specific Agents
```bash
# Read PM output
tmux-orc read --session user-auth:0 --tail 50

# Search for errors
tmux-orc search "error" --all-sessions
```

### VS Code Monitoring
If you set up VS Code:
1. Open Command Palette (Ctrl+Shift+P)
2. Run "Tasks: Run Task"
3. Select "Open All Agents"

This opens tmux windows and shows daemon logs.

## Step 8: Interact with the Team

### Send Messages to PM
```bash
# Via CLI
tmux-orc publish --session user-auth:0 "How is progress on authentication?"

# Via Claude (MCP)
"Ask the PM about authentication progress"
```

### Check Task Completion
```bash
# View task status
tmux-orc tasks status user-auth --tree

# Export progress report
tmux-orc tasks export user-auth --format html --output progress.html
```

## Complete Workflow Example

Here's a full example from start to finish:

```bash
# 1. Setup (one time only)
tmux-orc setup-all

# 2. Create feature description
echo "Build a real-time chat application with rooms" > chat-app.md

# 3. In Claude Code: Generate PRD
# /create-prd chat-app.md
# Complete survey and save as prd-chat.md

# 4. Execute PRD
tmux-orc execute ./prd-chat.md --project-name chat-app --team-size 6

# 5. Monitor progress
watch -n 30 'tmux-orc tasks status chat-app'

# 6. Check in with PM
tmux-orc publish --session chat-app:0 "Any blockers I can help with?"

# 7. View team activity
tmux attach -t chat-app
```

## Tips and Best Practices

### PRD Quality
- Be specific about technical requirements
- Include acceptance criteria
- Specify quality standards
- Define success metrics

### Team Management
- Start with 5-agent teams (PM + 2 devs + QA + Test)
- Let PM coordinate task distribution
- Monitor but don't micromanage
- Trust the quality gates

### Monitoring
- Check status every 15-30 minutes
- Look for idle agents
- Watch for test failures
- Ensure regular commits

### Communication
- Use structured messages
- Be clear and concise
- Provide context
- Respond to blockers quickly

## Troubleshooting

### Agents Not Responding
```bash
# Check agent health
tmux-orc recovery check

# Restart specific agent
tmux-orc agent restart chat-app:2
```

### Task Distribution Issues
```bash
# Manually distribute
tmux-orc tasks distribute chat-app --frontend 3 --backend 3
```

### MCP Server Issues
```bash
# Check MCP status
tmux-orc setup-check

# Restart MCP server
tmux-orc mcp-server --restart
```

## Next Steps

- Read [TASK_MANAGEMENT.md](./TASK_MANAGEMENT.md) for detailed task workflow
- Review [PM-QUICKSTART.md](./PM-QUICKSTART.md) for PM-specific guidance
- Check [examples/](./examples/) for more complex scenarios

## Support

- GitHub Issues: Report bugs and feature requests
- Documentation: See [docs/](./docs/) for detailed guides
- Examples: Check [examples/](./examples/) for common patterns