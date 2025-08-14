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

[... existing content remains the same ...]

## Coordination Guidelines

### Project Manager Coordination

- Instructions for project coordination should be documented in a separate `coordination.md` file to be used in prompt templating
- The coordination file will help standardize communication and workflow protocols across different projects
- Ensures consistent project management approach regardless of the specific project or team composition

### PRD-Driven Development Workflow

- **Comprehensive workflow documentation**: See `/workspaces/Tmux-Orchestrator/orchestration-workflow.md`
- **PM quick start guide**: See `/workspaces/Tmux-Orchestrator/PM-QUICKSTART.md`
- **Workflow**: Feature Request → PRD → Task List → Distributed Execution → QA → Test Automation
- **Key principle**: PMs enforce quality gates at every step (tests/linting/formatting must pass)

## Continuous Improvement

### Dogfooding and Issue Tracking
- While dogfooding you might come across other issues, you should note those for future enhancement/bug fixing

### System Resilience and Recovery
- As the orchestrator, you should periodically disrupt the agents to test system resilience:
  - Periodically kill Claude within an agent
  - Kill entire agents to verify recovery mechanisms
  - Monitor and identify why an agent fails to recover
  - Implement fixes for any detected recovery failures

### Test Case Management
- As we identify new agent terminal failure cases we should add them to the relevant parameterized tests e.g. tests/fixtures/monitor_states/*
- **Test Capture Guideline**: Don't make up test cases for the daemon, copy actual terminal screens at the time of failure

## Recent Monitoring Enhancements Completed: 2025-08-12
- **Rate Limit Handling**: Daemon now auto-pauses during rate limits and resumes after reset
- **Compaction Detection**: Fixed false idle alerts during agent compaction states
- See closeout report at `.tmux_orchestrator/planning/completed/20250812/MONITORING_FEATURES_CLOSEOUT.md`



# ROLES

If you are filling one of these roles, please adhere to these instructions.

## Project Manager (PM)

Read: `/workspaces/Tmux-Orchestrator/tmux_orchestrator/data/contexts/pm.md`

## Orchestrator

Read: `/workspaces/Tmux-Orchestrator/tmux_orchestrator/data/contexts/orchestrator.md`
