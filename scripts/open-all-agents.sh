#!/bin/bash
# Open all agent windows in separate terminals for interaction

# Detect the terminal emulator and OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    if command -v iTerm2 &> /dev/null; then
        # iTerm2 is available
        osascript -e 'tell application "iTerm2"
            create window with default profile
            tell current session of current window
                write text "tmux attach-session -t tmux-orc-dev:5"
                set name to "Project Manager"
            end tell
            
            tell current window
                create tab with default profile
                tell current session
                    write text "tmux attach-session -t tmux-orc-dev:2"
                    set name to "MCP Developer"
                end tell
            end tell
            
            tell current window
                create tab with default profile
                tell current session
                    write text "tmux attach-session -t tmux-orc-dev:3"
                    set name to "CLI Developer"
                end tell
            end tell
            
            tell current window
                create tab with default profile
                tell current session
                    write text "tmux attach-session -t tmux-orc-dev:4"
                    set name to "Agent Recovery Dev"
                end tell
            end tell
        end tell'
    else
        # Use Terminal.app
        osascript -e 'tell application "Terminal"
            do script "tmux attach-session -t tmux-orc-dev:5"
            do script "tmux attach-session -t tmux-orc-dev:2"
            do script "tmux attach-session -t tmux-orc-dev:3"
            do script "tmux attach-session -t tmux-orc-dev:4"
        end tell'
    fi
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    if command -v gnome-terminal &> /dev/null; then
        # GNOME Terminal
        gnome-terminal --tab --title="Project Manager" -- bash -c "tmux attach-session -t tmux-orc-dev:5; exec bash"
        gnome-terminal --tab --title="MCP Developer" -- bash -c "tmux attach-session -t tmux-orc-dev:2; exec bash"
        gnome-terminal --tab --title="CLI Developer" -- bash -c "tmux attach-session -t tmux-orc-dev:3; exec bash"
        gnome-terminal --tab --title="Agent Recovery" -- bash -c "tmux attach-session -t tmux-orc-dev:4; exec bash"
    elif command -v konsole &> /dev/null; then
        # KDE Konsole
        konsole --new-tab --title "Project Manager" -e bash -c "tmux attach-session -t tmux-orc-dev:5"
        konsole --new-tab --title "MCP Developer" -e bash -c "tmux attach-session -t tmux-orc-dev:2"
        konsole --new-tab --title "CLI Developer" -e bash -c "tmux attach-session -t tmux-orc-dev:3"
        konsole --new-tab --title "Agent Recovery" -e bash -c "tmux attach-session -t tmux-orc-dev:4"
    elif command -v xterm &> /dev/null; then
        # Fallback to xterm
        xterm -title "Project Manager" -e "tmux attach-session -t tmux-orc-dev:5" &
        xterm -title "MCP Developer" -e "tmux attach-session -t tmux-orc-dev:2" &
        xterm -title "CLI Developer" -e "tmux attach-session -t tmux-orc-dev:3" &
        xterm -title "Agent Recovery" -e "tmux attach-session -t tmux-orc-dev:4" &
    fi
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    # Windows (Git Bash/Cygwin)
    if command -v wt.exe &> /dev/null; then
        # Windows Terminal
        wt.exe new-tab --title "Project Manager" bash -c "tmux attach-session -t tmux-orc-dev:5"
        wt.exe new-tab --title "MCP Developer" bash -c "tmux attach-session -t tmux-orc-dev:2"
        wt.exe new-tab --title "CLI Developer" bash -c "tmux attach-session -t tmux-orc-dev:3"
        wt.exe new-tab --title "Agent Recovery" bash -c "tmux attach-session -t tmux-orc-dev:4"
    fi
fi

echo "Opening agent windows..."
echo "If windows didn't open automatically, use these commands manually:"
echo "  tmux attach-session -t tmux-orc-dev:5  # Project Manager"
echo "  tmux attach-session -t tmux-orc-dev:2  # MCP Developer"
echo "  tmux attach-session -t tmux-orc-dev:3  # CLI Developer"
echo "  tmux attach-session -t tmux-orc-dev:4  # Agent Recovery Developer"