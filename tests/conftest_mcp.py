"""
Shared configuration and mocks for MCP tests.
"""

import sys
from typing import Any, Callable, Dict, Optional
from unittest.mock import MagicMock

# Mock FastMCP modules for in-memory testing (avoid conflicts with pytest module imports)
# Don't mock 'mcp' namespace to avoid conflicts with test file imports


# Create a mock FastMCP class
class MockFastMCP:
    def __init__(self, name: str) -> None:
        self.name = name
        self.tools: Dict[str, Any] = {}

    def tool(self, name: Optional[str] = None, description: Optional[str] = None) -> Callable[[Any], Any]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            tool_name = name or func.__name__
            self.tools[tool_name] = func
            return func

        return decorator

    async def run_stdio_async(self) -> None:
        pass


# Mock the fastmcp module
mock_fastmcp = MagicMock()
mock_fastmcp.FastMCP = MockFastMCP
sys.modules["fastmcp"] = mock_fastmcp
sys.modules["fastmcp.server"] = MagicMock()

# Now we can import the MCP server without actual dependencies

# Import the actual classes from the main module for testing
try:
    from tmux_orchestrator.mcp_server import EnhancedCLIToMCPServer, MCPAutoGenerator
except ImportError:
    # If import fails, create mock versions
    EnhancedCLIToMCPServer = MagicMock()
    MCPAutoGenerator = MagicMock()


# Create a mock EnhancedHierarchicalSchema for backward compatibility
class EnhancedHierarchicalSchema:
    """Mock schema class for testing."""

    pass
