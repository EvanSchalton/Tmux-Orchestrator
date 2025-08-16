"""Async-safe caching layer for monitoring performance optimization."""

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, Generic, Optional, TypeVar

T = TypeVar("T")


class CacheStrategy(Enum):
    """Cache eviction strategies."""

    TTL = "ttl"  # Time-to-live based eviction
    LRU = "lru"  # Least recently used
    LFU = "lfu"  # Least frequently used


@dataclass
class CacheEntry(Generic[T]):
    """Single cache entry with metadata."""

    value: T
    created_at: float
    last_accessed: float
    access_count: int = 1
    ttl: Optional[float] = None

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.ttl is None:
            return False
        return (time.time() - self.created_at) > self.ttl

    def access(self) -> None:
        """Update access metadata."""
        self.last_accessed = time.time()
        self.access_count += 1


class AsyncMonitoringCache:
    """Thread-safe async caching for monitoring data.

    This cache supports multiple eviction strategies and provides
    async-safe operations for high-performance monitoring.
    """

    def __init__(self, default_ttl: float = 30.0, max_size: int = 1000, strategy: CacheStrategy = CacheStrategy.TTL):
        """Initialize the cache.

        Args:
            default_ttl: Default time-to-live for entries in seconds
            max_size: Maximum number of entries
            strategy: Cache eviction strategy
        """
        self.default_ttl = default_ttl
        self.max_size = max_size
        self.strategy = strategy

        # Cache storage
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

        # Metrics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0,
        }

    async def get(self, key: str) -> Optional[T]:
        """Get a value from the cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        async with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self.stats["misses"] += 1
                return None

            if entry.is_expired():
                self.stats["expirations"] += 1
                del self._cache[key]
                return None

            entry.access()
            self.stats["hits"] += 1
            return entry.value

    async def set(self, key: str, value: T, ttl: Optional[float] = None) -> None:
        """Set a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL override
        """
        async with self._lock:
            # Check if we need to evict
            if len(self._cache) >= self.max_size and key not in self._cache:
                await self._evict_one()

            entry = CacheEntry(
                value=value, created_at=time.time(), last_accessed=time.time(), ttl=ttl or self.default_ttl
            )

            self._cache[key] = entry

    async def get_or_compute(self, key: str, compute_fn: Callable[[], Awaitable[T]], ttl: Optional[float] = None) -> T:
        """Get from cache or compute if missing/expired.

        This method ensures the compute function is only called once
        even with concurrent requests for the same key.

        Args:
            key: Cache key
            compute_fn: Async function to compute value if not cached
            ttl: Optional TTL override

        Returns:
            Cached or computed value
        """
        # Fast path - check without lock first
        value = await self.get(key)
        if value is not None:
            return value

        # Slow path - compute with lock
        async with self._lock:
            # Double-check after acquiring lock
            entry = self._cache.get(key)
            if entry and not entry.is_expired():
                entry.access()
                self.stats["hits"] += 1
                return entry.value

        # Compute outside lock to allow concurrency
        value = await compute_fn()

        # Cache the computed value
        await self.set(key, value, ttl)
        return value

    async def delete(self, key: str) -> bool:
        """Delete a key from the cache.

        Args:
            key: Cache key

        Returns:
            True if key was deleted, False if not found
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()

    async def clean_expired(self) -> int:
        """Remove all expired entries.

        Returns:
            Number of entries removed
        """
        async with self._lock:
            expired_keys = [key for key, entry in self._cache.items() if entry.is_expired()]

            for key in expired_keys:
                del self._cache[key]
                self.stats["expirations"] += 1

            return len(expired_keys)

    async def _evict_one(self) -> None:
        """Evict one entry based on the configured strategy."""
        if not self._cache:
            return

        if self.strategy == CacheStrategy.TTL:
            # Evict oldest entry
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].created_at)
        elif self.strategy == CacheStrategy.LRU:
            # Evict least recently used
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].last_accessed)
        elif self.strategy == CacheStrategy.LFU:
            # Evict least frequently used
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].access_count)
        else:
            # Default to oldest
            oldest_key = next(iter(self._cache))

        del self._cache[oldest_key]
        self.stats["evictions"] += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total_requests if total_requests > 0 else 0

        return {
            **self.stats,
            "size": len(self._cache),
            "hit_rate": hit_rate,
            "total_requests": total_requests,
        }

    async def warm_cache(
        self, keys: list[str], compute_fn: Callable[[str], Awaitable[T]], ttl: Optional[float] = None
    ) -> None:
        """Pre-populate cache with multiple keys.

        Args:
            keys: List of keys to warm
            compute_fn: Async function that takes key and returns value
            ttl: Optional TTL override
        """
        tasks = []
        for key in keys:
            task = self.get_or_compute(key, lambda k=key: compute_fn(k), ttl)
            tasks.append(task)

        await asyncio.gather(*tasks, return_exceptions=True)


class LayeredCache:
    """Multi-layer cache with different TTLs for different data types."""

    def __init__(self):
        """Initialize layered cache with predefined layers."""
        self.layers = {
            # Fast-changing data with short TTL
            "pane_content": AsyncMonitoringCache(default_ttl=10.0, max_size=200),
            # Agent status with medium TTL
            "agent_status": AsyncMonitoringCache(default_ttl=30.0, max_size=500),
            # Session info with longer TTL
            "session_info": AsyncMonitoringCache(default_ttl=60.0, max_size=100),
            # Static config with very long TTL
            "config": AsyncMonitoringCache(default_ttl=300.0, max_size=50),
        }

    def get_layer(self, layer_name: str) -> AsyncMonitoringCache:
        """Get a specific cache layer.

        Args:
            layer_name: Name of the cache layer

        Returns:
            Cache layer instance

        Raises:
            KeyError: If layer doesn't exist
        """
        return self.layers[layer_name]

    async def get(self, layer: str, key: str) -> Optional[Any]:
        """Get value from specific layer."""
        return await self.layers[layer].get(key)

    async def set(self, layer: str, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set value in specific layer."""
        await self.layers[layer].set(key, value, ttl)

    async def clear_all(self) -> None:
        """Clear all cache layers."""
        tasks = [cache.clear() for cache in self.layers.values()]
        await asyncio.gather(*tasks)

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all layers."""
        return {name: cache.get_stats() for name, cache in self.layers.items()}


# Decorators for caching
def cached(cache: AsyncMonitoringCache, key_fn: Optional[Callable[..., str]] = None, ttl: Optional[float] = None):
    """Decorator for caching async function results.

    Args:
        cache: Cache instance to use
        key_fn: Function to generate cache key from arguments
        ttl: Optional TTL override
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        async def wrapper(*args, **kwargs) -> T:
            # Generate cache key
            if key_fn:
                key = key_fn(*args, **kwargs)
            else:
                # Simple key generation
                key = f"{func.__name__}:{str(args)}:{str(kwargs)}"

            # Use cache
            return await cache.get_or_compute(key, lambda: func(*args, **kwargs), ttl)

        return wrapper

    return decorator
