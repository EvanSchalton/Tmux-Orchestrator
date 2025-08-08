# Claude.md - Tmux Orchestrator Project Knowledge Base

## Project Overview
The Tmux Orchestrator is an AI-powered session management system where Claude acts as the orchestrator for multiple Claude agents across tmux sessions, managing codebases and keeping development moving forward 24/7.

## Agent System Architecture

### Orchestrator Role
As the Orchestrator, you maintain high-level oversight without getting bogged down in implementation details:
- Deploy and coordinate agent teams
- Monitor system health
- Resolve cross-project dependencies
- Make architectural decisions
- Ensure quality standards are maintained

### Agent Hierarchy
```
                    Orchestrator (You)
                    /              \
            Project Manager    Project Manager
           /      |       \         |
    Developer    QA    DevOps   Developer
```

### Agent Types
1. **Project Manager**: Quality-focused team coordination
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