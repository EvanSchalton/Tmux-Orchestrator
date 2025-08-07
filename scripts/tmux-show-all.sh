#!/bin/bash
# Dynamic TMUX dashboard creator - shows all active sessions in a split-pane view

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Parse arguments
MONITOR_SESSION="${1:-monitor}"
FILTER="${2:-corporate-coach}"  # Default filter for sessions

echo -e "${BLUE}🖥️  TMUX Multi-Session Dashboard${NC}"
echo -e "${BLUE}================================${NC}"

# Get all sessions (optionally filtered)
if [ -n "$FILTER" ]; then
    SESSIONS=$(tmux list-sessions -F "#{session_name}" 2>/dev/null | grep "$FILTER" | sort)
    echo -e "${GREEN}Filter: ${YELLOW}$FILTER${NC}"
else
    SESSIONS=$(tmux list-sessions -F "#{session_name}" 2>/dev/null | sort)
fi

# Count sessions
SESSION_COUNT=$(echo "$SESSIONS" | grep -c .)

if [ $SESSION_COUNT -eq 0 ]; then
    echo -e "${RED}❌ No sessions found${NC}"
    if [ -n "$FILTER" ]; then
        echo -e "${YELLOW}   Try removing the filter or starting some sessions first${NC}"
    fi
    exit 1
fi

# Kill existing monitor session if it exists
if tmux has-session -t "$MONITOR_SESSION" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Killing existing monitor session: $MONITOR_SESSION${NC}"
    tmux kill-session -t "$MONITOR_SESSION"
fi

echo -e "\n${GREEN}Found $SESSION_COUNT sessions:${NC}"
echo "$SESSIONS" | nl -w2 -s'. '

# Function to get the main window for a session (usually the Claude window)
get_main_window() {
    local session=$1
    # Try to find Claude windows first
    local claude_window=$(tmux list-windows -t "$session" -F "#{window_index}:#{window_name}" 2>/dev/null | grep -i claude | head -1 | cut -d: -f1)
    
    if [ -n "$claude_window" ]; then
        echo "$claude_window"
    else
        # Default to window 1 or 0
        if tmux list-windows -t "$session" -F "#{window_index}" 2>/dev/null | grep -q "1"; then
            echo "1"
        else
            echo "0"
        fi
    fi
}

# Create monitor session
echo -e "\n${GREEN}Creating monitor dashboard...${NC}"
tmux new-session -d -s "$MONITOR_SESSION"

