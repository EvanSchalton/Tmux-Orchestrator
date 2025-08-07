#!/bin/bash
# Restart the Project Manager agent without affecting other running agents

echo "🔄 RESTARTING PROJECT MANAGER"
echo "=============================="
echo "Time: $(date)"
echo ""

# Check if tmux server is running
if ! tmux list-sessions >/dev/null 2>&1; then
    echo "❌ No tmux server running - no agents to check"
    exit 1
fi

# Get project name
PROJECT_NAME=$(basename "$(pwd)")

echo "🔍 Checking current agent status..."

# Find existing PM session
PM_SESSION=$(tmux list-sessions -F "#{session_name}" 2>/dev/null | grep -E "$PROJECT_NAME-$PROJECT_NAME" || true)

if [ -n "$PM_SESSION" ]; then
    echo "⚠️  Found existing PM session: $PM_SESSION"
    echo "🛑 Killing existing PM session..."
    tmux kill-session -t "$PM_SESSION" 2>/dev/null || true
    sleep 2
fi

# Check if orchestrator is running
ORCHESTRATOR_RUNNING=$(tmux list-sessions -F "#{session_name}" 2>/dev/null | grep -E "orchestrator" || true)

if [ -z "$ORCHESTRATOR_RUNNING" ]; then
    echo "⚠️  Warning: Orchestrator is not running"
fi

# Check other running agents
echo ""
echo "📊 Currently running agents:"
tmux list-sessions -F "#{session_name}" 2>/dev/null | while read session; do
    echo "   ✓ $session"
done

echo ""
echo "🚀 Starting new PM agent..."

# Deploy PM using the existing deploy-agent script
DEPLOY_SCRIPT="$(dirname "$0")/deploy-agent.sh"

if [ ! -f "$DEPLOY_SCRIPT" ]; then
    echo "❌ Could not find deploy-agent.sh script"
    exit 1
fi

# Deploy PM agent
bash "$DEPLOY_SCRIPT" "$PROJECT_NAME" "pm"

echo ""
echo "⏳ Waiting for PM to initialize..."
sleep 10

# Get task file location from environment or default
TASK_FILE="${TMUX_ORCHESTRATOR_TASK_FILE:-tasks.md}"
TASK_FILE_ABS=$(realpath "$TASK_FILE" 2>/dev/null || echo "$TASK_FILE")

# Send comprehensive briefing to new PM
echo "📋 Briefing the new PM on current situation..."

PM_BRIEFING="You are the Project Manager for $PROJECT_NAME.

⚠️ IMPORTANT: You were just restarted. Other agents are still running.

Task file: $TASK_FILE_ABS

Your responsibilities:
1. Break down tasks into manageable work items
2. Create test plans BEFORE implementation
3. Ensure TDD principles are followed
4. Track progress and update documentation
5. Coordinate between all team members
6. Maintain EXCEPTIONAL quality standards

🔄 RESTART CONTEXT:
- You were restarted while other agents continue working
- Check current agent status using: .tmux-orchestrator/commands/agent-status.sh
- Review what other agents are working on
- Catch up on recent progress and coordinate accordingly

🤖 AGENT COMMUNICATION COMMANDS:
- Send message to any agent: tmux-message <session:window> 'your message'
- Available agents:
  • Orchestrator: tmux-message orchestrator:1 'message'
  • Frontend: tmux-message $PROJECT_NAME-frontend:2 'message'  
  • Backend: tmux-message $PROJECT_NAME-backend:2 'message'
  • QA: tmux-message $PROJECT_NAME-testing:2 'message'
- Check agent status: .tmux-orchestrator/commands/agent-status.sh
- List all agents: .tmux-orchestrator/commands/list-agents.sh

FIRST ACTIONS:
1. Run agent-status.sh to see what everyone is working on
2. Ask each agent for their current status
3. Review the task file to understand priorities
4. Resume coordination based on current progress

Critical: No shortcuts allowed. Quality over speed."

# Send briefing
tmux-message "$PROJECT_NAME-$PROJECT_NAME:2" "$PM_BRIEFING"

echo ""
echo "✅ PM successfully restarted!"
echo ""
echo "📊 Current agent sessions:"
tmux list-sessions -F "#{session_name}" 2>/dev/null | while read session; do
    echo "   ✓ $session"
done

echo ""
echo "💡 Next steps:"
echo "   1. Open PM terminal: tmux attach -t $PROJECT_NAME-$PROJECT_NAME"
echo "   2. Monitor PM catching up: .tmux-orchestrator/commands/agent-status.sh"
echo "   3. PM will check in with other agents automatically"
echo ""
echo "🎯 Quick PM access:"
echo "   VS Code: Ctrl+Shift+P → Tasks: Run Task → '👔 Open Project Manager Agent'"