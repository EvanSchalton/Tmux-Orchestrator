"""Async processing utilities for heavy CLI operations."""

import asyncio
import functools
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class AsyncCLIProcessor:
    """Async wrapper for heavy CLI operations to prevent blocking."""

    def __init__(self, max_workers: int = 4):
        """Initialize async processor.

        Args:
            max_workers: Maximum number of concurrent operations
        """
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._background_tasks: Dict[str, asyncio.Task] = {}

    async def run_heavy_operation_async(
        self, operation: Callable, *args, timeout: float = 30.0, task_id: Optional[str] = None, **kwargs
    ) -> Any:
        """Run a heavy operation asynchronously.

        Args:
            operation: Function to run
            timeout: Operation timeout in seconds
            task_id: Optional task identifier for tracking
            *args, **kwargs: Arguments for the operation

        Returns:
            Operation result
        """
        loop = asyncio.get_event_loop()

        try:
            # Run in thread pool to avoid blocking event loop
            result = await asyncio.wait_for(
                loop.run_in_executor(self.executor, operation, *args, **kwargs), timeout=timeout
            )

            logger.debug(f"Async operation completed: {operation.__name__}")
            return result

        except asyncio.TimeoutError:
            logger.error(f"Async operation timed out after {timeout}s: {operation.__name__}")
            raise
        except Exception as e:
            logger.error(f"Async operation failed: {operation.__name__}: {e}")
            raise

    def run_background_task(self, operation: Callable, task_id: str, *args, **kwargs) -> None:
        """Start a background task that runs without blocking.

        Args:
            operation: Function to run
            task_id: Unique task identifier
            *args, **kwargs: Arguments for the operation
        """
        if task_id in self._background_tasks:
            logger.warning(f"Background task {task_id} already running")
            return

        async def background_wrapper():
            try:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(self.executor, operation, *args, **kwargs)
                logger.info(f"Background task completed: {task_id}")
                return result
            except Exception as e:
                logger.error(f"Background task failed: {task_id}: {e}")
            finally:
                # Clean up task reference
                if task_id in self._background_tasks:
                    del self._background_tasks[task_id]

        # Create and store task
        task = asyncio.create_task(background_wrapper())
        self._background_tasks[task_id] = task

    def get_background_task_status(self, task_id: str) -> dict[str, Any]:
        """Get status of a background task.

        Args:
            task_id: Task identifier

        Returns:
            Task status information
        """
        if task_id not in self._background_tasks:
            return {"status": "not_found", "exists": False}

        task = self._background_tasks[task_id]

        if task.done():
            try:
                result = task.result()
                return {"status": "completed", "exists": True, "result": result, "exception": None}
            except Exception as e:
                return {"status": "failed", "exists": True, "result": None, "exception": str(e)}
        else:
            return {"status": "running", "exists": True, "result": None, "exception": None}

    async def batch_process_async(
        self,
        operations: list[Callable],
        args_list: list[tuple],
        batch_size: int = 5,
        timeout_per_operation: float = 10.0,
    ) -> list[Any]:
        """Process multiple operations in parallel batches.

        Args:
            operations: List of functions to run
            args_list: List of argument tuples for each operation
            batch_size: Number of operations to run concurrently
            timeout_per_operation: Timeout for each operation

        Returns:
            List of results in same order as operations
        """
        results = []

        # Process in batches to avoid overwhelming the system
        for i in range(0, len(operations), batch_size):
            batch_ops = operations[i : i + batch_size]
            batch_args = args_list[i : i + batch_size]

            # Create tasks for this batch
            tasks = []
            for op, args in zip(batch_ops, batch_args):
                task = self.run_heavy_operation_async(op, *args, timeout=timeout_per_operation)
                tasks.append(task)

            # Wait for batch completion
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            results.extend(batch_results)

        return results

    def cleanup(self) -> None:
        """Clean up resources."""
        # Cancel any running background tasks
        for task_id, task in self._background_tasks.items():
            if not task.done():
                task.cancel()
                logger.info(f"Cancelled background task: {task_id}")

        self._background_tasks.clear()

        # Shutdown executor
        self.executor.shutdown(wait=True)


def async_cli_wrapper(timeout: float = 30.0):
    """Decorator to make CLI operations async-ready.

    Args:
        timeout: Operation timeout in seconds
    """

    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            processor = AsyncCLIProcessor()
            try:
                return await processor.run_heavy_operation_async(func, *args, timeout=timeout, **kwargs)
            finally:
                processor.cleanup()

        return async_wrapper

    return decorator


# Global async processor instance for CLI operations
_global_processor: Optional[AsyncCLIProcessor] = None


def get_global_async_processor() -> AsyncCLIProcessor:
    """Get or create global async processor."""
    global _global_processor
    if _global_processor is None:
        _global_processor = AsyncCLIProcessor()
    return _global_processor


def cleanup_global_processor() -> None:
    """Clean up global processor."""
    global _global_processor
    if _global_processor:
        _global_processor.cleanup()
        _global_processor = None


# Example async-ready operations for heavy CLI commands
@async_cli_wrapper(timeout=60.0)
def async_team_status_operation(tmux_manager, session_name: str) -> dict[str, Any]:
    """Async wrapper for team status operations."""
    # This would wrap the actual team status logic
    return {"session": session_name, "status": "completed"}


@async_cli_wrapper(timeout=45.0)
def async_agent_discovery_operation(tmux_manager) -> list[dict[str, str]]:
    """Async wrapper for agent discovery operations."""
    # This would wrap heavy agent discovery logic
    return tmux_manager.list_agents_ultra_optimized()
