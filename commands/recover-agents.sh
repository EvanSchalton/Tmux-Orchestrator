#!/bin/bash
# Recover missing agents without affecting running agents
# Only starts agents that should be running but have crashed/been killed

echo "🔧 AGENT RECOVERY SYSTEM"
echo "========================"
echo "Time: $(date)"
echo ""

# Get project name and task file
PROJECT_NAME=$(basename "$(pwd)")
TASK_FILE="${1:-${TMUX_ORCHESTRATOR_TASK_FILE:-tasks.md}}"
TASK_FILE_ABS=$(realpath "$TASK_FILE" 2>/dev/null || echo "$TASK_FILE")

if [ ! -f "$TASK_FILE" ]; then
    echo "❌ Task file not found: $TASK_FILE"
    echo "Usage: $0 [task-file]"
    exit 1
fi

# Check if tmux server is running
if ! tmux list-sessions >/dev/null 2>&1; then
    echo "❌ No tmux server running - starting fresh deployment"
    echo "💡 Use: ./scripts/deploy.sh $TASK_FILE"
    exit 1
fi

echo "📋 Task file: $TASK_FILE_ABS"
echo "🔍 Analyzing current agent status..."

# Define expected agents based on typical team composition
EXPECTED_AGENTS=(
    "orchestrator:Orchestrator:1"
    "$PROJECT_NAME-$PROJECT_NAME:PM:2"
    "$PROJECT_NAME-frontend:Frontend Developer:2"
    "$PROJECT_NAME-backend:Backend Developer:2"
    "$PROJECT_NAME-testing:QA Engineer:2"
)

# Find currently running sessions
RUNNING_SESSIONS=$(tmux list-sessions -F "#{session_name}" 2>/dev/null)

# Arrays to track agent status
RUNNING_AGENTS=()
MISSING_AGENTS=()

echo ""
echo "📊 Agent Status:"
echo "================"

# Check each expected agent
for agent_info in "${EXPECTED_AGENTS[@]}"; do
    IFS=':' read -r session_name role window <<< "$agent_info"
    
    if echo "$RUNNING_SESSIONS" | grep -q "^$session_name$"; then
        echo "✅ $role ($session_name) - Running"
        RUNNING_AGENTS+=("$agent_info")
    else
        echo "❌ $role ($session_name) - MISSING"
        MISSING_AGENTS+=("$agent_info")
    fi
done

# If no agents are missing, we're done
if [ ${#MISSING_AGENTS[@]} -eq 0 ]; then
    echo ""
    echo "✅ All agents are running! No recovery needed."
    echo ""
    echo "💡 Use these commands to interact:"
    echo "   Monitor: .tmux-orchestrator/commands/agent-status.sh"
    echo "   Open all: VS Code → Tasks → '🎭 Open ALL Agent Terminals'"
    exit 0
fi

# Recovery needed
echo ""
echo "🚨 Recovery needed for ${#MISSING_AGENTS[@]} agent(s)"
echo ""
echo "🔄 Starting recovery process..."

# Source necessary scripts
DEPLOY_AGENT="$(dirname "$0")/deploy-agent.sh"
SEND_MESSAGE="/usr/local/bin/tmux-message"

if [ ! -f "$DEPLOY_AGENT" ]; then
    echo "❌ Could not find deploy-agent.sh script"
    exit 1
fi

# Recover each missing agent
for agent_info in "${MISSING_AGENTS[@]}"; do
    IFS=':' read -r session_name role window <<< "$agent_info"
    
    echo ""
    echo "🔄 Recovering $role..."
    
    case "$role" in
        "Orchestrator")
            # Use start-orchestrator script
            echo "   Starting Orchestrator..."
            bash "$(dirname "$0")/start-orchestrator.sh" "orchestrator"
            sleep 10
            
            # Send recovery briefing
            ORCHESTRATOR_BRIEF="You are the Tmux Orchestrator for $PROJECT_NAME.

⚠️ RECOVERY CONTEXT: You were restarted while other agents continue working.

Your responsibilities:
1. Coordinate work between all agents
2. Monitor progress and resolve blockers
3. Ensure code quality and git discipline
4. Manage team communication and priorities

IMMEDIATE ACTIONS:
1. Check status of all running agents
2. Review recent commits and progress
3. Identify any blockers or issues
4. Resume coordination

🤖 AGENT COMMUNICATION COMMANDS:
- Send message to any agent: tmux-message <session:window> 'your message'
- Available agents:
  • PM: tmux-message $PROJECT_NAME-$PROJECT_NAME:2 'message'
  • Frontend: tmux-message $PROJECT_NAME-frontend:2 'message'
  • Backend: tmux-message $PROJECT_NAME-backend:2 'message'
  • QA: tmux-message $PROJECT_NAME-testing:2 'message'
- Check agent status: .tmux-orchestrator/commands/agent-status.sh

Please respond with 'Orchestrator recovered and ready!' and check team status."
            
            $SEND_MESSAGE "orchestrator:1" "$ORCHESTRATOR_BRIEF"
            ;;
            
        "PM")
            # Deploy PM
            echo "   Deploying Project Manager..."
            bash "$DEPLOY_AGENT" "$PROJECT_NAME" "pm"
            sleep 10
            
            # Send recovery briefing (similar to restart-pm.sh)
            PM_BRIEF="You are the Project Manager for $PROJECT_NAME.

