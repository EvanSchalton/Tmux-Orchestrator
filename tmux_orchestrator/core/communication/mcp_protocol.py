"""MCP protocol handler for stdio-based communication with Claude."""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, Callable, Optional

from tmux_orchestrator.utils.exceptions import ValidationError

logger = logging.getLogger(__name__)


@dataclass
class MCPMessage:
    """Represents an MCP protocol message."""

    method: str
    params: dict[str, Any]
    id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {"jsonrpc": "2.0", "method": self.method, "params": self.params}
        if self.id:
            result["id"] = self.id
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MCPMessage":
        """Create from dictionary (JSON deserialization)."""
        return cls(method=data.get("method", ""), params=data.get("params", {}), id=data.get("id"))


@dataclass
class MCPResponse:
    """Represents an MCP protocol response."""

    result: Any
    id: str
    error: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        response = {"jsonrpc": "2.0", "id": self.id}
        if self.error:
            response["error"] = self.error
        else:
            response["result"] = self.result
        return response


class MCPProtocolHandler:
    """Handles MCP protocol communication over stdio."""

    def __init__(self):
        """Initialize the protocol handler."""
        self._handlers: dict[str, Callable] = {}
        self._running = False

    def register_handler(self, method: str, handler: Callable) -> None:
        """Register a handler for a specific MCP method.

        Args:
            method: The MCP method name (e.g., "tools/call")
            handler: Async function to handle the method
        """
        self._handlers[method] = handler
        logger.info(f"Registered handler for method: {method}")

    async def handle_message(self, message: MCPMessage) -> MCPResponse:
        """Handle an incoming MCP message.

        Args:
            message: The MCP message to handle

        Returns:
            MCPResponse with the result or error
        """
        handler = self._handlers.get(message.method)

        if not handler:
            return MCPResponse(
                id=message.id or "unknown",
                result=None,
                error={"code": -32601, "message": f"Method not found: {message.method}"},
            )

        try:
            # Call the handler with the params
            result = await handler(**message.params)
            return MCPResponse(id=message.id or "unknown", result=result)
        except ValidationError as e:
            return MCPResponse(
                id=message.id or "unknown", result=None, error={"code": -32602, "message": f"Invalid params: {str(e)}"}
            )
        except Exception as e:
            logger.error(f"Error handling method {message.method}: {e}")
            return MCPResponse(
                id=message.id or "unknown", result=None, error={"code": -32603, "message": f"Internal error: {str(e)}"}
            )

    async def read_message(self, reader: asyncio.StreamReader) -> Optional[MCPMessage]:
        """Read a single MCP message from stdin.

        Args:
            reader: AsyncIO stream reader

        Returns:
            MCPMessage or None if EOF
        """
        try:
            # Read until we get a complete JSON object
            # MCP messages are typically line-delimited JSON
            line = await reader.readline()
            if not line:
                return None

            data = json.loads(line.decode())
            return MCPMessage.from_dict(data)

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {e}")
            return None
        except Exception as e:
            logger.error(f"Error reading message: {e}")
            return None

    async def write_response(self, writer: asyncio.StreamWriter, response: MCPResponse) -> None:
        """Write an MCP response to stdout.

        Args:
            writer: AsyncIO stream writer
            response: The response to write
        """
        try:
            json_data = json.dumps(response.to_dict())
            writer.write(json_data.encode() + b"\n")
            await writer.drain()
        except Exception as e:
            logger.error(f"Error writing response: {e}")

    async def run_stdio_server(self) -> None:
        """Run the MCP server listening on stdio."""
        reader = asyncio.StreamReader()
        writer = asyncio.StreamWriter(transport=None, protocol=None, reader=None, loop=asyncio.get_event_loop())

        # Connect to stdin/stdout
        await asyncio.get_event_loop().connect_read_pipe(
            lambda: asyncio.StreamReaderProtocol(reader), asyncio.get_event_loop()._stdin
        )

        await asyncio.get_event_loop().connect_write_pipe(
            lambda: asyncio.StreamWriterProtocol(writer), asyncio.get_event_loop()._stdout
        )

        self._running = True
        logger.info("MCP protocol handler started on stdio")

        while self._running:
            message = await self.read_message(reader)
            if message is None:
                break

            response = await self.handle_message(message)
            await self.write_response(writer, response)

        logger.info("MCP protocol handler stopped")

    def stop(self) -> None:
        """Stop the protocol handler."""
        self._running = False
