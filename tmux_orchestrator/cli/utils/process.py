"""Process management utilities for CLI."""

import shutil
import subprocess


def run_command(command: list[str], check: bool = True, capture_output: bool = True) -> subprocess.CompletedProcess:
    """Run a system command and return the result."""
    return subprocess.run(command, check=check, capture_output=capture_output, text=True)


def check_command_exists(command: str) -> bool:
    """Check if a command exists in the system PATH."""
    return shutil.which(command) is not None
