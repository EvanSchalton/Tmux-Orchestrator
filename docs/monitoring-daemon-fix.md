# Monitoring Daemon Fix Guide

## Issues Identified

1. **Monitor daemon exits immediately** - The built-in monitor starts but exits right after initialization
2. **Recovery daemon crashes** - ImportError with Typer/Rich compatibility
3. **No reliable idle detection** - Agents can become idle without notification

## Root Causes

1. **Daemon Process Management**: The multiprocessing daemon=True flag causes the process to exit when parent exits
2. **Agent Discovery**: The monitor might not find agents due to session naming conventions
3. **Import Issues**: Possible version conflicts between Rich and other dependencies

## Solutions

### 1. Quick Fix - Use Simple Monitor

```bash
# Run the simple monitor script directly
python /workspaces/Tmux-Orchestrator/tmux_orchestrator/core/monitor_fix.py &

# Check it's running
ps aux | grep monitor_fix

# View logs
tail -f /tmp/tmux-orchestrator-simple-monitor.log
```

### 2. Proper Daemon with systemd (Production)

Create `/etc/systemd/system/tmux-orchestrator-monitor.service`:

```ini
[Unit]
Description=Tmux Orchestrator Monitor Daemon
After=network.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/path/to/project
ExecStart=/usr/bin/python3 -m tmux_orchestrator.core.monitor_fix
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable tmux-orchestrator-monitor
sudo systemctl start tmux-orchestrator-monitor
```

### 3. Alternative - Use tmux session for monitoring

```bash
# Create a monitoring session
tmux new-session -d -s monitor-daemon \
  "while true; do python -m tmux_orchestrator.core.monitor_fix; sleep 5; done"

# View monitor output
tmux attach -t monitor-daemon
```

### 4. Fix for the Original Daemon

The issue is in `/tmux_orchestrator/core/monitor.py`. The daemon process needs to be properly detached:

```python
# Change this:
self.daemon_process = multiprocessing.Process(
    target=self._run_monitoring_daemon,
    args=(interval,),
    daemon=True  # This causes early exit!
)

# To this:
self.daemon_process = multiprocessing.Process(
    target=self._run_monitoring_daemon,
    args=(interval,)
)
self.daemon_process.daemon = False  # Don't exit with parent
```

## Monitoring Best Practices

1. **Always verify daemon is running**:
   ```bash
   ps aux | grep -E "monitor|orchestrator" | grep -v grep
   ```

2. **Check logs regularly**:
   ```bash
   tail -f /tmp/tmux-orchestrator-*.log
   ```

3. **Set up PM notifications**:
   - Ensure PM agent is named with "pm" in session/window name
   - Monitor checks every 10 seconds by default
   - Idle threshold is 60 seconds (6 checks)

4. **Recovery from issues**:
   ```bash
   # Kill stuck monitors
   pkill -f "tmux-orchestrator.*monitor"

   # Clear PID files
   rm -f /tmp/tmux-orchestrator-*.pid

   # Restart monitoring
   tmux new-session -d -s monitor "python /path/to/monitor_fix.py"
   ```

## Custom Monitoring Script

Your custom script at `/tmp/monitor-agents.sh` is actually a good solution! It's simple and reliable:

```bash
#!/bin/bash
# Make it permanent
sudo cp /tmp/monitor-agents.sh /usr/local/bin/tmux-monitor
sudo chmod +x /usr/local/bin/tmux-monitor

# Run it
tmux new-session -d -s agent-monitor /usr/local/bin/tmux-monitor
```

## Debugging Tips

1. **Check agent discovery**:
   ```bash
   tmux list-sessions
   tmux list-windows -a -F "#{session_name}:#{window_index} #{window_name}"
   ```

2. **Test PM notification**:
   ```bash
   # Find PM session
   tmux list-windows -a | grep -i pm

   # Send test message
   tmux send-keys -t "SESSION:WINDOW" "echo 'Test notification'" Enter
   ```

3. **Monitor resource usage**:
   ```bash
   top -p $(pgrep -f "monitor|orchestrator" | tr '\n' ',')
   ```

## Long-term Fix

The monitoring system needs:
1. Proper process daemonization (not using multiprocessing.daemon)
2. Better error handling and recovery
3. Configurable thresholds and intervals
4. Integration with systemd or supervisor
5. Better agent discovery heuristics
