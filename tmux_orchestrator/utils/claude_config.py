"""Utilities for Claude Desktop MCP configuration."""

import json
import os
import platform
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


def get_claude_config_path() -> Optional[Path]:
    """Get Claude Desktop config path for current platform."""
    system = platform.system()

    if system == "Darwin":  # macOS
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif system == "Windows":
        return Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
    elif system == "Linux":
        xdg_config = os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
        return Path(xdg_config) / "Claude" / "claude_desktop_config.json"

    return None


def check_claude_installation() -> Tuple[bool, Optional[Path]]:
    """Check if Claude Desktop is installed by looking for config directory."""
    config_path = get_claude_config_path()

    if not config_path:
        return False, None

    # Check if Claude is installed (config directory exists)
    if config_path.parent.exists() or config_path.exists():
        return True, config_path

    return False, config_path


def check_mcp_registration() -> Tuple[bool, Optional[Path], Dict[str, Any]]:
    """Check if MCP server is registered with Claude.

    Returns:
        Tuple of (is_registered, config_path, server_details)
    """
    config_path = get_claude_config_path()

    if not config_path or not config_path.exists():
        return False, config_path, {}

    try:
        with open(config_path) as f:
            config = json.load(f)

        servers = config.get("mcpServers", {})
        if "tmux-orchestrator" in servers:
            return True, config_path, servers["tmux-orchestrator"]

    except Exception:
        pass

    return False, config_path, {}


def register_mcp_server() -> Tuple[bool, str]:
    """Register tmux-orchestrator MCP server with Claude Desktop.

    Returns:
        Tuple of (success, message)
    """
    # Check if Claude is installed
    is_installed, config_path = check_claude_installation()

    if not is_installed:
        return False, "Claude Desktop not found. Install from: https://claude.ai/download"

    if not config_path:
        return False, f"Unsupported platform: {platform.system()}"

    try:
        # Load existing config
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
        else:
            config = {}

        # Ensure mcpServers section exists
        if "mcpServers" not in config:
            config["mcpServers"] = {}

        # Add/update tmux-orchestrator MCP server
        config["mcpServers"]["tmux-orchestrator"] = {
            "command": "tmux-orc",
            "args": ["server", "start"],
            "env": {"TMUX_ORC_MCP_MODE": "claude"},
            "disabled": False,
        }

        # Ensure parent directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Write updated config
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

        return True, f"MCP server registered with Claude Desktop at {config_path}"

    except Exception as e:
        return False, f"Failed to register MCP server: {e}"


def update_mcp_registration(enabled: bool = True) -> bool:
    """Enable or disable MCP server in Claude config."""
    config_path = get_claude_config_path()

    if not config_path or not config_path.exists():
        return False

    try:
        with open(config_path) as f:
            config = json.load(f)

        if "mcpServers" in config and "tmux-orchestrator" in config["mcpServers"]:
            config["mcpServers"]["tmux-orchestrator"]["disabled"] = not enabled

            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)

            return True

    except Exception:
        pass

    return False


def get_registration_status() -> Dict[str, Any]:
    """Get comprehensive MCP registration status."""
    is_installed, config_path = check_claude_installation()
    is_registered, _, server_details = check_mcp_registration()

    return {
        "claude_installed": is_installed,
        "config_path": str(config_path) if config_path else None,
        "mcp_registered": is_registered,
        "server_details": server_details,
        "platform": platform.system(),
    }
