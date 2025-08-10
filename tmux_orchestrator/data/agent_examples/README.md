# Agent Examples Directory

This directory contains example templates for various agent roles that can be spawned in the Tmux Orchestrator system. These examples serve as inspiration and reference for Claude when creating custom agents for specific projects.

## Important Note

**Claude always creates custom agents based on project needs.** These templates are meant to provide guidance and inspiration, not to constrain agent creation. Each agent should be tailored to the specific requirements of your project.

## Directory Structure

Each `.md` file in this directory represents a different agent role:

- `api-designer.md` - API design and specification expert
- `backend-developer.md` - Backend development specialist
- `code-reviewer.md` - Code quality and review expert
- `database-architect.md` - Database design and optimization
- `developer.md` - General software developer
- `devops-engineer.md` - Infrastructure and deployment automation
- `documentation-writer.md` - Technical documentation specialist
- `frontend-developer.md` - Frontend and UI development
- `performance-engineer.md` - Performance optimization expert
- `project-manager.md` - Project coordination and management
- `qa-engineer.md` - Quality assurance and testing
- `security-engineer.md` - Security and compliance expert

## File Structure

Each agent example file follows this structure:

1. **Role Overview** - Brief description of the agent's purpose
2. **Core Responsibilities** - Key duties and tasks
3. **Technical Expertise** - Required skills and technologies
4. **Quality Standards** - Expected quality benchmarks
5. **Key Attributes** - Core characteristics of the agent
6. **Variations** - Different specializations within the role
7. **Integration Points** - How the agent works with others
8. **Success Metrics** - How to measure agent effectiveness

## Usage

### For Orchestrators (Claude)

When creating a team for a project:

1. Review the project requirements
2. Reference these examples for role ideas
3. Customize each agent's briefing for the specific project
4. Consider which variations would be most helpful
5. Adapt communication protocols for team cohesion

### For Users

To use these examples when spawning agents:

```bash
# View an example for inspiration
cat tmux_orchestrator/data/agent_examples/developer.md

# Create a custom agent based on the example
tmux-orc agent spawn my-developer orchestrator:2 \
  --briefing "You are a developer specializing in..."

# Or reference the example when asking Claude to create agents
# "Please create a backend developer agent similar to the example in tmux_orchestrator/data/agent_examples/backend-developer.md"
```

## Creating New Agent Examples

When contributing new agent examples:

1. Follow the existing file structure
2. Provide clear role overview and responsibilities
3. List concrete skills and expertise areas
4. Include quality standards and expectations
5. Provide multiple variations for flexibility
6. Define clear success metrics

## Best Practices

1. **Project Context**: Always include project-specific context in briefings
2. **Team Composition**: Consider how agents will work together
3. **Communication**: Define clear communication protocols
4. **Quality Standards**: Set explicit quality expectations
5. **Git Discipline**: Include version control practices

## Contributing

To add new agent examples:

1. Create a new `.md` file following the naming convention
2. Use the existing structure as a template
3. Submit a PR with the new agent example
4. Include use cases where this agent type excels

## Integration with Orchestrator

The orchestrator can reference these examples when:
- Planning team composition
- Creating custom agents
- Adjusting agent briefings
- Responding to project needs

Example orchestrator usage:
```bash
# List available agent examples
ls tmux_orchestrator/data/agent_examples/*.md

# Read a specific example for inspiration
cat tmux_orchestrator/data/agent_examples/security-engineer.md

# Create a custom agent based on an example
tmux-orc agent spawn my-security-expert orchestrator:4 \
  --briefing "Based on security-engineer example but focused on AWS..."
```

Remember: These are starting points. Every project deserves custom-tailored agents!
