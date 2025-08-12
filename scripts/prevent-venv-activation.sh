#!/bin/bash
# Script to prevent virtual environment activation in tmux sessions

# Function to clean venv from a specific pane
clean_venv_from_pane() {
    local target="$1"

    # Capture current pane content
    local content=$(tmux capture-pane -t "$target" -p 2>/dev/null || echo "")

    # Check if it contains the activation command
    if echo "$content" | grep -q "source.*test_env/bin/activate"; then
        # Clear the line if it's the current input
        tmux send-keys -t "$target" C-u 2>/dev/null || true
    fi
}

# Monitor all tmux panes
while true; do
    # Get all panes
    panes=$(tmux list-panes -a -F "#{session_name}:#{window_index}.#{pane_index}" 2>/dev/null || echo "")

    # Clean each pane
    for pane in $panes; do
        clean_venv_from_pane "$pane"
    done

    # Check every 2 seconds
    sleep 2
done
