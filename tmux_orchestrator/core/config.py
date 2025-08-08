"""Configuration management for TMUX Orchestrator."""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class Config:
    """Manages configuration for TMUX Orchestrator."""

    DEFAULT_CONFIG = {
        'project': {
            'name': None,
            'path': None
        },
        'team': {
            'pm': {
                'enabled': True,
                'window': 2
            },
            'agents': []
        },
        'monitoring': {
            'idle_check_interval': 10,
            'notification_cooldown': 300
        },
        'orchestrator': {
            'auto_commit_interval': 1800,
            'health_check_interval': 60
        },
        'server': {
            'host': '127.0.0.1',
            'port': 8000
        }
    }

    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        self._config: Dict[str, Any] = config_dict or self.DEFAULT_CONFIG.copy()

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> 'Config':
        """Load configuration from file or defaults."""
        if config_path is None:
            # Look for config in standard locations
            search_paths = [
                Path.cwd() / '.tmux-orchestrator' / 'config.yml',
                Path.cwd() / '.tmux-orchestrator' / 'config.yaml',
                Path.home() / '.config' / 'tmux-orchestrator' / 'config.yml',
                Path.home() / '.tmux-orchestrator' / 'config.yml',
            ]

            for path in search_paths:
                if path.exists():
                    config_path = path
                    break

        if config_path and config_path.exists():
            with open(config_path) as f:
                config_dict: Dict[str, Any] = yaml.safe_load(f) or {}
                # Merge with defaults
                merged_config = cls.DEFAULT_CONFIG.copy()
                cls._deep_merge(merged_config, config_dict)
                return cls(merged_config)

        # Check environment variables
        config = cls(cls.DEFAULT_CONFIG.copy())
        config._load_from_env()
        return config

    @staticmethod
    def _deep_merge(base: Dict[str, Any], update: Dict[str, Any]) -> None:
        """Deep merge update dict into base dict."""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                Config._deep_merge(base[key], value)
            else:
                base[key] = value

    def _load_from_env(self) -> None:
        """Load configuration from environment variables."""
        # Project settings
        if 'TMUX_ORCHESTRATOR_PROJECT' in os.environ:
            self._config['project']['path'] = os.environ['TMUX_ORCHESTRATOR_PROJECT']
            self._config['project']['name'] = Path(os.environ['TMUX_ORCHESTRATOR_PROJECT']).name

        # Server settings
        if 'TMUX_ORCHESTRATOR_HOST' in os.environ:
            self._config['server']['host'] = os.environ['TMUX_ORCHESTRATOR_HOST']
        if 'TMUX_ORCHESTRATOR_PORT' in os.environ:
            self._config['server']['port'] = int(os.environ['TMUX_ORCHESTRATOR_PORT'])

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation."""
        keys = key.split('.')
        value: Any = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """Set configuration value using dot notation."""
        keys = key.split('.')
        config: Dict[str, Any] = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def save(self, config_path: Optional[Path] = None) -> None:
        """Save configuration to file."""
        if config_path is None:
            config_path = Path.cwd() / '.tmux-orchestrator' / 'config.yml'

        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, 'w') as f:
            yaml.dump(self._config, f, default_flow_style=False)

    @property
    def project_name(self) -> Optional[str]:
        """Get project name."""
        project_config = self._config['project']
        name = project_config.get('name')
        path = project_config.get('path')
        return name or (Path(path).name if path else None)

    @property
    def project_path(self) -> Optional[Path]:
        """Get project path."""
        path = self._config['project']['path']
        return Path(path) if path else None

    @property
    def monitoring_interval(self) -> int:
        """Get monitoring interval."""
        return int(self._config['monitoring']['idle_check_interval'])

    @property
    def notification_cooldown(self) -> int:
        """Get notification cooldown."""
        return int(self._config['monitoring']['notification_cooldown'])

    def get_agent_config(self, agent_type: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific agent type."""
        agents = self._config['team']['agents']
        for agent in agents:
            if isinstance(agent, dict) and agent.get('type') == agent_type:
                return agent
        return None
