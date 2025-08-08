"""Restart failed agents using CLI integration."""

import logging
import subprocess
from typing import Tuple


def restart_agent(target: str, logger: logging.Logger) -> Tuple[bool, str]:
    """
    Restart a failed agent using the CLI restart command.

    Integrates with the existing tmux-orchestrator CLI agent restart functionality
    to provide a clean restart of failed agents.

    Args:
        target: Target agent in format 'session:window'
        logger: Logger instance for recording restart events

    Returns:
        Tuple of (success, message)

    Raises:
        ValueError: If target format is invalid
        RuntimeError: If restart command execution fails
    """
    # Validate target format
    if ':' not in target:
        raise ValueError(f"Invalid target format: {target}. Expected 'session:window'")

    logger.warning(f"Attempting to restart agent: {target}")

    try:
        # Use the CLI restart command
        subprocess.run([
            'tmux-orchestrator', 'agent', 'restart', target
        ], capture_output=True, text=True, check=True)

        success_message: str = f"Successfully restarted agent {target}"
        logger.info(success_message)
        return True, success_message

    except subprocess.CalledProcessError as e:
        error_message: str = f"CLI restart failed for {target}: {e.stderr}"
        logger.error(error_message)
        return False, error_message

    except FileNotFoundError:
        cli_error_message: str = (
            f"tmux-orchestrator CLI not found. Cannot restart {target}"
        )
        logger.error(cli_error_message)
        raise RuntimeError(cli_error_message)

    except Exception as e:
        unexpected_error_message: str = (
            f"Unexpected error restarting {target}: {str(e)}"
        )
        logger.error(unexpected_error_message)
        raise RuntimeError(unexpected_error_message)
