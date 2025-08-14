#!/usr/bin/env python3
"""Test script to compare change detection methods on live data."""

import logging
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from tmux_orchestrator.core.monitor_change_detection import (
    capture_snapshots_with_timing,
    compare_detection_methods,
    detect_idle_with_empty_prompt,
    detect_message_queued,
)
from tmux_orchestrator.utils.tmux import TMUXManager

# Set up logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def test_on_agent(tmux: TMUXManager, target: str):
    """Test detection methods on a specific agent."""
    logger.info(f"\nTesting agent: {target}")

    # Capture snapshots
    logger.info("Capturing snapshots...")
    snapshots = capture_snapshots_with_timing(tmux.capture_pane, target)

    # Compare methods
    results = compare_detection_methods(snapshots, logger)

    # Test other detection methods
    last_snapshot = snapshots[-1]
    idle_empty = detect_idle_with_empty_prompt(last_snapshot)
    message_queued = detect_message_queued(last_snapshot)

    logger.info(f"Results for {target}:")
    logger.info(f"  Simple method detected active: {results['simple_method']}")
    logger.info(f"  Levenshtein method detected active: {results['levenshtein_method']}")
    logger.info(f"  Levenshtein distances: {results['levenshtein_distances']}")
    logger.info(f"  Methods agree: {results['methods_agree']}")
    logger.info(f"  Idle with empty prompt: {idle_empty}")
    logger.info(f"  Message queued: {message_queued}")

    # Save snapshot for analysis if methods disagree
    if not results["methods_agree"]:
        logger.warning(f"Methods DISAGREE for {target}!")
        # Save snapshots for analysis
        for i, snapshot in enumerate(snapshots):
            filename = f"/tmp/{target.replace(':', '_')}_snapshot_{i}.txt"
            with open(filename, "w") as f:
                f.write(snapshot)
            logger.info(f"  Saved snapshot {i} to {filename}")

    return results


def main():
    """Main test function."""
    tmux = TMUXManager()

    # Find all monitor-fixes agents
    agents = []
    try:
        sessions = tmux.list_sessions()
        for session in sessions:
            if session["name"] == "monitor-fixes":
                windows = tmux.list_windows(session["name"])
                for window in windows:
                    target = f"{session['name']}:{window['index']}"
                    agents.append(target)
    except Exception as e:
        logger.error(f"Failed to discover agents: {e}")
        return

    logger.info(f"Found {len(agents)} agents to test: {agents}")

    # Test each agent
    all_results = {}
    agreement_count = 0

    for agent in agents:
        try:
            results = test_on_agent(tmux, agent)
            all_results[agent] = results
            if results["methods_agree"]:
                agreement_count += 1
        except Exception as e:
            logger.error(f"Failed to test {agent}: {e}")

    # Summary
    logger.info("\n=== SUMMARY ===")
    logger.info(f"Tested {len(all_results)} agents")
    logger.info(f"Methods agreed on {agreement_count}/{len(all_results)} agents")

    # Show disagreements
    disagreements = [(agent, res) for agent, res in all_results.items() if not res["methods_agree"]]
    if disagreements:
        logger.warning("\nDisagreements:")
        for agent, res in disagreements:
            logger.warning(f"  {agent}: Simple={res['simple_method']}, Levenshtein={res['levenshtein_method']}")
            logger.warning(f"    Distances: {res['levenshtein_distances']}")


if __name__ == "__main__":
    main()