⚠️ RECOVERY CONTEXT: You were restarted while other agents continue working.

Task file: $TASK_FILE_ABS

Your responsibilities remain the same, but you need to:
1. Catch up on current progress
2. Check what other agents are working on
3. Resume coordination immediately

IMMEDIATE ACTIONS:
1. Run: .tmux-orchestrator/commands/agent-status.sh
2. Ask each agent for current status
3. Review task file for priorities
4. Resume coordination based on progress

🤖 Communication commands available - use them to coordinate!

Please start by checking team status and resuming coordination."
            
            $SEND_MESSAGE "$PROJECT_NAME-$PROJECT_NAME:2" "$PM_BRIEF"
            ;;
            
        "Frontend Developer")
            # Deploy Frontend
            echo "   Deploying Frontend Developer..."
            bash "$DEPLOY_AGENT" "frontend" "developer"
            sleep 10
            
            # Send recovery briefing
            FRONTEND_BRIEF="You are the Frontend Developer for $PROJECT_NAME.

⚠️ RECOVERY CONTEXT: You were restarted. Other agents continue working.

Task file: $TASK_FILE_ABS

IMMEDIATE ACTIONS:
1. Check git status and recent commits
2. Review current frontend tasks
3. Coordinate with PM for priorities
4. Resume development work

Focus on frontend implementation tasks and maintain code quality."
            
            $SEND_MESSAGE "$PROJECT_NAME-frontend:2" "$FRONTEND_BRIEF"
            ;;
            
        "Backend Developer")
            # Deploy Backend
            echo "   Deploying Backend Developer..."
            bash "$DEPLOY_AGENT" "backend" "developer"
            sleep 10
            
            # Send recovery briefing
            BACKEND_BRIEF="You are the Backend Developer for $PROJECT_NAME.

⚠️ RECOVERY CONTEXT: You were restarted. Other agents continue working.

Task file: $TASK_FILE_ABS

IMMEDIATE ACTIONS:
1. Check git status and recent commits
2. Review current backend tasks
3. Coordinate with PM for priorities
4. Resume development work

Focus on backend implementation tasks and maintain code quality."
            
            $SEND_MESSAGE "$PROJECT_NAME-backend:2" "$BACKEND_BRIEF"
            ;;
            
        "QA Engineer")
            # Deploy QA
            echo "   Deploying QA Engineer..."
            bash "$DEPLOY_AGENT" "testing" "qa"
            sleep 10
            
            # Send recovery briefing
            QA_BRIEF="You are the QA Engineer for $PROJECT_NAME.

⚠️ RECOVERY CONTEXT: You were restarted. Other agents continue working.

Task file: $TASK_FILE_ABS

IMMEDIATE ACTIONS:
1. Check test suite status
2. Review recent development changes
3. Coordinate with PM for testing priorities
4. Resume testing activities

Focus on quality assurance and comprehensive testing."
            
            $SEND_MESSAGE "$PROJECT_NAME-testing:2" "$QA_BRIEF"
            ;;
    esac
    
    echo "   ✅ $role recovered!"
done

echo ""
echo "🎉 RECOVERY COMPLETE!"
echo "===================="
echo ""
echo "📊 Final agent status:"
tmux list-sessions -F "#{session_name}" 2>/dev/null | while read session; do
    echo "   ✓ $session"
done

echo ""
echo "💡 All agents have been briefed on the recovery context"
echo "   They will coordinate to resume work seamlessly"
echo ""
echo "🎯 Monitor recovery progress:"
echo "   Status: .tmux-orchestrator/commands/agent-status.sh"
echo "   Open all: VS Code → Tasks → '🎭 Open ALL Agent Terminals'"
echo "   PM check: VS Code → Tasks → '👔 PM Status Review & Individual Guidance'"
echo ""
echo "✨ Your team is back to full strength!"