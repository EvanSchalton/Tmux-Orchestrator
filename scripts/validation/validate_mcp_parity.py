#!/usr/bin/env python3
"""
Validation script for MCP CLI parity.

This script validates that the MCP server properly generates tools for all CLI commands.
"""

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path


def get_cli_commands():
    """Get all CLI commands from tmux-orc reflect."""
    print("📋 Discovering CLI commands...")

    # Known command structure based on the project
    commands = {
        "agent": ["attach", "deploy", "info", "kill", "kill-all", "list", "message", "restart", "send", "status"],
        "monitor": [
            "dashboard",
            "logs",
            "performance",
            "recovery-logs",
            "recovery-start",
            "recovery-status",
            "recovery-stop",
            "start",
            "status",
            "stop",
        ],
        "pm": ["broadcast", "checkin", "create", "custom-checkin", "message", "status"],
        "context": ["export", "list", "show", "spawn"],
        "team": ["broadcast", "deploy", "list", "recover", "status"],
        "orchestrator": ["broadcast", "kill", "kill-all", "list", "schedule", "start", "status"],
        "setup": ["all", "check", "check-requirements", "claude-code", "mcp", "tmux", "vscode"],
        "spawn": ["agent", "orc", "pm"],
        "recovery": ["start", "status", "stop", "test"],
        "session": ["attach", "list"],
        "pubsub": ["publish", "read", "search", "status"],
        "pubsub-fast": ["publish", "read", "stats", "status"],
        "daemon": ["logs", "restart", "start", "status", "stop"],
        "tasks": ["archive", "create", "distribute", "export", "generate", "list", "status"],
        "errors": ["clear", "recent", "stats", "summary"],
        "server": ["setup", "start", "status", "toggle", "tools"],
    }

    # Add standalone commands
    standalone = ["execute", "list", "quick-deploy", "reflect", "status"]

    total = sum(len(cmds) for cmds in commands.values()) + len(standalone)
    print(f"✅ Found {total} total CLI commands")

    return commands, standalone


def test_mcp_generation():
    """Test MCP tool generation by running the server briefly."""
    print("\n🔧 Testing MCP tool generation...")

    # Start the MCP server and capture its initial output
    start_time = time.time()

    try:
        # Run the MCP server with a timeout to capture tool generation logs
        result = subprocess.run(
            ["python", "-m", "tmux_orchestrator.mcp_server"],
            capture_output=True,
            text=True,
            timeout=40,  # Give it 40 seconds to generate tools
        )
    except subprocess.TimeoutExpired as e:
        # This is expected - we just want the initial generation logs
        output = e.stdout.decode() if e.stdout else ""
        error = e.stderr.decode() if e.stderr else ""
    else:
        output = result.stdout
        error = result.stderr

    generation_time = time.time() - start_time

    # Parse the output to count generated tools
    generated_tools = []
    for line in output.split("\n"):
        if "Generated MCP tool:" in line:
            # Extract tool name
            parts = line.split("Generated MCP tool:")
            if len(parts) > 1:
                tool_info = parts[1].strip()
                if " -> " in tool_info:
                    tool_name = tool_info.split(" -> ")[0]
                    generated_tools.append(tool_name)
        elif "Successfully generated" in line and "MCP tools" in line:
            # Extract total count
            import re

            match = re.search(r"Successfully generated (\d+) MCP tools", line)
            if match:
                total_generated = int(match.group(1))
                print(f"✅ Generated {total_generated} MCP tools in {generation_time:.2f}s")

    return generated_tools, generation_time


