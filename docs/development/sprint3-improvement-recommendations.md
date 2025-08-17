# Sprint 3 Code Improvement Recommendations

**Date**: 2025-08-17
**Reviewer**: Code Reviewer
**Purpose**: Quality enhancement roadmap for production readiness
**Based on**: Sprint 2 code review findings

## 🛡️ 1. ERROR HANDLING GAPS

### Critical Fixes Required 🔴

#### server.py - Missing Exception Handling
```python
# CURRENT (lines 60-65):
@server.command()
def status():
    from tmux_orchestrator.utils.claude_config import get_registration_status
    status_info = get_registration_status()  # ❌ No error handling

# REQUIRED:
@server.command()
@click.option('--json', 'json_output', is_flag=True, help='Output in JSON format')
def status(json_output: bool) -> None:
    try:
        from tmux_orchestrator.utils.claude_config import get_registration_status
        status_info = get_registration_status()
    except ImportError as e:
        error_msg = "Configuration utilities not available. Ensure tmux-orchestrator is properly installed."
        if json_output:
            click.echo(json.dumps({"success": False, "error": error_msg, "details": str(e)}))
        else:
            console.print(f"[red]❌ {error_msg}[/red]")
        return
    except Exception as e:
        error_msg = f"Failed to check status: {type(e).__name__}"
        if json_output:
            click.echo(json.dumps({"success": False, "error": error_msg, "details": str(e)}))
        else:
            console.print(f"[red]❌ {error_msg}: {e}[/red]")
        return
```

#### CLI Commands - Timeout Handling
```python
# ADD to all subprocess calls:
try:
    result = subprocess.run(
        ["tmux", "command"],
        capture_output=True,
        text=True,
        timeout=30  # ✅ Prevent hanging
    )
except subprocess.TimeoutExpired:
    logger.error("Command timed out after 30 seconds")
    raise CommandTimeoutError("Operation timed out")
```

### Comprehensive Error Categories 🟡

#### 1. Tmux Not Installed
```python
def check_tmux_installed() -> bool:
    """Verify tmux is installed and accessible."""
    try:
        result = subprocess.run(["tmux", "-V"], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except FileNotFoundError:
        console.print("[red]❌ tmux is not installed[/red]")
        console.print("[yellow]Install tmux:[/yellow]")
        console.print("  macOS: brew install tmux")
        console.print("  Ubuntu: sudo apt-get install tmux")
        console.print("  Fedora: sudo dnf install tmux")
        return False
```

#### 2. Permission Errors
```python
def handle_permission_error(e: PermissionError, path: Path) -> None:
    """Provide helpful guidance for permission errors."""
    console.print(f"[red]❌ Permission denied: {path}[/red]")
    if path.is_relative_to(Path.home()):
        console.print("[yellow]This appears to be in your home directory.[/yellow]")
        console.print(f"Try: chmod 755 {path.parent}")
    else:
        console.print("[yellow]This may require elevated permissions.[/yellow]")
        console.print(f"Try: sudo chown $USER {path}")
```

#### 3. Network/Process Communication
```python
def safe_send_message(session: str, message: str) -> bool:
    """Send message with comprehensive error handling."""
    try:
        # Validate session exists first
        if not tmux.has_session(session):
            raise SessionNotFoundError(f"Session '{session}' does not exist")

        # Send with timeout
        result = tmux.send_message(session, message, timeout=10)
        return result

    except SessionNotFoundError:
        console.print(f"[red]Session '{session}' not found[/red]")
        console.print("[yellow]List active sessions: tmux-orc list[/yellow]")
        return False
    except TimeoutError:
        console.print("[red]Message delivery timed out[/red]")
        console.print("[yellow]The agent may be unresponsive. Try: tmux-orc agent restart {session}[/yellow]")
        return False
```

## 🧪 2. TEST COVERAGE NEEDS

### Current Coverage Gaps 🔍

#### Priority 1: Core Operations Testing
```python
# tests/test_core_operations.py
import pytest
from tmux_orchestrator.core.agent_operations import spawn_agent, kill_agent

class TestAgentOperations:
    """Test critical agent operations."""

    def test_spawn_agent_success(self, mock_tmux):
        """Test successful agent spawn."""
        result = spawn_agent(mock_tmux, "test-session", "pm")
        assert result.success
        assert result.session_name == "test-session"

    def test_spawn_agent_session_exists(self, mock_tmux):
        """Test spawn with existing session."""
        mock_tmux.has_session.return_value = True
        with pytest.raises(SessionExistsError):
            spawn_agent(mock_tmux, "existing-session", "pm")

    def test_kill_agent_not_found(self, mock_tmux):
        """Test killing non-existent agent."""
        mock_tmux.has_session.return_value = False
        result = kill_agent(mock_tmux, "ghost-session:0")
        assert not result.success
        assert "not found" in result.message
```

