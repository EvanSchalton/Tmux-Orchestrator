# CLI Reflection MCP Server - Troubleshooting Guide

## 🚀 Fresh Server Deployment Troubleshooting

### **Common Deployment Issues**

#### **Issue 1: Module Import Errors**
**Symptoms**:
```
ModuleNotFoundError: No module named 'mcp'
ImportError: cannot import name 'Server' from 'mcp'
```

**Solutions**:
```bash
# Ensure MCP library is installed
pip install mcp

# If using virtual environment
source .venv/bin/activate
pip install -r requirements.txt

# Verify installation
python -c "import mcp; print(mcp.__version__)"
```

#### **Issue 2: CLI Command Not Found**
**Symptoms**:
```
FileNotFoundError: [Errno 2] No such file or directory: 'tmux-orc'
subprocess.CalledProcessError: Command 'tmux-orc' returned non-zero exit status 127
```

**Solutions**:
```bash
# Ensure tmux-orchestrator is installed
pip install -e .

# Verify CLI is available
which tmux-orc

# If not in PATH, add to PATH or use full path
export PATH="$PATH:$(pwd)/bin"

# Test CLI directly
tmux-orc --version
```

#### **Issue 3: CLI Reflection Fails**
**Symptoms**:
```
CLI reflection failed: Command 'tmux-orc reflect --format json' returned non-zero exit status
JSONDecodeError: Expecting value: line 1 column 1
```

**Solutions**:
```bash
# Test CLI reflection manually
tmux-orc reflect --format json

# Check for error output
tmux-orc reflect --format json 2>&1

# Ensure proper Python environment
python -m tmux_orchestrator.cli reflect --format json

# Debug with verbose output
TMUX_ORC_DEBUG=1 tmux-orc reflect --format json
```

#### **Issue 4: No Tools Generated**
**Symptoms**:
```
Generated MCP Tools: 0
No tools generated! Check CLI availability
```

**Root Causes & Solutions**:

1. **CLI Structure Parsing Issue**
```python
# Debug CLI structure discovery
import subprocess
import json

result = subprocess.run(
    ["tmux-orc", "reflect", "--format", "json"],
    capture_output=True, text=True
)
print(f"Return code: {result.returncode}")
print(f"Stdout: {result.stdout[:200]}")
print(f"Stderr: {result.stderr}")

# Parse and inspect structure
if result.returncode == 0:
    structure = json.loads(result.stdout)
    commands = [k for k, v in structure.items()
                if isinstance(v, dict) and v.get('type') == 'command']
    print(f"Found commands: {commands}")
```

2. **Permission Issues**
```bash
# Check file permissions
ls -la $(which tmux-orc)

# Ensure executable
chmod +x $(which tmux-orc)

# Check Python path issues
python -m tmux_orchestrator.cli --help
```

#### **Issue 5: Tool Execution Failures**
**Symptoms**:
```
Tool execution failed: Command timed out after 60 seconds
subprocess.CalledProcessError: Command returned non-zero exit status
```

**Solutions**:

1. **Timeout Issues**
```python
# Increase timeout in mcp_server_fresh.py
result = subprocess.run(
    cmd_parts,
    capture_output=True,
    text=True,
    timeout=120  # Increase from 60 to 120 seconds
)
```

2. **Command Construction Issues**
```python
# Debug command construction
print(f"Executing command: {' '.join(cmd_parts)}")

# Test command manually
tmux-orc list --json
tmux-orc status --json
```

3. **Working Directory Issues**
```python
# Ensure proper working directory
import os
result = subprocess.run(
    cmd_parts,
    capture_output=True,
    text=True,
    cwd=os.path.expanduser("~"),  # Or project directory
    timeout=60
)
```

### **Server Startup Issues**

#### **Issue 6: MCP Server Won't Start**
**Symptoms**:
```
Server failed: [specific error]
ImportError during server initialization
```

**Diagnostic Steps**:
```bash
# Test server initialization
python -c "
from tmux_orchestrator.mcp_server_fresh import FreshCLIMCPServer
server = FreshCLIMCPServer()
print('Server created successfully')
"

# Test with asyncio
python -c "
import asyncio
from tmux_orchestrator.mcp_server_fresh import FreshCLIMCPServer

async def test():
    server = FreshCLIMCPServer()
    await server.discover_cli_structure()
    tools = server.generate_all_mcp_tools()
    print(f'Generated {len(tools)} tools')

asyncio.run(test())
"
```

#### **Issue 7: STDIO Communication Errors**
**Symptoms**:
```
BrokenPipeError: [Errno 32] Broken pipe
EOFError: EOF when reading a line
```

**Solutions**:
1. **Ensure proper STDIO setup**
```python
# Check for proper async context
async with stdio_server() as (read_stream, write_stream):
    # Server should run here
    pass
```

