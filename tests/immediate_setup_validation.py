#!/usr/bin/env python3
"""
IMMEDIATE SETUP.PY VALIDATION PROTOCOL
Emergency testing for post-Backend Developer intervention
"""

import subprocess
import sys
import time
from pathlib import Path


def immediate_setup_test():
    """Run immediate validation of setup.py creation and import resolution"""

    print("🚨 EMERGENCY SETUP.PY VALIDATION")
    print("=" * 50)

    results = {
        "timestamp": time.time(),
        "setup_py_exists": False,
        "import_resolution": {},
        "cli_functionality": {},
        "overall_status": "UNKNOWN",
    }

    # Test 1: Check if setup.py exists
    setup_path = Path("/workspaces/Tmux-Orchestrator/setup.py")
    results["setup_py_exists"] = setup_path.exists()

    if results["setup_py_exists"]:
        print("✅ setup.py detected")
    else:
        print("❌ setup.py NOT FOUND")
        results["overall_status"] = "SETUP_MISSING"
        return results

    # Test 2: Import Resolution Tests
    critical_imports = [
        "tmux_orchestrator.cli.context",
        "tmux_orchestrator.cli.spawn",
        "tmux_orchestrator.cli.spawn_orc",
        "tmux_orchestrator.mcp_server",
    ]

    print("\n🔍 Testing critical imports...")
    import_failures = 0

    for module in critical_imports:
        try:
            cmd = f"python3 -c 'import {module}; print(\"SUCCESS\")'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)

            if result.returncode == 0 and "SUCCESS" in result.stdout:
                print(f"  ✅ {module}")
                results["import_resolution"][module] = "PASS"
            else:
                print(f"  ❌ {module}: {result.stderr.strip()}")
                results["import_resolution"][module] = f"FAIL: {result.stderr.strip()}"
                import_failures += 1

        except Exception as e:
            print(f"  ❌ {module}: {str(e)}")
            results["import_resolution"][module] = f"ERROR: {str(e)}"
            import_failures += 1

    # Test 3: CLI Command Tests
    print("\n🔧 Testing CLI functionality...")
    cli_commands = ["tmux-orc --help", "tmux-orc reflect"]
    cli_failures = 0

    for cmd in cli_commands:
        try:
            result = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=5)

            if result.returncode == 0:
                print(f"  ✅ {cmd}")
                results["cli_functionality"][cmd] = "PASS"
            else:
                print(f"  ❌ {cmd}: RC={result.returncode}")
                results["cli_functionality"][cmd] = f"FAIL: RC={result.returncode}"
                cli_failures += 1

        except Exception as e:
            print(f"  ❌ {cmd}: {str(e)}")
            results["cli_functionality"][cmd] = f"ERROR: {str(e)}"
            cli_failures += 1

    # Overall Status Determination
    if import_failures == 0 and cli_failures == 0:
        results["overall_status"] = "ALL_SYSTEMS_GO"
        print("\n🚀 ALL SYSTEMS GO - READY FOR MCP TESTING")
    elif import_failures > 0 and cli_failures == 0:
        results["overall_status"] = "IMPORT_ISSUES"
        print("\n⚠️  IMPORT ISSUES DETECTED")
    elif import_failures == 0 and cli_failures > 0:
        results["overall_status"] = "CLI_ISSUES"
        print("\n⚠️  CLI FUNCTIONALITY ISSUES")
    else:
        results["overall_status"] = "MULTIPLE_FAILURES"
        print("\n🚨 MULTIPLE SYSTEM FAILURES")

    return results


if __name__ == "__main__":
    results = immediate_setup_test()

    print("\n📊 VALIDATION SUMMARY:")
    print(f"Status: {results['overall_status']}")
    print(f"Setup.py exists: {results['setup_py_exists']}")
    print(
        f"Import tests: {len([v for v in results['import_resolution'].values() if v == 'PASS'])}/{len(results['import_resolution'])}"
    )
    print(
        f"CLI tests: {len([v for v in results['cli_functionality'].values() if v == 'PASS'])}/{len(results['cli_functionality'])}"
    )

    # Exit codes for coordination
    if results["overall_status"] == "ALL_SYSTEMS_GO":
        print("\n✅ READY TO PROCEED WITH MCP TESTING")
        sys.exit(0)
    elif results["overall_status"] == "SETUP_MISSING":
        print("\n❌ SETUP.PY STILL MISSING - BACKEND DEVELOPER INTERVENTION REQUIRED")
        sys.exit(2)
    else:
        print(f"\n⚠️  ISSUES DETECTED: {results['overall_status']}")
        sys.exit(1)
