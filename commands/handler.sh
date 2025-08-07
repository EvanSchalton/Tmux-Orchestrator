#!/bin/bash
# Tmux Orchestrator Command Handler

COMMAND=$1
shift

ORCH_DIR="/workspaces/corporate-coach/.tmux-orchestrator"

case "$COMMAND" in
  "start-orchestrator")
    bash "$ORCH_DIR/commands/start-orchestrator.sh" "$@"
    ;;
  "deploy-agent")
    bash "$ORCH_DIR/commands/deploy-agent.sh" "$@"
    ;;
  "agent-status")
    bash "$ORCH_DIR/commands/agent-status.sh" "$@"
    ;;
  "schedule-checkin")
    bash "$ORCH_DIR/commands/schedule-checkin.sh" "$@"
    ;;
  *)
    echo "Unknown command: $COMMAND"
    echo "Available commands: start-orchestrator, deploy-agent, agent-status, schedule-checkin"
    exit 1
    ;;
esac