2. **Buffer and flush issues**
```python
# Ensure output is flushed
sys.stdout.flush()
sys.stderr.flush()
```

### **Legacy Cleanup Issues**

#### **Issue 8: Import Errors After Cleanup**
**Symptoms**:
```
ImportError: cannot import name 'spawn_agent' from 'tmux_orchestrator.mcp.tools.agent_management'
ModuleNotFoundError: No module named 'tmux_orchestrator.mcp.handlers'
```

**Solutions**:
```bash
# Find all imports of removed modules
grep -r "from tmux_orchestrator.mcp" --include="*.py" .
grep -r "import tmux_orchestrator.mcp" --include="*.py" .

# Common files needing updates:
# - tmux_orchestrator/server/__init__.py
# - tests/test_mcp*.py
# - Any custom scripts importing MCP tools
```

#### **Issue 9: Test Failures After Migration**
**Symptoms**:
```
Tests expecting manual MCP tools fail
AttributeError: 'module' object has no attribute 'AgentHandlers'
```

**Solutions**:
1. **Update test imports**
```python
# OLD
from tmux_orchestrator.mcp_server import spawn_agent, send_message

# NEW
from tmux_orchestrator.mcp_server import FreshCLIMCPServer
# Tests should use CLI commands directly or mock MCP server
```

2. **Update test expectations**
```python
# Tests should expect auto-generated tools
# Tool names follow CLI command names with underscores
# e.g., "quick-deploy" becomes "quick_deploy"
```

### **Performance Issues**

#### **Issue 10: Slow Tool Generation**
**Symptoms**:
- Server startup takes >10 seconds
- Tool generation timeout

**Solutions**:
1. **Cache CLI structure**
```python
import pickle
import os

CACHE_FILE = "/tmp/tmux_orc_cli_cache.pkl"
CACHE_DURATION = 300  # 5 minutes

def get_cached_cli_structure():
    if os.path.exists(CACHE_FILE):
        age = time.time() - os.path.getmtime(CACHE_FILE)
        if age < CACHE_DURATION:
            with open(CACHE_FILE, 'rb') as f:
                return pickle.load(f)
    return None
```

2. **Optimize subprocess calls**
```python
# Use shell=False (already doing this)
# Ensure minimal environment
env = {'PATH': os.environ['PATH']}  # Minimal env
```

### **Debugging Techniques**

#### **Enable Debug Logging**
```python
# In mcp_server_fresh.py
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

#### **Trace Command Execution**
```python
# Add verbose command tracing
def _execute_cli_command(self, command_name: str, cli_args: List[str]):
    cmd_parts = ["tmux-orc", command_name] + cli_args
    logger.debug(f"Command parts: {cmd_parts}")
    logger.debug(f"Command line: {' '.join(cmd_parts)}")

    # Log environment
    logger.debug(f"Working directory: {os.getcwd()}")
    logger.debug(f"PATH: {os.environ.get('PATH', 'Not set')}")
```

#### **Test Individual Components**
```bash
# Test CLI discovery
python -c "
from tmux_orchestrator.mcp_server_fresh import FreshCLIMCPServer
import asyncio
server = FreshCLIMCPServer()
structure = asyncio.run(server.discover_cli_structure())
print(f'CLI structure keys: {list(structure.keys())[:5]}')
"

# Test tool generation
python -c "
from tmux_orchestrator.mcp_server_fresh import FreshCLIMCPServer
server = FreshCLIMCPServer()
import asyncio
asyncio.run(server.discover_cli_structure())
tools = server.generate_all_mcp_tools()
print(f'Generated tools: {list(tools.keys())}')
"

# Test argument conversion
python -c "
from tmux_orchestrator.mcp_server_fresh import FreshCLIMCPServer
server = FreshCLIMCPServer()
args = server._convert_arguments_to_cli({
    'args': ['test-session'],
    'options': {'json': True, 'verbose': True}
})
print(f'Converted args: {args}')
"
```

### **Recovery Procedures**

#### **Quick Recovery from Failed Deployment**
```bash
# 1. Restore backup
cp /tmp/mcp_server_backup_*.py tmux_orchestrator/mcp_server.py

# 2. Reinstall dependencies
pip install -e .

# 3. Verify CLI works
tmux-orc --version
tmux-orc list

# 4. Test basic MCP server
python -m tmux_orchestrator.mcp_server --test
```

#### **Clean Slate Recovery**
```bash
# If everything is broken, start fresh
git stash  # Save any uncommitted changes
git checkout main  # Or your working branch
pip install -e .  # Reinstall
python -m pytest tests/test_cli.py  # Verify CLI works
```

### **Health Check Script**
Create `scripts/mcp_health_check.py`:
```python
#!/usr/bin/env python3
"""Health check for CLI reflection MCP server."""

