# Sprint 2 Test Plan: Setup Command Claude Registration

## Overview
Test plan for validating the new setup command that registers tmux-orchestrator with Claude Desktop.

## Test Objectives
1. Verify setup command correctly configures Claude integration
2. Validate MCP server registration in Claude config
3. Test idempotent behavior (safe to run multiple times)
4. Ensure cross-platform compatibility

## Test Cases

### TC-101: Setup Command Basic Functionality
**Description**: Verify setup command executes successfully
**Pre-conditions**: tmux-orchestrator installed via pip
**Test Steps**:
1. Run `tmux-orc setup`
2. Verify command completes without errors
3. Check output messages for clarity
4. Validate return code is 0

**Expected Results**: Setup completes successfully with clear messaging

### TC-102: Claude Config File Creation
**Description**: Verify Claude config file is created/updated correctly
**Pre-conditions**: Clean environment (no existing Claude config)
**Test Steps**:
1. Remove/backup existing Claude config
2. Run `tmux-orc setup`
3. Verify config file created at correct location
4. Validate JSON structure and content

**Expected Results**: Valid Claude config with MCP server entry

### TC-103: Claude Config File Update
**Description**: Verify setup updates existing config without data loss
**Pre-conditions**: Existing Claude config with other servers
**Test Steps**:
1. Create Claude config with dummy MCP servers
2. Run `tmux-orc setup`
3. Verify tmux-orchestrator server added
4. Confirm existing servers preserved

**Expected Results**: Config updated, existing data intact

### TC-104: MCP Server Entry Validation
**Description**: Verify correct MCP server configuration
**Pre-conditions**: Setup completed
**Test Steps**:
1. Parse Claude config JSON
2. Locate tmux-orchestrator MCP entry
3. Validate server command path
4. Verify server name and settings

**Expected Results**:
```json
{
  "mcpServers": {
    "tmux-orchestrator": {
      "command": "tmux-orc",
      "args": ["mcp-server"]
    }
  }
}
```

### TC-105: Idempotent Behavior
**Description**: Verify setup can be run multiple times safely
**Pre-conditions**: Setup already completed once
**Test Steps**:
1. Run `tmux-orc setup` first time
2. Note config state
3. Run `tmux-orc setup` again
4. Compare config states

**Expected Results**: No duplicates, config unchanged on re-run

### TC-106: Cross-Platform Path Handling
**Description**: Verify setup works on different platforms
**Pre-conditions**: Test on Linux/Mac/Windows
**Test Steps**:
1. Test on Linux: Verify ~/.config/claude/config.json
2. Test on macOS: Verify ~/Library/Application Support/Claude/config.json
3. Test on Windows: Verify %APPDATA%\Claude\config.json
4. Validate path resolution

**Expected Results**: Correct paths for each platform

### TC-107: Permission Handling
**Description**: Verify graceful handling of permission issues
**Pre-conditions**: Various permission scenarios
**Test Steps**:
1. Make config dir read-only, run setup
2. Make config file read-only, run setup
3. Run without home directory access
4. Test with sudo/admin requirements

**Expected Results**: Clear error messages, suggested fixes

### TC-108: Setup Command Options
**Description**: Verify setup command flags and options
**Pre-conditions**: None
**Test Steps**:
1. Run `tmux-orc setup --help`
2. Run `tmux-orc setup --dry-run` (if supported)
3. Run `tmux-orc setup --force` (if supported)
4. Test verbose output options

**Expected Results**: Options work as documented

### TC-109: Post-Setup Validation
**Description**: Verify Claude can use the registered server
**Pre-conditions**: Setup completed
**Test Steps**:
1. Run setup command
2. Start Claude Desktop
3. Verify tmux-orchestrator appears in Claude
4. Test basic MCP tool functionality

**Expected Results**: Claude successfully uses MCP server

### TC-110: Setup Rollback/Uninstall
**Description**: Verify clean uninstall process
**Pre-conditions**: Setup completed
**Test Steps**:
1. Run `tmux-orc setup --uninstall` (if supported)
2. Or manually remove config entry
3. Verify clean removal
4. Test re-setup after removal

**Expected Results**: Clean removal and re-setup possible

## Automation Strategy
- Create pytest suite in `/tests/sprint2/test_setup_claude_registration.py`
- Mock file system operations for safety
- Test different platform paths
- Validate JSON schema compliance

## Success Criteria
- Setup command integrates seamlessly with Claude
- No data loss in existing configs
- Clear user feedback
- Cross-platform compatibility
- Idempotent and safe to re-run
