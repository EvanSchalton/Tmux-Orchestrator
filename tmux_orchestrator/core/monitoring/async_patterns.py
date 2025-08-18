"""
Async component patterns and best practices for the monitoring system.

This module provides reusable patterns, base classes, and utilities
for building async components in the monitoring architecture.
"""

import asyncio
import functools
import logging
import time
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Any, Callable, TypeVar

from .interfaces import MonitorComponent

T = TypeVar("T")


class AsyncMonitorComponent(MonitorComponent, ABC):
    """Base class for async monitoring components.

    Provides common patterns for initialization, cleanup, and error handling.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initialized = False
        self._initializing = False
        self._initialization_lock = asyncio.Lock()

    async def initialize_async(self) -> bool:
        """Initialize the component asynchronously.

        Returns:
            True if initialization successful
        """
        async with self._initialization_lock:
            if self._initialized:
                return True

            if self._initializing:
                # Wait for ongoing initialization
                while self._initializing:
                    await asyncio.sleep(0.1)
                return self._initialized

            self._initializing = True

            try:
                success = await self._do_initialize()
                self._initialized = success
                return success
            finally:
                self._initializing = False

    @abstractmethod
    async def _do_initialize(self) -> bool:
        """Perform actual initialization. Override in subclasses.

        Returns:
            True if initialization successful
        """
        pass

    async def cleanup_async(self) -> None:
        """Clean up resources asynchronously."""
        if self._initialized:
            await self._do_cleanup()
            self._initialized = False

    async def _do_cleanup(self) -> None:
        """Perform actual cleanup. Override in subclasses."""
        pass


class AsyncBatchProcessor:
    """Process items in batches for improved performance."""

    def __init__(self, batch_size: int = 10, max_wait_time: float = 0.5, logger: logging.Logger | None = None):
        """Initialize the batch processor.

        Args:
            batch_size: Maximum items per batch
            max_wait_time: Maximum time to wait before processing partial batch
            logger: Optional logger
        """
        self.batch_size = batch_size
        self.max_wait_time = max_wait_time
        self.logger = logger or logging.getLogger(__name__)
        self._queue: asyncio.Queue = asyncio.Queue()
        self._processing_task: asyncio.Task | None = None
        self._shutdown = False

    async def add_item(self, item: Any) -> None:
        """Add an item to be processed.

        Args:
            item: Item to process
        """
        if self._shutdown:
            raise RuntimeError("Batch processor is shut down")

        await self._queue.put(item)

    async def process_batches(self, processor: Callable[[list[Any]], Any]) -> None:
        """Process batches using the provided processor function.

        Args:
            processor: Async function to process a batch of items
        """
        self._processing_task = asyncio.create_task(self._process_loop(processor))

    async def _process_loop(self, processor: Callable[[list[Any]], Any]) -> None:
        """Main processing loop."""
        while not self._shutdown:
            batch = []
            deadline = time.time() + self.max_wait_time

            try:
                # Collect items for batch
                while len(batch) < self.batch_size:
                    timeout = max(0, deadline - time.time())
                    if timeout <= 0:
                        break

                    try:
                        item = await asyncio.wait_for(self._queue.get(), timeout=timeout)
                        batch.append(item)
                    except asyncio.TimeoutError:
                        break

                # Process batch if we have items
                if batch:
                    try:
                        await processor(batch)
                    except Exception as e:
                        self.logger.error(f"Error processing batch: {e}")

            except Exception as e:
                self.logger.error(f"Error in batch processing loop: {e}")
                await asyncio.sleep(1)  # Prevent tight loop on errors

    async def shutdown(self) -> None:
        """Shutdown the batch processor."""
        self._shutdown = True
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass


def with_timeout(timeout: float):
    """Decorator to add timeout to async functions.

    Args:
        timeout: Timeout in seconds
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
            except asyncio.TimeoutError:
                raise TimeoutError(f"{func.__name__} timed out after {timeout}s")

        return wrapper

    return decorator


