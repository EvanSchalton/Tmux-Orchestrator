#!/bin/bash
MINUTES=$1
TARGET=$2
NOTE=$3

if [ -z "$MINUTES" ] || [ -z "$TARGET" ] || [ -z "$NOTE" ]; then
  echo "Usage: $0 <minutes> <target> <note>"
  echo "Example: $0 30 orchestrator:0 'Review agent progress'"
  exit 1
fi

# Use the tmux-schedule command
/usr/local/bin/tmux-schedule "$MINUTES" "$NOTE" "$TARGET"
