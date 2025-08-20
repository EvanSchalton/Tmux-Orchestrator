# Claude Code Compliance Standards

## Task Management
- **Use todos** for any task requiring 3 or more steps
- **Maintain only ONE task** in "in_progress" status at a time
- **Update task status** immediately upon completion
- **Create new todos** for discovered blockers or issues

## Communication Standards
- **NO emojis** in responses unless user explicitly requests them
- **ALWAYS include** relevant code snippets in your reports
- **Use absolute file paths** like `/workspace/project/src/file.py`
- **Follow structured response format**:

### Response Template
```
## Task Completion Summary

### What Was Done
- [Specific actions taken with clear descriptions]
- [Files modified with absolute paths]

### Key Changes
- **File**: /absolute/path/to/file.py
  - [What changed and why]

### Code Snippets
```language
# Show actual implementation
def example():
    return "real code"
```

### Results
- [What works now that didn't before]
- [Any metrics or improvements]
```