"""Reflect command - Generate complete CLI command structure via runtime introspection."""

import click


def _has_regex_chars(pattern: str) -> bool:
    """Check if pattern contains regex metacharacters."""
    regex_chars = r"^$.*+?{}[]|()\\"
    return any(char in pattern for char in regex_chars)


def _matches_filter(command_path: str, filter_pattern: str) -> bool:
    """Check if command path matches the filter pattern."""
    if not filter_pattern:
        return True

    # Detect if pattern is regex
    if _has_regex_chars(filter_pattern):
        # Use regex matching
        import re

        try:
            pattern = re.compile(filter_pattern, re.IGNORECASE)
            return bool(pattern.search(command_path))
        except re.error:
            # Invalid regex, fall back to substring match
            return filter_pattern.lower() in command_path.lower()
    else:
        # Simple substring match (case-insensitive)
        return filter_pattern.lower() in command_path.lower()


def _filter_commands(
    commands: dict[str, click.Command], filter_pattern: str | None, parent_path: str = ""
) -> dict[str, click.Command]:
    """Recursively filter command structure."""
    if not filter_pattern:
        return commands

    filtered: dict[str, click.Command] = {}

    for name, cmd in commands.items():
        full_path = f"{parent_path} {name}".strip()

        if isinstance(cmd, click.Group):
            # For groups, check if group matches or any subcommand matches
            if _matches_filter(full_path, filter_pattern):
                # Group name matches, include entire group
                filtered[name] = cmd
            else:
                # Check subcommands
                sub_filtered = _filter_commands(dict(cmd.commands), filter_pattern, full_path)
                if sub_filtered:
                    # For filtered groups, just use the original group
                    # The filtering is handled when we iterate through subcommands
                    filtered[name] = cmd
        else:
            # For commands, just check the command path
            if _matches_filter(full_path, filter_pattern):
                filtered[name] = cmd

    return filtered


def reflect_commands(ctx: click.Context, format: str, include_hidden: bool, filter: str | None) -> None:
    """Generate complete CLI command structure via runtime introspection.

    <mcp>Discover all available CLI commands dynamically (args: format=tree/json/markdown, filter=pattern). Use this to explore CLI structure, build documentation, or find specific commands. Essential for understanding the full command surface area.</mcp>

    Dynamically discovers and documents all available tmux-orc commands by
    introspecting the Click command hierarchy. Useful for generating documentation,
    building auto-completion systems, or understanding the full CLI surface.

    Args:
        ctx: Click context containing the command hierarchy
        format: Output format - tree (human-readable), json (machine-readable),
               or markdown (documentation)
        include_hidden: Include internal/hidden commands in output

    Output Formats:
        • tree: Hierarchical display with emojis and descriptions
        • json: Structured data suitable for tooling integration
        • markdown: Documentation-ready format with headers

    Examples:
        Interactive exploration:
        $ tmux-orc reflect                    # Browse all commands
        $ tmux-orc reflect --filter agent     # Show only agent commands
        $ tmux-orc reflect --filter "^spawn"  # Commands starting with "spawn"
        $ tmux-orc reflect --filter "send|message"  # Commands matching pattern

        Generate documentation:
        $ tmux-orc reflect --format markdown > CLI_REFERENCE.md
        $ tmux-orc reflect --format markdown --filter team > TEAM_COMMANDS.md

        Build tooling integration:
        $ tmux-orc reflect --format json | jq '.agent.type'
        $ tmux-orc reflect --format json --filter pubsub

        Include internal commands:
        $ tmux-orc reflect --include-hidden   # Show debugging commands

    Real-World Use Cases:
        • API documentation generation for docs site
        • Auto-completion script generation for shells
        • Command discovery during development
        • Integration testing command validation
        • Administrative tooling development
    """
    console = ctx.obj["console"]

    try:
        # Get the root CLI group from the context
        root_cli = ctx.find_root().command

        # Ensure it's a Group with commands attribute
        if not isinstance(root_cli, click.Group):
            console.print("[red]Error: Root command is not a group[/red]")
            return

        # Filter commands if requested
        if filter:
            commands = _filter_commands(dict(root_cli.commands), filter)
            if not commands:
                console.print(f"[yellow]No commands match filter: {filter}[/yellow]")
                return
        else:
            commands = dict(root_cli.commands)

        if format == "json":
            _print_json_format(console, commands, include_hidden)
        elif format == "markdown":
            _print_markdown_format(console, commands, include_hidden)
        else:  # tree format
            _print_tree_format(console, commands, include_hidden)

    except Exception as e:
        console.print(f"[red]Error generating command reflection: {e}[/red]")


