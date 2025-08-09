# Product Requirements Document: Tmux Orchestrator CLI and MCP Server Completion

## Introduction/Overview

The Tmux Orchestrator is a hierarchical AI agent orchestration system that enables Claude agents to work together autonomously on development projects 24/7. The system implements a three-tier hierarchy (Orchestrator → Project Managers → Engineers) using a hub-and-spoke communication model to overcome context window limitations and prevent communication complexity.

Currently operational with shell scripts and basic Python structure, the system requires completion of the CLI interface and MCP (Model Context Protocol) server to provide a unified command interface and enable full agent autonomy. This PRD defines requirements for completing these components while preserving existing functionality.

## Goals

1. **Provide a unified CLI interface** (`tmux-orc`) that wraps existing shell scripts with improved discoverability
2. **Enable autonomous agent operations** through MCP server tools for spawning, communication, and recovery
3. **Implement automatic agent recovery** using the proven idle detection v2 algorithm (4-snapshot monitoring)
4. **Enhance monitoring capabilities** with real-time dashboards and activity tracking
5. **Maintain backward compatibility** with existing shell scripts and workflows
6. **Achieve 100% test coverage** following established development patterns

## User Stories

### Developer Stories
1. **As a developer**, I want to deploy a full development team with one command so that I can start projects quickly
2. **As a developer**, I want to see real-time status of all agents in a dashboard so that I know project progress
3. **As a developer**, I want failed agents to automatically restart with context so work continues uninterrupted
4. **As a developer**, I want to send messages to specific agents using the CLI instead of shell scripts
5. **As a developer**, I want to use tmux-orc from any terminal (not just VS Code) for maximum flexibility
6. **As a developer**, I want to monitor multiple projects simultaneously from a unified interface

### Agent Stories
7. **As an orchestrator**, I want to spawn specialized agents (PM, Dev, QA) so I can build appropriate teams
8. **As a Project Manager agent**, I want to broadcast messages to all team members for coordination
9. **As any agent**, I want to self-schedule check-ins so I can maintain autonomy
10. **As any agent**, I want to report activity to prevent false idle detection
11. **As any agent**, I want to restart failed team members so work isn't blocked
12. **As any agent**, I want to hand off work with proper context when switching tasks

### PM-Specific Stories
13. **As a PM agent**, I want to enforce git discipline (30-min commits) so work is never lost
14. **As a PM agent**, I want to run quality gates (tests, linting) before marking tasks complete
15. **As a PM agent**, I want to aggregate team status updates for the orchestrator

## Functional Requirements

### CLI Requirements

1. **FR-CLI-001**: The system must provide a `tmux-orc` command installed via Poetry
2. **FR-CLI-002**: The system must implement team management commands:
   - `tmux-orc start <project-name>` - Initialize orchestrator for a project
   - `tmux-orc team deploy <task-file>` - Deploy team based on task file
   - `tmux-orc team status <session>` - Show team hierarchy and health
   - `tmux-orc team recover <session>` - Recover all missing agents

3. **FR-CLI-003**: The system must implement agent management commands:
   - `tmux-orc agent deploy <component> <role>` - Deploy single agent (frontend/backend/database + developer/pm/qa)
   - `tmux-orc agent list [--session]` - List agents with idle/active status
   - `tmux-orc agent send <target> <message>` - Send message using send-claude-message.sh
   - `tmux-orc agent restart <target>` - Restart specific agent with context
   - `tmux-orc agent attach <target>` - Attach to agent terminal

4. **FR-CLI-004**: The system must implement PM-specific commands:
   - `tmux-orc pm checkin <session>` - Trigger PM status collection
   - `tmux-orc pm broadcast <session> <message>` - PM broadcasts to team
   - `tmux-orc pm report <session>` - Get aggregated team report

5. **FR-CLI-005**: The system must provide monitoring commands:
   - `tmux-orc monitor start [--interval]` - Start idle monitoring (default 10s)
   - `tmux-orc monitor stop` - Stop monitoring daemon
   - `tmux-orc monitor status [--verbose]` - Show monitor health and agent states
   - `tmux-orc monitor logs [--follow]` - View monitoring logs