#### Priority 2: CLI Command Testing
```python
# tests/test_cli_commands.py
from click.testing import CliRunner
from tmux_orchestrator.cli import cli

class TestCLICommands:
    """Test CLI command interfaces."""

    def test_server_start_test_mode(self):
        """Test server start in test mode."""
        runner = CliRunner()
        result = runner.invoke(cli, ['server', 'start', '--test'])
        assert result.exit_code == 0
        assert '"status": "ready"' in result.output

    def test_list_json_output(self):
        """Test list command JSON output."""
        runner = CliRunner()
        result = runner.invoke(cli, ['list', '--json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)

    @pytest.mark.parametrize("command,args", [
        ("list", []),
        ("status", []),
        ("reflect", ["--format", "json"]),
    ])
    def test_command_help(self, command, args):
        """Test help text for all commands."""
        runner = CliRunner()
        result = runner.invoke(cli, [command, "--help"] + args)
        assert result.exit_code == 0
        assert "Show help" in result.output or "Usage:" in result.output
```

#### Priority 3: Cross-Platform Testing
```python
# tests/test_cross_platform.py
import platform
import pytest
from tmux_orchestrator.cli.setup_claude import detect_claude_executable

class TestCrossPlatform:
    """Test cross-platform compatibility."""

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows only")
    def test_windows_claude_detection(self, mock_windows_env):
        """Test Claude detection on Windows."""
        mock_windows_env["LOCALAPPDATA"] = "C:\\Users\\Test\\AppData\\Local"
        result = detect_claude_executable()
        assert result is None or "Claude.exe" in str(result)

    @pytest.mark.skipif(platform.system() != "Darwin", reason="macOS only")
    def test_macos_claude_detection(self):
        """Test Claude detection on macOS."""
        result = detect_claude_executable()
        expected_paths = [
            "/Applications/Claude.app",
            Path.home() / "Applications/Claude.app"
        ]
        # Test checks expected paths

    @pytest.mark.parametrize("system,expected_config_path", [
        ("Windows", "%APPDATA%\\Claude"),
        ("Darwin", "~/Library/Application Support/Claude"),
        ("Linux", "~/.config/Claude"),
    ])
    def test_config_path_detection(self, system, expected_config_path):
        """Test configuration path detection across platforms."""
        # Mock platform.system() and verify correct path
```

### Test Infrastructure Needs

#### 1. Mock TMux Manager
```python
# tests/fixtures/tmux_fixtures.py
@pytest.fixture
def mock_tmux():
    """Provide mock TMux manager for testing."""
    mock = Mock(spec=TMUXManager)
    mock.has_session.return_value = False
    mock.list_sessions.return_value = []
    mock.send_message.return_value = True
    return mock
```

#### 2. Async Test Support
```python
# tests/test_mcp_server.py
import pytest
import asyncio
from tmux_orchestrator.mcp_server import FreshCLIToMCPServer

@pytest.mark.asyncio
async def test_mcp_tool_discovery():
    """Test MCP tool discovery."""
    server = FreshCLIToMCPServer()
    await server.discover_cli_structure()
    assert len(server.cli_commands) > 0
    assert "list" in server.cli_commands
```

#### 3. Integration Test Suite
```python
# tests/integration/test_end_to_end.py
class TestEndToEnd:
    """Full workflow integration tests."""

    def test_complete_agent_lifecycle(self, real_tmux):
        """Test spawn -> message -> kill lifecycle."""
        # 1. Spawn agent
        result = subprocess.run(["tmux-orc", "spawn", "pm", "--session", "test"])
        assert result.returncode == 0

        # 2. Send message
        result = subprocess.run(["tmux-orc", "agent", "send", "test:0", "Hello"])
        assert result.returncode == 0

        # 3. Kill agent
        result = subprocess.run(["tmux-orc", "agent", "kill", "test:0"])
        assert result.returncode == 0
```

## 📚 3. DOCUMENTATION IMPROVEMENTS

### Code Documentation Gaps

#### 1. Missing Module Docstrings
```python
# tmux_orchestrator/core/__init__.py
"""Core functionality for tmux orchestrator operations.

This module provides the foundational operations for managing tmux
sessions, spawning agents, and coordinating inter-agent communication.

Modules:
    agent_operations: Agent lifecycle management
    communication: Inter-agent messaging
    session_management: Tmux session control

Example:
    from tmux_orchestrator.core import spawn_agent

    result = spawn_agent(tmux_manager, "my-session", "pm")
    if result.success:
        print(f"Agent spawned in {result.session_name}")
"""
```

