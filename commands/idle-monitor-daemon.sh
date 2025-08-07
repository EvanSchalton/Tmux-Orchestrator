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

# Function to check if an agent is idle by detecting no terminal changes
is_agent_idle() {
    local session=$1
    local window=$2
    local agent_name=$3
    
    # Take 3 snapshots over 300ms to detect activity
    local snapshot1=$(tmux capture-pane -t "$session:$window" -p -S -10 2>/dev/null | tail -5 || echo "")
    sleep 0.1
    local snapshot2=$(tmux capture-pane -t "$session:$window" -p -S -10 2>/dev/null | tail -5 || echo "")
    sleep 0.1
    local snapshot3=$(tmux capture-pane -t "$session:$window" -p -S -10 2>/dev/null | tail -5 || echo "")
    sleep 0.1
    local snapshot4=$(tmux capture-pane -t "$session:$window" -p -S -10 2>/dev/null | tail -5 || echo "")
    
    # If all snapshots are identical, agent is idle
    if [ "$snapshot1" = "$snapshot2" ] && [ "$snapshot2" = "$snapshot3" ] && [ "$snapshot3" = "$snapshot4" ]; then
        # No change in 300ms = idle
        return 0
    fi
    
    # Also check if at Claude prompt (any snapshot)
    if echo "$snapshot4" | grep -q "│ >"; then
        # At prompt, likely idle
        return 0
    fi
    
    return 1  # Not idle (terminal changed)
}

# Function to check for unsubmitted message
has_unsubmitted_message() {
    local session="$1"
    local window="$2"
    
    # Capture the last 30 lines from the agent's terminal
    local terminal_content=$(tmux capture-pane -t "$session:$window" -p -S -30 2>/dev/null || echo "")
    
    # Look for tmux-message command that hasn't been submitted
    # Common patterns:
    # 1. tmux-message command without subsequent "Message sent" confirmation
    # 2. Command typed but cursor still on same line
    # 3. Line starts with tmux-message but no Enter was pressed
    
    # Check if last non-empty line contains tmux-message
    local last_line=$(echo "$terminal_content" | grep -v "^$" | tail -1)
    
    if echo "$last_line" | grep -q "tmux-message"; then
        # Check if there's a "Message sent to" confirmation after it
        local after_command=$(echo "$terminal_content" | grep -A5 "tmux-message" | tail -5)
        if ! echo "$after_command" | grep -q "Message sent to"; then
            # Found unsubmitted tmux-message command
            return 0
        fi
    fi
    
    # Also check for other common unsubmitted patterns
    # Sometimes the message is typed but Enter wasn't pressed
    if echo "$last_line" | grep -qE "(STATUS UPDATE:|Please report|What's your|Could you|Please provide|Hello|Hi there|I need|Can you)"; then
        # This looks like a message that should have been sent
        return 0
    fi
    
    return 1  # No unsubmitted message
}

# Function to auto-submit a message
auto_submit_message() {
    local session="$1"
    local window="$2"
    local agent_type="$3"
    
    log_message "Auto-submitting unsubmitted message for $agent_type ($session:$window)"
    
    # Send Enter key multiple times with delays to ensure submission
    tmux send-keys -t "$session:$window" End
    sleep 0.5
    tmux send-keys -t "$session:$window" Enter
    sleep 1
    tmux send-keys -t "$session:$window" Enter
    sleep 0.5
    
    return 0
}

# Function to find PM session dynamically
find_pm_session() {
    local pm_sessions=""
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

Please check their status and assign work:
$(echo "$idle_agents" | while read agent; do
    [ -n "$agent" ] && echo "• tmux-message $agent 'Please report your current status'"
done)

This is an automated notification from the idle monitor."
    
    # Send notification to PM
    tmux-message "$pm_target" "$message"
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
        CURRENT_TIME=$(date +%s)
        
        # Check orchestrator
        if tmux has-session -t "orchestrator" 2>/dev/null; then
            if is_agent_idle "orchestrator" "1" "Orchestrator"; then
                LAST_TIME=${last_notified["orchestrator"]:-0}
                if [ $((CURRENT_TIME - LAST_TIME)) -gt $NOTIFICATION_COOLDOWN ]; then
                    IDLE_AGENTS="${IDLE_AGENTS}orchestrator:1 (Orchestrator)\n"
                    last_notified["orchestrator"]=$CURRENT_TIME
                fi
            fi
        fi
        
        # Check project agents
        ALL_SESSIONS=$(tmux list-sessions -F "#{session_name}" 2>/dev/null | grep -v orchestrator)
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
        
        # Notify PM if any agents are idle
        if [ -n "$IDLE_AGENTS" ]; then
            # Remove trailing newline
            IDLE_AGENTS=$(echo -e "$IDLE_AGENTS" | sed '/^$/d')
            
            # Check if PM is busy before notifying
            PM_WINDOW=$(echo "$PM_TARGET" | cut -d: -f2)
            PM_SESSION=$(echo "$PM_TARGET" | cut -d: -f1)
            
            # Debug log
            log_message "Found idle agents: $(echo "$IDLE_AGENTS" | tr '\n' ', ')"
            
            if is_agent_idle "$PM_SESSION" "$PM_WINDOW" "PM"; then
                log_message "PM is idle, sending notification"
                notify_pm "$IDLE_AGENTS" "$PM_TARGET"
            else
                log_message "PM is busy, skipping notification"
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