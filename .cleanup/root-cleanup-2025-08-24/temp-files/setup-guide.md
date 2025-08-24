# Tmux Orchestrator MCP Setup Guide

**Version**: 1.0
**Date**: 2025-08-19
**Purpose**: Complete setup guide for Claude Code CLI integration with tmux-orchestrator MCP server

---

## 🚀 User Workflow Overview

The intended user workflow for tmux-orchestrator with Claude Code CLI integration:

```bash
# 1. Install package
pip install tmux-orc

# 2. Configure MCP server for Claude Code CLI (CURRENTLY BROKEN)
tmux-orc setup all

# 3. Spawn orchestrator with MCP access
tmux-orc spawn orc

# 4. All spawned agents automatically have MCP server access
```

**Current Problem**: Step 2 (`tmux-orc setup all`) does not properly configure Claude Code CLI's MCP integration.

---

## 🎯 What `tmux-orc setup all` Should Configure

### Primary Objective
The setup command must configure Claude Code CLI to recognize and use the tmux-orchestrator MCP server.

### Required Configuration Steps

#### 1. Claude Code CLI Configuration Directory
```bash
# Create .claude/config/ directory if missing
mkdir -p .claude/config/
```

#### 2. MCP Server Registration
Create/update `.claude/config/mcp.json` with tmux-orchestrator server configuration:

```json
{
  "servers": {
    "tmux-orchestrator": {
      "command": "python",
      "args": ["/absolute/path/to/tmux_orchestrator/mcp_server.py"],
      "env": {
        "TMUX_ORC_MCP_MODE": "true"
      }
    }
  }
}
```

#### 3. Path Resolution
- Detect current installation path of tmux-orchestrator
- Use absolute paths in MCP configuration to ensure reliability
- Handle different installation methods (pip, development install, etc.)

#### 4. Validation
- Test that `claude mcp` shows tmux-orchestrator server
- Verify MCP server file is accessible and executable
- Confirm JSON configuration syntax is valid

---

## 📋 Current vs Required Behavior

### Current Behavior (BROKEN)
```bash
$ tmux-orc setup all
# Currently does: [unknown - needs investigation]
# Result: Claude Code CLI shows "No MCP servers configured"

$ claude mcp
No MCP servers configured
```

### Required Behavior (TARGET)
```bash
$ tmux-orc setup all
✓ Creating Claude Code CLI configuration directory
✓ Configuring MCP server registration
✓ Setting tmux-orchestrator MCP server path
✓ Validating MCP configuration
✓ MCP server setup complete

$ claude mcp
Available MCP servers:
- tmux-orchestrator: configured and running
```

---

## 🔧 Technical Implementation Requirements

### Setup Command Enhancement

The `tmux-orc setup all` command needs to:

1. **Detect Claude Code CLI**
   ```python
   # Check if claude command is available
   import shutil
   if not shutil.which('claude'):
       raise Error("Claude Code CLI not found")
   ```

2. **Locate Tmux-Orchestrator Installation**
   ```python
   # Find MCP server file path
   import tmux_orchestrator
   mcp_server_path = os.path.join(
       os.path.dirname(tmux_orchestrator.__file__),
       'mcp_server.py'
   )
   ```

3. **Create MCP Configuration**
   ```python
   # Create .claude/config/mcp.json
   config = {
       "servers": {
           "tmux-orchestrator": {
               "command": "python",
               "args": [os.path.abspath(mcp_server_path)],
               "env": {"TMUX_ORC_MCP_MODE": "true"}
           }
       }
   }
   ```

4. **Handle Existing Configuration**
   ```python
   # Merge with existing mcp.json if it exists
   # Don't overwrite other MCP servers
   ```

5. **Validate Setup**
   ```python
   # Test configuration works
   # Verify claude mcp shows tmux-orchestrator
   ```

### Claude Code CLI MCP Configuration Format

**File**: `.claude/config/mcp.json`
**Purpose**: Register MCP servers with Claude Code CLI

**Required Structure**:
```json
{
  "servers": {
    "server-name": {
      "command": "executable",
      "args": ["arg1", "arg2"],
      "env": {
        "VAR": "value"
      }
    }
  }
}
```

