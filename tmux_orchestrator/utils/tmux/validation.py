"""Input validation and security checks for TMUX operations."""


class TmuxValidation:
    """Handles input validation and security checks for TMUX operations."""

    @staticmethod
    def validate_input(value: str, field_name: str = "input") -> str:
        """Validate input to prevent command injection vulnerabilities.

        Args:
            value: The input value to validate
            field_name: Name of the field being validated (for error messages)

        Returns:
            The validated input value

        Raises:
            ValueError: If input is invalid or unsafe
        """
        if not isinstance(value, str):
            raise ValueError(f"{field_name} must be string, got {type(value)}")

        # Check for null bytes (can cause issues with subprocess)
        if "\x00" in value:
            raise ValueError(f"{field_name} contains null byte")

        return value

    @staticmethod
    def validate_session_name(session_name: str) -> str:
        """Validate session name for safety and TMUX compatibility.

        Args:
            session_name: The session name to validate

        Returns:
            The validated session name

        Raises:
            ValueError: If session name is invalid
        """
        validated = TmuxValidation.validate_input(session_name, "session_name")

        # Check for empty or whitespace-only names
        if not validated.strip():
            raise ValueError("Session name cannot be empty or whitespace-only")

        # Check for problematic characters that might cause issues with TMUX
        problematic_chars = [":", ";", "&", "|", "<", ">", "(", ")", "{", "}", "[", "]", "$", "`", "\\", '"', "'"]
        for char in problematic_chars:
            if char in validated:
                raise ValueError(f"Session name contains problematic character: {char}")

        return validated

    @staticmethod
    def validate_target(target: str) -> str:
        """Validate TMUX target (session:window format).

        Args:
            target: The target to validate

        Returns:
            The validated target

        Raises:
            ValueError: If target format is invalid
        """
        validated = TmuxValidation.validate_input(target, "target")

        # Basic format check for session:window pattern
        if ":" not in validated:
            raise ValueError("Target must be in 'session:window' format")

        parts = validated.split(":")
        if len(parts) != 2:
            raise ValueError("Target must be in 'session:window' format")

        session_part, window_part = parts
        if not session_part.strip() or not window_part.strip():
            raise ValueError("Session and window parts cannot be empty")

        return validated

    @staticmethod
    def validate_keys(keys: str) -> str:
        """Validate keys to send to TMUX.

        Args:
            keys: The keys string to validate

        Returns:
            The validated keys string

        Raises:
            ValueError: If keys string is invalid
        """
        return TmuxValidation.validate_input(keys, "keys")

    @staticmethod
    def sanitize_window_name(window_name: str) -> str:
        """Sanitize window name for TMUX compatibility.

        Args:
            window_name: The window name to sanitize

        Returns:
            Sanitized window name safe for TMUX use
        """
        validated = TmuxValidation.validate_input(window_name, "window_name")

        # Replace problematic characters with safe alternatives
        sanitized = validated
        replacements = {
            ":": "-",
            ";": "-",
            "&": "and",
            "|": "-",
            "<": "_lt_",
            ">": "_gt_",
            "(": "_",
            ")": "_",
            "{": "_",
            "}": "_",
            "[": "_",
            "]": "_",
            "$": "_",
            "`": "_",
            "\\": "_",
            '"': "_",
            "'": "_",
        }

        for char, replacement in replacements.items():
            sanitized = sanitized.replace(char, replacement)

        # Ensure it's not empty after sanitization
        if not sanitized.strip():
            sanitized = "window"

        return sanitized.strip()
