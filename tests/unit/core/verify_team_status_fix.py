#!/usr/bin/env python3
"""Verification script for team status bug fix."""

import json
import subprocess
import sys
import time


def run_command(cmd):
    """Run a shell command and return output."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)


def test_team_status():
    """Test team status functionality."""
    print("Team Status Bug Fix Verification")
    print("=" * 50)

    # Test 1: Check if team status works without crashing
    print("\nTest 1: Basic team status functionality")
    print("-" * 40)

    # Get list of sessions
    code, stdout, stderr = run_command("tmux-orc list --json")
    if code != 0:
        print(f"❌ Failed to list agents: {stderr}")
        return False

    try:
        agents = json.loads(stdout)
        sessions = set(agent["session"] for agent in agents)

        if not sessions:
            print("⚠️  No active sessions found. Deploy a test team first.")
            return False

        # Test team status for each session
        for session in sessions:
            print(f"\nTesting session: {session}")
            code, stdout, stderr = run_command(f"tmux-orc team status {session}")

            if code != 0:
                print(f"❌ Team status failed with error: {stderr}")
                if "NameError" in stderr and "_is_actual_error" in stderr:
                    print("   Issue: Function definition order bug still present")
                return False
            else:
                print("✅ Team status completed successfully")

                # Check for false error reports
                if "Error" in stdout:
                    # Verify if it's a real error by checking individual agent
                    code2, stdout2, stderr2 = run_command("tmux-orc list --json")
                    if code2 == 0:
                        agents_in_session = [a for a in json.loads(stdout2) if a["session"] == session]
                        error_agents = [a for a in agents_in_session if "Error" in stdout and a["target"] in stdout]

                        for agent in error_agents:
                            # Cross-check with agent info
                            code3, stdout3, stderr3 = run_command(f"tmux-orc agent info {agent['target']}")
                            if "active" in stdout3.lower() and "✓" in stdout3:
                                print(
                                    f"⚠️  Potential false positive: {agent['target']} shown as Error but is actually healthy"
                                )

    except json.JSONDecodeError:
        print("❌ Failed to parse JSON output")
        return False

    # Test 2: Deploy new team and check
    print("\n\nTest 2: New team deployment and status")
    print("-" * 40)

    test_session = f"test-status-{int(time.time())}"
    code, stdout, stderr = run_command(f"tmux-orc team deploy frontend 2 --project-name {test_session}")

    if code != 0:
        print(f"❌ Failed to deploy test team: {stderr}")
        return False

    print("✅ Test team deployed successfully")
    time.sleep(3)  # Wait for agents to initialize

    # Check team status
    code, stdout, stderr = run_command(f"tmux-orc team status {test_session}-frontend")

    if code != 0:
        print(f"❌ Team status check failed: {stderr}")
        # Clean up
        run_command(f"tmux kill-session -t {test_session}-frontend")
        return False

    print("✅ Team status check passed")

    # Check for healthy agents
    if "Error" in stdout and "Idle" not in stdout and "Active" not in stdout:
        print("⚠️  All agents shown as Error - likely false positives")

    # Clean up
    run_command(f"tmux kill-session -t {test_session}-frontend")

    return True


def test_edge_cases():
    """Test edge cases."""
    print("\n\nTest 3: Edge cases")
    print("-" * 40)

    # Test non-existent session
    code, stdout, stderr = run_command("tmux-orc team status non-existent-session")
    if "not found" in stderr.lower() or "not found" in stdout.lower():
        print("✅ Non-existent session handled correctly")
    else:
        print("⚠️  Non-existent session handling unclear")

    return True


def main():
    """Run all tests."""
    success = True

    try:
        success &= test_team_status()
        success &= test_edge_cases()
    except Exception as e:
        print(f"\n❌ Test suite failed with exception: {e}")
        return 1

    print("\n" + "=" * 50)
    if success:
        print("✅ All tests completed successfully!")
        print("   The team status bug fix appears to be working correctly.")
        return 0
    else:
        print("❌ Some tests failed.")
        print("   The team status bug needs additional fixes.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
