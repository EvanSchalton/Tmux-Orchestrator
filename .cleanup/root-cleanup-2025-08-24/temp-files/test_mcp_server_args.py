#!/usr/bin/env python3
"""Test MCP server argument handling directly"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tmux_orchestrator.mcp_server import EnhancedCLIToMCPServer

# Test the _parse_kwargs_string method directly
server = EnhancedCLIToMCPServer()

test_cases = [
    # Test case 1: spawn pm command with proper args
    {
        "input": "action=pm args=[--session, test:0, --briefing, Test PM]",
        "expected_args": ["--session", "test:0", "--briefing", "Test PM"],
        "description": "Spawn PM with session and briefing",
    },
    # Test case 2: spawn agent command
    {
        "input": 'action=agent args=["backend-dev", "mcp-fix:3", "--briefing", "Backend Developer"]',
        "expected_args": ["backend-dev", "mcp-fix:3", "--briefing", "Backend Developer"],
        "description": "Spawn agent with role and target",
    },
    # Test case 3: Simple args without quotes
    {
        "input": "action=list args=[session-name]",
        "expected_args": ["session-name"],
        "description": "Simple positional argument",
    },
    # Test case 4: Args with CLI options
    {
        "input": "action=deploy args=[--extend, Additional context here]",
        "expected_args": ["--extend", "Additional", "context", "here"],
        "description": "CLI options without quotes",
    },
]

print("Testing MCP Server Argument Parsing")
print("=" * 60)

all_passed = True

for i, test in enumerate(test_cases, 1):
    print(f"\nTest {i}: {test['description']}")
    print(f"Input: {test['input']}")

    result = server._parse_kwargs_string(test["input"])

    if isinstance(result, dict) and "error" in result:
        print(f"❌ FAILED: Parse error - {result['error']}")
        all_passed = False
        continue

    actual_args = result.get("args", [])
    expected_args = test["expected_args"]

    print(f"Expected args: {expected_args}")
    print(f"Actual args: {actual_args}")

    if actual_args == expected_args:
        print("✅ PASSED")
    else:
        print("❌ FAILED")
        all_passed = False

        # Show the difference
        print("Differences:")
        for j, (exp, act) in enumerate(zip(expected_args, actual_args)):
            if exp != act:
                print(f"  Position {j}: expected '{exp}', got '{act}'")

print("\n" + "=" * 60)
print(f"Overall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")

# Now test the actual command execution
print("\n\nTesting Actual Command Building:")
print("=" * 60)

# Simulate what happens in the hierarchical tool function
test_kwargs = {"action": "pm", "args": ["--session", "test:0", "--briefing", "Test PM"]}

cmd_parts = ["tmux-orc", "spawn", "pm"]

# This is how the code builds the command
args = test_kwargs.get("args", [])
if args:
    for arg in args:
        cmd_parts.append(str(arg))

print(f"Built command: {' '.join(cmd_parts)}")
print("Expected: tmux-orc spawn pm --session test:0 --briefing Test PM")

if " ".join(cmd_parts) == "tmux-orc spawn pm --session test:0 --briefing Test PM":
    print("✅ Command building is correct")
else:
    print("❌ Command building is incorrect")
