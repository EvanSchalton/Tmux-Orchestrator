#!/usr/bin/env python3
"""
Debug script to understand spawn test failure
"""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from tmux_orchestrator.cli.spawn import spawn


def debug_spawn_failure():
    """Debug the spawn command failure in tests"""
    runner = CliRunner()

    # Create mock similar to test
    with patch("tmux_orchestrator.utils.tmux.TMUXManager") as mock_tmux_class:
        tmux_instance = MagicMock()
        mock_tmux_class.return_value = tmux_instance
        tmux_instance.list_sessions.return_value = [{"name": "test"}]
        tmux_instance.send_message.return_value = True
        tmux_instance.create_window.return_value = True
        tmux_instance.list_windows.return_value = []  # Start with empty session
        tmux_instance.send_keys.return_value = True
        tmux_instance.has_session.return_value = True  # Key: session exists

        with patch("time.sleep"), patch("tmux_orchestrator.cli.context.load_context") as mock_load:
            mock_load.return_value = "Agent context"

            result = runner.invoke(
                spawn, ["agent", "dev1", "test-session", "--briefing", "Dev 1"], obj={"tmux": tmux_instance}
            )

            print(f"Exit code: {result.exit_code}")
            print(f"Output: {result.output}")
            print(f"Exception: {result.exception}")
            if result.exception:
                import traceback

                print("Traceback:")
                print(
                    "".join(
                        traceback.format_exception(
                            type(result.exception), result.exception, result.exception.__traceback__
                        )
                    )
                )


if __name__ == "__main__":
    debug_spawn_failure()
