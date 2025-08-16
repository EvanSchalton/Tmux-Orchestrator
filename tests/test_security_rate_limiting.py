"""Test rate limiting functionality for security."""

import asyncio
from unittest.mock import Mock

import pytest

from tmux_orchestrator.utils.exceptions import RateLimitExceededError
from tmux_orchestrator.utils.rate_limiter import (
    RateLimitConfig,
    RateLimiter,
    SlidingWindowRateLimiter,
    rate_limit_decorator,
)


class TestRateLimiter:
    """Test token bucket rate limiter."""

    @pytest.mark.asyncio
    async def test_basic_rate_limiting(self):
        """Test basic rate limiting functionality."""
        config = RateLimitConfig(
            max_requests=5,
            window_seconds=1.0,
            burst_size=2,
            block_on_limit=False,
        )
        limiter = RateLimiter(config)

        # Should allow burst size immediately
        assert await limiter.check_rate_limit("user1") is True
        assert await limiter.check_rate_limit("user1") is True

        # Should be rate limited after burst
        with pytest.raises(RateLimitExceededError):
            await limiter.check_rate_limit("user1")

    @pytest.mark.asyncio
    async def test_multiple_users(self):
        """Test rate limiting tracks different users separately."""
        config = RateLimitConfig(
            max_requests=5,
            window_seconds=1.0,
            burst_size=1,
            block_on_limit=False,
        )
        limiter = RateLimiter(config)

        # User 1 gets limited
        assert await limiter.check_rate_limit("user1") is True
        with pytest.raises(RateLimitExceededError):
            await limiter.check_rate_limit("user1")

        # User 2 should still be allowed
        assert await limiter.check_rate_limit("user2") is True

    @pytest.mark.asyncio
    async def test_blocking_mode(self):
        """Test blocking mode waits for availability."""
        config = RateLimitConfig(
            max_requests=60,
            window_seconds=1.0,
            burst_size=1,
            block_on_limit=True,
        )
        limiter = RateLimiter(config)

        # Use up burst
        assert await limiter.check_rate_limit("user1") is True

        # Should block and eventually succeed
        start_time = asyncio.get_event_loop().time()
        assert await limiter.check_rate_limit("user1") is True
        elapsed = asyncio.get_event_loop().time() - start_time

        # Should have waited some time
        assert elapsed > 0

    @pytest.mark.asyncio
    async def test_quota_tracking(self):
        """Test remaining quota tracking."""
        config = RateLimitConfig(
            max_requests=10,
            window_seconds=60.0,
            burst_size=5,
            block_on_limit=False,
        )
        limiter = RateLimiter(config)

        # Check initial quota
        remaining, reset_time = await limiter.get_remaining_quota("user1")
        assert remaining == 5  # burst size
        assert reset_time == 0.0

        # Use some quota
        await limiter.check_rate_limit("user1")
        await limiter.check_rate_limit("user1")

        remaining, reset_time = await limiter.get_remaining_quota("user1")
        assert remaining == 3

    def test_reset_functionality(self):
        """Test rate limiter reset."""
        config = RateLimitConfig(burst_size=1)
        limiter = RateLimiter(config)

        # Create some buckets
        limiter._buckets["user1"] = Mock()
        limiter._buckets["user2"] = Mock()

        # Reset specific user
        limiter.reset("user1")
        assert "user1" not in limiter._buckets
        assert "user2" in limiter._buckets

        # Reset all
        limiter.reset()
        assert len(limiter._buckets) == 0


class TestSlidingWindowRateLimiter:
    """Test sliding window rate limiter."""

    @pytest.mark.asyncio
    async def test_sliding_window(self):
        """Test sliding window rate limiting."""
        limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=1.0)

        # Should allow up to limit
        assert await limiter.is_allowed("user1") is True
        assert await limiter.is_allowed("user1") is True
        assert await limiter.is_allowed("user1") is True

        # Should block at limit
        assert await limiter.is_allowed("user1") is False

        # Wait for window to slide
        await asyncio.sleep(1.1)

        # Should allow again
        assert await limiter.is_allowed("user1") is True

    @pytest.mark.asyncio
    async def test_request_expiration(self):
        """Test old requests are properly expired."""
        limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=0.5)

        # Make requests
        assert await limiter.is_allowed("user1") is True
        assert await limiter.is_allowed("user1") is True
        assert await limiter.is_allowed("user1") is False

        # Wait for half window
        await asyncio.sleep(0.3)

        # Still at limit
        assert await limiter.is_allowed("user1") is False

        # Wait for full window
        await asyncio.sleep(0.3)

        # Old requests should be expired
        assert await limiter.is_allowed("user1") is True


class TestRateLimitDecorator:
    """Test rate limit decorator."""

    @pytest.mark.asyncio
    async def test_decorator_basic(self):
        """Test basic decorator functionality."""
        call_count = 0

        @rate_limit_decorator(max_requests=2, window_seconds=1.0)
        async def test_function(user_id: str):
            nonlocal call_count
            call_count += 1
            return f"Called for {user_id}"

        # Should allow up to limit
        assert await test_function("user1") == "Called for user1"
        assert await test_function("user1") == "Called for user1"
        assert call_count == 2

        # Should raise on limit
        with pytest.raises(RateLimitExceededError):
            await test_function("user1")
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_decorator_custom_key(self):
        """Test decorator with custom key function."""

        @rate_limit_decorator(max_requests=1, window_seconds=1.0, key_func=lambda x, y: f"{x}-{y}")
        async def test_function(x: str, y: str):
            return f"{x},{y}"

        # Different keys should be independent
        assert await test_function("a", "1") == "a,1"
        assert await test_function("b", "1") == "b,1"
        assert await test_function("a", "2") == "a,2"

        # Same key should be limited
        with pytest.raises(RateLimitExceededError):
            await test_function("a", "1")


@pytest.mark.asyncio
async def test_rate_limiter_thread_safety():
    """Test rate limiter is thread-safe with concurrent access."""
    config = RateLimitConfig(
        max_requests=100,
        window_seconds=1.0,
        burst_size=10,
        block_on_limit=False,
    )
    limiter = RateLimiter(config)

    success_count = 0
    error_count = 0

    async def make_request(user_id: str, request_id: int):
        nonlocal success_count, error_count
        try:
            await limiter.check_rate_limit(user_id)
            success_count += 1
        except RateLimitExceededError:
            error_count += 1

    # Create many concurrent requests
    tasks = []
    for i in range(20):
        tasks.append(make_request("user1", i))

    await asyncio.gather(*tasks)

    # Should have allowed burst_size requests
    assert success_count == 10
    assert error_count == 10
