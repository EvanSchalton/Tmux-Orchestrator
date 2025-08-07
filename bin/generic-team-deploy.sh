#!/bin/bash
# Generic TMUX Orchestrator Team Deployment Script
# Usage: ./generic-team-deploy.sh <task-file> <project-name> [base-path]

set -e

# Parameters
TASK_FILE="$1"
PROJECT_NAME="$2"
BASE_PATH="${3:-/workspaces}"
PROJECT_PATH="$BASE_PATH/$PROJECT_NAME"

if [ -z "$TASK_FILE" ] || [ -z "$PROJECT_NAME" ]; then
    echo "Usage: $0 <task-file> <project-name> [base-path]"
    echo ""
    echo "Examples:"
    echo "  $0 /path/to/tasks.md my-project"
    echo "  $0 tasks.txt web-app /home/user/projects"
    echo ""
    echo "The task file should contain:"
    echo "  - A PRD with numbered tasks"
    echo "  - A markdown list of tasks" 
    echo "  - A plain text task list"
    exit 1
fi

# Validate paths
if [ ! -f "$TASK_FILE" ]; then
    echo "❌ Error: Task file not found: $TASK_FILE"
    exit 1
fi

if [ ! -d "$PROJECT_PATH" ]; then
    echo "❌ Error: Project path not found: $PROJECT_PATH"
    echo "   Make sure the project directory exists at: $BASE_PATH/$PROJECT_NAME"
    exit 1
fi

# Setup orchestrator paths
TASK_FILE_ABS="$(cd "$(dirname "$TASK_FILE")" && pwd)/$(basename "$TASK_FILE")"
TMUX_ORCHESTRATOR_PATH="$PROJECT_PATH/.tmux-orchestrator"

# Check for orchestrator installation
if [ ! -d "$TMUX_ORCHESTRATOR_PATH" ]; then
    echo "❌ Error: TMUX Orchestrator not installed in project"
    echo "   Expected directory: $TMUX_ORCHESTRATOR_PATH"
    echo "   Run the orchestrator installation script first"
    exit 1
fi

DEPLOY_AGENT="$TMUX_ORCHESTRATOR_PATH/commands/deploy-agent.sh"
SEND_MESSAGE="/usr/local/bin/tmux-message"
START_ORCHESTRATOR="$TMUX_ORCHESTRATOR_PATH/commands/start-orchestrator.sh"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🚀 Generic TMUX Orchestrator Team Deployment${NC}"
echo -e "${BLUE}===========================================${NC}"
echo -e "Project: ${YELLOW}$PROJECT_NAME${NC}"
echo -e "Path: ${YELLOW}$PROJECT_PATH${NC}"
echo -e "Task File: ${YELLOW}$TASK_FILE_ABS${NC}"
echo ""

# Ensure tmux-message is available
if [ ! -f "$SEND_MESSAGE" ]; then
    echo -e "${YELLOW}Setting up tmux-message command...${NC}"
    if [ -f "$TMUX_ORCHESTRATOR_PATH/scripts/send-claude-message.sh" ]; then
        sudo ln -sf "$TMUX_ORCHESTRATOR_PATH/scripts/send-claude-message.sh" "$SEND_MESSAGE"
        sudo chmod +x "$SEND_MESSAGE"
    else
        echo -e "${RED}❌ Error: send-claude-message.sh not found in orchestrator scripts${NC}"
        exit 1
    fi
fi

# Analyze task file to determine team composition  
echo -e "${GREEN}📋 Analyzing task file for team requirements...${NC}"
TASK_CONTENT=$(cat "$TASK_FILE")

# Configurable team detection patterns
NEEDS_FRONTEND=false
NEEDS_BACKEND=false  
NEEDS_DATABASE=false
NEEDS_TESTING=true  # Always include testing by default

# Frontend detection patterns
if echo "$TASK_CONTENT" | grep -iE "(frontend|react|vue|angular|ui|component|html|css|javascript|typescript|nextjs|nuxt|svelte|markdown|editor)" > /dev/null; then
    NEEDS_FRONTEND=true
fi

# Backend detection patterns
if echo "$TASK_CONTENT" | grep -iE "(backend|api|service|endpoint|server|python|node|java|go|rust|fastapi|express|django|flask|spring)" > /dev/null; then
    NEEDS_BACKEND=true
fi

# Database detection patterns  
if echo "$TASK_CONTENT" | grep -iE "(database|db|sql|nosql|postgres|mysql|mongo|redis|neo4j|pgvector|migration|schema|orm)" > /dev/null; then
    NEEDS_DATABASE=true
    NEEDS_BACKEND=true  # Database work typically requires backend
fi

# Display team composition
echo -e "\n${GREEN}🎯 Detected Team Requirements:${NC}"
echo -e "  ✓ Orchestrator (coordination & oversight)"
echo -e "  ✓ Project Manager (quality & planning)"
[ "$NEEDS_FRONTEND" = true ] && echo -e "  ✓ Frontend Developer"
[ "$NEEDS_BACKEND" = true ] && echo -e "  ✓ Backend Developer"  
[ "$NEEDS_DATABASE" = true ] && echo -e "  ✓ Database Specialist"
[ "$NEEDS_TESTING" = true ] && echo -e "  ✓ QA Engineer"