#### 2. Complex Function Documentation
```python
def deploy_team_optimized(
    tmux: TMUXManager,
    team_type: str,
    size: int,
    project_name: str,
    custom_config: dict[str, Any] | None = None
) -> tuple[bool, str]:
    """Deploy an optimized team configuration with role distribution.

    Creates a tmux session with multiple windows, each running a
    specialized Claude agent. Team composition is optimized based
    on team type and size.

    Args:
        tmux: TMUXManager instance for session control
        team_type: Type of team ('frontend', 'backend', 'fullstack', 'testing')
        size: Number of agents (2-8 recommended)
        project_name: Name for the tmux session
        custom_config: Optional configuration overrides
            - 'roles': List of specific roles to deploy
            - 'pm_context': Additional context for PM
            - 'skip_briefing': Skip initial briefing

    Returns:
        Tuple of (success: bool, message: str)
        - success: True if all agents deployed successfully
        - message: Success message or error description

    Raises:
        ValueError: If team_type is invalid or size out of range
        SessionExistsError: If session already exists

    Example:
        >>> success, msg = deploy_team_optimized(tmux, "frontend", 3, "my-app")
        >>> print(msg)
        "Successfully deployed frontend team with 3 agents"

    Notes:
        - PM is always deployed in window 0
        - Team composition varies by size (see team_compositions)
        - Each agent receives role-specific briefing
    """
```

### User Documentation Enhancements

#### 1. Troubleshooting Guide
```markdown
# docs/troubleshooting.md

## Common Issues and Solutions

### tmux-orc: command not found
**Problem**: CLI not available after installation
**Solutions**:
1. Ensure pip install completed: `pip show tmux-orchestrator`
2. Check PATH: `echo $PATH`
3. Reinstall: `pip install --force-reinstall tmux-orchestrator`

### MCP Server Not Connecting to Claude
**Problem**: Claude Desktop doesn't see MCP tools
**Solutions**:
1. Check registration: `tmux-orc server status`
2. Restart Claude Desktop
3. Verify config: `cat ~/.config/Claude/claude_desktop_config.json`
4. Re-register: `tmux-orc setup mcp --force`

### Agent Not Responding
**Problem**: Agent appears stuck or unresponsive
**Solutions**:
1. Check agent status: `tmux-orc agent info session:window`
2. View agent output: `tmux attach -t session:window`
3. Restart agent: `tmux-orc agent restart session:window`
4. Check logs: `tmux-orc daemon logs`
```

#### 2. Quick Reference Card
```markdown
# docs/quick-reference.md

## Essential Commands

### Agent Management
| Command | Description | Example |
|---------|-------------|---------|
| `list` | Show all agents | `tmux-orc list --json` |
| `spawn pm` | Create PM | `tmux-orc spawn pm --session project` |
| `agent send` | Message agent | `tmux-orc agent send project:0 "Status?"` |
| `agent restart` | Restart agent | `tmux-orc agent restart project:1` |

### Team Operations
| Command | Description | Example |
|---------|-------------|---------|
| `quick-deploy` | Fast team setup | `tmux-orc quick-deploy frontend 3` |
| `team status` | Team overview | `tmux-orc team status project` |
| `team broadcast` | Message all | `tmux-orc team broadcast project "Update"` |

### MCP/Claude Integration
| Command | Description | Example |
|---------|-------------|---------|
| `server start` | Start MCP | `tmux-orc server start` |
| `server status` | Check setup | `tmux-orc server status` |
| `setup claude-code` | Full setup | `tmux-orc setup claude-code` |
```

#### 3. API Reference Documentation
```python
# Generate from code using sphinx or similar
# docs/api/index.md

## Core API Reference

### tmux_orchestrator.core

#### spawn_agent
```python
spawn_agent(tmux: TMUXManager, session: str, agent_type: str) -> SpawnResult
```
Spawn a new Claude agent in specified session.

**Parameters:**
- `tmux`: TMUXManager instance
- `session`: Target session name
- `agent_type`: Agent type ('pm', 'dev', 'qa', etc.)

**Returns:**
- `SpawnResult` with success status and details

**Raises:**
- `SessionExistsError`: If session already exists
- `TMUXError`: If tmux operation fails
```

### Architecture Diagrams
```mermaid
# docs/architecture/system-overview.md

graph TB
    CLI[CLI Commands] --> Core[Core Operations]
    Core --> TMux[TMux Manager]
    Core --> MCP[MCP Server]

    TMux --> Sessions[Tmux Sessions]
    Sessions --> Agents[Claude Agents]

    MCP --> Claude[Claude Desktop]
    Claude --> Tools[MCP Tools]

    Monitor[Monitoring Daemon] --> Sessions
    Monitor --> Recovery[Auto Recovery]
```

## 📊 Priority Matrix

### Must Fix Before Release 🔴
1. Error handling in server.py status command
2. JSON standardization across all commands
3. Timeout handling for subprocess calls
4. Basic test suite (>60% coverage)

### Should Improve 🟡
1. Complete type annotations
2. Comprehensive error messages
3. Module docstrings
4. Quick reference documentation

### Nice to Have 🔵
1. 80%+ test coverage
2. API reference generation
3. Video tutorials
4. Performance benchmarks

---

**Sprint 3 Focus**: Production hardening through comprehensive error handling, essential test coverage, and user-facing documentation improvements.
