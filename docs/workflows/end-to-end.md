# End-to-End Workflow

## Setup Phase

1. **User clones a repo into a docker dev container**
   - Or works in local development environment
   - Ensures tmux is installed and working

2. **User installs CLI from GitHub**
   ```bash
   git clone https://github.com/org/tmux-orchestrator.git
   cd tmux-orchestrator
   pip install -e .
   ```

3. **User runs `tmux-orc setup claude-code`**
   - Installs slash commands to `~/.continue/commands/`
   - Configures MCP server in `~/.continue/config/mcp.json`
   - Creates `CLAUDE.md` in workspace with instructions
   - User must restart Claude Code to load slash commands

3.b **User optionally runs `tmux-orc setup vscode`**
   - Creates `.vscode/tasks.json` with orchestrator commands
   - Adds "Open All Agents" task
   - Adds "Show Daemon Logs" task
   - Configures debugging settings

## PRD Creation Phase

4. **User creates a project_description.md**
   - Brief description of desired features
   - High-level requirements
   - Any specific constraints

5. **User invokes `/create-prd project_description.md`**
   - Claude generates a PRD survey with clarifying questions
   - Survey covers technical details, quality standards, etc.

6. **User completes the PRD survey**
   - Answers all questions thoroughly
   - Claude generates comprehensive PRD
   - User saves as `prd-{feature}.md`

## Execution Phase

7. **User executes the PRD**

   **Option A: Via Claude (MCP)**
   ```
   "Execute the PRD at ./prd-user-auth.md"
   ```

   **Option B: Via CLI (Recommended)**
   ```bash
   tmux-orc execute ./prd-user-auth.md
   ```
   This will:
   - Create project structure
   - Plan custom team composition based on PRD
   - Deploy the optimized team
   - Brief PM with workflow

   **Option C: Manual orchestration**
   ```bash
   # Create project structure
   tmux-orc tasks create project-name --prd ./prd.md

   # Plan team composition
   tmux-orc team compose project-name --prd ./prd.md

   # Deploy custom team
   tmux-orc team deploy project-name --custom

   # Brief PM manually
   ```

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
