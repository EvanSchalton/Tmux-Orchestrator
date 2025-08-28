"""Check system requirements and provide setup guidance."""

import platform
import subprocess

from rich.console import Console

console = Console()


def check_requirements() -> None:
    """Check system requirements and provide setup guidance.

    Verifies that all required dependencies are installed and provides
    platform-specific installation instructions if any are missing.

    Examples:
        tmux-orc setup        # Run system check
    """
    console.print("[bold]Tmux Orchestrator System Setup Check[/bold]\n")

    # Check tmux installation
    console.print("Checking for tmux...", end=" ")
    try:
        result = subprocess.run(["tmux", "-V"], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            console.print(f"[green]✓ Found {version}[/green]")
        else:
            raise FileNotFoundError
    except FileNotFoundError:
        console.print("[red]✗ Not found[/red]")
        console.print("\n[yellow]tmux is required but not installed![/yellow]")

        # Provide platform-specific installation instructions
        system = platform.system().lower()
        if system == "darwin":
            console.print("\nInstall tmux on macOS:")
            console.print("  [cyan]brew install tmux[/cyan]")
        elif system == "linux":
            # Try to detect Linux distribution
            try:
                with open("/etc/os-release") as f:
                    os_info = f.read().lower()
                    if "ubuntu" in os_info or "debian" in os_info:
                        console.print("\nInstall tmux on Ubuntu/Debian:")
                        console.print("  [cyan]sudo apt-get update && sudo apt-get install -y tmux[/cyan]")
                    elif "fedora" in os_info or "centos" in os_info or "rhel" in os_info:
                        console.print("\nInstall tmux on Fedora/CentOS/RHEL:")
                        console.print("  [cyan]sudo yum install -y tmux[/cyan]")
                    elif "arch" in os_info:
                        console.print("\nInstall tmux on Arch Linux:")
                        console.print("  [cyan]sudo pacman -S tmux[/cyan]")
                    else:
                        console.print("\nInstall tmux on Linux:")
                        console.print("  Use your distribution's package manager to install 'tmux'")
            except Exception:
                console.print("\nInstall tmux on Linux:")
                console.print("  Use your distribution's package manager to install 'tmux'")
        else:
            console.print("\nPlease install tmux for your operating system")
            console.print("Visit: https://github.com/tmux/tmux/wiki/Installing")
        return

    # Check Python version
    console.print("Checking Python version...", end=" ")
    py_version = platform.python_version()
    py_major, py_minor = map(int, py_version.split(".")[:2])
    if py_major >= 3 and py_minor >= 11:
        console.print(f"[green]✓ Python {py_version}[/green]")
    else:
        console.print(f"[yellow]⚠ Python {py_version} (3.11+ recommended)[/yellow]")

    # Check if tmux-orc is properly installed
    console.print("Checking tmux-orc installation...", end=" ")
    try:
        import tmux_orchestrator  # noqa: F401

        console.print("[green]✓ Installed[/green]")
    except ImportError:
        console.print("[red]✗ Not properly installed[/red]")
        console.print("\nRun: [cyan]pip install git+https://github.com/EvanSchalton/Tmux-Orchestrator.git[/cyan]")
        return

    console.print("\n[green]✓ All system requirements met![/green]")
    console.print("\nNext steps:")
    console.print("1. Set up Claude Code integration: [cyan]tmux-orc setup claude-code[/cyan]")
    console.print("2. Configure VS Code: [cyan]tmux-orc setup vscode[/cyan]")
    console.print("3. Configure tmux: [cyan]tmux-orc setup tmux[/cyan]")
    console.print("4. Or run all setups: [cyan]tmux-orc setup all[/cyan]")
