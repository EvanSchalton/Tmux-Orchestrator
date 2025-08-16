"""Custom exceptions for tmux-orchestrator."""


class TmuxOrchestratorError(Exception):
    """Base exception for all tmux-orchestrator errors."""

    pass


class RateLimitExceededError(TmuxOrchestratorError):
    """Raised when rate limit is exceeded."""

    pass


class ValidationError(TmuxOrchestratorError):
    """Raised when input validation fails."""

    pass


class SecurityError(TmuxOrchestratorError):
    """Raised when a security violation is detected."""

    pass