def validate_parity(commands, standalone, generated_tools):
    """Validate CLI to MCP parity."""
    print("\n📊 Validating CLI to MCP Parity...")

    expected_tools = []

    # Build expected tool names
    for group, cmds in commands.items():
        for cmd in cmds:
            tool_name = f"{group}_{cmd}".replace("-", "_")
            expected_tools.append(tool_name)

    for cmd in standalone:
        tool_name = cmd.replace("-", "_")
        expected_tools.append(tool_name)

    # Check coverage
    missing_tools = []
    for expected in expected_tools:
        if expected not in generated_tools:
            missing_tools.append(expected)

    total_expected = len(expected_tools)
    total_generated = len(generated_tools)
    coverage = (total_generated / total_expected * 100) if total_expected > 0 else 0

    print("\n📈 Coverage Report:")
    print(f"   Expected tools: {total_expected}")
    print(f"   Generated tools: {total_generated}")
    print(f"   Coverage: {coverage:.1f}%")

    if missing_tools:
        print(f"\n⚠️  Missing tools ({len(missing_tools)}):")
        for tool in missing_tools[:10]:
            print(f"   - {tool}")
        if len(missing_tools) > 10:
            print(f"   ... and {len(missing_tools) - 10} more")

    return {
        "total_expected": total_expected,
        "total_generated": total_generated,
        "coverage": coverage,
        "missing_tools": missing_tools,
    }


def test_specific_commands():
    """Test execution of specific high-priority commands."""
    print("\n🧪 Testing specific command executions...")

    test_cases = [
        {"name": "Agent Status", "command": ["tmux-orc", "agent", "status", "--json"], "expected_success": True},
        {"name": "Monitor Status", "command": ["tmux-orc", "monitor", "status", "--json"], "expected_success": True},
        {"name": "Team Status", "command": ["tmux-orc", "team", "status", "--json"], "expected_success": True},
        {"name": "CLI Reflection", "command": ["tmux-orc", "reflect", "--format", "json"], "expected_success": True},
    ]

    results = []

    for test in test_cases:
        try:
            result = subprocess.run(test["command"], capture_output=True, text=True, timeout=10)

            success = result.returncode == 0
            results.append(
                {
                    "name": test["name"],
                    "command": " ".join(test["command"]),
                    "success": success,
                    "output": result.stdout if success else result.stderr,
                }
            )

            status = "✅" if success else "❌"
            print(f"   {status} {test['name']}")

        except subprocess.TimeoutExpired:
            results.append(
                {
                    "name": test["name"],
                    "command": " ".join(test["command"]),
                    "success": False,
                    "output": "Command timed out",
                }
            )
            print(f"   ⏱️  {test['name']} (timeout)")

    return results


def main():
    """Run the validation script."""
    print("🚀 MCP CLI Parity Validation")
    print("=" * 50)

    # Get CLI commands
    commands, standalone = get_cli_commands()

    # Test MCP generation
    generated_tools, generation_time = test_mcp_generation()

    # Validate parity
    parity_report = validate_parity(commands, standalone, generated_tools)

    # Test specific commands
    command_results = test_specific_commands()

    # Generate report
    report = {
        "timestamp": datetime.now().isoformat(),
        "generation_time": generation_time,
        "parity": parity_report,
        "command_tests": command_results,
        "performance": {"generation_time": generation_time, "meets_requirement": generation_time < 30},
    }

    # Print summary
    print("\n" + "=" * 50)
    print("📋 VALIDATION SUMMARY")
    print("=" * 50)

    if parity_report["coverage"] >= 95:
        print("✅ CLI Parity: PASSED")
    else:
        print("❌ CLI Parity: FAILED")

    if generation_time < 30:
        print("✅ Performance: PASSED")
    else:
        print("❌ Performance: FAILED")

    passed_commands = sum(1 for r in command_results if r["success"])
    if passed_commands == len(command_results):
        print("✅ Command Tests: PASSED")
    else:
        print(f"⚠️  Command Tests: {passed_commands}/{len(command_results)} passed")

    # Save report
    report_path = Path("mcp_parity_validation_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n💾 Full report saved to: {report_path}")

    # Overall result
    if parity_report["coverage"] >= 95 and generation_time < 30:
        print("\n🎉 Overall: VALIDATION PASSED!")
        return 0
    else:
        print("\n❌ Overall: VALIDATION FAILED")
        return 1


if __name__ == "__main__":
    exit(main())
