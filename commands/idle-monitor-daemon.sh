#!/bin/bash
# Idle Agent Monitor Daemon
# Monitors all agents for idle state and notifies PM when agents need work
# Runs continuously in background, checking every 10 seconds

MONITOR_INTERVAL=${1:-10}  # Default 10 seconds, can override
LOG_FILE="/tmp/tmux-orchestrator-idle-monitor.log"
PID_FILE="/tmp/tmux-orchestrator-idle-monitor.pid"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Function to check if an agent is idle by monitoring last line changes
is_agent_idle() {
    local session=$1
    local window=$2
    local agent_name=$3
    
    # Take 4 snapshots of the last 5 lines (excluding input box) at 300ms intervals
    local content1=$(tmux capture-pane -t "$session:$window" -p 2>/dev/null | head -n -3 | tail -5 | tr '\n' ' ' || echo "")
    sleep 0.3
    local content2=$(tmux capture-pane -t "$session:$window" -p 2>/dev/null | head -n -3 | tail -5 | tr '\n' ' ' || echo "")
    sleep 0.3
    local content3=$(tmux capture-pane -t "$session:$window" -p 2>/dev/null | head -n -3 | tail -5 | tr '\n' ' ' || echo "")
    sleep 0.3
    local content4=$(tmux capture-pane -t "$session:$window" -p 2>/dev/null | head -n -3 | tail -5 | tr '\n' ' ' || echo "")
    
    # Debug logging (temporarily enabled)
    log_message "DEBUG $agent_name: content1='$content1' content2='$content2' content3='$content3' content4='$content4'"
    
    # If all content snapshots are identical, no new output = idle
    if [ "$content1" = "$content2" ] && [ "$content2" = "$content3" ] && [ "$content3" = "$content4" ]; then
        # No new output in 900ms = idle
        log_message "DEBUG $agent_name: DETECTED AS IDLE"
        return 0
    fi
    
    log_message "DEBUG $agent_name: DETECTED AS ACTIVE"
    
    return 1  # New output detected, agent is active
}

# Function to check for unsubmitted message
has_unsubmitted_message() {
    local session="$1"
    local window="$2"
    
    # Capture the last 20 lines from the agent's terminal
    local terminal_content=$(tmux capture-pane -t "$session:$window" -p -S -20 2>/dev/null || echo "")
    
    # Check if there's text typed in Claude prompt that hasn't been submitted
    # Look for the Claude prompt box with content inside
    local prompt_line=$(echo "$terminal_content" | grep "│ >")
    
    # Check if there's text inside the prompt box (not just the empty prompt "│ >")
    if echo "$prompt_line" | grep -q "│ > .*[A-Za-z0-9]"; then
        # There's text in the prompt that should be submitted
        return 0
    fi
    
    # Also check for multiline messages in the prompt box
    # Look for lines that contain text after the prompt box started
    local in_prompt=false
    while IFS= read -r line; do
        if echo "$line" | grep -q "│ >"; then
            in_prompt=true
            # Check if there's content on the same line as the prompt
            if echo "$line" | grep "│ >.*[A-Za-z0-9]" > /dev/null; then
                return 0
            fi
        elif [ "$in_prompt" = true ] && echo "$line" | grep -q "│.*[A-Za-z0-9]"; then
            # Found content in the prompt box
            return 0
        elif echo "$line" | grep -q "╰─"; then
            # End of prompt box
            in_prompt=false
        fi
    done <<< "$terminal_content"
    
    # Legacy: Check for tmux-message commands
    local last_line=$(echo "$terminal_content" | grep -v "^$" | tail -1)
    if echo "$last_line" | grep -q "tmux-message"; then
        local after_command=$(echo "$terminal_content" | grep -A5 "tmux-message" | tail -5)
        if ! echo "$after_command" | grep -q "Message sent to"; then
            return 0
        fi
    fi
    
    return 1  # No unsubmitted message
}

# Function to auto-submit a message
auto_submit_message() {
    local session="$1"
    local window="$2"
    local agent_type="$3"
    
    log_message "Auto-submitting unsubmitted message for $agent_type ($session:$window)"
    
    # For Claude prompts, focus on the text area and submit
    tmux send-keys -t "$session:$window" C-a  # Go to beginning of line
    sleep 0.2
    tmux send-keys -t "$session:$window" C-e  # Go to end of line
    sleep 0.3
    tmux send-keys -t "$session:$window" Enter # Submit the message
    sleep 0.5
    tmux send-keys -t "$session:$window" Enter # Extra enter to ensure submission
    sleep 0.3
    
    return 0
}

