"""Test input sanitization functionality for security."""

import pytest

from tmux_orchestrator.utils.exceptions import ValidationError
from tmux_orchestrator.utils.input_sanitizer import (
    sanitize_input,
    sanitize_message,
    sanitize_path,
    sanitize_session_name,
    sanitize_target,
    sanitize_window_name,
    validate_agent_type,
    validate_integer_range,
    validate_team_type,
)


class TestSessionNameSanitization:
    """Test session name sanitization."""

    def test_valid_session_names(self):
        """Test valid session names pass through."""
        valid_names = [
            "my-project",
            "test_session",
            "project.dev",
            "session123",
            "a",
            "Project-Name_2.0",
        ]

        for name in valid_names:
            assert sanitize_session_name(name) == name

    def test_invalid_session_names(self):
        """Test invalid session names are rejected."""
        invalid_names = [
            "",  # Empty
            "session with spaces",  # Spaces
            "session$with$special",  # Special chars
            "session;with;semicolon",  # Semicolon
            "session|with|pipe",  # Pipe
            "a" * 65,  # Too long
            ".hidden",  # Starts with dot
            "0",  # Special tmux name
            "-",  # Special tmux name
            "=",  # Special tmux name
        ]

        for name in invalid_names:
            with pytest.raises(ValidationError):
                sanitize_session_name(name)


class TestWindowNameSanitization:
    """Test window name sanitization."""

    def test_valid_window_names(self):
        """Test valid window names pass through."""
        valid_names = [
            "Claude-pm",
            "Agent Window",
            "test_window",
            "window-123",
            "Backend Dev",
        ]

        for name in valid_names:
            assert sanitize_window_name(name) == name

    def test_invalid_window_names(self):
        """Test invalid window names are rejected."""
        invalid_names = [
            "",  # Empty
            "window$with$special",  # Special chars
            "window;with;semicolon",  # Semicolon
            "a" * 65,  # Too long
        ]

        for name in invalid_names:
            with pytest.raises(ValidationError):
                sanitize_window_name(name)


class TestTargetSanitization:
    """Test target string sanitization."""

    def test_valid_targets(self):
        """Test valid targets pass through."""
        valid_targets = [
            "session:0",
            "my-project:5",
            "test_session:123",
            "all",  # Special case
        ]

        for target in valid_targets:
            assert sanitize_target(target) == target.lower() if target == "all" else target

    def test_invalid_targets(self):
        """Test invalid targets are rejected."""
        invalid_targets = [
            "",  # Empty
            "session",  # Missing window
            "session:",  # Missing window number
            "session:abc",  # Non-numeric window
            "session:-1",  # Negative window
            "session:1000",  # Too large window
            "bad$session:0",  # Invalid session
            "session with space:0",  # Space in session
        ]

        for target in invalid_targets:
            with pytest.raises(ValidationError):
                sanitize_target(target)


class TestMessageSanitization:
    """Test message content sanitization."""

    def test_valid_messages(self):
        """Test valid messages pass through."""
        valid_messages = [
            "Hello world",
            "This is a test message with numbers 123",
            "Multi-line\nmessage\nwith\nbreaks",
            "Special chars: !@#%^&*()+=[]{}|\\:;\"'<>?,./",
        ]

        for message in valid_messages:
            # Should not raise and should return cleaned content
            result = sanitize_message(message)
            assert isinstance(result, str)
            assert len(result) > 0

    def test_dangerous_messages(self):
        """Test dangerous messages are rejected or cleaned."""
        dangerous_messages = [
            "",  # Empty
            "Message with `command injection`",
            "Message with $(command substitution)",
            "Message with ${variable expansion}",
            "a" * 10001,  # Too long
            "Message with \x1b[31mANSI\x1b[0m codes",
            "Message with \0 null bytes",
        ]

        for message in dangerous_messages:
            if message == "":
                with pytest.raises(ValidationError):
                    sanitize_message(message)
            elif "injection" in message or "substitution" in message or "expansion" in message:
                with pytest.raises(ValidationError):
                    sanitize_message(message)
            elif len(message) > 10000:
                with pytest.raises(ValidationError):
                    sanitize_message(message)
            else:
                # Should clean but not fail
                result = sanitize_message(message)
                assert "\x1b" not in result  # ANSI removed
                assert "\0" not in result  # Null bytes removed


