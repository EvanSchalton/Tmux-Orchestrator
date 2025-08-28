"""Configure tmux with optimal settings for agent development."""

import subprocess
from pathlib import Path

from rich.console import Console

console = Console()


def setup_tmux(force: bool) -> None:
    """Configure tmux with optimal settings for agent development.

    Configures:
    - Mouse support for easy window navigation
    - Scrollback buffer for reviewing agent output
    - Status bar customization
    - Key bindings for common operations

    Examples:
        tmux-orc setup tmux
        tmux-orc setup tmux --force
    """

    console.print("[cyan]Setting up tmux configuration...[/cyan]")

    tmux_conf_path = Path.home() / ".tmux.conf"

    # Check if config exists
    if tmux_conf_path.exists() and not force:
        from rich.prompt import Confirm

        if not Confirm.ask(f"{tmux_conf_path} already exists. Append tmux-orchestrator settings?", default=True):
            console.print("[yellow]Tmux setup cancelled.[/yellow]")
            return
        # Read existing config
        with open(tmux_conf_path) as f:
            existing_config = f.read()
    else:
        existing_config = ""

    # Check if our settings are already present
    if "# Tmux Orchestrator Settings" in existing_config and not force:
        console.print("[green]✓ Tmux already configured for tmux-orchestrator[/green]")
        return

    # Our recommended tmux settings
    tmux_settings = r"""
# Tmux Orchestrator Settings
# Added by tmux-orc setup tmux

# Enable mouse support for easy navigation
set -g mouse on

# Increase scrollback buffer for reviewing agent output
set -g history-limit 10000

# Start windows and panes at 1, not 0
set -g base-index 1
setw -g pane-base-index 1

# Renumber windows when one is closed
set -g renumber-windows on

# Improve colors
set -g default-terminal "screen-256color"

# Status bar improvements
set -g status-style 'bg=colour235 fg=colour255'
set -g status-left-length 50
set -g status-right-length 50

# Highlight active window
setw -g window-status-current-style 'fg=colour255 bg=colour239 bold'

# Activity alerts
setw -g monitor-activity on
set -g visual-activity on

# Easy window switching with Alt+number
bind -n M-1 select-window -t 1
bind -n M-2 select-window -t 2
bind -n M-3 select-window -t 3
bind -n M-4 select-window -t 4
bind -n M-5 select-window -t 5
bind -n M-6 select-window -t 6
bind -n M-7 select-window -t 7
bind -n M-8 select-window -t 8
bind -n M-9 select-window -t 9

# Easy pane navigation with Alt+arrows
bind -n M-Left select-pane -L
bind -n M-Right select-pane -R
bind -n M-Up select-pane -U
bind -n M-Down select-pane -D

# Reload config with Prefix + r
bind r source-file ~/.tmux.conf \; display "Config reloaded!"
"""

    # Write or append configuration
    with open(tmux_conf_path, "a" if existing_config and not force else "w") as f:
        if existing_config and not force:
            f.write("\n")
        f.write(tmux_settings)

    console.print(f"[green]✓ Tmux configuration updated: {tmux_conf_path}[/green]")

    # Check if tmux is running
    try:
        result = subprocess.run(["tmux", "list-sessions"], capture_output=True, text=True)
        if result.returncode == 0:
            console.print("\n[yellow]Tmux is running. To apply changes:[/yellow]")
            console.print("• Run: [cyan]tmux source-file ~/.tmux.conf[/cyan]")
            console.print("• Or press: [cyan]Ctrl+B then :source-file ~/.tmux.conf[/cyan]")
            console.print("• Or press: [cyan]Ctrl+B then r[/cyan] (if using our config)")
    except Exception:
        pass

    console.print("\n[green]Key features enabled:[/green]")
    console.print("• 🖱️  Mouse support - click windows to switch")
    console.print("• 📜 10,000 line scrollback buffer")
    console.print("• ⌨️  Alt+1-9 to switch windows")
    console.print("• 🔄 Ctrl+B then r to reload config")
