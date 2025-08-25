#!/usr/bin/env python3
"""
CLI Module Validation Testing Protocols
Post-Backend Developer MCP Setup Fix Implementation

This protocol validates CLI module integrity and MCP integration
after Backend Developer resolves setup module import errors.
"""

import json
import subprocess
import sys
import time
from typing import Any, Dict


class CLIModuleValidator:
    """Validates CLI modules after MCP setup fixes"""

    def __init__(self):
        self.test_results = {}
        self.validation_timestamp = time.time()

    def validate_core_cli_imports(self) -> Dict[str, Any]:
        """Test core CLI module import integrity"""
        import_tests = {
            "tmux_orchestrator.cli.context": "Context management imports",
            "tmux_orchestrator.cli.spawn": "Agent spawning imports",
            "tmux_orchestrator.cli.spawn_orc": "Orchestrator spawning imports",
            "tmux_orchestrator.mcp_server": "MCP server integration",
        }

        results = {"passed": 0, "failed": 0, "details": {}}

        for module, description in import_tests.items():
            try:
                # Test import statement
                cmd = f"python3 -c 'import {module}; print(\"SUCCESS\")'"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)

                if result.returncode == 0 and "SUCCESS" in result.stdout:
                    results["passed"] += 1
                    results["details"][module] = {"status": "PASS", "description": description}
                else:
                    results["failed"] += 1
                    results["details"][module] = {
                        "status": "FAIL",
                        "description": description,
                        "error": result.stderr.strip(),
                    }

            except Exception as e:
                results["failed"] += 1
                results["details"][module] = {"status": "ERROR", "description": description, "error": str(e)}

        return results

    def validate_mcp_server_startup(self) -> Dict[str, Any]:
        """Test MCP server can start without import errors"""
        test_cmd = "python3 -m tmux_orchestrator.mcp_server --help"

        try:
            result = subprocess.run(test_cmd.split(), capture_output=True, text=True, timeout=15)

            return {
                "status": "PASS" if result.returncode == 0 else "FAIL",
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "validation": "MCP server startup test",
            }

        except subprocess.TimeoutExpired:
            return {
                "status": "TIMEOUT",
                "validation": "MCP server startup test",
                "error": "Command timed out after 15 seconds",
            }
        except Exception as e:
            return {"status": "ERROR", "validation": "MCP server startup test", "error": str(e)}

    def validate_cli_command_structure(self) -> Dict[str, Any]:
        """Test CLI command structure integrity"""
        core_commands = ["tmux-orc --help", "tmux-orc reflect", "tmux-orc context show mcp", "tmux-orc list --help"]

        results = {"passed": 0, "failed": 0, "commands": {}}

        for cmd in core_commands:
            try:
                result = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=10)

                if result.returncode == 0:
                    results["passed"] += 1
                    results["commands"][cmd] = {"status": "PASS"}
                else:
                    results["failed"] += 1
                    results["commands"][cmd] = {
                        "status": "FAIL",
                        "returncode": result.returncode,
                        "stderr": result.stderr.strip(),
                    }

            except Exception as e:
                results["failed"] += 1
                results["commands"][cmd] = {"status": "ERROR", "error": str(e)}

        return results

    def validate_mcp_tool_discovery(self) -> Dict[str, Any]:
        """Test MCP tool discovery after fixes"""
        try:
            # Check if MCP tools are discoverable
            cmd = "tmux-orc reflect --format json"
            result = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=15)

            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    mcp_tools_found = any("mcp" in str(data).lower() for _ in [1])

                    return {
                        "status": "PASS",
                        "mcp_integration_detected": mcp_tools_found,
                        "cli_structure_valid": True,
                        "json_parseable": True,
                    }
                except json.JSONDecodeError:
                    return {
                        "status": "PARTIAL",
                        "cli_executable": True,
                        "json_parseable": False,
                        "raw_output": result.stdout[:200],
                    }
            else:
                return {"status": "FAIL", "returncode": result.returncode, "stderr": result.stderr}

        except Exception as e:
            return {"status": "ERROR", "error": str(e)}

    def run_complete_validation(self) -> Dict[str, Any]:
        """Run complete CLI module validation suite"""
        print("🔍 Running CLI Module Validation Suite...")

        validation_results = {
            "timestamp": self.validation_timestamp,
            "validation_type": "post_backend_fix",
            "tests": {},
        }

        # Test 1: Core CLI Imports
        print("  ✓ Testing core CLI imports...")
        validation_results["tests"]["imports"] = self.validate_core_cli_imports()

        # Test 2: MCP Server Startup
        print("  ✓ Testing MCP server startup...")
        validation_results["tests"]["mcp_server"] = self.validate_mcp_server_startup()

        # Test 3: CLI Command Structure
        print("  ✓ Testing CLI command structure...")
        validation_results["tests"]["cli_commands"] = self.validate_cli_command_structure()

        # Test 4: MCP Tool Discovery
        print("  ✓ Testing MCP tool discovery...")
        validation_results["tests"]["mcp_discovery"] = self.validate_mcp_tool_discovery()

        # Calculate overall status
        overall_status = self._calculate_overall_status(validation_results["tests"])
        validation_results["overall_status"] = overall_status

        return validation_results

    def _calculate_overall_status(self, tests: Dict[str, Any]) -> str:
        """Calculate overall validation status"""
        critical_failures = 0
        total_tests = len(tests)

        for test_name, test_result in tests.items():
            if isinstance(test_result, dict):
                if test_result.get("status") in ["FAIL", "ERROR"]:
                    critical_failures += 1
                elif test_result.get("failed", 0) > 0:
                    critical_failures += 1

        if critical_failures == 0:
            return "ALL_PASS"
        elif critical_failures < total_tests:
            return "PARTIAL_PASS"
        else:
            return "CRITICAL_FAILURE"


