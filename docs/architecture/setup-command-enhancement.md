# Setup Command Enhancement Guide

## 🎯 Overview

The `tmux-orc setup` command is the cornerstone of the simplified deployment strategy, handling all one-time configuration including Claude Desktop MCP registration.

## 🔧 Enhanced Setup Command Design

### **Current Setup Scope**
The setup command should handle:

1. **Tmux Configuration**: Verify and configure tmux environment
2. **Claude MCP Registration**: Register MCP server with Claude Desktop
3. **Shell Completion**: Install shell completions
4. **Initial Configuration**: Create default configuration files
5. **Validation**: Verify all components working

### **Implementation Structure**

```python
# tmux_orchestrator/cli/commands/setup.py

import click
import platform
import json
from pathlib import Path
from typing import Optional, Tuple

@click.command()
@click.option('--skip-tmux', is_flag=True, help='Skip tmux configuration')
@click.option('--skip-mcp', is_flag=True, help='Skip MCP registration')
@click.option('--skip-completion', is_flag=True, help='Skip shell completion')
@click.option('--force', is_flag=True, help='Force overwrite existing config')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def setup(skip_tmux, skip_mcp, skip_completion, force, verbose):
    """Set up tmux-orchestrator environment and integrations.

    This command handles all one-time setup tasks:
    • Tmux environment configuration
    • Claude Desktop MCP server registration
    • Shell completion installation
    • Initial configuration creation

    Run this once after installation to get everything working.
    """
    click.secho("🚀 Setting up tmux-orchestrator...", fg='green', bold=True)

    setup_results = []

    # Step 1: Tmux Configuration
    if not skip_tmux:
        result = setup_tmux_environment(verbose)
        setup_results.append(("Tmux Environment", result))

    # Step 2: Claude MCP Registration
    if not skip_mcp:
        result = setup_claude_mcp_integration(force, verbose)
        setup_results.append(("Claude MCP Integration", result))

    # Step 3: Shell Completion
    if not skip_completion:
        result = setup_shell_completion(verbose)
        setup_results.append(("Shell Completion", result))

    # Step 4: Initial Configuration
    result = setup_initial_configuration(force, verbose)
    setup_results.append(("Initial Configuration", result))

    # Step 5: Validation
    result = validate_setup(verbose)
    setup_results.append(("Setup Validation", result))

    # Report Results
    display_setup_results(setup_results)

    # Final Instructions
    display_next_steps()

def setup_tmux_environment(verbose: bool) -> dict:
    """Configure tmux environment for orchestrator."""
    if verbose:
        click.echo("🔧 Configuring tmux environment...")

    try:
        # Check if tmux is installed
        import subprocess
        result = subprocess.run(['tmux', '-V'], capture_output=True, text=True)
        if result.returncode != 0:
            return {
                "success": False,
                "message": "tmux not found. Please install tmux first.",
                "suggestion": "Install with: apt install tmux (Ubuntu) or brew install tmux (macOS)"
            }

        tmux_version = result.stdout.strip()

        # Create tmux config directory if needed
        tmux_config_dir = Path.home() / ".tmux"
        tmux_config_dir.mkdir(exist_ok=True)

        # Check for existing orchestrator config
        orchestrator_config = tmux_config_dir / "orchestrator.conf"

        if not orchestrator_config.exists():
            # Create minimal orchestrator tmux config
            config_content = """
# Tmux Orchestrator Configuration
# Optimized settings for agent management

# Enable mouse support for easier session management
set -g mouse on

# Increase history limit for agent output
set-option -g history-limit 10000

# Set window and pane numbering to start from 1
set -g base-index 1
setw -g pane-base-index 1

# Auto-renumber windows when one is closed
set -g renumber-windows on

# Enable focus events (useful for agent monitoring)
set -g focus-events on

# Orchestrator-specific key bindings
bind-key O display-popup -E "tmux-orc list"
bind-key S display-popup -E "tmux-orc status"
"""

            with open(orchestrator_config, 'w') as f:
                f.write(config_content.strip())

        return {
            "success": True,
            "message": f"tmux environment configured ({tmux_version})",
            "details": {
                "tmux_version": tmux_version,
                "config_path": str(orchestrator_config)
            }
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to configure tmux: {e}",
            "suggestion": "Check tmux installation and permissions"
        }

def setup_claude_mcp_integration(force: bool, verbose: bool) -> dict:
    """Register MCP server with Claude Desktop."""
    if verbose:
        click.echo("🤖 Setting up Claude Desktop MCP integration...")

    # Get Claude config path
    config_path = get_claude_config_path()

    if not config_path:
        return {
            "success": False,
            "message": "Claude Desktop not found on this system",
            "suggestion": "Install Claude Desktop from https://claude.ai/download"
        }

    try:
        # Load existing config
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
        else:
            config = {}

        # Check if already configured
        if 'mcpServers' in config and 'tmux-orchestrator' in config['mcpServers']:
            if not force:
                return {
                    "success": True,
                    "message": "MCP server already registered with Claude",
                    "details": {"config_path": str(config_path)}
                }

        # Ensure mcpServers section exists
        if 'mcpServers' not in config:
            config['mcpServers'] = {}

        # Add tmux-orchestrator server
        config['mcpServers']['tmux-orchestrator'] = {
            "command": "tmux-orc",
            "args": ["server", "start"],
            "env": {
                "TMUX_ORC_MCP_MODE": "claude"
            },
            "disabled": False
        }

        # Ensure parent directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Write updated config
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

        return {
            "success": True,
            "message": "MCP server registered with Claude Desktop",
            "details": {
                "config_path": str(config_path),
                "command": "tmux-orc server start"
            },
            "restart_required": True
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to register MCP server: {e}",
            "suggestion": "Check Claude Desktop installation and permissions"
        }

def get_claude_config_path() -> Optional[Path]:
    """Get Claude Desktop config path for current platform."""
    system = platform.system()

    if system == "Darwin":  # macOS
        config_path = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif system == "Windows":
        config_path = Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
    elif system == "Linux":
        xdg_config = os.environ.get('XDG_CONFIG_HOME', Path.home() / ".config")
        config_path = Path(xdg_config) / "Claude" / "claude_desktop_config.json"
    else:
        return None

    # Check if Claude installation exists
    if config_path.parent.exists() or config_path.exists():
        return config_path

    return None

def setup_shell_completion(verbose: bool) -> dict:
    """Install shell completion for tmux-orc command."""
    if verbose:
        click.echo("🔧 Setting up shell completion...")

    try:
        # This would integrate with Click's completion system
        # Implementation depends on shell detection

        shell = detect_shell()

        if shell == "bash":
            return setup_bash_completion()
        elif shell == "zsh":
            return setup_zsh_completion()
        elif shell == "fish":
            return setup_fish_completion()
        else:
            return {
                "success": False,
                "message": f"Shell completion not supported for {shell}",
                "suggestion": "Completion available for bash, zsh, and fish"
            }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to setup completion: {e}",
            "suggestion": "Continue without completion - not critical"
        }

def setup_initial_configuration(force: bool, verbose: bool) -> dict:
    """Create initial configuration files."""
    if verbose:
        click.echo("📝 Creating initial configuration...")

    try:
        # Create config directory
        config_dir = Path.home() / ".tmux_orchestrator"
        config_dir.mkdir(exist_ok=True)

        # Create main config file
        config_file = config_dir / "config.json"

        if not config_file.exists() or force:
            initial_config = {
                "version": "2.1.23",
                "setup_date": click.DateTime().today().isoformat(),
                "preferences": {
                    "default_agent_type": "developer",
                    "json_output": False,
                    "auto_attach": True
                },
                "claude_integration": {
                    "enabled": True,
                    "mcp_registered": True
                }
            }

            with open(config_file, 'w') as f:
                json.dump(initial_config, f, indent=2)

        return {
            "success": True,
            "message": "Initial configuration created",
            "details": {"config_path": str(config_file)}
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to create configuration: {e}",
            "suggestion": "Check home directory permissions"
        }

def validate_setup(verbose: bool) -> dict:
    """Validate that setup completed successfully."""
    if verbose:
        click.echo("✅ Validating setup...")

    validation_results = []

    # Test CLI commands
    try:
        import subprocess
        result = subprocess.run(['tmux-orc', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            validation_results.append(("CLI Command", True, result.stdout.strip()))
        else:
            validation_results.append(("CLI Command", False, "Command failed"))
    except Exception as e:
        validation_results.append(("CLI Command", False, str(e)))

    # Test MCP server
    try:
        result = subprocess.run(['tmux-orc', 'server', 'tools'], capture_output=True, text=True)
        if result.returncode == 0:
            validation_results.append(("MCP Server", True, "Server functional"))
        else:
            validation_results.append(("MCP Server", False, "Server issues"))
    except Exception as e:
        validation_results.append(("MCP Server", False, str(e)))

    # Check Claude registration
    config_path = get_claude_config_path()
    if config_path and config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)

            if 'mcpServers' in config and 'tmux-orchestrator' in config['mcpServers']:
                validation_results.append(("Claude Integration", True, "MCP registered"))
            else:
                validation_results.append(("Claude Integration", False, "Not registered"))
        except:
            validation_results.append(("Claude Integration", False, "Config error"))
    else:
        validation_results.append(("Claude Integration", False, "Claude not found"))

    # Overall success
    all_passed = all(result[1] for result in validation_results)

    return {
        "success": all_passed,
        "message": "Setup validation completed",
        "details": validation_results
    }

def display_setup_results(results: list):
    """Display setup results in a user-friendly format."""
    click.echo("\n📊 Setup Results:")
    click.echo("=" * 50)

    for component, result in results:
        if result["success"]:
            click.secho(f"✅ {component}", fg='green')
            click.echo(f"   {result['message']}")
        else:
            click.secho(f"❌ {component}", fg='red')
            click.echo(f"   {result['message']}")
            if 'suggestion' in result:
                click.secho(f"   💡 {result['suggestion']}", fg='yellow')

    click.echo("=" * 50)

def display_next_steps():
    """Display next steps for the user."""
    click.echo("\n🎉 Setup Complete!")
    click.echo("\nNext Steps:")
    click.echo("1. Restart Claude Desktop to activate MCP integration")
    click.echo("2. Try basic commands:")
    click.echo("   • tmux-orc list")
    click.echo("   • tmux-orc status")
    click.echo("3. In Claude Desktop, you should see tmux-orchestrator tools available")
    click.echo("\nFor help: tmux-orc --help")
```

## 🧪 Testing Setup Command

### **Local Testing**
```bash
# Test setup command
tmux-orc setup --verbose

# Test with options
tmux-orc setup --skip-mcp --force

# Validate after setup
tmux-orc server status
```

### **Integration Testing**
```bash
# Test Claude integration
# After setup + Claude restart
# Check tools appear in Claude
```

## 📊 Success Metrics

- [ ] Tmux environment configured
- [ ] Claude MCP registration successful
- [ ] Shell completion installed
- [ ] Configuration files created
- [ ] All validation checks pass
- [ ] Clear user guidance provided

The enhanced setup command becomes the single point of entry for all tmux-orchestrator configuration, making the deployment strategy truly simple and reliable.
