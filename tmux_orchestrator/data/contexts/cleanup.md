# Root Directory Cleanup Context

## Overview
This context provides standardized procedures for cleaning up root directory clutter that accumulates during development and agent operations.

## 🧹 Cleanup Philosophy
- **DELETE temporary files** - Don't just move clutter, eliminate it
- **PRESERVE legitimate files** - Don't break functionality
- **PREVENT future accumulation** - Update .gitignore patterns
- **MAINTAIN git cleanliness** - Remove tracking of temporary files

## 📋 Root Directory Cleanup Checklist

### Phase 1: Assessment
1. Run `ls -la` to inventory root directory contents
2. Check `git status` to see what's tracked vs untracked
3. Identify temporary vs legitimate files using categories below

### Phase 2: Delete Temporary Files
**Agent-generated reports** (always temporary):
```bash
rm -f AGENT_STATUS_REPORT.md
rm -f CICD_INVOKE_MIGRATION.md
rm -f QA_SPAWN_AGENT_TEST_REPORT.md
rm -f *_REPORT.md
rm -f *_SUMMARY.md
```

**Test artifacts** (always temporary):
```bash
rm -f test.db
rm -f test_output.json
rm -f *.db
rm -f *_test_results.json
```

**Build/coverage artifacts** (should be gitignored):
```bash
rm -rf htmlcov/
rm -f coverage.xml
rm -rf dist/
rm -rf logs/
rm -rf registry/
```

### Phase 3: Organize Legitimate Files
**Scripts that belong elsewhere**:
```bash
# Create destination if needed
mkdir -p scripts/experimental/
mkdir -p scripts/

# Move experimental scripts
if [ -d "experimental_scripts" ]; then
    mv experimental_scripts/* scripts/experimental/
    rmdir experimental_scripts
fi

# Move monitoring scripts
mv start_enhanced_monitor.sh scripts/ 2>/dev/null || true
```

### Phase 4: Update .gitignore
Add these patterns to prevent future accumulation:
```gitignore
# Temporary agent reports
/*_REPORT.md
/*_SUMMARY.md
/AGENT_*.md
/QA_*.md
/CICD_*.md

# Test artifacts
/*.db
/*_test_results.json
/test_output.json

# Runtime data (if not already covered)
/registry/
```

### Phase 5: Git Cleanup
```bash
# Remove tracked temporary files
git rm --cached *_REPORT.md *_SUMMARY.md *.db test_output.json 2>/dev/null || true

# Add updated .gitignore
git add .gitignore

# Verify clean state
git status
```

## ✅ Files That Should ALWAYS Stay in Root
- `README.md` - Project documentation
- `CHANGELOG.md` - Version history
- `CLAUDE.md` - Project knowledge base
- `pyproject.toml` - Python project config
- `pytest.ini` - Test configuration
- `tasks.py` - Invoke task definitions
- `poetry.lock` - Dependency lock file
- `.gitignore` - Git ignore rules
- Any `requirements*.txt` files

## 🚫 Files That Should NEVER Be in Root
- `*_REPORT.md` - Agent-generated reports
- `*_SUMMARY.md` - Agent-generated summaries
- `*.db` - Database files
- `test_output.json` - Test result files
- `htmlcov/` - Coverage HTML reports
- `registry/` - Runtime data
- `logs/` - Log directories
- `dist/` - Build artifacts

## 🔧 Common Cleanup Commands

**Quick assessment**:
```bash
# See what's in root
ls -la | grep -v "^d" | grep -v "^total"

# Check git tracking status
git ls-files | grep "^[^/]*$" | head -20
```

**Bulk cleanup** (use with caution):
```bash
# Remove common temporary patterns
rm -f *_REPORT.md *_SUMMARY.md *.db test_output.json

# Remove build artifacts
rm -rf htmlcov/ dist/ logs/ registry/
```

**Verify cleanup**:
```bash
# Root should only contain essential files
ls -1 | wc -l  # Should be small number (~10-15 files)

# Git status should be clean
git status --porcelain | wc -l  # Should be 0 or very small
```

## 🎯 PM Integration

When closing out ANY project, PMs should:

1. **Always run cleanup** before project closeout
2. **Check root directory** for accumulated files
3. **Follow this context** systematically
4. **Update .gitignore** if new patterns emerge
5. **Verify git status** is clean

Example PM closeout procedure:
```markdown
## Project Closeout

### Quality Gates Verified ✅
- All tests passing
- All linting clean
- All type checking clean

### Root Directory Cleanup ✅
- Followed cleanup context procedures
- Deleted temporary agent reports
- Organized misplaced scripts
- Updated .gitignore patterns
- Git status clean

### Final Status: COMPLETE ✅
```

## 🚨 Emergency Cleanup

If root directory becomes severely cluttered:

1. **Backup first**: `tar -czf root_backup.tar.gz *.md *.json *.py *.db 2>/dev/null || true`
2. **Use this context** to clean systematically
3. **Don't bulk delete** without checking each file
4. **Test functionality** after cleanup
5. **Update .gitignore** to prevent recurrence

## Recovery

If cleanup goes wrong:
1. Check git history: `git log --oneline -10`
2. Restore from backup if created
3. Use `git checkout HEAD~1 -- filename` to restore specific files
4. Restart cleanup more carefully

---

**Remember**: The goal is a clean, professional root directory that contains only essential project files. Everything else should be organized into appropriate subdirectories or deleted if temporary.