# Determine layout based on number of sessions
case $SESSION_COUNT in
    1)
        # Single session - just attach to it
        SESSION=$(echo "$SESSIONS" | head -1)
        WINDOW=$(get_main_window "$SESSION")
        tmux send-keys -t "$MONITOR_SESSION:0" "tmux attach -t $SESSION:$WINDOW" Enter
        ;;
    2)
        # Two sessions - vertical split
        SESSION1=$(echo "$SESSIONS" | sed -n '1p')
        SESSION2=$(echo "$SESSIONS" | sed -n '2p')
        WINDOW1=$(get_main_window "$SESSION1")
        WINDOW2=$(get_main_window "$SESSION2")
        
        tmux send-keys -t "$MONITOR_SESSION:0" "echo 'Session: $SESSION1' && tmux attach -t $SESSION1:$WINDOW1" Enter
        tmux split-window -h -t "$MONITOR_SESSION:0"
        tmux send-keys -t "$MONITOR_SESSION:0.1" "echo 'Session: $SESSION2' && tmux attach -t $SESSION2:$WINDOW2" Enter
        ;;
    3)
        # Three sessions - one on left, two on right
        SESSION1=$(echo "$SESSIONS" | sed -n '1p')
        SESSION2=$(echo "$SESSIONS" | sed -n '2p')
        SESSION3=$(echo "$SESSIONS" | sed -n '3p')
        WINDOW1=$(get_main_window "$SESSION1")
        WINDOW2=$(get_main_window "$SESSION2")
        WINDOW3=$(get_main_window "$SESSION3")
        
        tmux send-keys -t "$MONITOR_SESSION:0" "echo 'Session: $SESSION1' && tmux attach -t $SESSION1:$WINDOW1" Enter
        tmux split-window -h -t "$MONITOR_SESSION:0" -p 50
        tmux send-keys -t "$MONITOR_SESSION:0.1" "echo 'Session: $SESSION2' && tmux attach -t $SESSION2:$WINDOW2" Enter
        tmux split-window -v -t "$MONITOR_SESSION:0.1"
        tmux send-keys -t "$MONITOR_SESSION:0.2" "echo 'Session: $SESSION3' && tmux attach -t $SESSION3:$WINDOW3" Enter
        ;;
    4)
        # Four sessions - 2x2 grid
        SESSION1=$(echo "$SESSIONS" | sed -n '1p')
        SESSION2=$(echo "$SESSIONS" | sed -n '2p')
        SESSION3=$(echo "$SESSIONS" | sed -n '3p')
        SESSION4=$(echo "$SESSIONS" | sed -n '4p')
        WINDOW1=$(get_main_window "$SESSION1")
        WINDOW2=$(get_main_window "$SESSION2")
        WINDOW3=$(get_main_window "$SESSION3")
        WINDOW4=$(get_main_window "$SESSION4")
        
        tmux send-keys -t "$MONITOR_SESSION:0" "echo 'Session: $SESSION1' && tmux attach -t $SESSION1:$WINDOW1" Enter
        tmux split-window -h -t "$MONITOR_SESSION:0" -p 50
        tmux send-keys -t "$MONITOR_SESSION:0.1" "echo 'Session: $SESSION2' && tmux attach -t $SESSION2:$WINDOW2" Enter
        tmux split-window -v -t "$MONITOR_SESSION:0.0" -p 50
        tmux send-keys -t "$MONITOR_SESSION:0.2" "echo 'Session: $SESSION3' && tmux attach -t $SESSION3:$WINDOW3" Enter
        tmux split-window -v -t "$MONITOR_SESSION:0.1" -p 50
        tmux send-keys -t "$MONITOR_SESSION:0.3" "echo 'Session: $SESSION4' && tmux attach -t $SESSION4:$WINDOW4" Enter
        ;;
    5)
        # Five sessions - 2 top, 3 bottom
        SESSION1=$(echo "$SESSIONS" | sed -n '1p')
        SESSION2=$(echo "$SESSIONS" | sed -n '2p')
        SESSION3=$(echo "$SESSIONS" | sed -n '3p')
        SESSION4=$(echo "$SESSIONS" | sed -n '4p')
        SESSION5=$(echo "$SESSIONS" | sed -n '5p')
        WINDOW1=$(get_main_window "$SESSION1")
        WINDOW2=$(get_main_window "$SESSION2")
        WINDOW3=$(get_main_window "$SESSION3")
        WINDOW4=$(get_main_window "$SESSION4")
        WINDOW5=$(get_main_window "$SESSION5")
        
        # Top row (2 panes)
        tmux send-keys -t "$MONITOR_SESSION:0" "echo 'Session: $SESSION1' && tmux attach -t $SESSION1:$WINDOW1" Enter
        tmux split-window -h -t "$MONITOR_SESSION:0" -p 50
        tmux send-keys -t "$MONITOR_SESSION:0.1" "echo 'Session: $SESSION2' && tmux attach -t $SESSION2:$WINDOW2" Enter
        
        # Bottom row (3 panes)
        tmux split-window -v -t "$MONITOR_SESSION:0.0" -p 50
        tmux send-keys -t "$MONITOR_SESSION:0.2" "echo 'Session: $SESSION3' && tmux attach -t $SESSION3:$WINDOW3" Enter
        tmux split-window -h -t "$MONITOR_SESSION:0.2" -p 66
        tmux send-keys -t "$MONITOR_SESSION:0.3" "echo 'Session: $SESSION4' && tmux attach -t $SESSION4:$WINDOW4" Enter
        tmux split-window -h -t "$MONITOR_SESSION:0.3" -p 50
        tmux send-keys -t "$MONITOR_SESSION:0.4" "echo 'Session: $SESSION5' && tmux attach -t $SESSION5:$WINDOW5" Enter
        ;;
    *)
        # More than 5 - create a grid as best as possible
        echo -e "${YELLOW}⚠️  Many sessions detected. Showing first 6 in a 2x3 grid${NC}"
        
        # Create 2x3 grid for first 6 sessions
        for i in {1..6}; do
            SESSION=$(echo "$SESSIONS" | sed -n "${i}p")
            [ -z "$SESSION" ] && break
            
            WINDOW=$(get_main_window "$SESSION")
            
            case $i in
                1)
                    tmux send-keys -t "$MONITOR_SESSION:0" "echo 'Session: $SESSION' && tmux attach -t $SESSION:$WINDOW" Enter
                    ;;
                2)
                    tmux split-window -h -t "$MONITOR_SESSION:0" -p 50
                    tmux send-keys -t "$MONITOR_SESSION:0.1" "echo 'Session: $SESSION' && tmux attach -t $SESSION:$WINDOW" Enter
                    ;;
                3)
                    tmux split-window -v -t "$MONITOR_SESSION:0.0" -p 66
                    tmux send-keys -t "$MONITOR_SESSION:0.2" "echo 'Session: $SESSION' && tmux attach -t $SESSION:$WINDOW" Enter
                    ;;
                4)
                    tmux split-window -v -t "$MONITOR_SESSION:0.1" -p 66
                    tmux send-keys -t "$MONITOR_SESSION:0.3" "echo 'Session: $SESSION' && tmux attach -t $SESSION:$WINDOW" Enter
                    ;;
                5)
                    tmux split-window -v -t "$MONITOR_SESSION:0.2" -p 50
                    tmux send-keys -t "$MONITOR_SESSION:0.4" "echo 'Session: $SESSION' && tmux attach -t $SESSION:$WINDOW" Enter
                    ;;
                6)
                    tmux split-window -v -t "$MONITOR_SESSION:0.3" -p 50
                    tmux send-keys -t "$MONITOR_SESSION:0.5" "echo 'Session: $SESSION' && tmux attach -t $SESSION:$WINDOW" Enter
                    ;;
            esac
        done
        ;;
esac

# Balance panes for better layout
tmux select-layout -t "$MONITOR_SESSION:0" tiled

echo -e "\n${GREEN}✅ Dashboard created!${NC}"
echo -e "\n${BLUE}Commands:${NC}"
echo -e "  ${YELLOW}Attach:${NC} tmux attach -t $MONITOR_SESSION"
echo -e "  ${YELLOW}Navigate panes:${NC} Ctrl+B, arrow keys"
echo -e "  ${YELLOW}Zoom pane:${NC} Ctrl+B, z"
echo -e "  ${YELLOW}Detach:${NC} Ctrl+B, d"
echo -e "  ${YELLOW}Kill dashboard:${NC} tmux kill-session -t $MONITOR_SESSION"
echo -e "\n${BLUE}Tip:${NC} Each pane shows a different session. You can interact with each one!"

# Auto-attach if in interactive shell
if [ -t 0 ] && [ -t 1 ]; then
    echo -e "\n${YELLOW}Press Enter to attach to dashboard, or Ctrl+C to exit...${NC}"
    read -r
    tmux attach -t "$MONITOR_SESSION"
fi