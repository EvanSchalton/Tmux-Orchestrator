"""
Shared configuration and mocks for MCP tests.
"""

import sys
from unittest.mock import MagicMock

# Mock MCP and FastMCP modules for in-memory testing
sys.modules["mcp"] = MagicMock()
sys.modules["mcp.server"] = MagicMock()
sys.modules["mcp.server.Server"] = MagicMock()


# Create a mock FastMCP class
class MockFastMCP:
    def __init__(self, name):
        self.name = name
        self.tools = {}

    def tool(self, name=None, description=None):
        def decorator(func):
            tool_name = name or func.__name__
            self.tools[tool_name] = func
            return func

        return decorator

    async def run_stdio_async(self):
        pass


# Mock the fastmcp module
mock_fastmcp = MagicMock()
mock_fastmcp.FastMCP = MockFastMCP
sys.modules["fastmcp"] = mock_fastmcp
sys.modules["fastmcp.server"] = MagicMock()

# Now we can import the MCP server without actual dependencies
