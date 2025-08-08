# Enrich the task list with development notes.

Update the task list in the planning/ dir to explicitly incorporate the guidance from the /workspaces/agentic-finance/.claude/commands/development-patterns.md

This should explicitly add subtasks for each task to do the following:
1. start with tdd
2. finish with passing tests (no skips or warnings) & linting/formatting
3. follow the one-function-per-file/one-class-per-file pattern
4. design tests using functional pattern (not test classes)
5. use test fixtures and parameterization to keep tests DRY
6. After each major task do a comprehensive code review and refactor as needed to maintain high test quality.
7. For other elements of the development-patterns.md that are applicable for a given task/subtask add reminders/callouts or specific subtasks to remind the agent to adopt those patterns.
8. Add reminders to use subagents for each task (where applicable)
