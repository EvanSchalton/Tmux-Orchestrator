"""Rate limiting utilities for tmux-orchestrator.

Provides configurable rate limiting to prevent resource exhaustion attacks
and ensure fair usage of system resources.
"""

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Callable

from tmux_orchestrator.utils.exceptions import RateLimitExceededError


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    # Maximum requests per window
    max_requests: int = 100
    # Time window in seconds
    window_seconds: float = 60.0
    # Maximum burst size (requests that can be made immediately)
    burst_size: int = 10
    # Whether to block or raise exception when limit exceeded
    block_on_limit: bool = False
    # Custom error message
    error_message: str = "Rate limit exceeded. Please try again later."


class RateLimiter:
    """Token bucket rate limiter implementation.

    Uses a token bucket algorithm to allow burst traffic while maintaining
    an average rate limit. Thread-safe for concurrent access.
    """

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._buckets: dict[str, TokenBucket] = {}
        self._lock = asyncio.Lock()

    async def check_rate_limit(self, key: str) -> bool:
        """Check if request is allowed under rate limit.

        Args:
            key: Identifier for rate limit bucket (e.g., session ID, user ID)

        Returns:
            True if request is allowed, False if rate limited

        Raises:
            RateLimitExceededError: If block_on_limit is False and limit exceeded
        """
        async with self._lock:
            if key not in self._buckets:
                self._buckets[key] = TokenBucket(
                    capacity=self.config.burst_size,
                    refill_rate=self.config.max_requests / self.config.window_seconds,
                )

            bucket = self._buckets[key]
            if bucket.consume(1):
                return True

            if not self.config.block_on_limit:
                raise RateLimitExceededError(self.config.error_message)

            # Block until token is available
            while not bucket.consume(1):
                await asyncio.sleep(0.1)
            return True

    async def get_remaining_quota(self, key: str) -> tuple[int, float]:
        """Get remaining requests and time until reset.

        Args:
            key: Identifier for rate limit bucket

        Returns:
            Tuple of (remaining_requests, seconds_until_reset)
        """
        async with self._lock:
            if key not in self._buckets:
                return (self.config.burst_size, 0.0)

            bucket = self._buckets[key]
            return (int(bucket.tokens), bucket.time_until_refill())

    def reset(self, key: str | None = None) -> None:
        """Reset rate limit counters.

        Args:
            key: Specific key to reset, or None to reset all
        """
        if key:
            self._buckets.pop(key, None)
        else:
            self._buckets.clear()


class TokenBucket:
    """Token bucket implementation for rate limiting."""

    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = time.monotonic()

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from bucket.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens were consumed, False if insufficient tokens
        """
        self._refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_refill

        # Add tokens based on refill rate
        self.tokens = min(self.capacity, self.tokens + (elapsed * self.refill_rate))
        self.last_refill = now

    def time_until_refill(self) -> float:
        """Calculate time until at least one token is available."""
        if self.tokens >= 1:
            return 0.0

        needed = 1 - self.tokens
        return needed / self.refill_rate


class SlidingWindowRateLimiter:
    """Sliding window rate limiter for more precise rate limiting.

    Tracks exact request times within a sliding window for accurate
    rate limit enforcement.
    """

    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def is_allowed(self, key: str) -> bool:
        """Check if request is allowed within rate limit."""
        async with self._lock:
            now = time.time()
            requests = self._requests[key]

            # Remove expired requests
            cutoff = now - self.window_seconds
            while requests and requests[0] < cutoff:
                requests.popleft()

            # Check if under limit
            if len(requests) < self.max_requests:
                requests.append(now)
                return True

            return False


def rate_limit_decorator(
    max_requests: int = 60,
    window_seconds: float = 60.0,
    key_func: Callable[[Any], str] | None = None,
) -> Callable:
    """Decorator for rate limiting async functions.

    Args:
        max_requests: Maximum requests per window
        window_seconds: Time window in seconds
        key_func: Function to extract rate limit key from arguments

    Example:
        @rate_limit_decorator(max_requests=10, window_seconds=60)
        async def api_call(session_id: str):
            ...
    """
    limiter = SlidingWindowRateLimiter(max_requests, window_seconds)

    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            # Extract key for rate limiting
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                # Default: use first argument as key
                key = str(args[0]) if args else "default"

            if not await limiter.is_allowed(key):
                raise RateLimitExceededError(f"Rate limit exceeded: {max_requests} requests per {window_seconds}s")

            return await func(*args, **kwargs)

        return wrapper

    return decorator
