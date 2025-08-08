#!/bin/bash
# Example: Deploy a PRD-driven development team
# This script shows how to set up a complete team for the PRD workflow

PROJECT_NAME="my-feature"
PROJECT_DIR="/path/to/project"

echo "🚀 Deploying PRD-driven development team for: $PROJECT_NAME"

# 1. Create the tmux session
tmux new-session -d -s "$PROJECT_NAME" -c "$PROJECT_DIR"

# 2. Create Project Manager window
tmux rename-window -t "$PROJECT_NAME:0" "PM"
tmux send-keys -t "$PROJECT_NAME:0" "claude --dangerously-skip-permissions" Enter
sleep 5

# Brief the PM with PRD workflow
tmux send-keys -t "$PROJECT_NAME:0" "You are the Project Manager. You will follow our PRD-driven development workflow:

1. Use /workspaces/Tmux-Orchestrator/.claude/commands/create-prd.md for PRDs
2. Use /workspaces/Tmux-Orchestrator/.claude/commands/generate-tasks.md for task lists
3. Distribute tasks to dev teams and enforce quality gates
4. Coordinate QA testing and bug fixes
5. Request test automation

Read /workspaces/Tmux-Orchestrator/orchestration-workflow.md for complete details.
Read /workspaces/Tmux-Orchestrator/PM-QUICKSTART.md for quick reference.

Quality gates are mandatory - no task proceeds with failing tests/linting." Enter

# 3. Create Frontend Developer window
tmux new-window -t "$PROJECT_NAME" -n "Frontend-Dev" -c "$PROJECT_DIR/frontend"
tmux send-keys -t "$PROJECT_NAME:1" "claude --dangerously-skip-permissions" Enter
sleep 5
tmux send-keys -t "$PROJECT_NAME:1" "You are the Frontend Developer. You will receive task lists from the PM and execute them using /workspaces/Tmux-Orchestrator/.claude/commands/process-task-list.md

Requirements:
- All tests must pass (npm test)
- No linting errors (npm run lint)
- Commit every 30 minutes
- Report status after each task completion" Enter

# 4. Create Backend Developer window
tmux new-window -t "$PROJECT_NAME" -n "Backend-Dev" -c "$PROJECT_DIR/backend"
tmux send-keys -t "$PROJECT_NAME:2" "claude --dangerously-skip-permissions" Enter
sleep 5
tmux send-keys -t "$PROJECT_NAME:2" "You are the Backend Developer. You will receive task lists from the PM and execute them using /workspaces/Tmux-Orchestrator/.claude/commands/process-task-list.md

Requirements:
- All tests must pass (pytest)
- No linting errors (ruff check)
- Type checking must pass (mypy)
- Commit every 30 minutes
- Report status after each task completion" Enter

# 5. Create QA Engineer window
tmux new-window -t "$PROJECT_NAME" -n "QA-Engineer" -c "$PROJECT_DIR"
tmux send-keys -t "$PROJECT_NAME:3" "claude --dangerously-skip-permissions" Enter
sleep 5
tmux send-keys -t "$PROJECT_NAME:3" "You are the QA Engineer. You will receive test plans from the PM after developers complete features.

Your responsibilities:
- Manual testing of all user flows
- Report bugs in batches with reproduction steps
- Include screenshots/logs for issues
- Suggest test scenarios for automation
- Use Playwright MCP if needed for browser automation" Enter

# 6. Create Test Engineer window
tmux new-window -t "$PROJECT_NAME" -n "Test-Engineer" -c "$PROJECT_DIR/tests"
tmux send-keys -t "$PROJECT_NAME:4" "claude --dangerously-skip-permissions" Enter
sleep 5
tmux send-keys -t "$PROJECT_NAME:4" "You are the Test Engineer. You will receive QA workflows from the PM to automate.

Your responsibilities:
- Create Playwright tests for UI flows
- Create pytest tests for APIs
- Ensure tests are maintainable
- No flaky tests allowed
- Document all test scenarios" Enter

# 7. Create a monitoring dashboard window
tmux new-window -t "$PROJECT_NAME" -n "Dashboard" -c "$PROJECT_DIR"
tmux send-keys -t "$PROJECT_NAME:5" "watch -n 5 'tmux list-windows -t $PROJECT_NAME'" Enter

echo "✅ Team deployed successfully!"
echo ""
echo "Windows created:"
echo "  0: PM (Project Manager)"
echo "  1: Frontend-Dev"
echo "  2: Backend-Dev" 
echo "  3: QA-Engineer"
echo "  4: Test-Engineer"
echo "  5: Dashboard (monitoring)"
echo ""
echo "To attach: tmux attach -t $PROJECT_NAME"
echo "To send initial feature request to PM:"
echo "  /workspaces/Tmux-Orchestrator/send-claude-message.sh \"$PROJECT_NAME:0\" \"Feature request: [your 1-2 paragraph description]\""