**For tmux-orchestrator**:
```json
{
  "servers": {
    "tmux-orchestrator": {
      "command": "python",
      "args": ["/workspaces/Tmux-Orchestrator/tmux_orchestrator/mcp_server.py"],
      "env": {
        "TMUX_ORC_MCP_MODE": "true"
      }
    }
  }
}
```

---

## 🧪 Validation and Testing

### Post-Setup Validation Steps

1. **Verify Configuration File**
   ```bash
   # Check file exists
   ls -la .claude/config/mcp.json

   # Validate JSON syntax
   python -c "import json; json.load(open('.claude/config/mcp.json'))"
   ```

2. **Test Claude Code CLI Recognition**
   ```bash
   # Should show tmux-orchestrator server
   claude mcp
   ```

3. **Test MCP Server Accessibility**
   ```bash
   # Verify server file exists and is executable
   ls -la /path/to/tmux_orchestrator/mcp_server.py

   # Test Python import
   python -c "import tmux_orchestrator.mcp_server"
   ```

4. **Test Agent Access**
   ```bash
   # Spawn test agent and verify MCP tools available
   tmux-orc spawn agent test-agent --session test:1
   # Agent should have access to MCP functionality
   ```

### Success Criteria

✅ **Setup Command Works**:
- `tmux-orc setup all` completes without errors
- Creates proper `.claude/config/mcp.json`
- Handles existing configurations gracefully

✅ **Claude Code CLI Integration**:
- `claude mcp` shows tmux-orchestrator server
- Server status shows as "configured" and accessible
- No configuration conflicts with existing setup

✅ **Agent Accessibility**:
- Spawned orchestrators have MCP server access
- All agents inherit MCP configuration
- MCP tools work reliably across sessions

✅ **Persistence**:
- Configuration survives Claude Code CLI restarts
- Setup is idempotent (safe to run multiple times)
- No manual intervention required for new instances

---

## 🔍 Current Implementation Investigation

### Files to Analyze

1. **Setup Command Implementation**
   - Location: `tmux_orchestrator/cli/` (likely)
   - Current `setup all` command functionality
   - Missing MCP configuration logic

2. **MCP Server**
   - Location: `tmux_orchestrator/mcp_server.py`
   - Current implementation and compatibility
   - Required environment variables

3. **CLI Module Structure**
   - Command registration and argument parsing
   - Integration points for MCP setup

### Investigation Tasks

- [ ] Locate current `setup all` command implementation
- [ ] Analyze what setup currently does
- [ ] Identify where to add MCP configuration logic
- [ ] Test current MCP server functionality
- [ ] Document current gaps in Claude Code CLI integration

---

## 🚨 Critical Issues to Address

### 1. Path Resolution
- MCP configuration must use absolute paths
- Handle different installation scenarios (pip vs development)
- Ensure paths work across different environments

### 2. Configuration Merging
- Don't overwrite existing `.claude/config/mcp.json`
- Merge tmux-orchestrator config with existing servers
- Handle malformed existing configurations gracefully

### 3. Validation and Error Handling
- Clear error messages when Claude Code CLI not found
- Validate MCP server file accessibility
- Test configuration after creation

### 4. Cross-Platform Compatibility
- Handle Windows/Linux/macOS path differences
- Account for different Python installation methods
- Ensure configuration works in various environments

---

## 📝 Implementation Plan

### Phase 1: Investigation (CURRENT)
- [x] Document user workflow requirements
- [ ] Analyze current setup command implementation
- [ ] Test current MCP server functionality
- [ ] Identify integration gaps

### Phase 2: Enhancement Design
- [ ] Design MCP configuration logic
- [ ] Plan integration with existing setup command
- [ ] Define validation and error handling

### Phase 3: Implementation
- [ ] Enhance setup command with MCP configuration
- [ ] Add Claude Code CLI integration logic
- [ ] Implement configuration validation

### Phase 4: Testing and Validation
- [ ] Test enhanced setup command
- [ ] Verify agent MCP access
- [ ] Validate persistence across restarts

---

**Next Steps**: Investigate current `tmux-orc setup all` implementation to understand what needs to be enhanced for Claude Code CLI MCP integration.
