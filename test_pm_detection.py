#!/usr/bin/env python3
"""Test script to diagnose PM detection logic issues."""

import json
import subprocess


class TMUXManagerMock:
    """Minimal mock of TMUXManager for testing."""

    def list_windows(self, session):
        """List windows in a session."""
        cmd = ["tmux", "list-windows", "-t", session, "-F", '{"index": "#{window_index}", "name": "#{window_name}"}']
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Failed to list windows: {result.stderr}")

        windows = []
        for line in result.stdout.strip().split("\n"):
            if line:
                try:
                    windows.append(json.loads(line))
                except json.JSONDecodeError:
                    print(f"Failed to parse: {line}")
        return windows


def _is_pm_agent(tmux: TMUXManagerMock, target: str) -> bool:
    """Check if target is a PM agent - exact copy from monitor.py."""
    try:
        # Simple check: window name contains 'pm' or is identified as PM
        session, window = target.split(":")
        windows = tmux.list_windows(session)
        for w in windows:
            if w.get("index") == window:
                window_name = w.get("name", "").lower()
                return "pm" in window_name or "manager" in window_name
        return False
    except Exception as e:
        print(f"Exception in _is_pm_agent: {e}")
        return False


def _find_pm_in_session(tmux: TMUXManagerMock, session: str) -> str | None:
    """Find PM agent in a specific session - exact copy from monitor.py."""
    try:
        windows = tmux.list_windows(session)
        for window in windows:
            window_idx = str(window.get("index", ""))
            target = f"{session}:{window_idx}"
            if _is_pm_agent(tmux, target):
                return target
        return None
    except Exception as e:
        print(f"Exception in _find_pm_in_session: {e}")
        return None


def main():
    """Test PM detection logic."""
    tmux = TMUXManagerMock()
    session = "critical-fixes"

    print(f"Testing PM detection for session: {session}")
    print("-" * 50)

    # List all windows
    try:
        windows = tmux.list_windows(session)
        print("\nWindows in session:")
        for w in windows:
            index = w.get("index", "?")
            name = w.get("name", "Unknown")
            print(f"  {index}: {name}")

            # Test individual window
            target = f"{session}:{index}"
            is_pm = _is_pm_agent(tmux, target)
            print(f"    -> _is_pm_agent('{target}'): {is_pm}")
            print(f"    -> window_name.lower(): '{name.lower()}'")
            print(f"    -> 'pm' in window_name: {'pm' in name.lower()}")
            print(f"    -> 'manager' in window_name: {'manager' in name.lower()}")
    except Exception as e:
        print(f"Error listing windows: {e}")

    print("\n" + "-" * 50)

    # Test PM finder
    pm_target = _find_pm_in_session(tmux, session)
    print(f"\n_find_pm_in_session('{session}'): {pm_target}")

    # Test specific targets mentioned in the issue
    print("\n" + "-" * 50)
    print("\nTesting specific targets:")
    test_targets = ["critical-fixes:1", "critical-fixes:2", "critical-fixes:3", "critical-fixes:4"]

    for target in test_targets:
        is_pm = _is_pm_agent(tmux, target)
        print(f"  _is_pm_agent('{target}'): {is_pm}")

        # Additional debug info
        try:
            session, window = target.split(":")
            windows = tmux.list_windows(session)
            for w in windows:
                if w.get("index") == window:
                    print(f"    -> Found window: index={w.get('index')}, name='{w.get('name')}'")
                    print(f"    -> Type comparison: w.get('index')={repr(w.get('index'))}, window={repr(window)}")
                    print(f"    -> Equality: {w.get('index') == window}")
                    break
            else:
                print("    -> Window not found in list!")
        except Exception as e:
            print(f"    -> Error: {e}")


if __name__ == "__main__":
    main()
