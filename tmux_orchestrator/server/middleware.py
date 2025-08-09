"""Custom middleware for the MCP server."""

import logging
import time
from collections.abc import Awaitable
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware to log request timing and basic info."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Process request with timing."""
        start_time = time.time()

        # Log incoming request
        logging.info(f"Incoming {request.method} {request.url.path}")

        try:
            response = await call_next(request)

            # Calculate processing time
            process_time = time.time() - start_time

            # Add timing header
            response.headers["X-Process-Time"] = str(process_time)

            # Log completion
            logging.info(
                f"Completed {request.method} {request.url.path} "
                f"in {process_time:.4f}s with status {response.status_code}"
            )

            return response

        except Exception as e:
            process_time = time.time() - start_time
            logging.error(f"Error in {request.method} {request.url.path} after {process_time:.4f}s: {str(e)}")
            raise