import asyncio
import subprocess
import json
import sys

async def health_check():
    """Comprehensive health check."""
    print("🏥 CLI Reflection MCP Server Health Check\n")

    checks = {
        "CLI Available": check_cli(),
        "CLI Reflection": check_reflection(),
        "MCP Server Import": check_server_import(),
        "Tool Generation": await check_tool_generation(),
        "Command Execution": await check_command_execution()
    }

    print("\n📊 Results:")
    all_passed = True
    for check, result in checks.items():
        status = "✅" if result["success"] else "❌"
        print(f"{status} {check}: {result['message']}")
        if not result["success"]:
            all_passed = False
            if "details" in result:
                print(f"   Details: {result['details']}")

    print(f"\n{'✅ All checks passed!' if all_passed else '❌ Some checks failed!'}")
    return all_passed

def check_cli():
    """Check if CLI is available."""
    try:
        result = subprocess.run(
            ["tmux-orc", "--version"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return {"success": True, "message": f"CLI version: {result.stdout.strip()}"}
        else:
            return {"success": False, "message": "CLI returned error", "details": result.stderr}
    except FileNotFoundError:
        return {"success": False, "message": "tmux-orc not found in PATH"}
    except Exception as e:
        return {"success": False, "message": f"Check failed: {e}"}

def check_reflection():
    """Check if CLI reflection works."""
    try:
        result = subprocess.run(
            ["tmux-orc", "reflect", "--format", "json"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            structure = json.loads(result.stdout)
            commands = [k for k, v in structure.items()
                       if isinstance(v, dict) and v.get('type') == 'command']
            return {"success": True, "message": f"Found {len(commands)} CLI commands"}
        else:
            return {"success": False, "message": "Reflection failed", "details": result.stderr}
    except json.JSONDecodeError:
        return {"success": False, "message": "Invalid JSON from reflection"}
    except Exception as e:
        return {"success": False, "message": f"Check failed: {e}"}

def check_server_import():
    """Check if MCP server can be imported."""
    try:
        from tmux_orchestrator.mcp_server_fresh import FreshCLIMCPServer
        return {"success": True, "message": "Server module imports successfully"}
    except ImportError as e:
        return {"success": False, "message": f"Import failed: {e}"}
    except Exception as e:
        return {"success": False, "message": f"Check failed: {e}"}

async def check_tool_generation():
    """Check if tools can be generated."""
    try:
        from tmux_orchestrator.mcp_server_fresh import FreshCLIMCPServer
        server = FreshCLIMCPServer()
        await server.discover_cli_structure()
        tools = server.generate_all_mcp_tools()
        if tools:
            tool_names = list(tools.keys())[:3]
            return {"success": True, "message": f"Generated {len(tools)} tools (e.g., {', '.join(tool_names)})"}
        else:
            return {"success": False, "message": "No tools generated"}
    except Exception as e:
        return {"success": False, "message": f"Generation failed: {e}"}

async def check_command_execution():
    """Check if commands can be executed."""
    try:
        from tmux_orchestrator.mcp_server_fresh import FreshCLIMCPServer
        server = FreshCLIMCPServer()
        result = await server._execute_cli_command("list", {"options": {"json": True}})
        if result.get("success"):
            return {"success": True, "message": f"Command executed in {result.get('execution_time', 0):.2f}s"}
        else:
            return {"success": False, "message": "Command failed", "details": result.get("error")}
    except Exception as e:
        return {"success": False, "message": f"Execution failed: {e}"}

if __name__ == "__main__":
    success = asyncio.run(health_check())
    sys.exit(0 if success else 1)
```

## 🚀 Quick Reference Card

### **Deployment Checklist**
```bash
# 1. Backup old server
cp tmux_orchestrator/mcp_server.py /tmp/backup_mcp_server.py

# 2. Deploy fresh server
cp tmux_orchestrator/mcp_server_fresh.py tmux_orchestrator/mcp_server.py

# 3. Test server
python -m tmux_orchestrator.mcp_server

# 4. Run health check
python scripts/mcp_health_check.py
```

### **Common Fixes**
- **Import Error**: `pip install mcp`
- **CLI Not Found**: `pip install -e .`
- **No Tools**: Check `tmux-orc reflect --format json`
- **Timeout**: Increase timeout in subprocess calls
- **Test Failures**: Update imports to use FreshCLIMCPServer

### **Support Contacts**
- Architecture questions: Refer to `cli-reflection-mcp-architecture.md`
- CLI enhancement: See `cli-enhancement-patterns.md`
- Legacy cleanup: Check `LEGACY-CLEANUP-PLAN.md`

This troubleshooting guide should help the team quickly resolve any issues during the fresh server deployment.
