#!/bin/bash
# Setup project task management structure for a new project
# This script helps PMs quickly organize PRD-driven development

PROJECT_NAME=$1
PRD_FILE=$2

if [ -z "$PROJECT_NAME" ]; then
    echo "Usage: $0 <project-name> [prd-file]"
    echo "Example: $0 user-authentication ./prd-user-auth.md"
    exit 1
fi

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Setting up task management for project: $PROJECT_NAME${NC}"

# Use CLI to create project structure
echo -e "${YELLOW}Creating project structure...${NC}"
if [ -n "$PRD_FILE" ] && [ -f "$PRD_FILE" ]; then
    tmux-orc tasks create "$PROJECT_NAME" --prd "$PRD_FILE"
else
    tmux-orc tasks create "$PROJECT_NAME" --template
fi

# Show project location
PROJECT_DIR="$HOME/workspaces/Tmux-Orchestrator/.tmux_orchestrator/projects/$PROJECT_NAME"
echo -e "${GREEN}✓ Project created at: $PROJECT_DIR${NC}"

# Provide next steps
echo -e "\n${BLUE}Next Steps:${NC}"
echo "1. Review/edit PRD: $PROJECT_DIR/prd.md"
echo "2. Generate tasks from PRD using:"
echo "   /workspaces/Tmux-Orchestrator/.claude/commands/generate-tasks.md"
echo "3. Distribute tasks to agents:"
echo "   tmux-orc tasks distribute $PROJECT_NAME"
echo "4. Monitor progress:"
echo "   tmux-orc tasks status $PROJECT_NAME"

# Offer to open PRD in default editor
read -p "Open PRD for editing? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    ${EDITOR:-vim} "$PROJECT_DIR/prd.md"
fi
