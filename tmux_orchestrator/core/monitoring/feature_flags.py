"""
Feature flag management for gradual rollout of the new monitoring architecture.

This module provides a clean way to control feature rollout with environment
variables, configuration files, and runtime controls.
"""

import json
import os
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class RolloutStage(Enum):
    """Stages of feature rollout."""

    DISABLED = "disabled"  # Old monitor.py only
    CANARY = "canary"  # 5% of monitoring cycles use new system
    BETA = "beta"  # 50% use new system
    PRODUCTION = "production"  # 100% use new system
    LEGACY_DISABLED = "legacy_disabled"  # Old system completely removed


class FeatureFlags(BaseModel):
    """Feature flags for monitoring system rollout."""

    # Core feature flags
    use_modular_monitor: bool = False
    use_plugin_system: bool = False
    use_metrics_collector: bool = False
    use_concurrent_strategy: bool = False

    # Rollout configuration
    rollout_stage: RolloutStage = RolloutStage.DISABLED
    rollout_percentage: float = 0.0  # 0-100

    # Strategy selection
    default_strategy: str = "polling"
    allowed_strategies: list[str] = ["polling", "concurrent"]

    # Performance flags
    enable_async_monitoring: bool = False
    max_concurrent_checks: int = 10

    # Compatibility flags
    maintain_legacy_state_files: bool = True
    migrate_state_on_read: bool = True

    # Debug flags
    parallel_run_comparison: bool = False  # Run both systems and compare
    log_performance_metrics: bool = False
    verbose_migration_logs: bool = False

    # Timestamps
    flags_updated_at: datetime | None = None
    rollout_started_at: datetime | None = None

    class Config:
        use_enum_values = True

    @classmethod
    def load_from_env(cls) -> "FeatureFlags":
        """Load feature flags from environment variables.

        Environment variables:
        - TMUX_ORC_USE_MODULAR_MONITOR=true
        - TMUX_ORC_ROLLOUT_STAGE=beta
        - TMUX_ORC_DEFAULT_STRATEGY=concurrent
        """
        flags: dict[str, Any] = {}

        # Boolean flags
        bool_flags = [
            "use_modular_monitor",
            "use_plugin_system",
            "use_metrics_collector",
            "use_concurrent_strategy",
            "enable_async_monitoring",
            "maintain_legacy_state_files",
            "migrate_state_on_read",
            "parallel_run_comparison",
            "log_performance_metrics",
            "verbose_migration_logs",
        ]

        for flag in bool_flags:
            env_var = f"TMUX_ORC_{flag.upper()}"
            if env_var in os.environ:
                flags[flag] = os.environ[env_var].lower() in ("true", "1", "yes", "on")

        # String flags
        if "TMUX_ORC_ROLLOUT_STAGE" in os.environ:
            try:
                flags["rollout_stage"] = RolloutStage(os.environ["TMUX_ORC_ROLLOUT_STAGE"])
            except ValueError:
                pass

        if "TMUX_ORC_DEFAULT_STRATEGY" in os.environ:
            flags["default_strategy"] = os.environ["TMUX_ORC_DEFAULT_STRATEGY"]

        # Numeric flags
        if "TMUX_ORC_ROLLOUT_PERCENTAGE" in os.environ:
            try:
                flags["rollout_percentage"] = float(os.environ["TMUX_ORC_ROLLOUT_PERCENTAGE"])
            except ValueError:
                pass

        if "TMUX_ORC_MAX_CONCURRENT_CHECKS" in os.environ:
            try:
                flags["max_concurrent_checks"] = int(os.environ["TMUX_ORC_MAX_CONCURRENT_CHECKS"])
            except ValueError:
                pass

        # List flags
        if "TMUX_ORC_ALLOWED_STRATEGIES" in os.environ:
            flags["allowed_strategies"] = os.environ["TMUX_ORC_ALLOWED_STRATEGIES"].split(",")

        flags["flags_updated_at"] = datetime.now()

        return cls(**flags)

    @classmethod
    def load_from_file(cls, file_path: Path) -> "FeatureFlags":
        """Load feature flags from a JSON file.

        Args:
            file_path: Path to feature flags JSON file

        Returns:
            FeatureFlags instance
        """
        if not file_path.exists():
            return cls()

        with open(file_path) as f:
            data = json.load(f)

        # Convert timestamps
        for field in ["flags_updated_at", "rollout_started_at"]:
            if field in data and data[field]:
                data[field] = datetime.fromisoformat(data[field])

        return cls(**data)

    def save_to_file(self, file_path: Path) -> None:
        """Save feature flags to a JSON file.

        Args:
            file_path: Path to save feature flags
        """
        data = self.dict()

        # Convert timestamps to ISO format
        for field in ["flags_updated_at", "rollout_started_at"]:
            if data.get(field):
                data[field] = data[field].isoformat()

        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

    def should_use_new_system(self, cycle_id: int | None = None) -> bool:
        """Determine if the new monitoring system should be used.

        Args:
            cycle_id: Optional monitoring cycle ID for deterministic rollout

        Returns:
            True if new system should be used
        """
        # Check explicit flag first
        if not self.use_modular_monitor:
            return False

        # Check rollout stage
        if self.rollout_stage == RolloutStage.DISABLED:
            return False
        elif self.rollout_stage == RolloutStage.LEGACY_DISABLED:
            return True
        elif self.rollout_stage == RolloutStage.PRODUCTION:
            return True

        # For staged rollout, use percentage
        if self.rollout_stage in (RolloutStage.CANARY, RolloutStage.BETA):
            if cycle_id is not None:
                # Deterministic rollout based on cycle ID
                return (cycle_id % 100) < self.rollout_percentage
            else:
                # Random rollout
                import random

                return random.random() * 100 < self.rollout_percentage

        return False

    def update_rollout_stage(self, new_stage: RolloutStage) -> None:
        """Update the rollout stage with safety checks.

        Args:
            new_stage: New rollout stage
        """
        old_stage = self.rollout_stage
        self.rollout_stage = new_stage

        # Set default percentages for stages
        stage_percentages = {
            RolloutStage.DISABLED: 0.0,
            RolloutStage.CANARY: 5.0,
            RolloutStage.BETA: 50.0,
            RolloutStage.PRODUCTION: 100.0,
            RolloutStage.LEGACY_DISABLED: 100.0,
        }

        if new_stage in stage_percentages:
            self.rollout_percentage = stage_percentages[new_stage]

        # Track rollout start time
        if old_stage == RolloutStage.DISABLED and new_stage != RolloutStage.DISABLED:
            self.rollout_started_at = datetime.now()

        self.flags_updated_at = datetime.now()

    def get_effective_config(self) -> dict[str, Any]:
        """Get the effective configuration based on feature flags.

        Returns:
            Dictionary of effective configuration values
        """
        config = {
            "monitor_implementation": "modular" if self.use_modular_monitor else "legacy",
            "monitoring_strategy": self.default_strategy if self.use_plugin_system else "builtin",
            "metrics_enabled": self.use_metrics_collector,
            "async_enabled": self.enable_async_monitoring,
            "max_concurrency": self.max_concurrent_checks if self.use_concurrent_strategy else 1,
            "state_migration": self.migrate_state_on_read,
        }

        return config


