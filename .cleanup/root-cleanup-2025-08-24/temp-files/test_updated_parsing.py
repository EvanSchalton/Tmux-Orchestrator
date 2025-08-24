#!/usr/bin/env python3
"""Test the updated parsing logic"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tmux_orchestrator.mcp_server import EnhancedCLIToMCPServer

# Test the updated _parse_kwargs_string method
server = EnhancedCLIToMCPServer()

test_cases = [
    # MCP format with commas
    ("action=pm args=[--session, test:0, --briefing, Test PM]", ["--session", "test:0", "--briefing", "Test PM"]),
    # MCP format with quoted items
    (
        'action=agent args=["backend-dev", "mcp-fix:3", "--briefing", "Backend Developer"]',
        ["backend-dev", "mcp-fix:3", "--briefing", "Backend Developer"],
    ),
    # Space-separated format
    ('action=pm args=[--session test:0 --briefing "Test PM"]', ["--session", "test:0", "--briefing", "Test PM"]),
    # Simple args
    ("action=list args=[session-name]", ["session-name"]),
]

print("Testing Updated MCP Argument Parsing")
print("=" * 60)

all_passed = True

for i, (input_str, expected) in enumerate(test_cases, 1):
    print(f"\nTest {i}:")
    print(f"Input: {input_str}")

    result = server._parse_kwargs_string(input_str)

    if isinstance(result, dict) and "error" in result:
        print(f"❌ FAILED: {result['error']}")
        all_passed = False
        continue

    actual = result.get("args", [])
    print(f"Expected: {expected}")
    print(f"Actual:   {actual}")

    if actual == expected:
        print("✅ PASSED")
    else:
        print("❌ FAILED")
        all_passed = False

print("\n" + "=" * 60)
print(f"Result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")

# Test command building
print("\n\nTesting Command Building:")
print("=" * 60)

# Simulate hierarchical tool execution
kwargs = {"action": "pm", "args": ["--session", "test:0", "--briefing", "Test PM"]}
cmd_parts = ["tmux-orc", "spawn", "pm"]

for arg in kwargs.get("args", []):
    cmd_parts.append(str(arg))

final_command = " ".join(cmd_parts)
expected_command = "tmux-orc spawn pm --session test:0 --briefing Test PM"

print(f"Built:    {final_command}")
print(f"Expected: {expected_command}")
print(f"Result:   {'✅ CORRECT' if final_command == expected_command else '❌ INCORRECT'}")
