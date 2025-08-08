# Development Patterns for Agentic Workforce API

**Note**: This document should be updated as new guidance and patterns are established during development.

## Key Patterns Established

### General Coding Standards
- **Type hint everything**: All functions, methods, variables, and parameters should have proper type hints throughout the codebase
- **Use proper Pydantic methods**: Use `Model.model_validate(data)` for creating instances from dictionaries, but use direct constructor `Model(field=value)` when passing individual parameters
- **Handle type checking pragmatically**: Install type stubs for packages when available, but use `# type: ignore` comments when necessary rather than manually creating stubs
- **One function or class per file for business logic**: Each business logic function or DAO function should be in its own file named after that function. Exception: API routes, CLI commands, and orchestration files may contain multiple functions that handle parameter marshalling, dependency injection, and delegation to business logic functions
- **SQL in separate files**: SQL queries should be stored in separate *.sql files in a 'sql' directory (one sql directory per service) and loaded using pathlib.Path

### SOLID Principles Implementation
- **Single Responsibility Principle (SRP)**: Each function, class, module, and service should have one reason to change
  - Functions: Each business logic function handles one specific operation (e.g., `create_user.py`, `validate_email.py`)
  - Classes: Each model class represents one entity; each service class handles one domain
  - Services: Each microservice handles one bounded context (HR, Cost Tracking, Orchestration, etc.)
- **Open/Closed Principle (OCP)**: Code should be open for extension but closed for modification
  - Use dependency injection patterns for extensibility
  - Implement plugin architectures for consensus algorithms and agent intelligence
  - Use composition over inheritance for extending functionality
- **Liskov Substitution Principle (LSP)**: Derived classes must be substitutable for their base classes
  - All implementations of an interface must honor the contract
  - Abstract base classes should define clear behavioral contracts
  - Service implementations should be interchangeable through interface contracts
