# Project Cleanup Command

## Purpose
Automatically organize and clean up the planning directory structure by moving completed projects, archiving obsolete ones, and organizing loose files.

## Usage
```bash
# In Claude Code, type:
/project-cleanup
```

## What This Command Does

### 1. **Identify Completed Projects**
- Scans planning directory for projects with `project-closeout.md`, `*-complete.md`, or similar completion indicators
- Moves completed projects from `/planning/` to `/planning/completed/`

### 2. **Archive Obsolete Projects**
- Identifies projects that are no longer relevant based on:
  - Age (older projects that were superseded)
  - Duplicate functionality (multiple projects doing the same thing)
  - Projects marked as obsolete in their documentation
- Moves obsolete projects to `/planning/archived/`

### 3. **Organize Loose Files**
- Moves loose files from planning root to `/planning/_cleanup/loose-files/`
- Moves loose files from project root to `/planning/_cleanup/root-cleanup/`
- Preserves important files like README.md, CLAUDE.md, etc.

### 4. **Clean Up Empty Directories**
- Removes empty project directories
- Consolidates partial/incomplete projects

## Implementation

The command performs these operations:

```bash
#!/bin/bash
# Project Cleanup Script

PLANNING_DIR="/workspaces/Tmux-Orchestrator/.tmux_orchestrator/planning"
ROOT_DIR="/workspaces/Tmux-Orchestrator"

echo "🧹 Starting project cleanup..."

# 1. Find and move completed projects
echo "📋 Checking for completed projects..."
find "$PLANNING_DIR" -maxdepth 1 -type d -name "20*" | while read project_dir; do
    if [ -f "$project_dir/project-closeout.md" ] ||
       [ -f "$project_dir/"*"complete.md" ] ||
       [ -f "$project_dir/"*"closeout"* ]; then
        project_name=$(basename "$project_dir")
        echo "  ✅ Moving completed: $project_name"
        mv "$project_dir" "$PLANNING_DIR/completed/"
    fi
done

# 2. Move loose files from planning root
echo "📁 Organizing loose files in planning..."
mkdir -p "$PLANNING_DIR/_cleanup/loose-files"
find "$PLANNING_DIR" -maxdepth 1 -type f -name "*.md" -o -name "*.txt" -o -name "*.log" | while read file; do
    if [ "$(basename "$file")" != "README.md" ] &&
       [ "$(basename "$file")" != "EXECUTION_STRATEGY.md" ]; then
        echo "  📄 Moving: $(basename "$file")"
        mv "$file" "$PLANNING_DIR/_cleanup/loose-files/"
    fi
done

# 3. Move loose files from root
echo "🏠 Cleaning up root directory..."
mkdir -p "$PLANNING_DIR/_cleanup/root-cleanup"
find "$ROOT_DIR" -maxdepth 1 -type f \( -name "*.md" -o -name "*.py" -o -name "*.txt" -o -name "*.log" \) \
    ! -name "README.md" ! -name "CHANGELOG.md" ! -name "CLAUDE.md" \
    ! -name "DEVELOPMENT-GUIDE.md" ! -name "requirements*.txt" \
    ! -name "setup.py" ! -name "pyproject.toml" ! -name "pytest.ini" \
    ! -name "tasks.py" | while read file; do
    echo "  🏠 Moving: $(basename "$file")"
    mv "$file" "$PLANNING_DIR/_cleanup/root-cleanup/"
done

# 4. Remove empty directories
echo "🗑️  Removing empty project directories..."
find "$PLANNING_DIR" -maxdepth 1 -type d -empty -name "20*" | while read empty_dir; do
    echo "  🗑️  Removing: $(basename "$empty_dir")"
    rmdir "$empty_dir"
done

# 5. Clean up orphaned test sessions
echo "🧪 Cleaning up test sessions..."
tmux list-sessions -F "#{session_name}" 2>/dev/null | grep -E "(tmux-orc-stress-|tmux-orc-error-|invalid|newsession|test-pm-session|test-session)" | while read session; do
    echo "  🧪 Killing test session: $session"
    tmux kill-session -t "$session" 2>/dev/null || true
done

# 6. Archive very old projects (older than 30 days without activity)
echo "📦 Checking for archival candidates..."
find "$PLANNING_DIR" -maxdepth 1 -type d -name "20*" | while read project_dir; do
    if [ ! -d "$PLANNING_DIR/completed/$(basename "$project_dir")" ] &&
       [ ! -d "$PLANNING_DIR/archived/$(basename "$project_dir")" ]; then

        # Check if directory hasn't been modified in 30 days
        if [ $(find "$project_dir" -type f -mtime -30 | wc -l) -eq 0 ] &&
           [ $(find "$project_dir" -name "*active*" -o -name "*current*" | wc -l) -eq 0 ]; then
            project_name=$(basename "$project_dir")
            echo "  📦 Archiving old project: $project_name"
            mv "$project_dir" "$PLANNING_DIR/archived/"
        fi
    fi
done

echo "✅ Project cleanup complete!"
echo ""
echo "📊 Summary:"
echo "  📁 Completed projects moved to: planning/completed/"
echo "  📦 Archived projects moved to: planning/archived/"
echo "  🧹 Loose files organized in: planning/_cleanup/"
echo ""
echo "🔍 Review the organized files and remove any that are no longer needed."
```

## Safety Features

- **No deletion**: Files are moved, never deleted
- **Preserves important files**: README.md, CLAUDE.md, requirements.txt, etc. are never moved
- **Backup location**: All moved files can be easily retrieved from _cleanup directories
- **Incremental**: Can be run multiple times safely

## After Running

1. **Review the organized files** in `_cleanup/` directories
2. **Confirm completed projects** are properly moved
3. **Delete obsolete files** manually after review
4. **Update any references** to moved projects in documentation

## Manual Review Recommended

While this command automates the basic organization, manual review is recommended for:
- Projects that might still be active but lack clear status indicators
- Files that might be important but don't follow naming conventions
- Cross-references between projects that might be broken

---

*This command helps maintain a clean, organized project structure for better navigation and understanding of project history.*
