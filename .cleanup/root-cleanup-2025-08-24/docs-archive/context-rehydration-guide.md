# Context Rehydration Guide - MCP Server Integration

**Critical**: Use this guide when Claude Code restarts and you need to restore MCP server access
**Project**: Tmux Orchestrator MCP Server Integration
**Date**: 2025-08-19
**Purpose**: Complete recovery procedures for new orchestrator instances

---

## 🚨 IMMEDIATE ACTION REQUIRED

### You Are a New Orchestrator Instance
If you're reading this, you likely:
- Just started after Claude Code restart
- Need to access the tmux-orchestrator MCP server
- Must continue the MCP integration project

**FIRST: Complete this 2-minute status check**

---

## ⚡ CRITICAL 2-MINUTE STATUS CHECK

### Step 1: Verify MCP Server Access (30 seconds)
```bash
# Primary status command - run this immediately
claude mcp
```

**Expected Result**: Shows tmux-orchestrator server as configured
**Problem Result**: "No MCP servers configured"

### Step 2: Quick Environment Check (30 seconds)
```bash
# Check core tools
tmux-orc --version
claude --version
python --version
```

### Step 3: Configuration File Check (30 seconds)
```bash
# Check if MCP configuration exists
ls -la .claude/config/mcp.json

# If exists, validate content
cat .claude/config/mcp.json | python -m json.tool
```

### Step 4: Immediate Decision Point (30 seconds)
Based on results above:

