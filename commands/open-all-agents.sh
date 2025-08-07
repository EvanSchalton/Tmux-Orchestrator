#!/bin/bash
# Dynamic script to open all running agents in separate terminals
# This replaces hardcoded dependsOn with dynamic agent detection

echo "🎭 OPENING ALL ACTIVE AGENTS"
echo "==========================="
echo "Time: $(date)"
echo ""

# Get project name
PROJECT_NAME=$(basename "$(pwd)")
if [ "$PROJECT_NAME" = "." ] || [ -z "$PROJECT_NAME" ]; then
    echo "❌ Error: Cannot determine project name"
    exit 1
fi

# Function to open agent in VS Code terminal
open_agent_terminal() {
    local session=$1
    local window=${2:-0}
    local agent_name=$3
    
    echo "🔗 Opening $agent_name: $session:$window"
    
    # Use VS Code's terminal API if available, otherwise fall back to tmux
    if command -v code >/dev/null 2>&1; then
        # Create new terminal in VS Code and attach to tmux session
        code --command "workbench.action.terminal.new" \
             --command "workbench.action.terminal.sendSequence" \
             --args "tmux attach -t '$session:$window'"
    else
        # Fall back to direct tmux attach (will open in current terminal)
        tmux attach -t "$session:$window" &
    fi
    
    sleep 1  # Prevent overwhelming the system
}

# Find and categorize active sessions
echo "🔍 Detecting active agent sessions..."

# Find orchestrator sessions
ORCHESTRATOR_SESSIONS=$(tmux list-sessions -F "#{session_name}" 2>/dev/null | grep -E "orchestrator" || true)

# Find project agent sessions
AGENT_SESSIONS=$(tmux list-sessions -F "#{session_name}" 2>/dev/null | grep -E "$PROJECT_NAME" | grep -v orchestrator || true)

# Count sessions
TOTAL_COUNT=0
ORCHESTRATOR_COUNT=0
AGENT_COUNT=0

if [ -n "$ORCHESTRATOR_SESSIONS" ]; then
    ORCHESTRATOR_COUNT=$(echo "$ORCHESTRATOR_SESSIONS" | wc -l)
    TOTAL_COUNT=$((TOTAL_COUNT + ORCHESTRATOR_COUNT))
fi

if [ -n "$AGENT_SESSIONS" ]; then
    AGENT_COUNT=$(echo "$AGENT_SESSIONS" | wc -l)  
    TOTAL_COUNT=$((TOTAL_COUNT + AGENT_COUNT))
fi

echo "   Found $TOTAL_COUNT active sessions:"
echo "   - $ORCHESTRATOR_COUNT orchestrator(s)"
echo "   - $AGENT_COUNT project agent(s)"
echo ""

if [ $TOTAL_COUNT -eq 0 ]; then
    echo "❌ No active agent sessions found!"
    echo ""
    echo "💡 Try deploying a team first:"
    echo "   ./scripts/deploy-$PROJECT_NAME-team.sh tasks.md"
    exit 1
fi

echo "🚀 Opening sessions..."

# Open orchestrator sessions
if [ -n "$ORCHESTRATOR_SESSIONS" ]; then
    while IFS= read -r session; do
        if [ -n "$session" ]; then
            open_agent_terminal "$session" "0" "Orchestrator"
        fi
    done <<< "$ORCHESTRATOR_SESSIONS"
fi

# Open agent sessions with intelligent window detection
if [ -n "$AGENT_SESSIONS" ]; then
    while IFS= read -r session; do
        if [ -n "$session" ]; then
            # Get all windows for this session and find Claude agents
            WINDOWS=$(tmux list-windows -t "$session" -F "#{window_index}:#{window_name}" 2>/dev/null)
            
            while IFS= read -r window; do
                if [ -n "$window" ] && echo "$window" | grep -q "Claude"; then
                    WINDOW_INDEX=$(echo "$window" | cut -d: -f1)
                    WINDOW_NAME=$(echo "$window" | cut -d: -f2-)
                    
                    # Determine agent type from window name and session
                    AGENT_TYPE="Agent"
                    if echo "$session" | grep -q "pm\\|manager"; then
                        AGENT_TYPE="PM"
                    elif echo "$WINDOW_NAME" | grep -q "pm"; then
                        AGENT_TYPE="PM"
                    elif echo "$WINDOW_NAME" | grep -q "frontend"; then
                        AGENT_TYPE="Frontend"
                    elif echo "$WINDOW_NAME" | grep -q "backend"; then
                        AGENT_TYPE="Backend"
                    elif echo "$WINDOW_NAME" | grep -q "qa\\|testing"; then
                        AGENT_TYPE="QA"
                    fi
                    
                    open_agent_terminal "$session" "$WINDOW_INDEX" "$AGENT_TYPE ($session)"
                fi
            done <<< "$WINDOWS"
        fi
    done <<< "$AGENT_SESSIONS"
fi

echo ""
echo "✅ All active agents opened!"
echo ""
echo "💡 Useful commands after opening agents:"
echo "   - List all agents: .tmux-orchestrator/commands/list-agents.sh"
echo "   - Agent status: .tmux-orchestrator/commands/agent-status.sh"
echo "   - Force PM check-in: .tmux-orchestrator/commands/force-pm-checkin.sh"
echo "   - Send message: tmux-message <session:window> 'message'"

# Optional: Show agent status after opening
echo ""
read -p "📊 Show agent status dashboard? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    .tmux-orchestrator/commands/agent-status.sh
fi