echo -e "\n${YELLOW}Press Enter to deploy team, or Ctrl+C to cancel...${NC}"
read -r

# Step 1: Start Orchestrator
echo -e "\n${GREEN}1. Starting TMUX Orchestrator${NC}"
if [ -f "$START_ORCHESTRATOR" ]; then
    bash "$START_ORCHESTRATOR" "orchestrator"
else
    echo -e "${RED}❌ Orchestrator start script not found!${NC}"
    echo "   Expected: $START_ORCHESTRATOR"
    exit 1
fi

sleep 5

# Brief the orchestrator
echo -e "${GREEN}📋 Briefing the Orchestrator...${NC}"
$SEND_MESSAGE "orchestrator:0" "You are the TMUX Orchestrator for $PROJECT_NAME.

Project Path: $PROJECT_PATH
Task File: $TASK_FILE_ABS

Your responsibilities:
1. Read and understand all tasks in the file
2. Coordinate the team to implement the tasks
3. Ensure high quality standards - no shortcuts
4. Monitor git commits (every 30 minutes)
5. Resolve blockers and dependencies

Team composition is being deployed based on task requirements.
Please read the task file and prepare to coordinate implementation."

sleep 8

# Step 2: Deploy Project Manager
echo -e "\n${GREEN}2. Deploying Project Manager${NC}"
bash "$DEPLOY_AGENT" "$PROJECT_NAME" "pm"
sleep 5

echo -e "${GREEN}📋 Briefing the Project Manager...${NC}"
$SEND_MESSAGE "$PROJECT_NAME-$PROJECT_NAME:Claude-pm" "You are the Project Manager for $PROJECT_NAME.

Project Path: $PROJECT_PATH
Task File: $TASK_FILE_ABS

Your responsibilities:
1. Break down tasks into manageable work items
2. Create test plans BEFORE implementation
3. Ensure TDD principles are followed
4. Track progress and update documentation
5. Coordinate between all team members
6. Maintain EXCEPTIONAL quality standards

Critical: No shortcuts allowed. Quality over speed.
Please read the task file and create an implementation plan."

sleep 8

# Step 3: Deploy Frontend Developer (if needed)
if [ "$NEEDS_FRONTEND" = true ]; then
    echo -e "\n${GREEN}3. Deploying Frontend Developer${NC}"
    bash "$DEPLOY_AGENT" "frontend" "developer"
    sleep 5
    
    echo -e "${GREEN}📋 Briefing the Frontend Developer...${NC}"
    $SEND_MESSAGE "$PROJECT_NAME-frontend:Claude-developer" "You are the Frontend Developer for $PROJECT_NAME.

Project Path: $PROJECT_PATH  
Task File: $TASK_FILE_ABS

Focus on:
- UI/UX implementation tasks
- Frontend framework components
- User interactions and flows
- Responsive design
- Accessibility

Requirements:
- Follow existing code patterns
- Build/compile after every change
- Write tests for all components
- Use feature branches
- Commit every 30 minutes

Read the task file and identify all frontend-related tasks."
    
    sleep 8
fi

# Step 4: Deploy Backend Developer (if needed)
if [ "$NEEDS_BACKEND" = true ]; then
    echo -e "\n${GREEN}4. Deploying Backend Developer${NC}"
    bash "$DEPLOY_AGENT" "backend" "developer" 
    sleep 5
    
    echo -e "${GREEN}📋 Briefing the Backend Developer...${NC}"
    BACKEND_BRIEF="You are the Backend Developer for $PROJECT_NAME.

Project Path: $PROJECT_PATH
Task File: $TASK_FILE_ABS

Focus on:
- API endpoints and services
- Business logic implementation
- Data processing pipelines"
    
    if [ "$NEEDS_DATABASE" = true ]; then
        BACKEND_BRIEF="$BACKEND_BRIEF
- Database setup and migrations
- Schema design and optimization  
- Data persistence layers"
    fi
    
    BACKEND_BRIEF="$BACKEND_BRIEF

Requirements:
- Follow language/framework best practices
- Proper dependency management
- Write comprehensive tests
- Proper error handling
- Feature branches
- Commit every 30 minutes

Read the task file and identify all backend tasks."
    
    $SEND_MESSAGE "$PROJECT_NAME-backend:Claude-developer" "$BACKEND_BRIEF"
    
    sleep 8
fi

# Step 5: Deploy QA Engineer
if [ "$NEEDS_TESTING" = true ]; then
    echo -e "\n${GREEN}5. Deploying QA Engineer${NC}"
    bash "$DEPLOY_AGENT" "testing" "qa"
    sleep 5
    
    echo -e "${GREEN}📋 Briefing the QA Engineer...${NC}"
    $SEND_MESSAGE "$PROJECT_NAME-testing:Claude-qa" "You are the QA Engineer for $PROJECT_NAME.

