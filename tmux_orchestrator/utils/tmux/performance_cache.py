"""Performance caching utilities for TMUX operations."""

import logging
import time
from typing import Any, Optional


class PerformanceCache:
    """Handles caching for TMUX operations to improve performance."""

    def __init__(self, cache_ttl: float = 5.0):
        """Initialize performance cache.

        Args:
            cache_ttl: Cache time-to-live in seconds (default 5s)
        """
        self._cache_ttl = cache_ttl
        self._logger = logging.getLogger(__name__)

        # Performance caches
        self._agent_cache: dict[str, Any] = {}
        self._agent_cache_time: float = 0.0
        self._session_cache: dict[str, Any] = {}
        self._session_cache_time: float = 0.0

    @property
    def cache_ttl(self) -> float:
        """Get cache TTL value."""
        return self._cache_ttl

    @cache_ttl.setter
    def cache_ttl(self, value: float) -> None:
        """Set cache TTL value."""
        if value < 0:
            raise ValueError("Cache TTL must be non-negative")
        self._cache_ttl = value

    def get_cached_agents(self) -> Optional[list[dict[str, str]]]:
        """Get cached agent list if still valid.

        Returns:
            Cached agent list or None if cache is invalid/empty
        """
        current_time = time.time()

        if (current_time - self._agent_cache_time) < self._cache_ttl and self._agent_cache:
            self._logger.debug("Using cached agent list")
            agents = self._agent_cache.get("agents", [])
            return agents if isinstance(agents, list) else []

        return None

    def cache_agents(self, agents: list[dict[str, str]]) -> None:
        """Cache agent list with timestamp.

        Args:
            agents: List of agent dictionaries to cache
        """
        self._agent_cache = {"agents": agents}
        self._agent_cache_time = time.time()
        self._logger.debug(f"Cached {len(agents)} agents")

    def get_cached_sessions(self) -> Optional[list[dict[str, Any]]]:
        """Get cached session list if still valid.

        Returns:
            Cached session list or None if cache is invalid/empty
        """
        current_time = time.time()

        if (current_time - self._session_cache_time) < self._cache_ttl and self._session_cache:
            self._logger.debug("Using cached session list")
            sessions = self._session_cache.get("sessions", [])
            return sessions if isinstance(sessions, list) else []

        return None

    def cache_sessions(self, sessions: list[dict[str, Any]]) -> None:
        """Cache session list with timestamp.

        Args:
            sessions: List of session dictionaries to cache
        """
        self._session_cache = {"sessions": sessions}
        self._session_cache_time = time.time()
        self._logger.debug(f"Cached {len(sessions)} sessions")

    def invalidate_agent_cache(self) -> None:
        """Clear the agent cache to force fresh data on next request."""
        self._agent_cache.clear()
        self._agent_cache_time = 0.0
        self._logger.debug("Agent cache invalidated")

    def invalidate_session_cache(self) -> None:
        """Clear the session cache to force fresh data on next request."""
        self._session_cache.clear()
        self._session_cache_time = 0.0
        self._logger.debug("Session cache invalidated")

    def invalidate_all_caches(self) -> None:
        """Clear all caches to force fresh data on next requests."""
        self.invalidate_agent_cache()
        self.invalidate_session_cache()
        self._logger.debug("All caches invalidated")

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        current_time = time.time()

        return {
            "cache_ttl": self._cache_ttl,
            "agent_cache": {
                "size": len(self._agent_cache),
                "age_seconds": current_time - self._agent_cache_time if self._agent_cache_time > 0 else None,
                "is_valid": (current_time - self._agent_cache_time) < self._cache_ttl
                if self._agent_cache_time > 0
                else False,
            },
            "session_cache": {
                "size": len(self._session_cache),
                "age_seconds": current_time - self._session_cache_time if self._session_cache_time > 0 else None,
                "is_valid": (current_time - self._session_cache_time) < self._cache_ttl
                if self._session_cache_time > 0
                else False,
            },
        }

    def is_agent_cache_valid(self) -> bool:
        """Check if agent cache is still valid.

        Returns:
            True if cache is valid and not expired
        """
        if not self._agent_cache or self._agent_cache_time == 0:
            return False

        current_time = time.time()
        return (current_time - self._agent_cache_time) < self._cache_ttl

    def is_session_cache_valid(self) -> bool:
        """Check if session cache is still valid.

        Returns:
            True if cache is valid and not expired
        """
        if not self._session_cache or self._session_cache_time == 0:
            return False

        current_time = time.time()
        return (current_time - self._session_cache_time) < self._cache_ttl

    def warm_up_cache(
        self, agents: Optional[list[dict[str, str]]] = None, sessions: Optional[list[dict[str, Any]]] = None
    ) -> None:
        """Pre-populate caches with data.

        Args:
            agents: Optional agent list to cache
            sessions: Optional session list to cache
        """
        if agents is not None:
            self.cache_agents(agents)

        if sessions is not None:
            self.cache_sessions(sessions)

        self._logger.debug("Cache warm-up completed")

    def get_agent_cache_age(self) -> Optional[float]:
        """Get age of agent cache in seconds.

        Returns:
            Cache age in seconds, or None if cache is empty
        """
        if self._agent_cache_time == 0:
            return None
        return time.time() - self._agent_cache_time

    def get_session_cache_age(self) -> Optional[float]:
        """Get age of session cache in seconds.

        Returns:
            Cache age in seconds, or None if cache is empty
        """
        if self._session_cache_time == 0:
            return None
        return time.time() - self._session_cache_time
