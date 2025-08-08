# Agent Templates Library

This directory contains reusable agent templates for different specializations. The orchestrator and PM can mix and match these templates based on project needs.

## Available Agent Types

### Core Development
- `frontend-developer.yaml` - UI/UX focused development
- `backend-developer.yaml` - API and server development
- `fullstack-developer.yaml` - End-to-end development
- `cli-developer.yaml` - Command-line interface specialist
- `mobile-developer.yaml` - Mobile app development

### Specialized Roles
- `api-designer.yaml` - API architecture and design
- `database-engineer.yaml` - Database design and optimization
- `devops-engineer.yaml` - Infrastructure and deployment
- `security-engineer.yaml` - Security analysis and implementation
- `performance-engineer.yaml` - Performance optimization

### Quality Assurance
- `qa-engineer.yaml` - Manual testing and quality checks
- `test-automation.yaml` - Automated test development
- `accessibility-tester.yaml` - A11y compliance testing
- `security-tester.yaml` - Security testing specialist

### Architecture & Design
- `solution-architect.yaml` - High-level system design
- `ui-ux-designer.yaml` - User interface design
- `technical-writer.yaml` - Documentation specialist

### Project Management
- `project-manager.yaml` - Standard PM role
- `technical-lead.yaml` - Technical PM with coding
- `scrum-master.yaml` - Agile process management

## Team Composition Process

1. **Analyze PRD** - Identify required skills and technologies
2. **Select Agents** - Choose appropriate agent templates
3. **Customize Prompts** - Adjust for project specifics
4. **Define Interactions** - Create communication model
5. **Document Team** - Generate team-composition.md

## Template Format

Each template includes:
- **role**: Agent's primary role
- **specialization**: Specific focus areas
- **prompt**: System prompt template
- **skills**: Technical competencies
- **quality_standards**: Expected quality criteria
- **communication**: Interaction patterns

## Dynamic Team Examples

### API-Heavy Project
- 1 PM
- 2 Backend Developers
- 1 API Designer
- 1 Database Engineer
- 1 Test Automation

### CLI Tool Project
- 1 Technical Lead
- 2 CLI Developers
- 1 Documentation Writer
- 1 QA Engineer

### Security-Critical Project
- 1 PM
- 1 Security Engineer
- 2 Backend Developers
- 1 Security Tester
- 1 DevOps Engineer

## Customization

Templates can be customized by:
1. Modifying the system prompt
2. Adding project-specific context
3. Adjusting quality standards
4. Defining custom interaction patterns