# Function to find PM session dynamically
find_pm_session() {
    # First check tmux-orc-dev session for Project-Manager window
    if tmux has-session -t "tmux-orc-dev" 2>/dev/null; then
        local pm_window=$(tmux list-windows -t "tmux-orc-dev" -F "#{window_index}:#{window_name}" 2>/dev/null | grep -E "Project-Manager" | head -1 || true)
        if [ -n "$pm_window" ]; then
            echo "tmux-orc-dev:$(echo "$pm_window" | cut -d: -f1)"
            return 0
        fi
    fi
    
    # Fallback to searching other sessions
    local all_sessions=$(tmux list-sessions -F "#{session_name}" 2>/dev/null)
    
    while IFS= read -r session; do
        if [ -n "$session" ]; then
            # Check if this session has a PM window
            local pm_window=$(tmux list-windows -t "$session" -F "#{window_index}:#{window_name}" 2>/dev/null | grep -E "Claude-pm|pm|Project-Manager" | head -1 || true)
            if [ -n "$pm_window" ]; then
                echo "$session:$(echo "$pm_window" | cut -d: -f1)"
                return 0
            fi
        fi
    done <<< "$all_sessions"
    
    return 1  # No PM found
}

# Function to notify PM about idle agents
notify_pm() {
    local idle_agents="$1"
    local pm_target="$2"
    
    local message="🚨 IDLE AGENT ALERT:

The following agents appear to be idle and need tasks:
$idle_agents

Please check their status and assign work as needed.

This is an automated notification from the idle monitor."
    
    # Send notification to PM using the correct script
    "/workspaces/Tmux-Orchestrator/send-claude-message.sh" "$pm_target" "$message"
    log_message "Notified PM about idle agents: $(echo "$idle_agents" | tr '\n' ', ')"
}