- **Interface Segregation Principle (ISP)**: Clients should not be forced to depend on interfaces they don't use
  - Create focused, client-specific interfaces rather than monolithic ones
  - Split large service interfaces into smaller, cohesive contracts
  - Services should expose only the operations their clients need (e.g., HR service shouldn't expose orchestration methods)
  - Data pipelines should have distinct interfaces for different stages (ingestion, processing, output)
- **Dependency Inversion Principle (DIP)**: Depend on abstractions, not concretions
  - High-level modules should not depend on low-level modules; both should depend on abstractions
  - Use dependency injection for database sessions, external services, and configuration
  - Services should depend on interface contracts, not concrete implementations
  - Abstract data access behind repository interfaces

### Service Architecture Principles
- **Services as Classes**: Each microservice should follow the same SOLID principles as individual classes
  - **Service SRP**: Each service handles one bounded context with a single responsibility
  - **Service OCP**: Services should be extensible through configuration and plugin patterns without modification
  - **Service LSP**: Different implementations of a service interface should be interchangeable
  - **Service ISP**: Services should expose focused APIs tailored to specific client needs
  - **Service DIP**: Services should depend on abstract contracts, not concrete service implementations
- **Interface Segregation Between Services**: 
  - Design focused service contracts rather than monolithic APIs
  - Separate read and write operations into different interfaces when appropriate
  - Create client-specific service facades that expose only needed operations
  - Data pipelines should have distinct service interfaces for each processing stage
- **Loose Coupling**: Services should communicate through well-defined interfaces and message contracts
- **High Cohesion**: Related functionality should be grouped within the same service boundary

### Code Organization Patterns
- **Business Logic Functions**: Each business logic function should be in its own file (e.g., `create_user.py`, `validate_email.py`)
- **DAO Functions**: Database access functions should be segmented per file (e.g., `get_user_by_id.py`, `update_user_status.py`)
- **Service Classes**: Complex services with multiple related operations can be in a single class file, but delegate to individual function files for actual operations
- **API Routes**: Route files may contain multiple endpoint functions that handle HTTP-specific concerns (parameter validation, response formatting, dependency injection) and delegate to business logic functions
- **CLI Commands**: Command-line interface files may contain multiple command functions that handle argument parsing and delegate to business logic functions
- **Main/Entry Point Files**: Application entry points and orchestration files may contain multiple functions for initialization, configuration, and coordination
- **Module Transition Pattern**: When creating a new sub-module with one-function-per-file structure, remove the original orchestration Python file and move its imports and `__all__` exports to the new directory's `__init__.py` file. This ensures clean module organization without import conflicts between files and directories with the same name

### Dependency Management
- **Use Poetry for dependency management**: All package installations and dependency management should use Poetry, not pip
- **Add dependencies with Poetry**: Use `poetry add <package>` for runtime dependencies and `poetry add --group dev <package>` for development dependencies
- **Install dependencies**: Use `poetry install` to install all dependencies from the lock file
- **Update dependencies**: Use `poetry update` to update dependencies while respecting version constraints
- **Virtual environment**: Poetry automatically manages the virtual environment; use `poetry shell` or `poetry run <command>` to execute commands in the environment

### Test Directory Structure
- **Tests mirror application code structure**: The test directory structure should mirror the application code directory structure, including file organization
  - Each application code file should have a corresponding test file in the same relative path in the tests directory
  - For example, if there's a file at `api/hr/resume.py`, there should be a corresponding test file at `tests/test_hr/resume_test.py`
  - All tests for a given function or class should be in one test file that has the same relative path as the application code
- **One-function-per-file test pattern**: Test files should mirror the one-function-per-file pattern of the application code
  - Each application code file should have a corresponding test file with the naming pattern `[application_code]_test.py`
  - Test files should only contain tests relevant to their corresponding application code file
  - Refactor large test files by creating copies for each import from application code, then cleaning up irrelevant tests and unused imports
- **Test file refactoring process**:
  1. Create a copy of the large test file for each application code import with the name `[application_code]_test.py`
  2. Remove all tests not relevant to the referenced application code from each copy
  3. Clean up unused imports in each test file copy
  4. Verify all tests have been migrated across the new test files (ensure no tests are missed)
  5. Only after all tests are confirmed migrated, delete the original large test file
- **NO `__init__.py` files in tests directory**: Pytest discovery works better without them and avoids import conflicts
- Test directories must start with `test_` (e.g., `test_hr/`, `test_jira/`)
- All test files must end with `_test.py` (e.g., `resume_crud_test.py`, not `test_resume_crud.py`)
- Follow structure: `tests/test_module/test_submodule/file_test.py`

### Testing Approach
- **NO standalone test scripts**: All tests must be in the `tests/` directory structure
- **NO ad-hoc testing scripts**: Never create standalone Python scripts for testing (like `debug_validation.py`, `test_validator.py`, etc.) - all testing must be done through proper test functions in the tests directory
- **NO manual terminal testing**: Never run manual Python commands in terminal to test behavior - write proper test functions instead
- **NO experimental scripts in workspace root**: Do not create temporary test files, diagnostic scripts, or validation scripts in the workspace root or anywhere outside the tests directory
- **Use `invoke` command for task execution**: Instead of direct terminal commands, use invoke tasks
- **Run tests via pytest**: Always use `pytest` command from the proper test directory
- **Use test functions not classes**: Prefer `def test_*()` functions over `class Test*:` classes
- **Type hint everything**: All test functions, fixtures, and variables should have proper type hints
- **Use test_uuid fixture**: Use `test_uuid` fixture from conftest for traceability, not hardcoded UUIDs
- **Create factory fixtures**: Use helper test-case factory fixtures that include `test_uuid` in data for traceability
- **Traceable test data**: Include `test_uuid` in descriptions and other fields so test data can be traced in logs/DB
- **Use pytest parameterization**: Use `@pytest.mark.parametrize` for testing multiple scenarios efficiently
- **Don't test built-ins**: Don't write tests for built-in functionality like enum values or Python core features
- **Write tests to verify actual behavior**: If tests are failing and you're unsure why, add diagnostic tests to understand the current behavior within the proper test files
- **Don't test Pydantic basics**: Don't test that constructor parameters are assigned to model fields - test custom validators, business logic, and edge cases
- **Use proper Pydantic methods**: Use `Model.model_validate(data)` for creating instances from dictionaries, but use direct constructor `Model(field=value)` when passing individual parameters
- **Fix all warnings**: Address deprecation warnings, type warnings, and other warnings identified during testing
- **Keep test files manageable**: Break up large test files into smaller, feature-focused files instead of creating monolithic test files
- **Feature-segmented test organization**: Group tests by feature, functionality, or logical component rather than putting all tests for a module in a single file
- **Test file size limits**: Aim to keep test files under 300-500 lines to maintain readability and ease of maintenance
- **Logical test grouping**: Create separate test files for different aspects of complex modules (e.g., `test_model_validation.py`, `test_model_operations.py` instead of a single `test_model.py`)

### Test Coverage Requirements
- **Target 100% branch and statement coverage**: Strive for complete code coverage to ensure all code paths are tested
- **Use coverage reporting**: All test runs should include coverage analysis with branch coverage enabled
- **Coverage reports**: Generate terminal output and both XML and HTML reports for detailed coverage analysis
- **Exclude coverage gaps only when justified**: Missing coverage should be explicitly justified and documented
- **Coverage-driven development**: Use coverage reports to identify untested code paths and write targeted tests

### TDD Implementation
- Write failing tests first (Red)
- Implement minimal code to pass (Green) 
- Refactor while keeping tests green
- Complete one sub-task at a time with user permission

### Task Management
- Mark completed tasks with `[x]` in task list files
- Update "Relevant Files" section as files are created/modified
- **Run quality checks before completion**: Run `mypy` and `ruff` to check for type errors and code quality issues
- **Fix all quality issues**: Address any errors, warnings, or style issues identified by static analysis tools
- **Verify complete test coverage**: Only mark a task as complete when both `invoke test` and `invoke check` run clean without filtering (no errors across the entire codebase)
- **Coverage verification**: Use coverage reports to ensure 100% branch and statement coverage before task completion
- Stop after each sub-task completion and wait for user approval

### SQLModel/SQLAlchemy Patterns
- Use `Column` with `sa_column` parameter for complex types like arrays
- Import SQLAlchemy types when SQLModel doesn't support them natively
- Use PostgreSQL ARRAY type for list fields: `sa_column=Column(ARRAY(String))`
- Store SQL queries in *.sql files within a 'sql' directory structure (e.g., `api/hr/sql/job_description/find_by_skills.sql`)
- Load SQL queries using pathlib: `(Path(__file__).parent / "../sql/job_description/find_by_skills.sql").read_text()`

