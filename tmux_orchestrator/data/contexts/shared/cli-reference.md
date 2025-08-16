# tmux-orc CLI Discovery Guide

## 🚨 IMPORTANT: Dynamic Command Discovery

**DO NOT rely on hardcoded command examples below.** The tmux-orc CLI is actively evolving. Instead:

### 🎯 **NEW: Dynamic CLI Discovery**

Use the `reflect` command for always-current CLI structure:

```bash
# Tree view of all commands and subcommands
tmux-orc reflect

# JSON format for automation tools
tmux-orc reflect --format json

# Markdown format for documentation
tmux-orc reflect --format markdown
```

This command automatically discovers all available commands, options, and help text without requiring manual updates.

### 🔍 **ALWAYS start with `--help` flags:**

```bash
# Discover all available commands
tmux-orc --help

# Explore specific command groups
tmux-orc agent --help
tmux-orc monitor --help
tmux-orc spawn --help
tmux-orc team --help
tmux-orc tasks --help
tmux-orc pm --help

# Get detailed help for specific commands
tmux-orc agent message --help
tmux-orc monitor start --help
tmux-orc spawn pm --help
```

### 📋 **Command Discovery Workflow:**

1. **Start with main help**: `tmux-orc --help`
2. **Explore command groups**: `tmux-orc [GROUP] --help`
3. **Check specific commands**: `tmux-orc [GROUP] [COMMAND] --help`
4. **Test with examples**: Use the examples shown in help text

### 🎯 **Common Command Patterns:**

```bash
# General pattern for most commands
tmux-orc [GROUP] [COMMAND] [TARGET] [OPTIONS]

# Examples (verify these with --help first!)
tmux-orc spawn pm --session myproject:1
tmux-orc agent message myproject:2 "Hello"
tmux-orc monitor status
tmux-orc team status myproject
```

### 🔧 **Target Format:**
Most commands use `session:window` format (e.g., `myproject:1`, `dev:0`)

### ⚡ **Quick Discovery Examples:**

```bash
# Get complete CLI structure overview
tmux-orc reflect

# Get JSON structure for tools/automation
tmux-orc reflect --format json

# Generate markdown documentation
tmux-orc reflect --format markdown

# What agent commands exist?
tmux-orc agent --help

# What are the agent message options?
tmux-orc agent message --help

# What monitor commands are available?
tmux-orc monitor --help

# How do I spawn a PM?
tmux-orc spawn pm --help
```

## 📚 **Reference Sections (For Context Only)**

> ⚠️ **WARNING**: The specific commands below may be outdated. Always verify with `--help` first!

### Common Command Groups:
- `agent` - Agent management and communication
- `monitor` - System monitoring and health
- `spawn` - Creating new agents/PMs
- `team` - Team coordination and status
- `tasks` - Task management workflows
- `pm` - Project Manager operations
- `session` - Session management
- `setup` - Environment setup

### Typical Workflows:
1. **Start monitoring**: `tmux-orc monitor --help` → explore options
2. **Spawn PM**: `tmux-orc spawn pm --help` → see required args
3. **Check agent status**: `tmux-orc agent --help` → find status commands
4. **Send messages**: `tmux-orc agent --help` → find messaging commands

### Environment & Configuration:
- Use `tmux-orc --help` to see global options
- Check for `--config-file`, `--json`, `--verbose` flags
- Look for environment variable documentation in help text

## 🎯 **Best Practices:**

1. **Never memorize commands** - Always check `--help` first
2. **Use tab completion** if available in your shell
3. **Start with examples** shown in help text
4. **Test commands safely** - many have `--dry-run` options
5. **Check for JSON output** - use `--json` for scripting

## 🔄 **Staying Current:**

This guide intentionally avoids specific command syntax because:
- Commands change frequently during development
- New commands are added regularly
- Options and arguments evolve
- Help text is always authoritative

**Remember: `tmux-orc --help` and `tmux-orc [COMMAND] --help` are your primary references!**
