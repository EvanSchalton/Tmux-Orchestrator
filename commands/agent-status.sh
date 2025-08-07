#!/bin/bash
echo "🤖 AGENT STATUS REPORT"
echo "====================="
echo "Time: $(date)"
echo ""

# List all sessions
for session in $(tmux list-sessions -F "#{session_name}" 2>/dev/null); do
  # Skip non-project sessions
  if [[ ! "$session" =~ (orchestrator|corporate-coach) ]]; then
    continue
  fi
  
  echo "📦 Session: $session"
  
  # List windows in session
  for window in $(tmux list-windows -t "$session" -F "#{window_index}:#{window_name}" 2>/dev/null); do
    window_index=$(echo "$window" | cut -d: -f1)
    window_name=$(echo "$window" | cut -d: -f2-)
    
    echo "  🪟 Window $window_index: $window_name"
    
    # Capture recent activity
    recent=$(tmux capture-pane -t "$session:$window_index" -p 2>/dev/null | tail -5 | head -3)
    if [ -n "$recent" ]; then
      echo "     Recent activity:"
      echo "$recent" | sed 's/^/       /'
    fi
    echo ""
  done
  echo ""
done