def generate_validation_report(results: Dict[str, Any]) -> str:
    """Generate human-readable validation report"""
    report = f"""
🔍 CLI Module Validation Report
================================
Timestamp: {time.ctime(results["timestamp"])}
Validation Type: {results["validation_type"]}
Overall Status: {results["overall_status"]}

📊 Test Results Summary:
"""

    for test_name, test_data in results["tests"].items():
        report += f"\n🔹 {test_name.upper()}:\n"

        if test_name == "imports":
            report += f"  Passed: {test_data['passed']}/{test_data['passed'] + test_data['failed']}\n"
            for module, details in test_data["details"].items():
                status_emoji = "✅" if details["status"] == "PASS" else "❌"
                report += f"    {status_emoji} {module}: {details['status']}\n"

        elif test_name == "mcp_server":
            status_emoji = "✅" if test_data["status"] == "PASS" else "❌"
            report += f"  {status_emoji} Status: {test_data['status']}\n"

        elif test_name == "cli_commands":
            report += f"  Passed: {test_data['passed']}/{test_data['passed'] + test_data['failed']}\n"

        elif test_name == "mcp_discovery":
            status_emoji = "✅" if test_data["status"] == "PASS" else "❌"
            report += f"  {status_emoji} Status: {test_data['status']}\n"

    # Recommendations
    report += "\n🎯 Recommendations:\n"

    if results["overall_status"] == "ALL_PASS":
        report += "  ✅ All validations passed - Ready for MCP testing execution\n"
    elif results["overall_status"] == "PARTIAL_PASS":
        report += "  ⚠️  Some issues detected - Review failed tests before proceeding\n"
    else:
        report += "  ❌ Critical failures detected - Backend Developer coordination needed\n"

    return report


if __name__ == "__main__":
    print("🧪 CLI Module Validation Protocol")
    print("Preparing for post-Backend Developer fix validation...")

    validator = CLIModuleValidator()
    results = validator.run_complete_validation()

    report = generate_validation_report(results)
    print(report)

    # Save results to file
    results_file = f"/workspaces/Tmux-Orchestrator/tests/cli_validation_results_{int(time.time())}.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n📁 Results saved to: {results_file}")

    # Exit code based on validation results
    if results["overall_status"] == "ALL_PASS":
        sys.exit(0)
    elif results["overall_status"] == "PARTIAL_PASS":
        sys.exit(1)
    else:
        sys.exit(2)
