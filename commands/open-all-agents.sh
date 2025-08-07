#!/bin/bash
# Dynamic script to open all running agents in separate VS Code terminals
# Automatically creates new terminals and attaches to each agent session

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

# Function to create VS Code terminal connection info
show_agent_connection() {
    local session=$1
    local window=${2:-1}
    local agent_name=$3
    
    echo "  📋 $agent_name"
    echo "     VS Code Task: 'Open $agent_name Agent'"  
    echo "     Manual Command: tmux attach -t '$session:$window'"
    echo ""
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
    echo "   ./scripts/deploy.sh tasks.md"
    exit 1
fi

echo "🚀 Available Agent Sessions:"
echo ""

# Show orchestrator sessions
if [ -n "$ORCHESTRATOR_SESSIONS" ]; then
    echo "🎯 ORCHESTRATOR SESSIONS:"
    while IFS= read -r session; do
        if [ -n "$session" ]; then
            show_agent_connection "$session" "0" "Orchestrator ($session)"
        fi
    done <<< "$ORCHESTRATOR_SESSIONS"
fi

# Show agent sessions with intelligent window detection
if [ -n "$AGENT_SESSIONS" ]; then
    echo "🤖 PROJECT AGENT SESSIONS:"
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
                    
                    show_agent_connection "$session" "$WINDOW_INDEX" "$AGENT_TYPE ($session)"
                fi
            done <<< "$WINDOWS"
        fi
    done <<< "$AGENT_SESSIONS"
fi

echo "🚀 INSTANT VS CODE ACCESS - OPEN ALL AGENTS AT ONCE:"
echo "   📋 Command Palette (Ctrl+Shift+P) → 'Tasks: Run Task' → Select:"
echo ""
echo "   ✨ 🎭 Open ALL Agent Terminals  ← OPENS ALL 5 AGENTS SIMULTANEOUSLY!"
echo ""
echo "   Or open individual agents:"
echo "   🎯 Open Orchestrator Agent    - Main coordinator"
echo "   👔 Open Project Manager Agent - Planning & quality control"  
echo "   🎨 Open Frontend Agent        - UI/UX development"
echo "   ⚙️ Open Backend Agent         - API & server logic"
echo "   🧪 Open QA Agent             - Testing & verification"
echo ""
echo "🎯 PM TEAM MANAGEMENT:"
echo "   👔 PM Status Review & Individual Guidance  ← Smart: Reviews each agent, gives PM commands"
echo "   📢 PM Broadcast Message to All Agents      ← Simple: Same message to everyone" 
echo "   💬 PM Custom Check-in with All Agents      ← Custom: Your message to all"
echo ""
echo "   💡 Each opens a NEW terminal panel and connects automatically!"
echo ""
echo "📋 MANUAL CONNECTION:"
echo "   Alternative: Open terminal manually and run commands above"
echo ""
echo "🔧 OTHER USEFUL COMMANDS:"
echo "   - List all agents: .tmux-orchestrator/commands/list-agents.sh"
echo "   - Agent status: .tmux-orchestrator/commands/agent-status.sh"  
echo "   - Force PM check-in: .tmux-orchestrator/commands/force-pm-checkin.sh"
echo "   - Send message: tmux-message <session:window> 'message'"

# Show agent status automatically for VS Code tasks
echo ""
echo "📊 AGENT STATUS:"
echo "=================="
.tmux-orchestrator/commands/agent-status.sh 2>/dev/null || echo "   Status check temporarily unavailable"