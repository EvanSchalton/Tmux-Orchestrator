#!/bin/bash
# List all active TMUX Orchestrator agents

echo "🤖 ACTIVE AGENT SESSIONS"
echo "======================="
echo "Time: $(date)"
echo ""

# Get project name from current directory or use generic pattern
PROJECT_NAME=$(basename "$(pwd)")
if [ "$PROJECT_NAME" = "." ] || [ -z "$PROJECT_NAME" ]; then
    PROJECT_NAME="*"
fi

# Function to get session status
get_session_status() {
    local session=$1
    local last_activity
    last_activity=$(tmux display-message -t "$session" -p "#{client_activity}" 2>/dev/null || echo "0")
    
    if [ "$last_activity" = "0" ]; then
        echo "❓ Unknown"
    else
        local current_time=$(date +%s)
        local diff=$((current_time - last_activity))
        
        if [ $diff -lt 300 ]; then  # 5 minutes
            echo "🟢 Active"
        elif [ $diff -lt 1800 ]; then  # 30 minutes
            echo "🟡 Idle"
        else
            echo "🔴 Inactive"
        fi
    fi
}

# Function to get last message/activity
get_last_activity() {
    local session=$1
    local window=${2:-1}
    
    # Try to capture last few lines and find the most recent Claude output
    local recent_output
    recent_output=$(tmux capture-pane -t "$session:$window" -p 2>/dev/null | tail -3 | head -1 | cut -c1-50)
    
    if [ -n "$recent_output" ] && [ "$recent_output" != "" ]; then
        echo "$recent_output..."
    else
        echo "No recent activity"
    fi
}

# Check if tmux server is running first
if ! tmux list-sessions >/dev/null 2>&1; then
    echo "❌ No tmux server running"
    echo ""
    echo "💡 Try deploying a team first:"
    echo "   ./scripts/deploy.sh tasks.md"
    echo ""
    exit 0
fi

# Find and list orchestrator sessions
echo "🎯 ORCHESTRATOR SESSIONS:"
orchestrator_sessions=$(tmux list-sessions -F "#{session_name}" 2>/dev/null | grep -E "orchestrator" || true)
if [ -n "$orchestrator_sessions" ]; then
    for session in $orchestrator_sessions; do
        status=$(get_session_status "$session")
        activity=$(get_last_activity "$session" "1")
        # Skip window count to avoid tmux server crashes
        windows="?"
        
        echo "  📡 $session"
        echo "     Status: $status"
        echo "     Windows: $windows"
        echo "     Last: $activity"
        echo ""
    done
else
    echo "  ❌ No orchestrator sessions found"
    echo ""
fi

# Find and list project agent sessions
echo "🏢 PROJECT AGENT SESSIONS:"
agent_sessions=$(tmux list-sessions -F "#{session_name}" 2>/dev/null | grep -E "$PROJECT_NAME" | grep -v orchestrator || true)
if [ -n "$agent_sessions" ]; then
    for session in $agent_sessions; do
        status=$(get_session_status "$session")
        # Skip window details to avoid tmux server crashes
        echo "  🤖 $session"
        echo "     Status: $status"
        echo "     Windows: ? (details disabled to prevent crashes)"
        echo ""
    done
else
    echo "  ❌ No project agent sessions found for pattern: $PROJECT_NAME"
    echo ""
fi

# Summary statistics
total_sessions=$(tmux list-sessions 2>/dev/null | wc -l)
orchestrator_count=$(echo "$orchestrator_sessions" | grep -c . 2>/dev/null || echo "0")
agent_count=$(echo "$agent_sessions" | grep -c . 2>/dev/null || echo "0")

echo "📊 SUMMARY:"
echo "  Total tmux sessions: $total_sessions"
echo "  Orchestrator sessions: $orchestrator_count"
echo "  Agent sessions: $agent_count"

# Quick actions
echo ""
echo "💡 QUICK ACTIONS:"
echo "  Attach to orchestrator: tmux attach -t orchestrator"
echo "  Agent status dashboard: .tmux-orchestrator/commands/agent-status.sh"
echo "  Force PM check-in: .tmux-orchestrator/commands/force-pm-checkin.sh"
echo "  Send message: tmux-message <session:window> \"message\""