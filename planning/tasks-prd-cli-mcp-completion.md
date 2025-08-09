# Task List: Tmux Orchestrator CLI and MCP Server Completion

*Generated from: prd-cli-mcp-completion.md*

## Relevant Files

### CLI Implementation
- `tmux_orchestrator/cli/__init__.py` - Main CLI entry point with Click commands
- `tmux_orchestrator/cli/team.py` - Team management commands (deploy, status, recover)
- `tmux_orchestrator/cli/orchestrator.py` - Orchestrator operations (schedule, list)
- `tmux_orchestrator/cli/setup.py` - VS Code setup command implementation
- `tests/cli/test_cli_init.py` - Unit tests for main CLI
- `tests/cli/test_team.py` - Unit tests for team commands
- `tests/cli/test_orchestrator.py` - Unit tests for orchestrator commands
- `tests/cli/test_setup.py` - Unit tests for setup-vscode command

### MCP Server Implementation
- `tmux_orchestrator/server/routes/agent_management.py` - Agent spawn/restart/kill routes
- `tmux_orchestrator/server/routes/communication.py` - Message and broadcast routes
- `tmux_orchestrator/server/routes/monitoring.py` - Status and activity reporting routes
- `tmux_orchestrator/server/routes/coordination.py` - Team creation and handoff routes
- `tmux_orchestrator/server/models/` - Pydantic request/response models
- `tests/server/test_agent_management.py` - Unit tests for agent management routes
- `tests/server/test_communication.py` - Unit tests for communication routes
- `tests/server/test_monitoring.py` - Unit tests for monitoring routes
- `tests/server/test_coordination.py` - Unit tests for coordination routes

### Core Business Logic
- `tmux_orchestrator/core/agent_operations/spawn_agent.py` - Agent creation logic
- `tmux_orchestrator/core/agent_operations/restart_agent.py` - Agent restart logic
- `tmux_orchestrator/core/communication/send_message.py` - Message sending logic
- `tmux_orchestrator/core/communication/broadcast_message.py` - PM broadcast logic
- `tmux_orchestrator/core/monitoring/get_session_status.py` - Session status logic
- `tmux_orchestrator/core/monitoring/get_agent_status.py` - Agent status logic
- `tmux_orchestrator/core/recovery/detect_failure.py` - Failure detection logic
- `tmux_orchestrator/core/recovery/auto_restart.py` - Auto-restart logic
- `tmux_orchestrator/core/team_operations/deploy_team.py` - Team deployment logic
- `tmux_orchestrator/core/setup/generate_vscode_tasks.py` - VS Code tasks generation
- `tests/core/` - Corresponding test files for all core modules

### Configuration and Templates
- `tmux_orchestrator/templates/vscode_tasks.json` - Template for VS Code tasks.json
- `tmux_orchestrator/config/agent_types.py` - Agent type definitions and validation
- `tmux_orchestrator/config/team_templates.py` - Team composition templates
- `examples/` - Example task files and generated configurations

### Documentation Updates
- `README.md` - Installation instructions and CLI usage
- `CLI_QUICKSTART.md` - Updated CLI command reference
- `docs/mcp-server.md` - MCP server API documentation
- `docs/agent-recovery.md` - Recovery system documentation

### Cleanup Files
- Remove or archive outdated files and consolidate scattered functionality

### Notes

- All CLI commands must delegate business logic to `core/` modules following one-function-per-file pattern
- MCP server routes are exceptions to one-function-per-file (multiple routes per file OK)
- Use existing `TMUXManager` class, don't reimplement tmux operations
- All tests must achieve 100% branch and statement coverage
- Use `poetry run pytest` to run tests with coverage reporting
- Follow type hints everywhere requirement
- Use existing `send-claude-message.sh` script for all agent communication

## Tasks

- [ ] 1.0 Project Cleanup and Organization
  - [ ] 1.1 Audit all existing files and identify obsolete/duplicate functionality
  - [ ] 1.2 Archive or remove outdated shell scripts that will be replaced by CLI
  - [ ] 1.3 Consolidate scattered configuration into centralized config structure
  - [ ] 1.4 Update .gitignore to exclude test artifacts and temporary files
  - [ ] 1.5 Run `mypy` and `ruff` on entire codebase, fix all issues
  - [ ] 1.6 Ensure all existing tests pass before starting new development

