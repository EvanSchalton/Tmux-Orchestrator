#!/usr/bin/env python3
"""
Test runner for hierarchical MCP structure tests.
"""

import asyncio
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from test_hierarchical_mcp import main  # noqa: E402

if __name__ == "__main__":
    print("🚀 Running Hierarchical MCP Test Suite")
    print("=" * 60)
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
