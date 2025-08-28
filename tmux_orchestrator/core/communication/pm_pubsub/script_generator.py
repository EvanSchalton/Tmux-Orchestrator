"""PM monitoring script generation utilities."""

from pathlib import Path


def create_pm_monitoring_script() -> str:
    """Create a monitoring script for PMs to check daemon notifications.

    Returns:
        Path to created monitoring script
    """
    script_content = """#!/bin/bash
# PM Daemon Notification Monitor
# Run this periodically to check for daemon notifications

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PM_SESSION="${1:-pm:0}"

echo "🔍 Checking daemon notifications for $PM_SESSION..."

# Check for critical/high priority management messages
tmux-orc read --session "$PM_SESSION" --filter "CRITICAL\\|HIGH PRIORITY" --tail 5

echo -e "\\n📊 Pubsub System Status:"
tmux-orc status --format simple

echo -e "\\n🔄 Recent Recovery Actions:"
tmux-orc read --session "$PM_SESSION" --filter "recovery" --tail 3

echo -e "\\n✅ Monitoring check complete at $(date)"
"""

    script_path = Path("/tmp/pm_daemon_monitor.sh")
    script_path.write_text(script_content)
    script_path.chmod(0o755)

    return str(script_path)


def create_advanced_pm_script() -> str:
    """Create an advanced PM monitoring script with structured message handling.

    Returns:
        Path to created advanced script
    """
    advanced_script = """#!/bin/bash
# Advanced PM Daemon Notification Monitor
# Handles structured daemon messages and provides detailed analysis

PM_SESSION="${1:-pm:0}"
LOG_FILE="${2:-/tmp/pm_monitor.log}"

echo "🚀 Advanced PM Monitor starting for $PM_SESSION..."

# Function to log with timestamp
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Check structured messages
log_message "Checking structured daemon messages..."
tmux-orc read --session "$PM_SESSION" --format json --tail 20 > /tmp/pm_messages.json

# Parse and categorize messages
python3 -c "
import json
import sys
from datetime import datetime, timedelta

try:
    with open('/tmp/pm_messages.json') as f:
        data = json.load(f)

    messages = data.get('stored_messages', [])
    categories = {'health': [], 'recovery': [], 'status': [], 'critical': []}

    for msg in messages:
        content = msg.get('content', '').lower()
        priority = msg.get('priority', 'normal')

        if 'health' in content or 'monitoring' in content:
            categories['health'].append(msg)
        elif 'recovery' in content or 'restart' in content:
            categories['recovery'].append(msg)
        elif priority in ['critical', 'high']:
            categories['critical'].append(msg)
        else:
            categories['status'].append(msg)

    print(f'📊 Message Summary:')
    print(f'  Health: {len(categories[\"health\"])} messages')
    print(f'  Recovery: {len(categories[\"recovery\"])} messages')
    print(f'  Critical: {len(categories[\"critical\"])} messages')
    print(f'  Status: {len(categories[\"status\"])} messages')

    # Show recent critical messages
    if categories['critical']:
        print(f'\\n🚨 Recent Critical Messages:')
        for msg in categories['critical'][-3:]:
            timestamp = msg.get('timestamp', 'unknown')
            content = msg.get('content', 'No content')
            print(f'  [{timestamp}] {content[:100]}...')

except Exception as e:
    print(f'Error parsing messages: {e}')
    sys.exit(1)
"

# Check pubsub health
log_message "Checking pubsub system health..."
tmux-orc health --detailed

# Summary report
log_message "Monitor check complete. Summary logged to $LOG_FILE"

echo "✅ Advanced monitoring complete. Check $LOG_FILE for details."
"""

    advanced_path = Path("/tmp/advanced_pm_monitor.sh")
    advanced_path.write_text(advanced_script)
    advanced_path.chmod(0o755)

    return str(advanced_path)
