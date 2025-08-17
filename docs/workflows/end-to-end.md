# Complete End-to-End Workflow Guide

This guide walks you through a complete project lifecycle using the TMUX Orchestrator, from initial setup to project completion.

## Phase 1: Environment Setup

### 1. Install TMUX Orchestrator

Choose your installation method:

**Option A: Quick Install (Recommended)**
```bash
pip install tmux-orchestrator
```

**Option B: Development Install**
```bash
git clone https://github.com/EvanSchalton/Tmux-Orchestrator.git
cd tmux-orchestrator
pip install -e .
```

### 2. Initialize Your Environment

```bash
# Set up the orchestrator
tmux-orc setup

# Configure Claude Code integration (recommended)
tmux-orc setup claude-code

# Optional: Set up VSCode integration
tmux-orc setup vscode
```

**What this does:**
- Installs slash commands to `~/.continue/commands/`
- Configures MCP server in `~/.continue/config/mcp.json`
- Creates `CLAUDE.md` with project instructions
- Sets up VSCode tasks for agent management

**Important:** Restart Claude Code after setup to load slash commands.

### 3. Verify Installation

```bash
# Check CLI is working
tmux-orc --help

# Test basic functionality
tmux-orc reflect

# Verify tmux integration
tmux list-sessions || echo "No active sessions (this is normal)"
```

## Phase 2: Project Planning

### 4. Create Your Project Description

Start by describing your project requirements:

```bash
# Create a simple project description
cat > project_description.md << EOF
# My Todo Application

## Overview
Build a modern todo application with user authentication and real-time updates.

## Key Features
- User registration and authentication
- Create, read, update, delete tasks
- Real-time synchronization across devices
- Responsive web interface
- REST API backend

## Technical Requirements
- Frontend: React with TypeScript
- Backend: Node.js with Express
- Database: PostgreSQL
- Testing: Jest for unit tests, Cypress for E2E
- Deployment: Docker containers

## Quality Standards
- 90%+ test coverage
- Accessibility compliance (WCAG 2.1)
- Performance: <2s page load times
- Security: JWT authentication, input validation
EOF
```

### 5. Generate Comprehensive PRD

Use Claude to expand your description into a detailed PRD:

**Via Claude Code (recommended):**
```
/create-prd project_description.md
```

**Via CLI:**
```bash
tmux-orc prd create project_description.md
```

**What happens:**
- Claude analyzes your requirements
- Generates clarifying questions about technical details
- Creates a comprehensive Product Requirements Document
- Saves as `prd-{project-name}.md`

### 6. Review and Refine PRD

- Answer all clarifying questions thoroughly
- Review the generated PRD for completeness
- Make any necessary adjustments
- Ensure all requirements are clear and testable

## Phase 3: Team Deployment and Execution

### 7. Execute Your PRD

Deploy an AI team to implement your project:

**Option A: Automated Execution (Recommended)**
```bash
tmux-orc execute ./prd-todo-app.md
```

**Option B: Via Claude Code**
```
"Execute the PRD at ./prd-todo-app.md"
```

**Option C: Step-by-Step Manual Control**
```bash
# 1. Create project structure
tmux-orc tasks create todo-app --prd ./prd-todo-app.md

# 2. Plan optimal team composition
tmux-orc team compose todo-app --prd ./prd-todo-app.md

# 3. Deploy the team
tmux-orc team deploy todo-app --custom

# 4. Brief PM with project details
tmux-orc pm brief todo-app --prd ./prd-todo-app.md
```

**What the automated execution does:**
- Analyzes PRD requirements
- Determines optimal team composition (PM + Frontend + Backend + QA + etc.)
- Creates project structure in `.tmux_orchestrator/projects/todo-app/`
- Deploys agents to appropriate tmux sessions
- Briefs PM with complete project context

## Team Planning Phase (NEW)

7.5 **Team composition is planned**
   - System analyzes PRD requirements
   - Suggests optimal team composition
   - Creates `team-composition.md` with:
     - Agent roles and specializations
     - Interaction diagrams
     - Recovery information
   - Example compositions:
     - API project: PM + API Designer + 2 Backend + Test Automation
     - CLI project: PM + 2 CLI Developers + Tech Writer + QA
     - Fullstack: PM + Frontend + Backend + QA + Test Engineer

## Task Management Phase

8. **PM generates task list from PRD**
   - Uses `/generate-tasks` slash command
   - Saves to `.tmux_orchestrator/projects/{name}/tasks.md`

9. **Tasks are distributed to agents**
   ```bash
   tmux-orc tasks distribute project-name
   ```
   - Each agent gets their task file
   - Located in `.tmux_orchestrator/projects/{name}/agents/`

10. **Development begins**
    - Agents work through their task lists
    - Update task files with progress
    - Commit code every 30 minutes
    - Report status after each task

## Monitoring Phase

11. **User monitors progress**
    - `tmux-orc tasks status project-name`
    - `tmux-orc team status project-name`
    - `tmux-orc read --session project:window`

12. **User interacts with team**
    - Send messages: `tmux-orc publish --session pm:0 "message"`
    - Check specific agents: `tmux-orc agent status`
    - Handle blockers and questions

## Completion Phase

13. **Tasks are completed**
    - All tests passing
    - Code reviewed and committed
    - Documentation updated

14. **Project is archived**
    ```bash
    tmux-orc tasks archive project-name
    ```


------


The user should be able to ask claude (MCP), use the CLI, or if they installed the vscode integration to "Open All Agents" which should open the tmux window(s) for the user to monitor behavior - it should also open a terminal that shows the daemon's logs.

The user should be able to ask claude, use the CLI, or the VS code terminal to send commands to the PM as needed.