6. **FR-CLI-006**: The system must implement recovery commands:
   - `tmux-orc monitor recovery-start` - Start recovery daemon
   - `tmux-orc monitor recovery-stop` - Stop recovery daemon
   - `tmux-orc monitor recovery-status` - Show recovery status

7. **FR-CLI-007**: The system must provide dashboard and status:
   - `tmux-orc status` - Current snapshot with session/agent tables
   - `tmux-orc dashboard [--refresh N]` - Auto-refreshing dashboard

8. **FR-CLI-008**: The system must support orchestrator operations:
   - `tmux-orc orchestrator schedule <minutes> <target> <note>` - Schedule check-ins
   - `tmux-orc list` - List all active sessions

9. **FR-CLI-009**: The system must provide VS Code integration setup:
   - `tmux-orc setup-vscode [--project-dir]` - Generate tasks.json with all CLI commands
   - Generated tasks.json must include all tmux-orc commands with proper labels
   - Tasks must work with any terminal, not require VS Code terminal
   - Support custom project directory or use current directory

### MCP Server Requirements

10. **FR-MCP-001**: The system must expose MCP server at `http://localhost:8000` with FastAPI
11. **FR-MCP-002**: The system must implement agent management tools:
    - `tmux_spawn_agent` - Parameters: component, role, session, briefing
    - `tmux_restart_agent` - Parameters: target, preserve_context
    - `tmux_kill_agent` - Parameters: target, reason

12. **FR-MCP-003**: The system must implement communication tools:
    - `tmux_send_message` - Parameters: target, message, wait_response
    - `tmux_broadcast_message` - Parameters: session, message, role_filter
    - `tmux_get_messages` - Parameters: target, since_timestamp

13. **FR-MCP-004**: The system must implement monitoring tools:
    - `tmux_get_session_status` - Parameters: session, include_agents
    - `tmux_get_agent_status` - Parameters: target, include_activity
    - `tmux_report_activity` - Parameters: agent_id, activity_type

14. **FR-MCP-005**: The system must implement coordination tools:
    - `tmux_create_team` - Parameters: task_file, project_name
    - `tmux_schedule_checkin` - Parameters: minutes, target, note
    - `tmux_handoff_work` - Parameters: from_agent, to_agent, context

15. **FR-MCP-006**: Each tool must include JSON schema with descriptions
16. **FR-MCP-007**: The server must support concurrent requests via async/await
17. **FR-MCP-008**: The server must integrate with existing TMUXManager

### Agent Recovery Requirements

18. **FR-REC-001**: The system must use idle detection v2 algorithm (4 snapshots at 300ms intervals)
19. **FR-REC-002**: The system must distinguish idle (no output change) from failed (unresponsive)
20. **FR-REC-003**: The system must detect unsubmitted messages in Claude UI
21. **FR-REC-004**: The system must auto-restart failed agents within 60 seconds
22. **FR-REC-005**: The system must restore agent briefing and role after restart
23. **FR-REC-006**: The system must preserve work context using tmux capture-pane
24. **FR-REC-007**: The system must implement 5-minute cooldown between notifications
25. **FR-REC-008**: The system must log all recovery events with timestamps

### Communication Requirements

26. **FR-COMM-001**: All agent messages must use send-claude-message.sh (0.5s delay)
27. **FR-COMM-002**: The system must support structured message templates (STATUS UPDATE, TASK)
28. **FR-COMM-003**: PM agents must be able to broadcast to all team members
29. **FR-COMM-004**: Messages must support session:window and session:window.pane formats
30. **FR-COMM-005**: The system must implement message acknowledgment ("ACK")

### Git Integration Requirements

31. **FR-GIT-001**: The system must enforce 30-minute auto-commit reminders
32. **FR-GIT-002**: The system must check for feature branch creation
33. **FR-GIT-003**: The system must validate meaningful commit messages
34. **FR-GIT-004**: The system must support emergency recovery procedures

## Non-Goals (Out of Scope)

1. **GUI/Web Interface** - CLI and MCP only (web dashboard is future work)
2. **Cloud Deployment** - Local machine operation only
3. **Multi-Machine Orchestration** - Single machine tmux sessions only
4. **Agent Intelligence** - No AI/LLM improvements, infrastructure only
5. **Shell Script Modification** - Preserve all existing scripts
6. **Database Persistence** - Use tmux session state and file logs only
7. **User Authentication** - Rely on system permissions
8. **WebSocket Support** - HTTP/REST only for now
9. **Custom Agent Types** - Only supported roles: developer, pm, qa, reviewer