class FeatureFlagManager:
    """Manages feature flags with persistence and hot-reloading."""

    def __init__(self, config_dir: Path):
        """Initialize the feature flag manager.

        Args:
            config_dir: Directory for feature flag storage
        """
        self.config_dir = config_dir
        self.flags_file = config_dir / "feature_flags.json"
        self._flags: FeatureFlags | None = None
        self._last_modified: float | None = None

    def get_flags(self) -> FeatureFlags:
        """Get current feature flags with hot-reload support.

        Returns:
            Current feature flags
        """
        # Check if file has been modified
        if self.flags_file.exists():
            current_mtime = self.flags_file.stat().st_mtime
            if self._last_modified is None or current_mtime > self._last_modified:
                self._flags = FeatureFlags.load_from_file(self.flags_file)
                self._last_modified = current_mtime

        # Load from environment if no file exists
        if self._flags is None:
            self._flags = FeatureFlags.load_from_env()

        return self._flags

    def update_flags(self, updates: dict[str, Any]) -> FeatureFlags:
        """Update feature flags and persist.

        Args:
            updates: Dictionary of flag updates

        Returns:
            Updated feature flags
        """
        flags = self.get_flags()

        for key, value in updates.items():
            if hasattr(flags, key):
                setattr(flags, key, value)

        flags.flags_updated_at = datetime.now()
        flags.save_to_file(self.flags_file)
        self._flags = flags

        return flags

    def reset_flags(self) -> FeatureFlags:
        """Reset all flags to defaults.

        Returns:
            Reset feature flags
        """
        self._flags = FeatureFlags()
        self._flags.save_to_file(self.flags_file)
        return self._flags
