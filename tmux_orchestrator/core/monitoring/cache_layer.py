"""
Caching layer for monitoring operations with metrics integration.

This module provides caching for frequently accessed data to reduce
TMux command overhead and improve monitoring performance.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .metrics_collector import MetricsCollector


class CacheEntryStatus(Enum):
    """Status of a cache entry."""

    FRESH = "fresh"
    STALE = "stale"
    EXPIRED = "expired"
    INVALID = "invalid"


@dataclass
class CacheEntry:
    """A single cache entry with metadata."""

    key: str
    value: Any
    created_at: float
    last_accessed: float
    access_count: int = 0
    ttl: float = 60.0  # Time to live in seconds
    stale_time: float = 30.0  # Time before considered stale
    tags: list[str] = field(default_factory=list)

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return (time.time() - self.created_at) > self.ttl

    def is_stale(self) -> bool:
        """Check if entry is stale but not expired."""
        age = time.time() - self.created_at
        return age > self.stale_time and age <= self.ttl

    def get_status(self) -> CacheEntryStatus:
        """Get current status of the entry."""
        if self.is_expired():
            return CacheEntryStatus.EXPIRED
        elif self.is_stale():
            return CacheEntryStatus.STALE
        else:
            return CacheEntryStatus.FRESH


class CacheLayer:
    """High-performance caching layer with metrics integration."""

    def __init__(
        self,
        metrics_collector: MetricsCollector | None = None,
        logger: logging.Logger | None = None,
        max_entries: int = 10000,
        default_ttl: float = 60.0,
        cleanup_interval: float = 300.0,
        enable_background_refresh: bool = True,
    ):
        """Initialize the cache layer.

        Args:
            metrics_collector: Optional metrics collector for tracking
            logger: Logger instance
            max_entries: Maximum number of cache entries
            default_ttl: Default time to live for entries
            cleanup_interval: Interval for cleanup tasks
            enable_background_refresh: Enable background refresh of stale entries
        """
        self.metrics = metrics_collector
        self.logger = logger or logging.getLogger(__name__)
        self.max_entries = max_entries
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        self.enable_background_refresh = enable_background_refresh

        # Cache storage
        self._cache: dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

        # Background tasks
        self._cleanup_task: asyncio.Task | None = None
        self._refresh_queue: asyncio.Queue = asyncio.Queue()
        self._refresh_task: asyncio.Task | None = None

        # Cache statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "refreshes": 0,
            "expirations": 0,
        }

    async def initialize(self) -> None:
        """Initialize the cache and start background tasks."""
        self.logger.info(f"Initializing cache layer (max_entries={self.max_entries}, ttl={self.default_ttl})")

        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        # Start refresh task if enabled
        if self.enable_background_refresh:
            self._refresh_task = asyncio.create_task(self._refresh_loop())

        # Record initialization in metrics
        if self.metrics:
            self.metrics.set_gauge("cache.initialized", 1.0)
            self.metrics.set_gauge("cache.max_entries", float(self.max_entries))

    async def cleanup(self) -> None:
        """Clean up cache resources and stop background tasks."""
        self.logger.info("Shutting down cache layer")

        # Cancel background tasks
        for task in [self._cleanup_task, self._refresh_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Clear cache
        async with self._lock:
            self._cache.clear()

        # Update metrics
        if self.metrics:
            self.metrics.set_gauge("cache.initialized", 0.0)

    async def get(self, key: str, refresh_if_stale: bool = True) -> tuple[Any | None, CacheEntryStatus]:
        """Get a value from cache.

        Args:
            key: Cache key
            refresh_if_stale: Queue for refresh if stale

        Returns:
            Tuple of (value, status)
        """
        async with self._lock:
            entry = self._cache.get(key)

            if not entry:
                self.stats["misses"] += 1
                if self.metrics:
                    self.metrics.increment_counter("cache.misses")
                return None, CacheEntryStatus.INVALID

            # Update access metadata
            entry.last_accessed = time.time()
            entry.access_count += 1

            status = entry.get_status()

            if status == CacheEntryStatus.EXPIRED:
                # Remove expired entry
                del self._cache[key]
                self.stats["expirations"] += 1
                if self.metrics:
                    self.metrics.increment_counter("cache.expirations")
                return None, status

            self.stats["hits"] += 1
            if self.metrics:
                self.metrics.increment_counter("cache.hits")

            # Queue for refresh if stale
            if status == CacheEntryStatus.STALE and refresh_if_stale and self.enable_background_refresh:
                await self._refresh_queue.put(key)

            return entry.value, status

    async def set(
        self,
        key: str,
        value: Any,
        ttl: float | None = None,
        stale_time: float | None = None,
        tags: list[str | None] = None,
    ) -> None:
        """Set a value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live (uses default if None)
            stale_time: Time before stale (defaults to ttl/2)
            tags: Optional tags for cache entry
        """
        if ttl is None:
            ttl = self.default_ttl

        if stale_time is None:
            stale_time = ttl / 2

        entry = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            last_accessed=time.time(),
            ttl=ttl,
            stale_time=stale_time,
            tags=tags or [],
        )

        async with self._lock:
            # Check if we need to evict entries
            if len(self._cache) >= self.max_entries:
                await self._evict_lru()

            self._cache[key] = entry

        # Track in metrics
        if self.metrics:
            self.metrics.set_gauge("cache.entries", float(len(self._cache)))
            self.metrics.record_histogram("cache.entry_size", len(str(value)))

    async def invalidate(self, key: str) -> bool:
        """Invalidate a cache entry.

        Args:
            key: Cache key to invalidate

        Returns:
            True if entry was found and removed
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                if self.metrics:
                    self.metrics.increment_counter("cache.invalidations")
                return True
            return False

    async def invalidate_by_tags(self, tags: list[str]) -> int:
        """Invalidate all entries with specified tags.

        Args:
            tags: Tags to match

        Returns:
            Number of entries invalidated
        """
        invalidated = 0

        async with self._lock:
            keys_to_remove = []

            for key, entry in self._cache.items():
                if any(tag in entry.tags for tag in tags):
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del self._cache[key]
                invalidated += 1

        if self.metrics and invalidated > 0:
            self.metrics.increment_counter("cache.tag_invalidations", invalidated)

        return invalidated

    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()

        self.logger.info(f"Cleared {count} cache entries")

        if self.metrics:
            self.metrics.increment_counter("cache.clears")
            self.metrics.set_gauge("cache.entries", 0.0)

    async def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self._cache:
            return

        # Find LRU entry
        lru_key = min(self._cache.keys(), key=lambda k: self._cache[k].last_accessed)

        del self._cache[lru_key]
        self.stats["evictions"] += 1

        if self.metrics:
            self.metrics.increment_counter("cache.evictions")

    async def _cleanup_loop(self) -> None:
        """Background task to clean up expired entries."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_expired()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cache cleanup: {e}")

    async def _cleanup_expired(self) -> None:
        """Remove expired entries from cache."""
        expired_count = 0

        async with self._lock:
            expired_keys = [key for key, entry in self._cache.items() if entry.is_expired()]

            for key in expired_keys:
                del self._cache[key]
                expired_count += 1

        if expired_count > 0:
            self.logger.debug(f"Cleaned up {expired_count} expired cache entries")
            if self.metrics:
                self.metrics.increment_counter("cache.cleanup_expired", expired_count)

    async def _refresh_loop(self) -> None:
        """Background task to refresh stale entries."""
        while True:
            try:
                # Wait for refresh requests
                _key = await self._refresh_queue.get()

                # Note: In a real implementation, this would call
                # the actual refresh function provided during setup
                self.stats["refreshes"] += 1

                if self.metrics:
                    self.metrics.increment_counter("cache.refreshes")

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cache refresh: {e}")

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        hit_rate = 0.0
        total_requests = self.stats["hits"] + self.stats["misses"]
        if total_requests > 0:
            hit_rate = self.stats["hits"] / total_requests

        return {
            **self.stats,
            "entries": len(self._cache),
            "hit_rate": hit_rate,
            "total_requests": total_requests,
            "max_entries": self.max_entries,
        }

    async def warmup(self, keys: list[str], loader_func) -> int:
        """Pre-populate cache with specified keys.

        Args:
            keys: List of keys to pre-load
            loader_func: Async function to load values

        Returns:
            Number of entries loaded
        """
        loaded = 0

        for key in keys:
            try:
                value = await loader_func(key)
                if value is not None:
                    await self.set(key, value)
                    loaded += 1
            except Exception as e:
                self.logger.error(f"Error warming up cache key {key}: {e}")

        self.logger.info(f"Cache warmup complete: loaded {loaded}/{len(keys)} entries")

        if self.metrics:
            self.metrics.increment_counter("cache.warmup_entries", loaded)

        return loaded


class AgentContentCache(CacheLayer):
    """Specialized cache for agent window content."""

    def __init__(self, *args, **kwargs):
        """Initialize agent content cache with appropriate defaults."""
        # Set shorter TTL for agent content
        kwargs.setdefault("default_ttl", 30.0)  # 30 seconds
        kwargs.setdefault("max_entries", 1000)  # Limit entries
        super().__init__(*args, **kwargs)

    def make_key(self, session: str, window: str) -> str:
        """Generate cache key for agent content.

        Args:
            session: Session name
            window: Window index

        Returns:
            Cache key
        """
        return f"agent_content:{session}:{window}"

    async def get_agent_content(self, session: str, window: str) -> tuple[str | None, CacheEntryStatus]:
        """Get cached agent content.

        Args:
            session: Session name
            window: Window index

        Returns:
            Tuple of (content, cache status)
        """
        key = self.make_key(session, window)
        return await self.get(key)

    async def set_agent_content(self, session: str, window: str, content: str, is_idle: bool = False) -> None:
        """Cache agent content.

        Args:
            session: Session name
            window: Window index
            content: Window content
            is_idle: Whether agent is idle (affects TTL)
        """
        key = self.make_key(session, window)

        # Use longer TTL for idle agents
        ttl = 60.0 if is_idle else 30.0

        # Tag with session for bulk invalidation
        tags = [f"session:{session}"]

        await self.set(key, content, ttl=ttl, tags=tags)

    async def invalidate_session(self, session: str) -> int:
        """Invalidate all cache entries for a session.

        Args:
            session: Session name

        Returns:
            Number of entries invalidated
        """
        return await self.invalidate_by_tags([f"session:{session}"])


class TMuxCommandCache(CacheLayer):
    """Specialized cache for TMux command results."""

    def __init__(self, *args, **kwargs):
        """Initialize TMux command cache."""
        # Longer TTL for TMux metadata
        kwargs.setdefault("default_ttl", 300.0)  # 5 minutes
        kwargs.setdefault("max_entries", 500)
        super().__init__(*args, **kwargs)

    async def get_sessions(self) -> tuple[list[dict | None], CacheEntryStatus]:
        """Get cached session list."""
        return await self.get("tmux:sessions")

    async def set_sessions(self, sessions: list[dict]) -> None:
        """Cache session list."""
        await self.set("tmux:sessions", sessions, ttl=60.0)  # Shorter TTL

    async def get_windows(self, session: str) -> tuple[list[dict | None], CacheEntryStatus]:
        """Get cached window list for session."""
        return await self.get(f"tmux:windows:{session}")

    async def set_windows(self, session: str, windows: list[dict]) -> None:
        """Cache window list for session."""
        await self.set(f"tmux:windows:{session}", windows, ttl=60.0, tags=[f"session:{session}"])
