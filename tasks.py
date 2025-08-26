"""Invoke tasks for Tmux Orchestrator development."""

from invoke import task


@task
def install(c):
    """Install all dependencies including dev."""
    c.run("poetry install")
    c.run("poetry run pre-commit install")
    print("✅ Dependencies installed and pre-commit hooks configured")


@task
def test(c, verbose=False, coverage=False):
    """Run all tests."""
    cmd = "poetry run pytest"
    if verbose:
        cmd += " -v"
    if coverage:
        cmd += " --cov=tmux_orchestrator --cov-report=term-missing --cov-report=html"
    c.run(cmd)


@task
def format(c, check=False):
    """Format code with ruff."""
    cmd = "poetry run ruff format"
    if check:
        cmd += " --check"
    cmd += " tmux_orchestrator tests"
    c.run(cmd)


@task
def lint(c, fix=False):
    """Run linting with ruff."""
    cmd = "poetry run ruff check"
    if fix:
        cmd += " --fix"
    cmd += " tmux_orchestrator tests"
    c.run(cmd)


@task
def type_check(c):
    """Run type checking with mypy."""
    c.run("poetry run mypy tmux_orchestrator")


@task
def security(c):
    """Run security checks with bandit."""
    c.run("poetry run bandit -r tmux_orchestrator -ll --skip B108")


@task
def check(c):
    """Run all CI/CD checks (what GitHub Actions runs)."""
    print("🔍 Running all CI/CD checks...")
    print("\n📝 Checking code formatting...")
    format(c, check=True)
    print("\n🔧 Running linter...")
    lint(c)
    print("\n🔒 Running security checks...")
    security(c)
    print("\n🔍 Running type checker...")
    type_check(c)
    print("\n🧪 Running tests...")
    test(c)
    print("\n✅ All checks passed! Ready to push.")


@task
def pre_commit(c):
    """Run pre-commit on all files."""
    c.run("poetry run pre-commit run --all-files")


@task
def pre_commit_hooks(c):
    """Run the exact same checks as pre-commit hooks (for testing centralization)."""
    print("🔗 Running centralized pre-commit checks...")

    # Format check (as pre-commit does)
    print("\n1️⃣ Format check...")
    format(c, check=True)

    # Lint check
    print("\n2️⃣ Lint check...")
    lint(c)

    # Type check
    print("\n3️⃣ Type check...")
    type_check(c)

    # Security check
    print("\n4️⃣ Security check...")
    security(c)

    # Quick test validation
    print("\n5️⃣ Quick test validation...")
    quick(c)

    print("\n✅ All centralized pre-commit checks passed!")


@task
def clean(c):
    """Clean up generated files."""
    c.run('find . -type d -name "__pycache__" -exec rm -rf {} +', warn=True)
    c.run('find . -type f -name "*.pyc" -delete')
    c.run('find . -type f -name "*.pyo" -delete')
    c.run('find . -type f -name "*.coverage" -delete')
    c.run("rm -rf .coverage htmlcov .pytest_cache .mypy_cache .ruff_cache", warn=True)
    print("✅ Cleaned up generated files")


@task
def quick(c):
    """Quick checks before committing (optimized for pre-commit performance)."""
    print("⚡ Running quick checks...")

    # Fast linting (no fix, just check)
    print("🔧 Quick lint check...")
    c.run("poetry run ruff check tmux_orchestrator tests")

    # Type checking (already fast)
    print("🔍 Type checking...")
    type_check(c)

    # Run smoke tests (subset for speed)
    print("🧪 Smoke tests...")
    c.run("poetry run pytest tests/unit/cli/spawn_auto_increment_test.py -v --tb=short -q --maxfail=3")

    print("✅ Quick checks passed")


@task
def full(c):
    """Full check including formatting and all tests."""
    clean(c)
    format(c)
    check(c)


@task
def ci(c):
    """Run the exact same checks as CI/CD (for local validation)."""
    print("🚀 Running local CI/CD simulation...")
    print("\nThis runs the exact same checks as GitHub Actions:")
    print("- Ruff linting")
    print("- Ruff formatting check")
    print("- Bandit security scan")
    print("- MyPy type checking")
    print("- Pytest tests\n")

    # Run each check exactly as CI/CD does
    print("1️⃣ Linting with Ruff...")
    c.run("poetry run ruff check tmux_orchestrator tests")

    print("\n2️⃣ Checking formatting with Ruff...")
    c.run("poetry run ruff format --check tmux_orchestrator tests")

    print("\n3️⃣ Security scan with Bandit...")
    c.run("poetry run bandit -r tmux_orchestrator -ll --skip B108")

    print("\n4️⃣ Type checking with MyPy...")
    c.run("poetry run mypy tmux_orchestrator")

    print("\n5️⃣ Running tests with Pytest...")
    c.run("poetry run pytest")

    print("\n✅ Local CI/CD passed! Your code matches what will run on GitHub.")


@task
def serve_docs(c, port=8000):
    """Serve documentation locally."""
    print(f"📚 Serving documentation at http://localhost:{port}")
    c.run(f"cd docs && python -m http.server {port}")


@task
def update_deps(c):
    """Update dependencies while respecting version constraints."""
    c.run("poetry update")
    print("✅ Dependencies updated")


@task
def show_errors(c):
    """Show current mypy errors with context."""
    print("🔍 Current MyPy errors:")
    c.run(
        "poetry run mypy tmux_orchestrator --show-error-codes 2>&1 | grep -E '^tmux_orchestrator.*error:' || echo 'No errors found!'",
        warn=True,
    )


@task(help={"component": "Component to test (cli, core, server, sdk)", "module": "Specific module within component"})
def test_component(c, component, module=None):
    """Run tests for a specific component."""
    path = f"tests/test_{component}"
    if module:
        path += f"/test_{module}.py"
    c.run(f"poetry run pytest {path} -v")


# Aliases for common commands
@task
def t(c):
    """Alias for test."""
    test(c)


@task
def f(c):
    """Alias for format."""
    format(c)


@task(name="l")
def lint_alias(c):
    """Alias for lint."""
    lint(c)


@task
def q(c):
    """Alias for quick."""
    quick(c)


@task
def test_warnings(c):
    """Run tests with warnings as errors."""
    c.run("poetry run pytest --no-cov -W error::Warning --tb=no -q")
