#!/bin/bash
SESSION_NAME=${1:-orchestrator}

# Check if session already exists
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
  echo "❌ Session '$SESSION_NAME' already exists!"
  echo "Attach with: tmux attach -t $SESSION_NAME"
  exit 1
fi

# Create orchestrator session
echo "🚀 Creating orchestrator session..."
tmux new-session -d -s "$SESSION_NAME" -c /workspaces/corporate-coach
tmux rename-window -t "$SESSION_NAME:1" "Orchestrator"

# Start Claude with proper environment
echo "🤖 Starting Claude..."
tmux send-keys -t "$SESSION_NAME:1" 'export TERM=xterm-256color' Enter
tmux send-keys -t "$SESSION_NAME:1" 'source /workspaces/corporate-coach/.venv/bin/activate' Enter
sleep 2
tmux send-keys -t "$SESSION_NAME:1" 'FORCE_COLOR=1 NODE_NO_WARNINGS=1 claude --dangerously-skip-permissions' Enter
sleep 10

# Send briefing
echo "📋 Sending orchestrator briefing..."
/usr/local/bin/tmux-message "$SESSION_NAME:1" "You are the Tmux Orchestrator for Corporate Coach.

Your responsibilities:
1. Coordinate work between all agents
2. Monitor progress and resolve blockers
3. Ensure code quality and git discipline
4. Manage team communication and priorities

🤖 AGENT COMMUNICATION COMMANDS:
- Send message to any agent: tmux-message <session:window> 'your message'
- Available agents:
  • PM: tmux-message corporate-coach-corporate-coach:2 'message'
  • Frontend: tmux-message corporate-coach-frontend:2 'message'
  • Backend: tmux-message corporate-coach-backend:2 'message'
  • QA: tmux-message corporate-coach-testing:2 'message'
- Check agent status: .tmux-orchestrator/commands/agent-status.sh
- List all agents: .tmux-orchestrator/commands/list-agents.sh

Please respond with 'Orchestrator ready!' and begin coordinating the team."

echo "✅ Orchestrator started! Access with: tmux attach -t $SESSION_NAME"
