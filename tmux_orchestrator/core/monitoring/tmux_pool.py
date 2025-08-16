"""TMux connection pooling for high-performance async operations."""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Dict, Optional, Set

from tmux_orchestrator.utils.tmux import TMUXManager


@dataclass
class PooledConnection:
    """Wrapper for a pooled TMUX connection."""

    tmux: TMUXManager
    created_at: float
    last_used: float
    use_count: int = 0

    def is_stale(self, max_age: float = 300) -> bool:
        """Check if connection is stale and should be recycled."""
        return (time.time() - self.created_at) > max_age


class TMuxConnectionPool:
    """Connection pool for TMUX operations with async support.

    This pool manages TMUX connections to prevent overwhelming the TMUX
    server with concurrent operations while maximizing performance.
    """

    def __init__(
        self,
        min_size: int = 5,
        max_size: int = 20,
        connection_timeout: float = 30.0,
        max_connection_age: float = 300.0,
        logger: Optional[logging.Logger] = None,
    ):
        """Initialize the connection pool.

        Args:
            min_size: Minimum number of connections to maintain
            max_size: Maximum number of connections allowed
            connection_timeout: Timeout for acquiring a connection
            max_connection_age: Maximum age before recycling a connection
            logger: Optional logger instance
        """
        self.min_size = min_size
        self.max_size = max_size
        self.connection_timeout = connection_timeout
        self.max_connection_age = max_connection_age
        self.logger = logger or logging.getLogger(__name__)

        # Pool state
        self._pool: asyncio.Queue[PooledConnection] = asyncio.Queue(maxsize=max_size)
        self._semaphore = asyncio.Semaphore(max_size)
        self._active_connections: Set[PooledConnection] = set()
        self._total_created = 0
        self._initialized = False
        self._shutdown = False

        # Metrics
        self.stats = {
            "connections_created": 0,
            "connections_recycled": 0,
            "connections_reused": 0,
            "acquisition_timeouts": 0,
            "total_acquisitions": 0,
        }

    async def initialize(self) -> None:
        """Initialize the pool with minimum connections."""
        if self._initialized:
            return

        self.logger.info(f"Initializing TMux connection pool (min={self.min_size}, max={self.max_size})")

        # Create initial connections
        create_tasks = []
        for _ in range(self.min_size):
            create_tasks.append(self._create_connection())

        connections = await asyncio.gather(*create_tasks, return_exceptions=True)

        # Add successful connections to pool
        for conn in connections:
            if isinstance(conn, PooledConnection):
                await self._pool.put(conn)
            else:
                self.logger.error(f"Failed to create initial connection: {conn}")

        self._initialized = True
        self.logger.info(f"TMux pool initialized with {self._pool.qsize()} connections")

    async def close(self) -> None:
        """Close all connections and shut down the pool."""
        self.logger.info("Shutting down TMux connection pool")
        self._shutdown = True

        # Close all pooled connections
        closed = 0
        while not self._pool.empty():
            try:
                _conn = self._pool.get_nowait()
                # In reality, TMUXManager doesn't need explicit closing
                # but we track it for metrics
                closed += 1
            except asyncio.QueueEmpty:
                break

        self.logger.info(f"Closed {closed} pooled connections")

    @asynccontextmanager
    async def acquire(self):
        """Acquire a connection from the pool.

        This is an async context manager that ensures connections
        are properly returned to the pool after use.

        Yields:
            TMUXManager instance

        Raises:
            asyncio.TimeoutError: If connection cannot be acquired within timeout
        """
        if not self._initialized:
            await self.initialize()

        if self._shutdown:
            raise RuntimeError("Connection pool is shut down")

        conn = None
        start_time = time.time()

        try:
            # Try to get a connection within timeout
            self.stats["total_acquisitions"] += 1

            try:
                conn = await asyncio.wait_for(self._get_connection(), timeout=self.connection_timeout)
            except asyncio.TimeoutError:
                self.stats["acquisition_timeouts"] += 1
                self.logger.error(f"Timeout acquiring connection after {self.connection_timeout}s")
                raise

            # Track active connection
            self._active_connections.add(conn)

            # Update connection usage
            conn.last_used = time.time()
            conn.use_count += 1

            acquisition_time = time.time() - start_time
            if acquisition_time > 1.0:
                self.logger.warning(f"Slow connection acquisition: {acquisition_time:.2f}s")

            # Yield the TMUX manager
            yield conn.tmux

        finally:
            if conn:
                # Return connection to pool
                self._active_connections.discard(conn)

                # Check if connection should be recycled
                if conn.is_stale(self.max_connection_age):
                    self.stats["connections_recycled"] += 1
                    self.logger.debug(f"Recycling stale connection (age: {time.time() - conn.created_at:.0f}s)")
                    # Create a new connection to replace it
                    asyncio.create_task(self._replace_connection())
                else:
                    # Return to pool for reuse
                    self.stats["connections_reused"] += 1
                    try:
                        self._pool.put_nowait(conn)
                    except asyncio.QueueFull:
                        # Pool is full, just discard
                        self.logger.debug("Pool full, discarding connection")

    async def _get_connection(self) -> PooledConnection:
        """Get a connection from the pool or create a new one."""
        # Try to get from pool first
        try:
            conn = self._pool.get_nowait()
            return conn
        except asyncio.QueueEmpty:
            pass

        # Check if we can create a new connection
        async with self._semaphore:
            # Double-check pool (might have been populated while waiting)
            try:
                conn = self._pool.get_nowait()
                return conn
            except asyncio.QueueEmpty:
                pass

            # Create new connection
            if self._total_created < self.max_size:
                return await self._create_connection()
            else:
                # Wait for a connection to be returned
                return await self._pool.get()

    async def _create_connection(self) -> PooledConnection:
        """Create a new pooled connection."""
        # In the real implementation, we might want to create
        # separate TMUX client instances or connection contexts
        tmux = TMUXManager()

        conn = PooledConnection(tmux=tmux, created_at=time.time(), last_used=time.time())

        self._total_created += 1
        self.stats["connections_created"] += 1

        self.logger.debug(f"Created new connection (total: {self._total_created})")
        return conn

    async def _replace_connection(self) -> None:
        """Replace a recycled connection with a new one."""
        try:
            new_conn = await self._create_connection()
            await self._pool.put(new_conn)
        except Exception as e:
            self.logger.error(f"Failed to replace connection: {e}")

    def get_stats(self) -> Dict[str, any]:
        """Get pool statistics."""
        return {
            **self.stats,
            "pool_size": self._pool.qsize(),
            "active_connections": len(self._active_connections),
            "total_created": self._total_created,
        }

    async def health_check(self) -> bool:
        """Check pool health."""
        if not self._initialized or self._shutdown:
            return False

        # Ensure minimum connections
        if self._pool.qsize() < self.min_size:
            deficit = self.min_size - self._pool.qsize()
            self.logger.warning(f"Pool below minimum size, creating {deficit} connections")

            create_tasks = []
            for _ in range(deficit):
                create_tasks.append(self._create_connection())

            connections = await asyncio.gather(*create_tasks, return_exceptions=True)

            for conn in connections:
                if isinstance(conn, PooledConnection):
                    await self._pool.put(conn)

        return True


# Async wrapper for TMUX operations
class AsyncTMUXManager:
    """Async wrapper for TMUX operations using connection pooling."""

    def __init__(self, pool: TMuxConnectionPool):
        """Initialize with a connection pool.

        Args:
            pool: TMux connection pool to use
        """
        self.pool = pool

    async def capture_pane_async(self, target: str, lines: int = 50) -> str:
        """Asynchronously capture pane content.

        Args:
            target: Target pane (session:window)
            lines: Number of lines to capture

        Returns:
            Captured pane content
        """
        async with self.pool.acquire() as tmux:
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, tmux.capture_pane, target, lines)

    async def send_keys_async(self, target: str, keys: str) -> bool:
        """Asynchronously send keys to a pane.

        Args:
            target: Target pane
            keys: Keys to send

        Returns:
            Success status
        """
        async with self.pool.acquire() as tmux:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, tmux.send_keys, target, keys)

    async def list_sessions_async(self) -> list:
        """Asynchronously list TMUX sessions."""
        async with self.pool.acquire() as tmux:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, tmux.list_sessions)

    async def list_windows_async(self, session: str) -> list:
        """Asynchronously list windows in a session."""
        async with self.pool.acquire() as tmux:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, tmux.list_windows, session)
