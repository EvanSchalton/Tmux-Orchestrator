"""Lazy loading system for CLI commands to improve startup performance.

Reduces CLI startup time from 1-2.4s to <200ms by deferring imports until needed.
"""

import importlib
from typing import Any, Optional, cast

import click


class LazyCommandGroup(click.Group):
    """Click Group that loads commands lazily on first access."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lazy_commands: dict[str, dict[str, Any]] = {}

    def add_lazy_command(
        self,
        name: str,
        module_path: str,
        command_attr: str,
        fallback_module: Optional[str] = None,
        fallback_attr: Optional[str] = None,
    ) -> None:
        """Register a command for lazy loading.

        Args:
            name: Command name
            module_path: Python module path (e.g., 'tmux_orchestrator.cli.agent')
            command_attr: Attribute name in module (e.g., 'agent')
            fallback_module: Optional fallback module if primary fails
            fallback_attr: Optional fallback attribute name
        """
        self._lazy_commands[name] = {
            "module_path": module_path,
            "command_attr": command_attr,
            "fallback_module": fallback_module,
            "fallback_attr": fallback_attr,
            "loaded": False,
            "command": None,
        }

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        """Get command, loading lazily if needed."""
        # Check if already loaded
        if cmd_name in self.commands:
            return self.commands[cmd_name]

        # Check if it's a lazy command
        if cmd_name in self._lazy_commands:
            return self._load_lazy_command(cmd_name)

        return None

    def list_commands(self, ctx: click.Context) -> list[str]:
        """List all available commands including lazy ones."""
        commands = list(self.commands.keys())
        commands.extend(self._lazy_commands.keys())
        return sorted(commands)

    def _load_lazy_command(self, cmd_name: str) -> click.Command | None:
        """Load a lazy command on demand."""
        cmd_info = self._lazy_commands[cmd_name]

        if cmd_info["loaded"]:
            return cmd_info["command"]

        try:
            # Try primary module
            module = importlib.import_module(cmd_info["module_path"])
            command = getattr(module, cmd_info["command_attr"])

            # Add to commands dict for future access
            self.commands[cmd_name] = command
            cmd_info["loaded"] = True
            cmd_info["command"] = command

            return command

        except (ImportError, AttributeError):
            # Try fallback if available
            if cmd_info["fallback_module"] and cmd_info["fallback_attr"]:
                try:
                    fallback_module = importlib.import_module(cmd_info["fallback_module"])
                    command = getattr(fallback_module, cmd_info["fallback_attr"])

                    self.commands[cmd_name] = command
                    cmd_info["loaded"] = True
                    cmd_info["command"] = command

                    return command

                except (ImportError, AttributeError):
                    pass

            # Mark as failed to avoid repeated attempts
            cmd_info["loaded"] = True
            cmd_info["command"] = None
            return None


def create_lazy_cli() -> LazyCommandGroup:
    """Create CLI with lazy-loaded command groups for optimal startup performance."""

    # Create lazy CLI group
    cli = LazyCommandGroup(name="tmux-orc", help="TMUX Orchestrator - AI-powered tmux session management.")

    # Register all command groups for lazy loading
    cli.add_lazy_command("agent", "tmux_orchestrator.cli.agent", "agent")

    cli.add_lazy_command("monitor", "tmux_orchestrator.cli.monitor", "monitor")

    cli.add_lazy_command("pm", "tmux_orchestrator.cli.pm", "pm")

    cli.add_lazy_command("context", "tmux_orchestrator.cli.context", "context")

    cli.add_lazy_command(
        "team",
        "tmux_orchestrator.cli.team",
        "team",
        fallback_module="tmux_orchestrator.cli.team_compose",
        fallback_attr="team",
    )

    cli.add_lazy_command("orchestrator", "tmux_orchestrator.cli.orchestrator", "orchestrator")

    cli.add_lazy_command("setup", "tmux_orchestrator.cli.setup_claude", "setup")

    cli.add_lazy_command("spawn", "tmux_orchestrator.cli.spawn", "spawn")

    cli.add_lazy_command("spawn-orc", "tmux_orchestrator.cli.spawn_orc", "spawn_orc")

    cli.add_lazy_command("recovery", "tmux_orchestrator.cli.recovery", "recovery")

    cli.add_lazy_command("session", "tmux_orchestrator.cli.session", "session")

    cli.add_lazy_command("pubsub", "tmux_orchestrator.cli.pubsub", "pubsub")

    # Note: pubsub-fast was consolidated into pubsub

    cli.add_lazy_command("daemon", "tmux_orchestrator.cli.daemon", "daemon")

    cli.add_lazy_command("tasks", "tmux_orchestrator.cli.tasks", "tasks")

    cli.add_lazy_command("execute", "tmux_orchestrator.cli.execute", "execute")

    cli.add_lazy_command("errors", "tmux_orchestrator.cli.errors", "errors")

    cli.add_lazy_command("server", "tmux_orchestrator.cli.server", "server")

    return cli


class LazyCommand(click.Command):
    """Individual command that loads lazily."""

    def __init__(self, name: str, module_path: str, command_attr: str, **kwargs):
        self.module_path = module_path
        self.command_attr = command_attr
        self._loaded_command: Optional[click.Command] = None
        super().__init__(name, **kwargs)

    def invoke(self, ctx: click.Context) -> Any:
        """Load and invoke the actual command."""
        if self._loaded_command is None:
            module = importlib.import_module(self.module_path)
            self._loaded_command = getattr(module, self.command_attr)

        return self._loaded_command.invoke(ctx)

    def get_usage(self, ctx: click.Context) -> str:
        """Get usage, loading command if needed."""
        if self._loaded_command is None:
            try:
                module = importlib.import_module(self.module_path)
                self._loaded_command = getattr(module, self.command_attr)
            except (ImportError, AttributeError):
                return cast(str, super().get_usage(ctx))

        return cast(str, self._loaded_command.get_usage(ctx))

    def get_help(self, ctx: click.Context) -> str | None:
        """Get help text, loading command if needed."""
        if self._loaded_command is None:
            try:
                module = importlib.import_module(self.module_path)
                self._loaded_command = getattr(module, self.command_attr)
            except (ImportError, AttributeError):
                return cast(Optional[str], super().get_help(ctx))

        return cast(Optional[str], self._loaded_command.get_help(ctx))
