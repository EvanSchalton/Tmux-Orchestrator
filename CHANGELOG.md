# Tmux Orchestrator Changelog

## Version 2.1.14 - Monitoring System Improvements

### 🔧 Fixed

#### Critical Fix: False Positive Crash Detection
- **Resolved**: False positive crash detection when agents type "@" symbol in their prompts
- **Root Cause**: The "@" symbol was incorrectly included in bash prompt detection patterns
- **Impact**: Prevented unnecessary agent restarts and PM notifications

#### Major Improvement: Simplified Auto-Submit
- **Changed**: Auto-submit mechanism from complex key sequences (C-a, C-e, Enter) to single Enter key
- **Benefits**: More reliable message submission, reduced complexity, better compatibility
- **Implementation**: Updated to use new `tmux.press_enter()` method

### 🏗️ Refactoring

#### Monitor Module Restructuring
- **New Module**: Created `monitor_helpers.py` with extracted helper functions
- **Test Coverage**: Achieved 91% test coverage on helper functions
- **Functions Extracted**:
  - `is_claude_interface_present()`: Detects active Claude UI
  - `detect_agent_state()`: Determines agent state from terminal content
  - `has_unsubmitted_message()`: Checks for pending messages
  - `should_notify_pm()`: PM notification logic with cooldowns

#### Updated tmux Integration
- **Methods**: Replaced `send_keys()` with `send_text()` and `press_enter()`
- **Literal Flag**: Added support for tmux literal flag to prevent key interpretation
- **Reliability**: Improved text sending accuracy and special character handling

### 🐛 Bug Fixes
- Fixed crash detection logic to prioritize Claude UI indicators before checking bash prompts
- Removed "@" symbol from bash prompt indicators list
- Enhanced idle agent detection with more accurate state tracking
- Fixed false positives from terminal content analysis

### ⚠️ Known Issues
- False positive crash detection still occurs when "claude --dangerously-skip-permissions" appears in agent terminal
- Monitor may attempt to restart agents that are actively working if the command text appears in their visible terminal content
- Workaround: The system checks for Claude UI indicators first, reducing but not eliminating false positives

### 📊 Testing
- Created comprehensive test suite for monitor helpers
- Added fixtures for various agent states
- Improved test isolation and reliability
- 12 test failures remain in auto-recovery and auto-submit tests (under investigation)

---

## Version 2.0.0 - Enhanced Agent Communication & VS Code Integration

### 🎉 Major Enhancements

#### Agent Communication System
- **Enhanced tmux-message**: Auto-submit messages with proper Enter keypress
- **Agent Coordination**: PM and Orchestrator now have full inter-agent communication commands
- **Status Monitoring**: Real-time agent status checking and monitoring
- **Team Check-ins**: PM can conduct off-cycle status checks with all agents

#### VS Code Integration
- **Individual Agent Tasks**: Open any agent in a new VS Code terminal
- **Open All Agents**: Single command opens all 5 agents simultaneously
- **PM Check-in Tasks**: Standard and custom check-in commands
- **Complete Task Suite**: 18 integrated VS Code tasks for full orchestrator control

#### Stability & Reliability
- **Fixed Window Indexing**: All scripts use consistent :1 window references for tmux base-index 1
- **Claude Environment**: Proper TERM, venv activation, and Node.js warnings suppression
- **Crash Prevention**: Removed tmux queries that caused server crashes
- **Auto-Recovery**: Better error handling and graceful degradation

### 🤖 New Commands

#### PM Management
- `pm-checkin-all.sh` - Comprehensive status check with all team members
- `pm-custom-checkin.sh` - Custom message check-ins for specific situations
- Enhanced agent briefings with communication commands

#### Agent Coordination
- Enhanced `start-orchestrator.sh` with full coordination capabilities
- Updated `deploy-agent.sh` with proper environment setup
- Improved `list-agents.sh` with crash-safe operation

#### VS Code Tasks
- 🎯 Open Orchestrator Agent
- 👔 Open Project Manager Agent
- 🎨 Open Frontend Agent
- ⚙️ Open Backend Agent
- 🧪 Open QA Agent
- 🎭 Open ALL Agent Terminals (simultaneous)
- 👔 PM Check-in with All Agents
- 💬 PM Custom Check-in with All Agents

### 🔧 Technical Improvements

#### tmux-message Enhancements
- Clear existing input with Ctrl+C before sending
- Increased delay from 0.5s to 1.5s for proper Claude registration
- Automatic Enter submission - no manual intervention required

#### Agent Environment Setup
- `TERM=xterm-256color` for proper terminal support
- Python virtual environment activation
- `NODE_NO_WARNINGS=1` and `FORCE_COLOR=1` flags
- Sequential startup with proper delays

#### Window Management
- Consistent `:1` window indexing across all scripts
- Fixed VS Code task window references
- Proper session and window targeting

### 💡 Usage Examples

#### Quick Agent Access
```bash
# VS Code Command Palette (Ctrl+Shift+P)
Tasks: Run Task → "🎭 Open ALL Agent Terminals"
```

#### PM Team Management
```bash
# Standard comprehensive check-in
Tasks: Run Task → "👔 PM Check-in with All Agents"

# Custom check-in for specific situations
Tasks: Run Task → "💬 PM Custom Check-in with All Agents"
```

#### Agent Communication
```bash
# Send message to any agent
tmux-message orchestrator:1 "Priority update: Focus on Neo4j auth issues"
tmux-message corporate-coach-frontend:2 "UI fixes needed for login flow"
```

### 🐛 Bug Fixes
- Fixed agent communication auto-submission
- Resolved tmux window indexing inconsistencies
- Eliminated tmux server crashes from complex queries
- Fixed VS Code task interactive prompt blocking

### 📋 Breaking Changes
- Window references changed from `:0` to `:1` (requires tmux base-index 1)
- Enhanced agent briefings include new communication commands
- tmux-message now auto-submits (no manual Enter required)

### 🎯 Migration Guide
For existing deployments:
1. Update tmux.conf with `set -g base-index 1`
2. Replace all scripts with new versions
3. Update VS Code tasks.json with new task definitions
4. Test agent communication with new auto-submit tmux-message

---

## Previous Versions

### Version 1.0.0 - Initial Release
- Basic tmux orchestrator functionality
- Simple agent deployment scripts
- Manual agent management