- [ ] 2.0 CLI Foundation and Core Commands
  - [ ] 2.1 Complete `tmux_orchestrator/cli/__init__.py` with proper Click group structure
  - [ ] 2.2 Implement missing CLI commands in existing files (agent.py, monitor.py, pm.py)
  - [ ] 2.3 Create `tmux_orchestrator/cli/team.py` with team management commands
  - [ ] 2.4 Create `tmux_orchestrator/cli/orchestrator.py` with orchestrator operations
  - [ ] 2.5 Implement `tmux_orchestrator/cli/setup.py` for VS Code integration
  - [ ] 2.6 Add comprehensive `--help` text with examples for all commands
  - [ ] 2.7 Implement `--json` output option for scriptable commands
  - [ ] 2.8 Test all CLI commands work in different terminals (not just VS Code)
  - [ ] 2.9 Follow development patterns: type hints everywhere, Click best practices

- [ ] 3.0 Core Business Logic Implementation
  - [ ] 3.1 Create `tmux_orchestrator/core/agent_operations/` module with spawn/restart functions
  - [ ] 3.2 Create `tmux_orchestrator/core/communication/` module with messaging functions
  - [ ] 3.3 Create `tmux_orchestrator/core/monitoring/` module with status functions
  - [ ] 3.4 Create `tmux_orchestrator/core/recovery/` module with failure detection
  - [ ] 3.5 Create `tmux_orchestrator/core/team_operations/` module with team deployment
  - [ ] 3.6 Create `tmux_orchestrator/core/setup/` module with VS Code generation
  - [ ] 3.7 All business logic functions must integrate with existing `TMUXManager`
  - [ ] 3.8 All functions must use `send-claude-message.sh` for agent communication
  - [ ] 3.9 Follow one-function-per-file pattern strictly for business logic
  - [ ] 3.10 Implement proper error handling with clear error messages

- [ ] 4.0 MCP Server Routes Implementation
  - [ ] 4.1 Complete `tmux_orchestrator/server/__init__.py` FastAPI app setup
  - [ ] 4.2 Create `tmux_orchestrator/server/routes/agent_management.py` with spawn/restart/kill
  - [ ] 4.3 Create `tmux_orchestrator/server/routes/communication.py` with messaging tools
  - [ ] 4.4 Create `tmux_orchestrator/server/routes/monitoring.py` with status tools
  - [ ] 4.5 Create `tmux_orchestrator/server/routes/coordination.py` with team management
  - [ ] 4.6 Create `tmux_orchestrator/server/models/` with all Pydantic request/response models
  - [ ] 4.7 Add proper JSON schema definitions for all MCP tools
  - [ ] 4.8 Implement OpenAPI/Swagger documentation at `/docs` endpoint
  - [ ] 4.9 Add health check endpoint and CORS configuration
  - [ ] 4.10 All routes must delegate to business logic functions in `core/`
  - [ ] 4.11 Follow development patterns: async/await, proper error handling, type hints

- [ ] 5.0 Agent Recovery System
  - [ ] 5.1 Implement idle detection v2 algorithm (4 snapshots at 300ms intervals)
  - [ ] 5.2 Create failure detection logic that distinguishes idle from failed
  - [ ] 5.3 Implement unsubmitted message detection in Claude UI
  - [ ] 5.4 Create auto-restart mechanism with context preservation
  - [ ] 5.5 Implement agent briefing restoration after restart
  - [ ] 5.6 Add 5-minute cooldown between recovery notifications
  - [ ] 5.7 Create comprehensive recovery event logging
  - [ ] 5.8 Integrate recovery system with existing monitoring daemon
  - [ ] 5.9 Add CLI commands for recovery management (start/stop/status)
  - [ ] 5.10 Test recovery system with intentionally failed agents

