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

# Start Claude
echo "🤖 Starting Claude..."
tmux send-keys -t "$SESSION_NAME:1" "claude --dangerously-skip-permissions" Enter
sleep 5

# Send briefing
echo "📋 Sending orchestrator briefing..."
/usr/local/bin/tmux-message "$SESSION_NAME:1" "You are the Tmux Orchestrator for the Corporate Coach project. Your responsibilities include:
1. Managing multiple Claude agents across different components
2. Coordinating work between frontend, backend, and database teams
3. Monitoring progress and resolving blockers
4. Ensuring code quality and git discipline

Reference: /workspaces/corporate-coach/references/Tmux-Orchestrator/CLAUDE.md

First, rename all tmux windows with descriptive names for better organization."

echo "✅ Orchestrator started! Access with: tmux attach -t $SESSION_NAME"
