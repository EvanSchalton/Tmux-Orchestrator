"""Detect Claude Code executable across platforms."""

import os
import platform
import shutil
from pathlib import Path


def detect_claude_executable() -> Path | None:
    """Detect Claude Code executable across platforms.

    Returns:
        Path to Claude executable if found, None otherwise
    """
    system = platform.system().lower()

    # Common executable names to try
    candidates = []

    if system == "windows":
        # Windows: Check Program Files and App Data
        candidates.extend(
            [
                Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Claude" / "Claude.exe",
                Path(os.environ.get("PROGRAMFILES", "")) / "Claude" / "Claude.exe",
                Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Claude" / "Claude.exe",
            ]
        )
        # Also check PATH
        claude_in_path = shutil.which("claude")
        if claude_in_path:
            candidates.append(Path(claude_in_path))

    elif system == "darwin":
        # macOS: Check Applications folder
        candidates.extend(
            [
                Path("/Applications/Claude.app/Contents/MacOS/Claude"),
                Path.home() / "Applications" / "Claude.app" / "Contents" / "MacOS" / "Claude",
            ]
        )

    elif system == "linux":
        # Linux: Check common installation locations
        candidates.extend(
            [
                Path("/usr/bin/claude"),
                Path("/usr/local/bin/claude"),
                Path.home() / ".local" / "bin" / "claude",
                Path("/opt/Claude/claude"),
                Path("/snap/bin/claude"),  # Snap package
                Path.home() / "AppImages" / "Claude.AppImage",
            ]
        )
        # Also check PATH
        claude_in_path = shutil.which("claude")
        if claude_in_path:
            candidates.append(Path(claude_in_path))

    # Check which candidates exist
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            try:
                # Verify it's executable
                if os.access(candidate, os.X_OK):
                    return candidate
            except Exception:
                continue

    return None
