---
description: Clean up Claude configuration files to improve performance
thinking: "The user wants to reduce Claude performance issues by cleaning up bloated config files. I'll create a command that backs up and cleans the main culprits we identified: conversation history and project cache."
---

# Clean Up Claude Configuration

This command helps reduce Claude Code performance issues by cleaning up bloated configuration files.

## What it does:

1. Creates a timestamped backup of your Claude configuration
2. Reduces conversation history to the last 10 entries
3. Clears project cache directories
4. Shows before/after file sizes

## Execute cleanup:

```bash
# Create backup directory
BACKUP_DIR=~/claude-backup-$(date +%Y%m%d-%H%M%S)
mkdir -p $BACKUP_DIR

# Backup important files
echo "📦 Creating backup in $BACKUP_DIR..."
cp ~/.claude.json $BACKUP_DIR/claude.json.backup 2>/dev/null || echo "No .claude.json found"
cp -r ~/.claude/projects $BACKUP_DIR/ 2>/dev/null || echo "No projects directory found"

# Show current sizes
echo -e "\n📊 Current file sizes:"
ls -lh ~/.claude.json 2>/dev/null || echo "No .claude.json found"
du -sh ~/.claude/projects/* 2>/dev/null || echo "No project caches found"

# Clean conversation history (keep last 10 entries)
if [ -f ~/.claude.json ]; then
    echo -e "\n🧹 Cleaning conversation history..."
    cat ~/.claude.json | jq '.projects |= with_entries(.value.history |= .[-10:])' > ~/.claude.json.tmp && mv ~/.claude.json.tmp ~/.claude.json
    echo "✅ Kept last 10 history entries per project"
fi

# Clean project cache
if [ -d ~/.claude/projects ]; then
    echo -e "\n🧹 Cleaning project cache..."
    find ~/.claude/projects -type f -delete
    echo "✅ Cleared project cache files"
fi

# Show new sizes
echo -e "\n📊 New file sizes:"
ls -lh ~/.claude.json 2>/dev/null || echo "No .claude.json found"
du -sh ~/.claude/projects/* 2>/dev/null || echo "No project caches found"

echo -e "\n✨ Cleanup complete! Backup saved to: $BACKUP_DIR"
```

## Tips:

- Run this command periodically if you notice Claude Code slowing down
- The main culprits are usually:
  - `~/.claude.json` - Contains conversation history
  - `~/.claude/projects/` - Contains project caches
- Your backup can be restored if needed by copying files back from the backup directory
