# PRD Survey: Tmux Orchestrator CLI and MCP Server Completion

## Project Context
You're developing a Tmux Orchestrator that uses Claude agents to coordinate development work. The system already has working shell scripts and basic Python structure, but needs the CLI commands and MCP server routes to be fully implemented.

## Clarifying Questions

### 1. Problem/Goal
**Q: What specific problems does completing the CLI and MCP server solve for users?**
A: Currently users must use shell scripts directly or tmux commands manually. The completed CLI will provide a unified, discoverable interface for all orchestration tasks. The MCP server will allow Claude agents to programmatically control the orchestration system, enabling true autonomous development teams.

### 2. Target Users
**Q: Who are the primary users of the completed CLI and MCP server?**
A:
- **CLI Users**: Developers who want to manage AI agent teams for their projects
- **MCP Server Users**: Claude agents that need to spawn other agents, communicate between teams, and manage their own lifecycle

### 3. Core Functionality
**Q: What are the key actions users should be able to perform?**
A:
- **CLI**: Deploy agents/teams, monitor status, send messages, view dashboards, restart failed agents, manage project sessions
- **MCP Server**: Agents can spawn new agents, send inter-agent messages, check session status, restart failed agents, create teams
- **Terminal**: User should be able to open a tmux window and toggle between agents

### 4. User Stories
**Q: Can you provide key user stories?**
A:
- As a developer, I want to deploy a full development team with one command so that I can start a project quickly
- As a developer, I want to see real-time status of all agents so that I know what's happening (and be able to interact with them as needed)
- As an agent, I want to spawn specialized helper agents so that I can delegate specific tasks
- As an agent, I want to communicate with other agents so that we can coordinate work
- As a developer, I want failed agents to automatically restart so that work continues uninterrupted
- As a developer, I want to be able to send messages to an agent via the CLI (directly typing in the terminal can cause race conditions if another agent submits text)

### 5. Acceptance Criteria
**Q: How will we know when this feature is successfully implemented?**
A:
- All CLI commands listed in help actually work
- MCP server exposes tools that agents can discover and use
- Agent recovery system detects and restarts failed Claude instances
- Dashboard shows real-time agent status
- 100% test coverage with all tests passing
- Documentation is complete and accurate
- Deamon is automatically initializied while agents are running to monitor for idleness and reports idleness to management agents (should use tmux groups for mgmt, workers, etc.)

### 6. Scope/Boundaries
**Q: What should this implementation NOT include?**
A:
- GUI/Web interface (CLI & MCP only)
- Cloud deployment features
- Multi-machine orchestration (local only)
- Agent intelligence improvements

### 7. Data Requirements
**Q: What data needs to be tracked and displayed?**
A:
- Agent status (active, idle, failed)
- Session and window information
- Agent roles and types
- Message history between agents
- Recovery events and logs
- Task assignments and progress

### 8. Design/UI
**Q: Are there any UI/UX requirements for the CLI?**
A:
- Use Rich library for attractive terminal output
- Consistent color coding (green=success, red=error, yellow=warning)
- Table-based displays for status information
- Progress indicators for long operations
- Clear, helpful error messages

### 9. Edge Cases
**Q: What edge cases should we handle?**
A:
- Agent crashes during critical operations
- Multiple agents sending messages simultaneously
- Tmux session doesn't exist when trying to attach
- Network issues preventing MCP server access
- Circular agent spawning (agents creating agents infinitely)
- Resource limits (too many agents)
- TMUX command not submitted (written but "enter" not pressed - daemon should check and submit)
- Claude code shutsdown w/in a terminal (needs to be restarted)

### 10. Integration Requirements
**Q: How should this integrate with existing systems?**
A:
- Must work with existing shell scripts (replace w/ CLI commands)
- Should use existing TMUXManager class (or similar)
- Must follow development patterns in .claude/commands/development-patterns.md
- Should integrate with existing (or enhanced) idle monitoring daemon
- Must support similar workflows as current workflows

---

Please review these questions and answers. Would you like to modify any answers or add additional context before I generate the PRD?

There's also the other branch for the daemon to consider.
