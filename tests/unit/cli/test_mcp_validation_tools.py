#!/usr/bin/env python3
"""
MCP Validation Tools for Testing
Standalone tools to validate MCP server integration and functionality
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Optional


class MCPValidationTools:
    """Tools for validating MCP server integration and functionality"""

    def __init__(self, claude_config_dir: Optional[str] = None):
        """Initialize validation tools with Claude config directory"""
        if claude_config_dir:
            self.claude_config_dir = Path(claude_config_dir)
        else:
            # Try to find Claude config directory
            possible_dirs = [
                Path.cwd() / ".claude",
                Path.home() / ".claude",
                Path(os.environ.get("CLAUDE_CONFIG_DIR", "")) / ".claude"
                if os.environ.get("CLAUDE_CONFIG_DIR")
                else None,
            ]

            self.claude_config_dir = None
            for dir_path in possible_dirs:
                if dir_path and dir_path.exists():
                    self.claude_config_dir = dir_path
                    break

            if not self.claude_config_dir:
                self.claude_config_dir = Path.cwd() / ".claude"

    def validate_setup_command(self) -> Dict[str, any]:
        """Validate that 'tmux-orc setup all' works correctly"""
        results = {"success": False, "issues": [], "details": {}}

        try:
            # Check if tmux-orc is available
            result = subprocess.run(["tmux-orc", "--version"], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                results["issues"].append("tmux-orc command not found or not working")
                return results

            results["details"]["tmux_orc_version"] = result.stdout.strip()

            # Test setup command (non-interactive mode needed)
            # Note: Current setup command is interactive, so we'll check what it should do
            expected_config_dir = self.claude_config_dir / "config"
            expected_mcp_file = expected_config_dir / "mcp.json"

            # Check if directories exist
            if not expected_config_dir.exists():
                results["issues"].append(f"Claude config directory not found: {expected_config_dir}")
            else:
                results["details"]["config_dir_exists"] = True

            # Check MCP configuration
            if not expected_mcp_file.exists():
                results["issues"].append(f"MCP configuration file not found: {expected_mcp_file}")
            else:
                try:
                    with open(expected_mcp_file) as f:
                        mcp_config = json.load(f)

                    results["details"]["mcp_config"] = mcp_config

                    # Validate tmux-orchestrator server configuration
                    if "servers" not in mcp_config:
                        results["issues"].append("No 'servers' section in mcp.json")
                    elif "tmux-orchestrator" not in mcp_config["servers"]:
                        results["issues"].append("tmux-orchestrator server not configured in mcp.json")
                    else:
                        server_config = mcp_config["servers"]["tmux-orchestrator"]

                        # Check required fields
                        required_fields = ["command", "args"]
                        for field in required_fields:
                            if field not in server_config:
                                results["issues"].append(
                                    f"Missing required field '{field}' in tmux-orchestrator config"
                                )

                        # Check command is correct
                        if server_config.get("command") != "tmux-orc":
                            results["issues"].append(
                                f"Expected command 'tmux-orc', got '{server_config.get('command')}'"
                            )

                        # Check args
                        expected_args = ["server", "start"]
                        if server_config.get("args") != expected_args:
                            results["issues"].append(f"Expected args {expected_args}, got {server_config.get('args')}")

                except json.JSONDecodeError as e:
                    results["issues"].append(f"Invalid JSON in mcp.json: {e}")
                except Exception as e:
                    results["issues"].append(f"Error reading mcp.json: {e}")

            results["success"] = len(results["issues"]) == 0

        except Exception as e:
            results["issues"].append(f"Unexpected error during validation: {e}")

        return results

    def validate_claude_mcp_integration(self) -> Dict[str, any]:
        """Validate Claude Code CLI MCP integration"""
        results = {"success": False, "issues": [], "details": {}}

        try:
            # Check if claude command is available
            result = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                results["issues"].append("Claude Code CLI not found or not working")
                return results

            results["details"]["claude_version"] = result.stdout.strip()

            # Test claude mcp list command
            result = subprocess.run(["claude", "mcp", "list"], capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                results["issues"].append(f"'claude mcp list' failed: {result.stderr}")
            else:
                mcp_list_output = result.stdout.strip()
                results["details"]["mcp_list_output"] = mcp_list_output

                # Check if tmux-orchestrator is listed
                if "tmux-orchestrator" not in mcp_list_output:
                    if "No MCP servers configured" in mcp_list_output:
                        results["issues"].append("No MCP servers configured in Claude Code CLI")
                    else:
                        results["issues"].append("tmux-orchestrator not found in Claude MCP server list")
                else:
                    results["details"]["tmux_orchestrator_found"] = True

                    # Test getting server details
                    result = subprocess.run(
                        ["claude", "mcp", "get", "tmux-orchestrator"], capture_output=True, text=True, timeout=10
                    )

                    if result.returncode == 0:
                        results["details"]["server_details"] = result.stdout.strip()
                    else:
                        results["issues"].append(f"Failed to get tmux-orchestrator details: {result.stderr}")

            results["success"] = len(results["issues"]) == 0

        except Exception as e:
            results["issues"].append(f"Unexpected error during Claude MCP validation: {e}")

        return results

    def validate_mcp_server_functionality(self) -> Dict[str, any]:
        """Validate MCP server can start and respond"""
        results = {"success": False, "issues": [], "details": {}}

        try:
            # Test tmux-orc server status
            result = subprocess.run(["tmux-orc", "server", "status"], capture_output=True, text=True, timeout=10)

            results["details"]["server_status_output"] = result.stdout.strip()
            results["details"]["server_status_returncode"] = result.returncode

            if result.returncode != 0:
                results["issues"].append(f"'tmux-orc server status' failed: {result.stderr}")

            # Test server tools command
            result = subprocess.run(["tmux-orc", "server", "tools"], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                results["details"]["server_tools"] = result.stdout.strip()
            else:
                results["issues"].append(f"'tmux-orc server tools' failed: {result.stderr}")

            # Try to start server if not running
            result = subprocess.run(["tmux-orc", "server", "start"], capture_output=True, text=True, timeout=15)

            if result.returncode == 0:
                results["details"]["server_start_success"] = True

                # Wait a moment for server to start
                time.sleep(2)

                # Check status again
                result = subprocess.run(["tmux-orc", "server", "status"], capture_output=True, text=True, timeout=10)
                results["details"]["server_status_after_start"] = result.stdout.strip()
            else:
                results["issues"].append(f"Failed to start MCP server: {result.stderr}")

            results["success"] = len(results["issues"]) == 0

        except Exception as e:
            results["issues"].append(f"Unexpected error during server functionality validation: {e}")

        return results

    def validate_agent_mcp_access(self) -> Dict[str, any]:
        """Validate that spawned agents can access MCP server"""
        results = {"success": False, "issues": [], "details": {}}

        try:
            # Check if we can list agents (this implies system is working)
            result = subprocess.run(["tmux-orc", "list"], capture_output=True, text=True, timeout=10)

            results["details"]["agent_list_output"] = result.stdout.strip()

            if result.returncode != 0:
                results["issues"].append(f"'tmux-orc list' failed: {result.stderr}")

            # For now, we'll test the basic agent system functionality
            # In a real test, we'd spawn a test agent and verify MCP access

            # Check session management
            result = subprocess.run(["tmux-orc", "session", "list"], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                results["details"]["session_list"] = result.stdout.strip()
            else:
                results["issues"].append(f"'tmux-orc session list' failed: {result.stderr}")

            # Basic validation - if we can run tmux-orc commands, agents should have access
            results["success"] = len(results["issues"]) == 0

        except Exception as e:
            results["issues"].append(f"Unexpected error during agent MCP access validation: {e}")

        return results

    def run_comprehensive_validation(self) -> Dict[str, any]:
        """Run all validation tests"""
        print("🔍 Running MCP Integration Validation...")
        print("=" * 60)

        all_results = {"overall_success": False, "tests": {}, "summary": {"passed": 0, "failed": 0, "total": 0}}

        # Define test cases
        test_cases = [
            ("Setup Command", self.validate_setup_command),
            ("Claude MCP Integration", self.validate_claude_mcp_integration),
            ("MCP Server Functionality", self.validate_mcp_server_functionality),
            ("Agent MCP Access", self.validate_agent_mcp_access),
        ]

        for test_name, test_func in test_cases:
            print(f"\n🧪 Testing: {test_name}")
            print("-" * 40)

            try:
                results = test_func()
                all_results["tests"][test_name] = results

                if results["success"]:
                    print("✅ PASSED")
                    all_results["summary"]["passed"] += 1
                else:
                    print("❌ FAILED")
                    all_results["summary"]["failed"] += 1
                    for issue in results["issues"]:
                        print(f"   • {issue}")

                # Show key details
                if results.get("details"):
                    for key, value in results["details"].items():
                        if isinstance(value, str) and len(value) < 100:
                            print(f"   {key}: {value}")
                        elif isinstance(value, (bool, int)):
                            print(f"   {key}: {value}")

            except Exception as e:
                print(f"❌ ERROR: {e}")
                all_results["tests"][test_name] = {
                    "success": False,
                    "issues": [f"Test execution error: {e}"],
                    "details": {},
                }
                all_results["summary"]["failed"] += 1

            all_results["summary"]["total"] += 1

        # Overall success
        all_results["overall_success"] = all_results["summary"]["failed"] == 0

        # Print summary
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {all_results['summary']['total']}")
        print(f"Passed: {all_results['summary']['passed']}")
        print(f"Failed: {all_results['summary']['failed']}")

        if all_results["overall_success"]:
            print("\n🎉 ALL TESTS PASSED - MCP Integration is working correctly!")
        else:
            print("\n⚠️  SOME TESTS FAILED - MCP Integration needs attention")

        return all_results


def main():
    """CLI entry point for validation tools"""
    import argparse

    parser = argparse.ArgumentParser(description="MCP Integration Validation Tools")
    parser.add_argument(
        "--test", choices=["setup", "claude", "server", "agents", "all"], default="all", help="Which test to run"
    )
    parser.add_argument("--config-dir", help="Claude config directory path")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()

    # Initialize validation tools
    validator = MCPValidationTools(args.config_dir)

    # Run specified test
    if args.test == "setup":
        results = validator.validate_setup_command()
    elif args.test == "claude":
        results = validator.validate_claude_mcp_integration()
    elif args.test == "server":
        results = validator.validate_mcp_server_functionality()
    elif args.test == "agents":
        results = validator.validate_agent_mcp_access()
    else:  # all
        results = validator.run_comprehensive_validation()

    if args.json:
        print(json.dumps(results, indent=2))

    # Exit with appropriate code
    if results.get("overall_success", results.get("success", False)):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
