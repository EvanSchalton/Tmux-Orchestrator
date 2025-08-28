"""Pydantic models for monitor commands."""

from pathlib import Path

from pydantic import BaseModel, validator


class ConfigPath(BaseModel):
    """Pydantic model to validate config file paths against path traversal."""

    path: str

    @validator("path")
    def validate_config_path(cls, v):  # noqa: N805
        """Validate config file path to prevent path traversal attacks."""
        if not v:
            return v

        config_path = Path(v).resolve()

        # Allow only specific safe directories for config files
        allowed_dirs = [
            Path.cwd().resolve(),  # Current working directory
            Path.home().resolve() / ".config" / "tmux-orchestrator",  # User config dir
            Path.home().resolve() / ".tmux_orchestrator",  # User home config
            (Path.cwd() / ".tmux_orchestrator").resolve(),  # Project config
        ]

        # Check if the config file is within any allowed directory
        for allowed_dir in allowed_dirs:
            try:
                config_path.relative_to(allowed_dir)
                # If we get here, the path is within an allowed directory
                break
            except ValueError:
                continue
        else:
            # Path is not within any allowed directory
            raise ValueError(f"Config file path not allowed: {v}. Must be within allowed directories.")

        # Additional security: ensure it's a .yml, .yaml, or .conf file
        if config_path.suffix.lower() not in [".yml", ".yaml", ".conf", ".json"]:
            raise ValueError(f"Config file must have .yml, .yaml, .conf, or .json extension: {v}")

        return str(config_path)
