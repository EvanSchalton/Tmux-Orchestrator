#!/usr/bin/env python3
"""Analyze detection method comparison results to evaluate accuracy."""

import json
import sys
from collections import defaultdict
from pathlib import Path


def analyze_comparison_log(log_file: Path):
    """Analyze the detection comparison log file."""
    if not log_file.exists():
        print(f"Log file not found: {log_file}")
        return

    # Statistics
    total_comparisons = 0
    agreements = 0
    disagreements = 0
    state_transitions: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    disagreement_details = []

    # Read and analyze log
    with open(log_file) as f:
        for line in f:
            try:
                data = json.loads(line.strip())
                total_comparisons += 1

                current_state = data["current_method"]["state"]
                new_state = data["new_method"]["state"]

                if data["agreement"]:
                    agreements += 1
                else:
                    disagreements += 1
                    disagreement_details.append(
                        {
                            "timestamp": data["timestamp"],
                            "target": data["target"],
                            "current": current_state,
                            "new": new_state,
                            "new_details": data["new_method"],
                        }
                    )

                # Track state transitions
                state_transitions[current_state][new_state] += 1

            except json.JSONDecodeError:
                print(f"Failed to parse line: {line}")
                continue

    # Print results
    print("\n=== Detection Method Comparison Analysis ===")
    print(f"Log file: {log_file}")
    print(f"Total comparisons: {total_comparisons}")
    print(f"Agreements: {agreements} ({agreements/total_comparisons*100:.1f}%)")
    print(f"Disagreements: {disagreements} ({disagreements/total_comparisons*100:.1f}%)")

    # Print confusion matrix
    print("\n=== Confusion Matrix ===")
    print("Current Method → New Method")
    all_states = set()
    for current in state_transitions:
        all_states.add(current)
        for new in state_transitions[current]:
            all_states.add(new)

    # Header
    print(f"{'Current':<20}", end="")
    for state in sorted(all_states):
        print(f"{state:<15}", end="")
    print()

    # Data
    for current in sorted(all_states):
        print(f"{current:<20}", end="")
        for new in sorted(all_states):
            count = state_transitions[current][new]
            if count > 0:
                print(f"{count:<15}", end="")
            else:
                print(f"{'.':<15}", end="")
        print()

    # Print disagreement details
    if disagreement_details:
        print("\n=== Recent Disagreements (last 10) ===")
        for detail in disagreement_details[-10:]:
            print(f"\n{detail['timestamp']} - {detail['target']}")
            print(f"  Current: {detail['current']}")
            print(f"  New: {detail['new']}")
            print(f"  Active: {detail['new_details']['is_active']}")
            print(f"  Crashed: {detail['new_details']['is_crashed']}")
            print(f"  Error: {detail['new_details']['is_error']}")
            print(f"  Idle: {detail['new_details']['is_idle']}")
            print(f"  Has Message: {detail['new_details']['has_message']}")
            if detail["new_details"]["message_content"]:
                print(f"  Message: {detail['new_details']['message_content'][:50]}...")


def main():
    """Main entry point."""
    # Default log location
    log_file = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator/logs/monitor-detection-comparison.jsonl")

    if len(sys.argv) > 1:
        log_file = Path(sys.argv[1])

    analyze_comparison_log(log_file)


if __name__ == "__main__":
    main()