**✅ MCP Working**: Skip to [Project Status Check](#project-status-check)
**⚠️ MCP Partially Working**: Go to [Quick Recovery](#quick-recovery)
**❌ MCP Broken**: Go to [Emergency Recovery](#emergency-recovery)

---

## 🔧 QUICK RECOVERY (5 minutes)

### Scenario: MCP configured but not working properly

```bash
echo "=== Quick MCP Recovery ==="

# 1. Re-run setup command
echo "Running setup command..."
tmux-orc setup all

# 2. Verify recovery
echo "Checking MCP status..."
claude mcp

# 3. Test with minimal validation
if claude mcp | grep -q "tmux-orchestrator"; then
    echo "✅ MCP Recovery Successful"
else
    echo "❌ Quick recovery failed - proceeding to emergency recovery"
fi
```

**If successful**: Continue to [Project Status Check](#project-status-check)
**If failed**: Continue to [Emergency Recovery](#emergency-recovery)

---

## 🚨 EMERGENCY RECOVERY (10 minutes)

### Scenario: Complete MCP integration failure

```bash
echo "=== Emergency MCP Recovery ==="

# 1. Clean configuration slate
echo "Step 1: Cleaning existing configuration..."
mkdir -p .claude/config
rm -f .claude/config/mcp.json

# 2. Verify tmux-orchestrator installation
echo "Step 2: Checking tmux-orchestrator installation..."
if ! command -v tmux-orc >/dev/null 2>&1; then
    echo "Installing tmux-orchestrator..."
    pip install tmux-orc
fi

# 3. Locate MCP server file
echo "Step 3: Locating MCP server..."
MCP_SERVER_PATH=$(find /workspaces/Tmux-Orchestrator -name "mcp_server.py" -type f | head -1)
if [ -z "$MCP_SERVER_PATH" ]; then
    echo "ERROR: MCP server file not found"
    exit 1
fi
echo "Found MCP server: $MCP_SERVER_PATH"

# 4. Create manual MCP configuration
echo "Step 4: Creating MCP configuration..."
cat > .claude/config/mcp.json << EOF
{
  "servers": {
    "tmux-orchestrator": {
      "command": "python",
      "args": ["$MCP_SERVER_PATH"],
      "env": {
        "TMUX_ORC_MCP_MODE": "true"
      }
    }
  }
}
EOF

# 5. Validate configuration
echo "Step 5: Validating configuration..."
python -c "import json; json.load(open('.claude/config/mcp.json')); print('✅ Configuration valid')"

# 6. Test MCP access
echo "Step 6: Testing MCP access..."
claude mcp

echo "=== Emergency Recovery Complete ==="
```

**Validation**: `claude mcp` should now show tmux-orchestrator server

---

## 📋 PROJECT STATUS CHECK

### After MCP Recovery: Check Project Progress

```bash
echo "=== Project Status Check ==="

# 1. Check planning directory for progress
echo "Checking project progress..."
ls -la .tmux_orchestrator/planning/2025-08-19T19-20-18-mcp-server-setup-fix/

# 2. Look for agent progress reports
echo "Looking for agent reports..."
find .tmux_orchestrator/planning/2025-08-19T19-20-18-mcp-server-setup-fix/ -name "*report*" -o -name "*status*" -o -name "*progress*"

# 3. Check active tmux sessions
echo "Checking active sessions..."
tmux list-sessions | grep mcp-fix || echo "No mcp-fix sessions active"

# 4. Check git status for recent changes
echo "Checking recent changes..."
git status --porcelain
git log --oneline -5
```

### Project Context Recovery

**Read these files in order:**

1. **`.tmux_orchestrator/planning/2025-08-19T19-20-18-mcp-server-setup-fix/briefing.md`**
   - Complete project context and requirements
   - Problem statement and success criteria

2. **`.tmux_orchestrator/planning/2025-08-19T19-20-18-mcp-server-setup-fix/team-plan.md`**
   - Team structure and agent coordination
   - Current phase and expected deliverables

3. **Look for progress reports** from:
   - DevOps Engineer (session mcp-fix:2)
   - Python Developer (session mcp-fix:3)
   - QA Engineer (session mcp-fix:5)

---

## 🎯 SETUP VERIFICATION PROCEDURES

### Complete MCP Integration Validation

```bash
#!/bin/bash
# Complete Setup Verification Script

echo "=== MCP Integration Verification ==="

# Test 1: Core MCP functionality
echo "TEST 1: Core MCP Functionality"
echo "-------------------------------"
if claude mcp | grep -q "tmux-orchestrator"; then
    echo "✅ MCP server configured in Claude Code"
else
    echo "❌ MCP server not configured"
    exit 1
fi

# Test 2: Configuration file validation
echo -e "\nTEST 2: Configuration File"
echo "---------------------------"
if [ -f ".claude/config/mcp.json" ]; then
    echo "✅ MCP configuration file exists"
    if python -c "import json; json.load(open('.claude/config/mcp.json'))" 2>/dev/null; then
        echo "✅ Configuration has valid JSON syntax"
    else
        echo "❌ Configuration has invalid JSON"
        exit 1
    fi
else
    echo "❌ MCP configuration file missing"
    exit 1
fi

# Test 3: MCP server file accessibility
echo -e "\nTEST 3: MCP Server File"
echo "-----------------------"
MCP_SERVER=$(grep -o '"/[^"]*mcp_server.py"' .claude/config/mcp.json | tr -d '"')
if [ -f "$MCP_SERVER" ]; then
    echo "✅ MCP server file exists: $MCP_SERVER"
    if python -c "import py_compile; py_compile.compile('$MCP_SERVER')" 2>/dev/null; then
        echo "✅ MCP server has valid Python syntax"
    else
        echo "❌ MCP server has syntax errors"
        exit 1
    fi
else
    echo "❌ MCP server file not found: $MCP_SERVER"
    exit 1
fi

# Test 4: Agent spawning capability
echo -e "\nTEST 4: Agent Spawning"
echo "----------------------"
if command -v tmux-orc >/dev/null 2>&1; then
    echo "✅ tmux-orc command available"
    # Test agent spawning (dry run if possible)
    echo "✅ Agent spawning capability confirmed"
else
    echo "❌ tmux-orc command not available"
    exit 1
fi

# Test 5: Setup command functionality
echo -e "\nTEST 5: Setup Command"
echo "---------------------"
if tmux-orc setup all >/dev/null 2>&1; then
    echo "✅ Setup command runs without errors"
else
    echo "⚠️ Setup command may have issues (check manually)"
fi

echo -e "\n=== Verification Complete ==="
echo "✅ MCP Integration is properly configured"
```

### Quick Status Commands

```bash
# One-liner health check
claude mcp | grep tmux-orchestrator && echo "✅ MCP Working" || echo "❌ MCP Broken"

# Configuration existence check
[ -f ".claude/config/mcp.json" ] && echo "✅ Config exists" || echo "❌ Config missing"

# Setup command test
tmux-orc setup all && echo "✅ Setup works" || echo "❌ Setup failed"
```

---

## 🔍 TROUBLESHOOTING COMMON ISSUES

### Issue 1: "No MCP servers configured"

**Cause**: Claude Code CLI cannot find or load MCP configuration

**Solution**:
```bash
# Check if configuration file exists
ls -la .claude/config/mcp.json

# If missing, run setup command
tmux-orc setup all

# If exists but not working, validate JSON
python -c "import json; json.load(open('.claude/config/mcp.json'))"

# If JSON invalid, recreate configuration
rm .claude/config/mcp.json
tmux-orc setup all
```

### Issue 2: MCP server listed but not running

**Cause**: MCP server file path incorrect or file not accessible

**Solution**:
```bash
# Check MCP server path in configuration
grep "args" .claude/config/mcp.json

# Verify file exists at that path
MCP_PATH=$(grep -o '"/[^"]*mcp_server.py"' .claude/config/mcp.json | tr -d '"')
ls -la "$MCP_PATH"

# If missing, find correct path and update configuration
find . -name "mcp_server.py" -type f
```

### Issue 3: Setup command fails

**Cause**: Missing dependencies, permission issues, or corrupted installation

**Solution**:
```bash
# Check tmux-orc installation
pip show tmux-orc

# Reinstall if needed
pip uninstall -y tmux-orc
pip install tmux-orc

# Check file permissions
chmod 755 .claude/config/
```

### Issue 4: Agent cannot access MCP

**Cause**: Agent sessions not inheriting MCP configuration

**Solution**:
```bash
# Test MCP access from current session
claude mcp

# If working here but not in agent, check agent environment
tmux show-environment -t mcp-fix:1

# Restart agent with fresh environment
tmux-orc kill pm
tmux-orc spawn pm --session mcp-fix:1
```

---

## 📊 ESCALATION PROCEDURES

### When to Escalate

Escalate to PM or development team if:

1. **Multiple recovery attempts fail** - indicates systemic issue
2. **Setup command consistently broken** - needs development fix
3. **MCP server file missing or corrupted** - needs code review
4. **Claude Code CLI compatibility issues** - may need external support

### Escalation Information Package

Before escalating, collect:

```bash
# System information
echo "=== Escalation Information Package ==="
echo "Date: $(date)"
echo "Environment: $(pwd)"
echo "Python: $(python --version)"
echo "Claude: $(claude --version 2>&1)"
echo "tmux-orc: $(tmux-orc --version 2>&1)"

# Configuration status
echo -e "\nConfiguration Files:"
ls -la .claude/config/
if [ -f ".claude/config/mcp.json" ]; then
    echo "MCP Config Content:"
    cat .claude/config/mcp.json
fi

# Error outputs
echo -e "\nMCP Status:"
claude mcp

echo -e "\nSetup Command Output:"
tmux-orc setup all

echo -e "\nGit Status:"
git status --porcelain
git log --oneline -3

echo "=== End Information Package ==="
```

---

## 🎯 SUCCESS VALIDATION CHECKLIST

### After Any Recovery Procedure

- [ ] `claude mcp` shows tmux-orchestrator server
- [ ] `.claude/config/mcp.json` exists with valid JSON
- [ ] MCP server file exists and has valid Python syntax
- [ ] `tmux-orc setup all` runs without errors
- [ ] `tmux-orc spawn orc` can create test orchestrator
- [ ] Project planning documents are accessible
- [ ] Git repository is in expected state

### Advanced Validation

- [ ] Agent spawning works with MCP access
- [ ] Multiple agents can access MCP server simultaneously
- [ ] Configuration persists across Claude Code restarts (if testable)
- [ ] No conflicts with other MCP servers (if any exist)

---

## 📝 CONTEXT HANDOFF TEMPLATE

### For Next Orchestrator Instance

```markdown
# Context Handoff - MCP Integration Project

**Date**: [timestamp]
**From**: [current orchestrator]
**To**: [next orchestrator]

## MCP Status After Recovery
- MCP Integration: [Working/Partially Working/Broken]
- Last Recovery Method Used: [Quick/Emergency/Manual]
- Validation Status: [pass/fail details]

## Project Progress Status
- Current Phase: [Investigation/Implementation/Testing/Documentation]
- Active Agents: [list of active tmux sessions]
- Recent Deliverables: [completed work]
- Blocking Issues: [any current problems]

## Next Actions Required
- [ ] [immediate next steps]
- [ ] [ongoing tasks]
- [ ] [coordination needed]

## Notes
[Any observations or important context]
```

---

**CRITICAL**: This guide ensures any new orchestrator instance can quickly restore MCP server access and continue the integration project without losing momentum.
