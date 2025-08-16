#!/usr/bin/env python3
"""
QA Test Script: Simulate PM outputting 'failed' messages

This script simulates a healthy PM that outputs legitimate messages containing 'failed'.
Use this to test if the monitor incorrectly kills the PM.

Usage:
1. Spawn this in a tmux window
2. Monitor daemon should NOT kill this window
3. If daemon kills it, the bug is confirmed
"""

import time

print("Starting PM simulation - testing 'failed' keyword bug...")
print("This PM is healthy but will output messages containing 'failed'")
print()

# Simulate normal PM startup
print("╭─ Assistant ─────────────────────────────────────────────────────╮")
print("│ I'm ready to assist with your project. Let me run some tests   │")
print("│ to check the current state...                                  │")
print("╰─────────────────────────────────────────────────────────────────╯")
print()

time.sleep(2)

# Output 1: Test failures (should NOT kill PM)
print("╭─ Assistant ─────────────────────────────────────────────────────╮")
print("│ I ran the test suite and found some issues:                    │")
print("│                                                                 │")
print("│ ❌ 3 tests failed in test_authentication.py                    │")
print("│ ❌ 2 tests failed in test_database.py                          │")
print("│ ❌ 1 test failed in test_api_validation.py                     │")
print("│                                                                 │")
print("│ Let me analyze these failures and fix them...                  │")
print("╰─────────────────────────────────────────────────────────────────╯")
print()

time.sleep(3)

# Output 2: Deployment failures (should NOT kill PM)
print("╭─ Assistant ─────────────────────────────────────────────────────╮")
print("│ The deployment failed due to configuration issues:             │")
print("│                                                                 │")
print("│ • Database connection failed - fixing connection string        │")
print("│ • SSL certificate validation failed - updating certificates    │")
print("│ • Health check failed - adjusting timeout settings            │")
print("│                                                                 │")
print("│ Working on resolving these deployment issues...                │")
print("╰─────────────────────────────────────────────────────────────────╯")
print()

time.sleep(3)

# Output 3: Build failures (should NOT kill PM)
print("╭─ Assistant ─────────────────────────────────────────────────────╮")
print("│ Build process encountered some failures:                       │")
print("│                                                                 │")
print("│ • Linting failed - fixing code style issues                   │")
print("│ • Type checking failed - adding missing type annotations      │")
print("│ • Security scan failed - addressing vulnerabilities           │")
print("│                                                                 │")
print("│ All these failures are now being resolved systematically...    │")
print("╰─────────────────────────────────────────────────────────────────╯")
print()

# Keep running to simulate ongoing work
print("╭─────────────────────────────────────────────────────────────────╮")
print("│ > Continuing work on fixing the issues...                      │")
print("╰─────────────────────────────────────────────────────────────────╯")

# Keep the script running so monitor can observe it
counter = 0
while True:
    time.sleep(10)
    counter += 1

    # Occasionally show activity to prove PM is working
    if counter % 3 == 0:
        print()
        print("╭─ Assistant ─────────────────────────────────────────────────────╮")
        print(f"│ Status update #{counter//3}: Still working on the failed tests │")
        print("│ and deployment issues. Making good progress...                 │")
        print("╰─────────────────────────────────────────────────────────────────╯")
        print()
        print("╭─────────────────────────────────────────────────────────────────╮")
        print("│ > Analyzing next failed component...                           │")
        print("╰─────────────────────────────────────────────────────────────────╯")

    # If we've been running for a while, the test is likely passing
    if counter > 50:  # 50 * 10 seconds = ~8 minutes
        print()
        print("✅ SUCCESS: PM has been running for 8+ minutes without being killed!")
        print("✅ The 'failed' keyword bug appears to be fixed!")
        break