class TestPathSanitization:
    """Test path sanitization."""

    def test_valid_paths(self):
        """Test valid paths are accepted."""
        valid_paths = [
            "/workspaces/project",
            "./relative/path",
            "simple_file.txt",
            "/home/user/documents",
        ]

        for path in valid_paths:
            result = sanitize_path(path)
            assert isinstance(result, str)

    def test_dangerous_paths(self):
        """Test dangerous paths are rejected."""
        dangerous_paths = [
            "",  # Empty
            "../../../etc/passwd",  # Directory traversal
            "/etc/passwd",  # System file
            "/etc/shadow",  # System file
            "/.ssh/id_rsa",  # SSH key
            "/.aws/credentials",  # AWS credentials
            "/private/var/log",  # Private directory
            "a" * 1025,  # Too long
        ]

        for path in dangerous_paths:
            with pytest.raises(ValidationError):
                sanitize_path(path)


class TestAgentTypeValidation:
    """Test agent type validation."""

    def test_valid_agent_types(self):
        """Test valid agent types are accepted."""
        valid_types = [
            "pm",
            "project-manager",
            "developer",
            "dev",
            "backend",
            "frontend",
            "qa",
            "qa-engineer",
            "tester",
            "devops",
            "ops",
            "reviewer",
            "code-reviewer",
            "researcher",
            "research",
            "docs",
            "documentation",
            "writer",
            "orchestrator",
            "orc",
        ]

        for agent_type in valid_types:
            result = validate_agent_type(agent_type)
            assert result == agent_type.lower()

    def test_invalid_agent_types(self):
        """Test invalid agent types are rejected."""
        invalid_types = [
            "hacker",
            "admin",
            "root",
            "system",
            "unknown-type",
        ]

        for agent_type in invalid_types:
            with pytest.raises(ValidationError):
                validate_agent_type(agent_type)


class TestTeamTypeValidation:
    """Test team type validation."""

    def test_valid_team_types(self):
        """Test valid team types are accepted."""
        valid_types = ["frontend", "backend", "fullstack", "testing"]

        for team_type in valid_types:
            result = validate_team_type(team_type)
            assert result == team_type.lower()

    def test_invalid_team_types(self):
        """Test invalid team types are rejected."""
        invalid_types = ["invalid", "hack", "admin"]

        for team_type in invalid_types:
            with pytest.raises(ValidationError):
                validate_team_type(team_type)


class TestIntegerRangeValidation:
    """Test integer range validation."""

    def test_valid_integers(self):
        """Test valid integers in range are accepted."""
        assert validate_integer_range(5, 1, 10, "test") == 5
        assert validate_integer_range("5", 1, 10, "test") == 5
        assert validate_integer_range(1, 1, 10, "test") == 1
        assert validate_integer_range(10, 1, 10, "test") == 10

    def test_invalid_integers(self):
        """Test invalid integers are rejected."""
        with pytest.raises(ValidationError):
            validate_integer_range(0, 1, 10, "test")  # Below range

        with pytest.raises(ValidationError):
            validate_integer_range(11, 1, 10, "test")  # Above range

        with pytest.raises(ValidationError):
            validate_integer_range("abc", 1, 10, "test")  # Not a number

        with pytest.raises(ValidationError):
            validate_integer_range(None, 1, 10, "test")  # None


class TestGenericSanitization:
    """Test generic sanitize_input function."""

    def test_dispatching(self):
        """Test that generic function dispatches correctly."""
        assert sanitize_input("test-session", "session") == "test-session"
        assert sanitize_input("test-window", "window") == "test-window"
        assert sanitize_input("session:0", "target") == "session:0"
        assert sanitize_input("Hello world", "message") == "Hello world"

    def test_unknown_type(self):
        """Test unknown input type raises error."""
        with pytest.raises(ValidationError):
            sanitize_input("value", "unknown_type")


class TestSecurityBypass:
    """Test security bypass attempts."""

    def test_null_byte_injection(self):
        """Test null byte injection attempts are blocked."""
        with pytest.raises(ValidationError):
            sanitize_session_name("test\x00session")

        # Message sanitizer should remove null bytes
        result = sanitize_message("test\x00message")
        assert "\x00" not in result

    def test_unicode_normalization(self):
        """Test unicode normalization attacks."""
        # These should be handled by basic validation
        dangerous_unicode = [
            "test\u202esession",  # Right-to-left override
            "test\ufeff session",  # Zero-width no-break space
        ]

        for dangerous in dangerous_unicode:
            with pytest.raises(ValidationError):
                sanitize_session_name(dangerous)

    def test_length_limits(self):
        """Test length limits prevent DoS attacks."""
        # Session name too long
        with pytest.raises(ValidationError):
            sanitize_session_name("a" * 65)

        # Message too long
        with pytest.raises(ValidationError):
            sanitize_message("a" * 10001)

        # Path too long
        with pytest.raises(ValidationError):
            sanitize_path("a" * 1025)