def _print_json_format(console, commands: dict, include_hidden: bool) -> None:
    """Print commands in JSON format."""
    import json

    def serialize_command(cmd, path=""):
        if isinstance(cmd, click.Group):
            result = {"type": "group", "name": cmd.name, "help": cmd.help or "", "commands": {}}
            for name, subcmd in cmd.commands.items():
                if not include_hidden and name.startswith("_"):
                    continue
                result["commands"][name] = serialize_command(subcmd, f"{path} {name}".strip())
            return result
        else:
            return {
                "type": "command",
                "name": cmd.name,
                "help": cmd.help or "",
                "params": [{"name": p.name, "type": type(p).__name__} for p in cmd.params],
            }

    result = {}
    for name, cmd in commands.items():
        if not include_hidden and name.startswith("_"):
            continue
        result[name] = serialize_command(cmd, name)

    console.print(json.dumps(result, indent=2))


def _print_markdown_format(console, commands: dict, include_hidden: bool) -> None:
    """Print commands in Markdown format."""
    console.print("# TMUX Orchestrator CLI Reference\n")

    def print_command_md(cmd, level=2):
        if isinstance(cmd, click.Group):
            console.print(f"{'#' * level} {cmd.name}")
            if cmd.help:
                console.print(f"\n{cmd.help}\n")

            for name, subcmd in sorted(cmd.commands.items()):
                if not include_hidden and name.startswith("_"):
                    continue
                print_command_md(subcmd, level + 1)
        else:
            console.print(f"{'#' * level} {cmd.name}")
            if cmd.help:
                console.print(f"\n{cmd.help}\n")

    for name, cmd in sorted(commands.items()):
        if not include_hidden and name.startswith("_"):
            continue
        print_command_md(cmd)


def _print_tree_format(console, commands: dict, include_hidden: bool) -> None:
    """Print commands in tree format."""
    console.print("🌳 [bold green]TMUX Orchestrator CLI Commands[/bold green]\n")

    def print_command_tree(cmd, prefix="", is_last=True):
        if isinstance(cmd, click.Group):
            # Print group
            connector = "└── " if is_last else "├── "
            console.print(f"{prefix}{connector}📁 [bold blue]{cmd.name}[/bold blue]")

            # Brief help if available
            if cmd.help:
                help_text = cmd.help.split("\n")[0][:60] + "..." if len(cmd.help) > 60 else cmd.help.split("\n")[0]
                next_prefix = prefix + ("    " if is_last else "│   ")
                console.print(f"{next_prefix}   [dim]{help_text}[/dim]")

            # Print subcommands
            subcmds = [
                (name, subcmd)
                for name, subcmd in sorted(cmd.commands.items())
                if include_hidden or not name.startswith("_")
            ]

            for i, (name, subcmd) in enumerate(subcmds):
                is_subcmd_last = i == len(subcmds) - 1
                subcmd_prefix = prefix + ("    " if is_last else "│   ")
                print_command_tree(subcmd, subcmd_prefix, is_subcmd_last)
        else:
            # Print command
            connector = "└── " if is_last else "├── "
            console.print(f"{prefix}{connector}⚡ [green]{cmd.name}[/green]")

            # Brief help if available
            if cmd.help:
                help_text = cmd.help.split("\n")[0][:60] + "..." if len(cmd.help) > 60 else cmd.help.split("\n")[0]
                next_prefix = prefix + ("    " if is_last else "│   ")
                console.print(f"{next_prefix}   [dim]{help_text}[/dim]")

    cmd_list = [(name, cmd) for name, cmd in sorted(commands.items()) if include_hidden or not name.startswith("_")]

    for i, (name, cmd) in enumerate(cmd_list):
        is_last = i == len(cmd_list) - 1
        print_command_tree(cmd, "", is_last)
