# Claude.md - Tmux Orchestrator Project Knowledge Base

## Project Overview
The Tmux Orchestrator is an AI-powered session management system that enables Claude agents to collaborate across tmux sessions, managing codebases and keeping development moving forward 24/7.

## Document-Driven Team Workflow

### Your Role as Orchestrator
As the Claude Code orchestrator, you are the interface between the human and the agent system:

1. **Planning Phase**: You create team plan documents in `.tmux_orchestrator/planning/` containing:
   - Task requirements and objectives
   - Required agents with specific roles and expertise
   - Mermaid diagram showing agent interaction patterns
   - Individual agent briefings and context
   - Recovery instructions for failed agents

2. **Execution Phase**: You spawn the PM and guide them to build the team:
   ```bash
   # You can use standardized context for PM
   tmux-orc spawn pm --session session-name:1
   # Or with custom extensions:
   tmux-orc spawn pm --session session-name:1 --extend "Project specific: ..."

   # The PM then spawns other agents based on your plan
   tmux-orc spawn agent backend-dev session-name:2 --briefing "..."
   tmux-orc spawn agent qa-engineer session-name:3 --briefing "..."
   ```

3. **Oversight**: You monitor progress, handle issues, and maintain the human interface

### Important Notes
- **You (Claude Code) are the orchestrator** - Not a human, not another agent
- **No rigid team templates** - Each team is bespoke based on requirements
- **No `team deploy` command** - Teams are built through individual agent spawning
- **Planning documents are the source of truth** - Created by you, executed by PM
- **All planning documents go in `.tmux_orchestrator/planning/`** - Not in project root

### Orchestrator vs Project Manager
- **Orchestrator (You)**: Interface with human, create plans, spawn PM, monitor system - NEVER DO IMPLEMENTATION WORK
- **PM Agent**: Execute detailed plans, coordinate team agents, report back to you - DOES ALL THE ACTUAL WORK
- **Window 0**: Can be empty or used for system monitoring - not necessarily human-occupied

**CRITICAL RULE**: Orchestrators NEVER write code, edit files, or do hands-on work. When asked to implement anything, orchestrators ALWAYS create a plan and spawn a PM to execute it.

### Agent Types
1. **Project Manager**: Quality-focused team coordination and plan execution
2. **Developer**: Implementation and technical decisions
3. **QA Engineer**: Testing and verification
4. **DevOps**: Infrastructure and deployment
5. **Code Reviewer**: Security and best practices
6. **Researcher**: Technology evaluation
7. **Documentation Writer**: Technical documentation

## 🔐 Git Discipline - MANDATORY FOR ALL AGENTS

### Git Commit Guidelines
- **Commit Identity Guidance**:
  - Don't commit as Claude Code / Anthropic, commit as "tmux-orc"

[... rest of existing content remains the same ...]

## Recent Monitoring Enhancements Completed: 2025-08-12
- **Rate Limit Handling**: Daemon now auto-pauses during rate limits and resumes after reset
- **Compaction Detection**: Fixed false idle alerts during agent compaction states
- See closeout report at `.tmux_orchestrator/planning/completed/20250812/MONITORING_FEATURES_CLOSEOUT.md`

## Daemon Recovery Improvements Status: 2025-08-16
- **PM Recovery Grace Period**: ✅ IMPLEMENTED - Progressive delays (2-10s) and 5-minute cooldown
- **MCP Protocol Import Fixes**: ✅ IMPLEMENTED - Circular imports resolved via local imports
- **False Positive PM Detection**: ✅ IMPLEMENTED - Context-aware detection prevents killing healthy PMs (commit 381bf99)
- **3-minute grace period**: PMs are protected from health checks immediately after recovery
- See closeout report at `.tmux_orchestrator/planning/daemon-recovery-fixes-closeout.md`

## CLI Command Discovery

### Dynamic CLI Reference
For always-current CLI commands and options, use the built-in discovery tools:

```bash
# Complete CLI structure overview
tmux-orc reflect

# JSON format for automation
tmux-orc reflect --format json

# Markdown format for documentation
tmux-orc reflect --format markdown

# Help for specific commands
tmux-orc [COMMAND] --help
```

**Important**: Never rely on hardcoded CLI examples in documentation. Always use `tmux-orc reflect` or `--help` flags for current syntax.

## System Notifications and Status Messages

### Known Status Updates
- "Bypassing Permissions" is not an error, and is simply a system status update
- "Auto-update failed" is a routine status message and not indicative of a critical issue

# ROLES

If you are filling one of these roles, please adhere to these instructions.

## Project Manager (PM)

Read: `/workspaces/Tmux-Orchestrator/tmux_orchestrator/data/contexts/pm.md`

## Orchestrator

Read: `/workspaces/Tmux-Orchestrator/tmux_orchestrator/data/contexts/orchestrator.md`

## Root Directory Final State
- **Final Root Directory Confirmed**:
  - README.md - Main project documentation
  - DEVELOPMENT-GUIDE.md - Architecture and development guide
  - CHANGELOG.md - Version history
  - CLAUDE.md - Project-specific Claude context
  - tasks.py - Main tasks utility (moved back per your request)

- **Key Notes**:
  - These files are expected to stay in the root
  - Other tests/scripts/docs/etc are likely not and should be cleaned up before commits

## System Error Logging and Reporting
- **Tmux-Orc Command Failure Logging**:
  - If tmux-orc commands fail, especially those hardcoded in context, log the failure in a project briefing file
  - Hardcoded commands should be removed in favor of using the reflection command for dynamic CLI discovery