## Design Considerations

### CLI Design
- Use Rich library for tables, panels, progress bars
- Implement command aliases for common operations
- Support both interactive and scriptable modes
- Provide `--json` output option for automation
- Include examples in all `--help` text
- Preserve existing shell script functionality
- Must work in any terminal (Terminal.app, iTerm2, gnome-terminal, etc.)
- No dependency on VS Code integrated terminal

### VS Code Integration Design
- `tmux-orc setup-vscode` generates complete tasks.json
- Tasks call tmux-orc CLI commands (not direct tmux)
- Support for opening multiple terminal panels
- Tasks organized by category (Agent, Team, Monitor, etc.)
- Each task includes clear description and keyboard shortcut

### MCP Server Design
- Follow MCP protocol specification exactly
- Use Pydantic models for all request/response validation
- Implement proper error codes and messages
- Support OpenAPI documentation at `/docs`
- Use dependency injection for TMUXManager
- Implement health check endpoint

### Code Organization
- Follow one-function-per-file for business logic (except CLI/API routes)
- Separate concerns: parsing, validation, business logic, tmux operations
- Use existing project structure:
  - `tmux_orchestrator/cli/` - Click commands
  - `tmux_orchestrator/server/` - FastAPI routes
  - `tmux_orchestrator/core/` - Business logic
  - `tmux_orchestrator/utils/` - Shared utilities

### Integration Points
- Must work with existing send-claude-message.sh
- Must integrate with idle-monitor-daemon.sh
- Must use existing TMUXManager class
- Must follow VS Code tasks.json patterns
- Must support DevContainer integration

## Technical Considerations

### Dependencies
- Poetry for all dependency management (no pip)
- Click 8.1.7 for CLI
- FastAPI 0.104.1 for MCP server
- Rich 13.7.0 for terminal UI
- Existing shell scripts remain unchanged

### Testing Requirements
- 100% branch and statement coverage requirement
- Use pytest with fixtures
- Mock tmux operations for unit tests
- Integration tests with real tmux sessions
- Test concurrent operations and race conditions
- Use `test_uuid` fixture for traceability

### Performance Requirements
- Commands execute in <1 second (except long operations)
- Dashboard refresh without flicker
- Support 50+ concurrent agents
- Monitoring overhead <5% CPU
- Message delivery <100ms latency

### Error Handling
- Graceful handling of missing sessions/windows
- Clear error messages with recovery suggestions
- Prevent circular agent spawning (max depth: 3)
- Resource limits (max 20 agents per session)
- Timeout handling for unresponsive agents

## Success Metrics

1. **Functional Completeness**: 100% of defined commands operational
2. **Backward Compatibility**: All existing scripts continue working
3. **Agent Autonomy**: Agents successfully self-manage teams
4. **Recovery Success**: 95%+ of failed agents restart successfully
5. **Test Coverage**: 100% branch and statement coverage
6. **Performance**: 95% of commands complete in <1 second
7. **Reliability**: <0.1% command failure rate
8. **Adoption**: 80%+ of users prefer CLI over direct scripts

## Migration Path

1. **Phase 1**: Complete CLI wrapping existing scripts
2. **Phase 2**: Implement MCP server with basic tools
3. **Phase 3**: Add recovery system
4. **Phase 4**: Enhanced monitoring and dashboards
5. **Phase 5**: Deprecate direct script usage (optional)

## Open Questions

1. Should MCP server require API keys for agent authentication?
2. What's the maximum team size limit (currently ~20 agents)?
3. Should we implement rate limiting (100 requests/minute)?
4. Log rotation policy (daily? size-based? 7-day retention)?
5. Maximum recovery attempts before marking agent as failed (3? 5?)
6. Support for custom team templates via YAML/JSON?
7. Should dashboard support split-pane view for multiple sessions?
8. What telemetry to collect (command usage, error rates, recovery stats)?
9. Should we add WebSocket support for real-time updates in v2?
10. Integration with external monitoring (Prometheus/Grafana)?

---

*Generated: 2025-01-08*
*Version: 2.0*
*Status: Updated based on full documentation review*
*Next Steps: Create task list, assign to development team*
