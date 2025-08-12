# Agent Over-Engineering Issue

## Issue: AI Agents Massively Overcomplicating Simple Requirements

### Problem Description
AI agents, particularly the PM agent, are introducing unnecessary complexity and over-engineering solutions for simple requirements. This leads to scope creep, delayed delivery, and bloated architectures.

### Observed Behavior
1. **Authentication Implementation**: PM/developers attempting to build auth system despite PRD explicitly not requiring it
2. **Redis Introduction**: Adding Redis caching layer for a simple kanban board that could use SQLite
3. **Microservices Tendency**: Suggesting complex distributed architecture for a prototype
4. **Enterprise Patterns**: Applying enterprise-level solutions to simple problems

### Specific Examples
- **Redis for Caching**: Proposed for a kanban board with likely <1000 tasks
- **Complex Authentication**: JWT tokens, user sessions, role-based access (not in PRD)
- **Over-architecting**: Multiple databases, complex deployment setups
- **Unnecessary Services**: Additional services beyond the simple API + frontend

### Impact
- **High severity** - Significantly increases development time
- Introduces unnecessary dependencies (Redis, auth libraries, etc.)
- Makes system harder to maintain and debug
- Diverts from actual requirements in PRD
- Creates complexity where simplicity would work

### Root Cause Analysis
1. **AI Training Bias**: Agents trained on enterprise codebases default to complex solutions
2. **Lack of Context**: Don't understand this is a prototype/MVP
3. **No Cost Awareness**: Don't consider operational complexity
4. **Pattern Matching**: Apply patterns from large-scale systems to small projects

### Recommended Solution Architecture
**KEEP IT SIMPLE:**
- SQLite database (already exists in project)
- FastAPI backend with basic CRUD operations
- React frontend with simple state management
- Basic WebSocket for real-time updates
- MCP server with 9 straightforward tools

**NO NEED FOR:**
- Redis or any caching layer
- Authentication or user management
- Complex deployment orchestration
- Microservices architecture
- Enterprise monitoring/logging

### Intervention Required
Human orchestrators must actively prevent over-engineering by:
1. **Explicit Constraints**: Tell agents \"use SQLite, no Redis\"
2. **Scope Enforcement**: Redirect when agents add non-PRD features
3. **Architecture Reviews**: Question every new dependency
4. **KISS Principle**: Remind agents to Keep It Simple

### Lessons Learned
- AI agents need explicit architectural constraints
- \"Build the simplest thing that works\" must be reinforced constantly
- PRD should include explicit \"what NOT to build\" sections
- Regular architecture reviews prevent scope creep

### Workaround Applied
- Immediate intervention to stop Redis implementation
- Clear guidance to use existing SQLite setup
- Reminders about project scope and simplicity
- Assigned full-stack developer to prevent over-engineering

---
*Reported: 2025-08-10*
*Version: tmux-orchestrator v2.1.13*
*Document: tmux-orchestrator-feedback-2.1.13-6*
*Priority: P1 - HIGH (affects project delivery)*
*Status: Ongoing issue requiring constant oversight*