# Main monitoring loop
main() {
    log_message "Starting Idle Agent Monitor Daemon (interval: ${MONITOR_INTERVAL}s)"
    
    # Save PID for stop script
    echo $$ > "$PID_FILE"
    
    # Track last notification time for each agent to avoid spam
    declare -A last_notified
    NOTIFICATION_COOLDOWN=300  # 5 minutes between notifications for same agent
    
    while true; do
        # Check if tmux server is running
        if ! tmux list-sessions >/dev/null 2>&1; then
            log_message "No tmux server running, sleeping..."
            sleep "$MONITOR_INTERVAL"
            continue
        fi
        
        # Find PM session
        PM_TARGET=$(find_pm_session)
        if [ -z "$PM_TARGET" ]; then
            log_message "No PM session found, sleeping..."
            sleep "$MONITOR_INTERVAL"
            continue
        fi
        
        # First pass: Check for unsubmitted messages and auto-submit them
        ALL_SESSIONS=$(tmux list-sessions -F "#{session_name}" 2>/dev/null)
        while IFS= read -r session; do
            if [ -n "$session" ]; then
                # Check all windows in session
                local windows=$(tmux list-windows -t "$session" -F "#{window_index}:#{window_name}" 2>/dev/null)
                while IFS= read -r window_info; do
                    if [ -n "$window_info" ]; then
                        local window_idx=$(echo "$window_info" | cut -d: -f1)
                        local window_name=$(echo "$window_info" | cut -d: -f2)
                        
                        # Check if it's a Claude window (agent or PM)
                        if echo "$window_name" | grep -q "Claude"; then
                            # Check for unsubmitted message
                            if has_unsubmitted_message "$session" "$window_idx"; then
                                # Determine agent type for logging
                                local agent_type="Agent"
                                if echo "$window_name" | grep -qi "pm"; then
                                    agent_type="PM"
                                elif echo "$session" | grep -qi "frontend"; then
                                    agent_type="Frontend"
                                elif echo "$session" | grep -qi "backend"; then
                                    agent_type="Backend"
                                elif echo "$session" | grep -qi "testing"; then
                                    agent_type="QA"
                                elif [ "$session" = "orchestrator" ]; then
                                    agent_type="Orchestrator"
                                fi
                                
                                # Auto-submit the message
                                auto_submit_message "$session" "$window_idx" "$agent_type"
                            fi
                        fi
                    fi
                done <<< "$windows"
            fi
        done <<< "$ALL_SESSIONS"
        
        # Second pass: Check for idle agents
        IDLE_AGENTS=""
        IDLE_AGENTS_FOR_NOTIFICATION=""
        CURRENT_TIME=$(date +%s)
        
        # Check tmux-orc-dev session agents
        if tmux has-session -t "tmux-orc-dev" 2>/dev/null; then
            # Map of windows to agent types in tmux-orc-dev
            declare -A agent_windows=(
                ["1"]="Orchestrator"
                ["2"]="MCP-Developer" 
                ["3"]="CLI-Developer"
                ["4"]="Agent-Recovery-Dev"
                ["5"]="Project-Manager"
            )
            
            for window in "${!agent_windows[@]}"; do
                agent_type="${agent_windows[$window]}"
                if is_agent_idle "tmux-orc-dev" "$window" "$agent_type"; then
                    # Add to idle agents list for logging
                    IDLE_AGENTS="${IDLE_AGENTS}tmux-orc-dev:${window} (${agent_type})\n"
                    
                    # Check cooldown for notifications
                    LAST_TIME=${last_notified["tmux-orc-dev:$window"]:-0}
                    if [ $((CURRENT_TIME - LAST_TIME)) -gt $NOTIFICATION_COOLDOWN ]; then
                        IDLE_AGENTS_FOR_NOTIFICATION="${IDLE_AGENTS_FOR_NOTIFICATION}tmux-orc-dev:${window} (${agent_type})\n"
                        last_notified["tmux-orc-dev:$window"]=$CURRENT_TIME
                    fi
                fi
            done
        fi
        
        # Check other project sessions (legacy support)
        ALL_SESSIONS=$(tmux list-sessions -F "#{session_name}" 2>/dev/null | grep -v -E "orchestrator|tmux-orc-dev")
        while IFS= read -r session; do
            if [ -n "$session" ]; then
                # Determine agent type and window
                if echo "$session" | grep -q "frontend"; then
                    AGENT_TYPE="Frontend"
                    WINDOW="2"
                elif echo "$session" | grep -q "backend"; then
                    AGENT_TYPE="Backend"
                    WINDOW="2"
                elif echo "$session" | grep -q "testing"; then
                    AGENT_TYPE="QA"
                    WINDOW="2"
                elif echo "$session" | grep -E "pm|project-manager" > /dev/null 2>&1; then
                    continue  # Skip PM sessions
                else
                    # For other sessions, check all windows for Claude agents
                    local windows=$(tmux list-windows -t "$session" -F "#{window_index}:#{window_name}" 2>/dev/null)
                    while IFS= read -r window_info; do
                        if [ -n "$window_info" ] && echo "$window_info" | grep -q "Claude"; then
                            local window_idx=$(echo "$window_info" | cut -d: -f1)
                            local window_name=$(echo "$window_info" | cut -d: -f2)
                            # Skip PM windows
                            if echo "$window_name" | grep -E "pm|Project-Manager" > /dev/null 2>&1; then
                                continue
                            fi
                            # Determine agent type from window name
                            if echo "$window_name" | grep -qi "developer"; then
                                AGENT_TYPE="Developer"
                            elif echo "$window_name" | grep -qi "qa"; then
                                AGENT_TYPE="QA"
                            else
                                AGENT_TYPE="Agent"
                            fi
                            WINDOW="$window_idx"
                            break
                        fi
                    done <<< "$windows"
                    
                    # If no Claude window found, skip
                    if [ -z "$WINDOW" ]; then
                        continue
                    fi
                fi
                
                # Check if idle
                if is_agent_idle "$session" "$WINDOW" "$AGENT_TYPE"; then
                    LAST_TIME=${last_notified["$session"]:-0}
                    if [ $((CURRENT_TIME - LAST_TIME)) -gt $NOTIFICATION_COOLDOWN ]; then
                        IDLE_AGENTS="${IDLE_AGENTS}${session}:${WINDOW} (${AGENT_TYPE})\n"
                        last_notified["$session"]=$CURRENT_TIME
                    fi
                fi
            fi
        done <<< "$ALL_SESSIONS"
        
        # Report status based on actual idle detection
        if [ -n "$IDLE_AGENTS" ]; then
            # Remove trailing newline
            IDLE_AGENTS=$(echo -e "$IDLE_AGENTS" | sed '/^$/d')
            
            # Log that agents are idle
            log_message "Found idle agents: $(echo "$IDLE_AGENTS" | tr '\n' ', ')"
            
            # Only notify PM if there are agents that haven't been notified recently
            if [ -n "$IDLE_AGENTS_FOR_NOTIFICATION" ]; then
                # Remove trailing newline
                IDLE_AGENTS_FOR_NOTIFICATION=$(echo -e "$IDLE_AGENTS_FOR_NOTIFICATION" | sed '/^$/d')
                
                # Check if PM is busy before notifying
                PM_WINDOW=$(echo "$PM_TARGET" | cut -d: -f2)
                PM_SESSION=$(echo "$PM_TARGET" | cut -d: -f1)
                
                if is_agent_idle "$PM_SESSION" "$PM_WINDOW" "PM"; then
                    log_message "PM is idle, sending notification"
                    notify_pm "$IDLE_AGENTS_FOR_NOTIFICATION" "$PM_TARGET"
                else
                    log_message "PM is busy, skipping notification"
                fi
            else
                log_message "Idle agents detected but in cooldown period"
            fi
        else
            # Log that no agents are idle
            log_message "All agents are active"
        fi
        
        # Sleep before next check
        sleep "$MONITOR_INTERVAL"
    done
}

# Handle shutdown gracefully
cleanup() {
    log_message "Stopping Idle Agent Monitor Daemon"
    rm -f "$PID_FILE"
    exit 0
}

trap cleanup EXIT INT TERM

# Start the monitor
main "$@"