- [ ] 6.0 VS Code Integration and Templates
  - [ ] 6.1 Create `tmux_orchestrator/templates/vscode_tasks.json` template
  - [ ] 6.2 Implement `tmux-orc setup-vscode` command with project directory support
  - [ ] 6.3 Generate tasks.json with all CLI commands and proper labels
  - [ ] 6.4 Add interactive inputs for common parameters (component, role, session)
  - [ ] 6.5 Include task categories and keyboard shortcuts in generated file
  - [ ] 6.6 Test generated tasks work in VS Code with different terminals
  - [ ] 6.7 Create examples directory with sample generated files
  - [ ] 6.8 Follow development patterns: validation, error handling, type safety

- [ ] 7.0 Comprehensive Testing Suite
  - [ ] 7.1 Set up test directory structure mirroring application code
  - [ ] 7.2 Create unit tests for all CLI commands using Click testing utilities
  - [ ] 7.3 Create unit tests for all MCP server routes with FastAPI TestClient
  - [ ] 7.4 Create unit tests for all business logic functions with mocked tmux
  - [ ] 7.5 Create integration tests with real tmux sessions for critical paths
  - [ ] 7.6 Test concurrent operations and race conditions
  - [ ] 7.7 Achieve 100% branch and statement coverage requirement
  - [ ] 7.8 Use `test_uuid` fixture for traceability in all tests
  - [ ] 7.9 Run `poetry run pytest --cov --cov-report=html` and verify coverage
  - [ ] 7.10 Follow development patterns: proper fixtures, no test classes

- [ ] 8.0 Documentation and Installation
  - [ ] 8.1 Update `README.md` with installation instructions via Poetry
  - [ ] 8.2 Add CLI usage examples and common workflows to README
  - [ ] 8.3 Update `CLI_QUICKSTART.md` with complete command reference
  - [ ] 8.4 Create `docs/mcp-server.md` with API documentation and examples
  - [ ] 8.5 Create `docs/agent-recovery.md` explaining the recovery system
  - [ ] 8.6 Add troubleshooting section for common issues
  - [ ] 8.7 Verify installation works in clean environment
  - [ ] 8.8 Test CLI commands work after Poetry installation
  - [ ] 8.9 Create migration guide from shell scripts to CLI
  - [ ] 8.10 Follow development patterns: clear examples, junior developer friendly

- [ ] 9.0 Quality Assurance and Release Preparation
  - [ ] 9.1 Run complete quality check: `mypy`, `ruff`, `pytest` all pass
  - [ ] 9.2 Verify backward compatibility with existing shell scripts
  - [ ] 9.3 Test performance requirements (commands <1 second)
  - [ ] 9.4 Test resource limits (20 agents per session maximum)
  - [ ] 9.5 Verify all 34 functional requirements are implemented
  - [ ] 9.6 Test MCP server handles concurrent requests properly
  - [ ] 9.7 Validate VS Code integration works across platforms
  - [ ] 9.8 Run full integration test with multi-agent development team
  - [ ] 9.9 Update version numbers and changelog
  - [ ] 9.10 Create release documentation and migration notes

- [ ] 10.0 Deployment and Integration Testing
  - [ ] 10.1 Test installation via Poetry in fresh environment
  - [ ] 10.2 Verify CLI works in multiple terminal environments
  - [ ] 10.3 Test MCP server startup and tool discovery
  - [ ] 10.4 Run end-to-end test: deploy team, monitor, recover failed agent
  - [ ] 10.5 Validate agent autonomy through MCP tools
  - [ ] 10.6 Test performance with 20+ concurrent agents
  - [ ] 10.7 Verify monitoring dashboard real-time updates
  - [ ] 10.8 Test VS Code integration across different platforms
  - [ ] 10.9 Run stress tests for failure scenarios
  - [ ] 10.10 Final quality gate: all tests pass, 100% coverage, no warnings

---

*Target Implementation Time: 4-6 weeks for junior developer*
*Prerequisites: Familiarity with Python, Click, FastAPI, tmux*
*Success Criteria: All 34 functional requirements implemented with 100% test coverage*