def with_retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0, exceptions: tuple = (Exception,)):
    """Decorator to add retry logic to async functions.

    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between retries
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        raise

            raise last_exception

        return wrapper

    return decorator


class AsyncCircuitBreaker:
    """Circuit breaker pattern for async operations."""

    def __init__(
        self, failure_threshold: int = 5, recovery_timeout: float = 60.0, expected_exception: type = Exception
    ):
        """Initialize the circuit breaker.

        Args:
            failure_threshold: Failures before opening circuit
            recovery_timeout: Time before attempting to close circuit
            expected_exception: Exception type that triggers the breaker
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self._failure_count = 0
        self._last_failure_time: float | None = None
        self._state = "closed"  # closed, open, half-open

    @property
    def is_open(self) -> bool:
        """Check if circuit is open."""
        if self._state == "open":
            # Check if we should transition to half-open
            if self._last_failure_time and time.time() - self._last_failure_time > self.recovery_timeout:
                self._state = "half-open"
                return False
            return True
        return False

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Call function through circuit breaker.

        Args:
            func: Async function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: If circuit is open
        """
        if self.is_open:
            raise CircuitBreakerOpenError("Circuit breaker is open")

        try:
            result = await func(*args, **kwargs)

            # Success - reset on half-open
            if self._state == "half-open":
                self._state = "closed"
                self._failure_count = 0

            return result

        except self.expected_exception:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._failure_count >= self.failure_threshold:
                self._state = "open"

            raise


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""

    pass


class AsyncResourcePool:
    """Generic async resource pool implementation."""

    def __init__(
        self, factory: Callable[[], Any], min_size: int = 1, max_size: int = 10, logger: logging.Logger | None = None
    ):
        """Initialize the resource pool.

        Args:
            factory: Async factory function to create resources
            min_size: Minimum pool size
            max_size: Maximum pool size
            logger: Optional logger
        """
        self.factory = factory
        self.min_size = min_size
        self.max_size = max_size
        self.logger = logger or logging.getLogger(__name__)

        self._pool: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self._semaphore = asyncio.Semaphore(max_size)
        self._created = 0
        self._shutdown = False

    async def initialize(self) -> None:
        """Initialize the pool with minimum resources."""
        for _ in range(self.min_size):
            resource = await self.factory()
            await self._pool.put(resource)
            self._created += 1

    @asynccontextmanager
    async def acquire(self):
        """Acquire a resource from the pool."""
        if self._shutdown:
            raise RuntimeError("Pool is shut down")

        async with self._semaphore:
            try:
                # Try to get from pool
                resource = self._pool.get_nowait()
            except asyncio.QueueEmpty:
                # Create new resource if under limit
                if self._created < self.max_size:
                    resource = await self.factory()
                    self._created += 1
                else:
                    # Wait for available resource
                    resource = await self._pool.get()

            try:
                yield resource
            finally:
                # Return to pool
                if not self._shutdown:
                    await self._pool.put(resource)

    async def shutdown(self) -> None:
        """Shutdown the pool and clean up resources."""
        self._shutdown = True

        # Drain the pool
        resources = []
        while not self._pool.empty():
            try:
                resources.append(self._pool.get_nowait())
            except asyncio.QueueEmpty:
                break

        # Clean up resources if they have cleanup method
        for resource in resources:
            if hasattr(resource, "cleanup"):
                try:
                    await resource.cleanup()
                except Exception as e:
                    self.logger.error(f"Error cleaning up resource: {e}")


# Example usage patterns
async def example_async_component():
    """Example of using async component patterns."""

    class MyAsyncComponent(AsyncMonitorComponent):
        async def _do_initialize(self) -> bool:
            # Initialize resources
            self.resource_pool = AsyncResourcePool(factory=self._create_connection, min_size=5, max_size=20)
            await self.resource_pool.initialize()
            return True

        async def _create_connection(self):
            # Create some resource
            return {"connection": "dummy"}

        @with_timeout(5.0)
        @with_retry(max_attempts=3, delay=0.5)
        async def fetch_data(self, target: str) -> dict[str, Any]:
            async with self.resource_pool.acquire() as _conn:
                # Use connection to fetch data
                return {"target": target, "data": "example"}

    # Usage
    component = MyAsyncComponent(None, None, logging.getLogger())
    await component.initialize_async()

    try:
        data = await component.fetch_data("test-target")
        print(f"Fetched: {data}")
    finally:
        await component.cleanup_async()