Project Path: $PROJECT_PATH
Task File: $TASK_FILE_ABS

Your responsibilities:
1. Create comprehensive test plans
2. Write automated tests (unit, integration, E2E)
3. Test all user workflows
4. Performance testing
5. Regression testing
6. Security testing

Available tools:
- Framework-specific testing tools
- Browser automation (if applicable)
- Load testing tools

Work closely with developers to understand features before testing.
Read the task file and plan your testing strategy."
    
    sleep 8
fi

# Step 6: Final coordination
echo -e "\n${GREEN}6. Finalizing team coordination${NC}"
TEAM_SUMMARY="Your $PROJECT_NAME team is deployed and ready:

Sessions created:"
TEAM_SUMMARY="$TEAM_SUMMARY
- orchestrator: Orchestrator
- $PROJECT_NAME-$PROJECT_NAME: Project Manager"

[ "$NEEDS_FRONTEND" = true ] && TEAM_SUMMARY="$TEAM_SUMMARY
- $PROJECT_NAME-frontend: Frontend Developer"
[ "$NEEDS_BACKEND" = true ] && TEAM_SUMMARY="$TEAM_SUMMARY  
- $PROJECT_NAME-backend: Backend Developer"
[ "$NEEDS_TESTING" = true ] && TEAM_SUMMARY="$TEAM_SUMMARY
- $PROJECT_NAME-testing: QA Engineer"

TEAM_SUMMARY="$TEAM_SUMMARY

Project Path: $PROJECT_PATH
Task File: $TASK_FILE_ABS

Key principles:
1. Quality over speed - no shortcuts
2. TDD for all features
3. Git commits every 30 minutes
4. Feature branches for all work
5. Clear communication between team members

Start by having each agent read the task file and report understanding.
Then have the PM create a coordinated implementation plan.

Monitor with: tmux list-sessions | grep $PROJECT_NAME"

$SEND_MESSAGE "orchestrator:0" "$TEAM_SUMMARY"

# Create project-specific monitoring script
MONITOR_SCRIPT="$PROJECT_PATH/.tmux-orchestrator/monitor-$PROJECT_NAME-team.sh"
echo -e "\n${GREEN}7. Creating monitoring script${NC}"
cat > "$MONITOR_SCRIPT" << EOF
#!/bin/bash
# Monitor $PROJECT_NAME team status

echo "🔍 $PROJECT_NAME Team Status"
echo "=========================="
echo "Project: $PROJECT_PATH"
echo "Task File: $TASK_FILE_ABS"
echo ""

# List active sessions
echo "📦 Active Sessions:"
tmux list-sessions | grep "$PROJECT_NAME" || echo "  No sessions found"

# Show recent activity
echo -e "\n📋 Recent Activity:"
for session in \$(tmux list-sessions -F "#{session_name}" | grep "$PROJECT_NAME\\|orchestrator"); do
    echo -e "\n--- \$session ---"
    tmux capture-pane -t "\$session:0" -p 2>/dev/null | tail -5 || echo "  No output captured"
done

echo -e "\n💡 Useful Commands:"
echo "  Attach: tmux attach -t <session>"
echo "  Send: tmux-message <session:window> 'message'"
echo "  Status: $TMUX_ORCHESTRATOR_PATH/commands/agent-status.sh"
EOF

chmod +x "$MONITOR_SCRIPT"

# Create restart script  
RESTART_SCRIPT="$PROJECT_PATH/.tmux-orchestrator/restart-$PROJECT_NAME.sh"
cat > "$RESTART_SCRIPT" << EOF
#!/bin/bash
# Restart $PROJECT_NAME team
cd "$PROJECT_PATH"
bash "$TMUX_ORCHESTRATOR_PATH/../references/Tmux-Orchestrator/bin/generic-team-deploy.sh" "$TASK_FILE_ABS" "$PROJECT_NAME" "$BASE_PATH"
EOF
chmod +x "$RESTART_SCRIPT"

# Summary
echo -e "\n${BLUE}✅ Team Deployment Complete!${NC}"
echo -e "${GREEN}============================${NC}"
echo -e "\n${GREEN}Project:${NC} ${YELLOW}$PROJECT_NAME${NC}"
echo -e "${GREEN}Path:${NC} ${YELLOW}$PROJECT_PATH${NC}"
echo -e "${GREEN}Task File:${NC} ${YELLOW}$TASK_FILE_ABS${NC}"
echo -e "\n${GREEN}Commands:${NC}"
echo -e "  Monitor: ${YELLOW}$MONITOR_SCRIPT${NC}"
echo -e "  Restart: ${YELLOW}$RESTART_SCRIPT${NC}"
echo -e "  Attach: ${YELLOW}tmux attach -t <session-name>${NC}"
echo -e "  Status: ${YELLOW}$TMUX_ORCHESTRATOR_PATH/commands/agent-status.sh${NC}"
echo -e "\n${YELLOW}⚡ Your autonomous $PROJECT_NAME team is now working!${NC}"