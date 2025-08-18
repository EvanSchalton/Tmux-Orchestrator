# Tmux-Orc Environment Error Resolution Brief

## Issues Identified

### 1. pkg_resources Deprecation Warning
```
UserWarning: pkg_resources is deprecated as an API
```

### 2. Terminal Emulator Detection Error
```
Error: Could not detect terminal emulator
```

### 3. Claude Code Raw Mode Error
```
Error: Raw mode is not supported on the current process.stdin
```

## Root Cause Analysis

These errors indicate that tmux-orc is being run in an environment where:
1. The terminal emulator cannot be properly detected
2. Claude Code cannot access raw mode for interactive input
3. The environment may be missing required terminal capabilities

## Resolution Steps

### Step 1: Verify Terminal Environment
```bash
# Check if running inside tmux
echo $TMUX

# Check terminal type
echo $TERM

# Verify tmux is installed
which tmux
tmux -V
```

### Step 2: Fix Terminal Detection
```bash
# Set proper terminal environment
export TERM=xterm-256color

# If inside tmux, ensure proper terminal
tmux set-option -g default-terminal "screen-256color"
```

### Step 3: Run tmux-orc Inside Tmux Session
The error suggests you're trying to spawn an orchestrator outside of a tmux session. Try:

```bash
# Start a new tmux session first
tmux new-session -s corporate-coach -d

# Attach to the session
tmux attach -t corporate-coach

# Now run tmux-orc from within tmux
tmux-orc spawn orc
```

### Step 4: Alternative Spawn Method
If the above doesn't work, try spawning with explicit session target:

```bash
# From outside tmux, specify the session
tmux-orc spawn orc --session corporate-coach:0
```

### Step 5: Fix pkg_resources Warning
This is a warning about deprecated setuptools usage. To fix:

```bash
# Update setuptools in your virtual environment
pip install --upgrade setuptools

# Or pin to a version that still supports pkg_resources
pip install "setuptools<81"
```

### Step 6: Environment Variables for Claude
Ensure these are set:

```bash
export FORCE_COLOR=1
export NODE_NO_WARNINGS=1
export ANTHROPIC_API_KEY="your-key-here"
```

### Step 7: Debug Mode
Run with verbose output to get more information:

```bash
# Check tmux-orc configuration
tmux-orc reflect

# List current sessions and agents
tmux-orc list

# Check if monitor daemon is running
tmux-orc monitor status
```

## Quick Fix Script

Create and run this script to set up the environment:

```bash
#!/bin/bash
# save as fix-tmux-env.sh

# Set terminal environment
export TERM=xterm-256color
export FORCE_COLOR=1
export NODE_NO_WARNINGS=1

# Check if we're in tmux
if [ -z "$TMUX" ]; then
    echo "Not in tmux. Creating new session..."
    tmux new-session -s corporate-coach -d
    tmux send-keys -t corporate-coach:0 "cd $(pwd)" C-m
    tmux send-keys -t corporate-coach:0 "source .venv/bin/activate" C-m
    echo "Attaching to tmux session..."
    exec tmux attach -t corporate-coach
else
    echo "Already in tmux. Running tmux-orc..."
    tmux-orc spawn orc
fi
```

## Alternative: Use PM Instead of Orchestrator

If orchestrator spawn continues to fail, try spawning a PM directly:

```bash
# Inside tmux
tmux-orc spawn pm --session corporate-coach:1
```

## Additional Debugging

If issues persist:

1. **Check Node.js/Claude Code Installation**:
   ```bash
   which claude
   claude --version
   ```

2. **Verify Python Environment**:
   ```bash
   which python
   python --version
   pip show tmux-orchestrator
   ```

3. **Check for Conflicting Processes**:
   ```bash
   ps aux | grep tmux
   tmux list-sessions
   ```

## Expected Working State

When properly configured:
- You should be inside a tmux session
- Terminal should be detected as screen-256color or tmux-256color
- Claude Code should launch without raw mode errors
- The orchestrator should spawn in a new window within your tmux session

## Contact for Help

If these steps don't resolve the issue:
1. Check the tmux-orchestrator GitHub issues
2. Ensure you're using the latest version of tmux-orchestrator
3. Verify all dependencies are properly installed
