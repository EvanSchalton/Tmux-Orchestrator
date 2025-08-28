"""Intelligent terminal content caching for idle detection."""

from pydantic import BaseModel

from tmux_orchestrator.utils.string_utils import efficient_change_score, levenshtein_distance


class TerminalCache(BaseModel):
    """Intelligent terminal content caching for idle detection."""

    early_value: str | None = None
    later_value: str | None = None
    max_distance: int = 10
    use_levenshtein: bool = False  # Toggle between Levenshtein and efficient scoring

    @property
    def status(self) -> str:
        """Get the current idle status based on content changes."""
        if self.early_value is None or self.later_value is None:
            return "unknown"

        if self.match():
            return "continuously_idle"  # No significant changes
        else:
            return "newly_idle"  # Significant changes detected

    def match(self) -> bool:
        """Check if terminal content matches (minimal changes)."""
        if self.early_value is None or self.later_value is None:
            return False

        if self.use_levenshtein:
            # Use proper Levenshtein distance for precise change detection
            distance = levenshtein_distance(self.early_value, self.later_value)
            return distance <= self.max_distance
        else:
            # Use efficient change scoring optimized for terminal content
            score = efficient_change_score(self.early_value, self.later_value)
            return score <= self.max_distance

    def update(self, value: str) -> None:
        """Update cache with new terminal content."""
        self.early_value = self.later_value
        self.later_value = value
