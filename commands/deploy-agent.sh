#!/bin/bash
COMPONENT=$1
ROLE=${2:-developer}

if [ -z "$COMPONENT" ]; then
  echo "Usage: $0 <component> [role]"
  echo "Components: frontend, backend, database, docs"
  echo "Roles: developer (default), pm, qa, reviewer"
  exit 1
fi

SESSION_NAME="corporate-coach-$COMPONENT"
WINDOW_NAME="Claude-$ROLE"

# Create session if doesn't exist
if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
  echo "📦 Creating session for $COMPONENT..."
  tmux new-session -d -s "$SESSION_NAME" -c /workspaces/corporate-coach
fi

# Create window for agent
echo "🪟 Creating window for $ROLE..."
tmux new-window -t "$SESSION_NAME" -n "$WINDOW_NAME" -c /workspaces/corporate-coach

# Start Claude with proper environment
echo "🤖 Starting Claude agent..."
tmux send-keys -t "$SESSION_NAME:$WINDOW_NAME" 'export TERM=xterm-256color' Enter
tmux send-keys -t "$SESSION_NAME:$WINDOW_NAME" 'source /workspaces/corporate-coach/.venv/bin/activate' Enter
sleep 2
tmux send-keys -t "$SESSION_NAME:$WINDOW_NAME" 'FORCE_COLOR=1 NODE_NO_WARNINGS=1 claude --dangerously-skip-permissions' Enter
sleep 10

# Send role-specific briefing
echo "📋 Briefing $ROLE agent..."
case "$ROLE" in
  "developer")
    /usr/local/bin/tmux-message "$SESSION_NAME:$WINDOW_NAME" "You are the $COMPONENT developer for Corporate Coach. Focus on implementing features according to the PRD and maintaining code quality. Commit every 30 minutes with meaningful messages."
    ;;
  "pm")
    /usr/local/bin/tmux-message "$SESSION_NAME:$WINDOW_NAME" "You are the Project Manager for $COMPONENT. Maintain high quality standards, coordinate work, and ensure proper testing. No shortcuts!"
    ;;
  "qa")
    /usr/local/bin/tmux-message "$SESSION_NAME:$WINDOW_NAME" "You are the QA engineer for $COMPONENT. Test thoroughly, create test plans, and verify all functionality meets requirements."
    ;;
  "reviewer")
    /usr/local/bin/tmux-message "$SESSION_NAME:$WINDOW_NAME" "You are the code reviewer for $COMPONENT. Review for security, performance, and best practices. Ensure code follows project standards."
    ;;
esac

echo "✅ $ROLE agent deployed for $COMPONENT!"
echo "Access with: tmux attach -t $SESSION_NAME"
