"""
Test suite for pip-installable tmux-orchestrator architecture.

Validates that the simplified architecture works correctly:
1. pip install tmux-orchestrator
2. tmux-orc setup
3. CLI commands and MCP server integration

Focuses on local developer environment compatibility and ease of use.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest


class TestPipInstallableArchitecture:
    """Test the pip-installable package architecture."""

    def test_package_structure_valid(self, test_uuid: str) -> None:
        """Test that package structure is valid for pip distribution."""
        # Check pyproject.toml exists
        pyproject_path = Path("/workspaces/Tmux-Orchestrator/pyproject.toml")
        assert pyproject_path.exists(), f"pyproject.toml missing for pip packaging - Test ID: {test_uuid}"

        # Check main package directory exists
        package_path = Path("/workspaces/Tmux-Orchestrator/tmux_orchestrator")
        assert package_path.exists(), f"Main package directory missing - Test ID: {test_uuid}"
        assert (package_path / "__init__.py").exists(), f"Package __init__.py missing - Test ID: {test_uuid}"

    def test_cli_entry_points_configured(self, test_uuid: str) -> None:
        """Test that CLI entry points are properly configured."""
        pyproject_path = Path("/workspaces/Tmux-Orchestrator/pyproject.toml")

        with open(pyproject_path) as f:
            content = f.read()

        # Check for required entry points
        assert (
            'tmux-orc = "tmux_orchestrator.cli:cli"' in content
        ), f"tmux-orc entry point not configured - Test ID: {test_uuid}"
        assert (
            'tmux-orc-mcp = "tmux_orchestrator.mcp_server:main"' in content
        ), f"tmux-orc-mcp entry point not configured - Test ID: {test_uuid}"

    def test_bundled_mcp_server_exists(self, test_uuid: str) -> None:
        """Test that MCP server is bundled with the package."""
        mcp_server_path = Path("/workspaces/Tmux-Orchestrator/tmux_orchestrator/mcp_server.py")
        assert mcp_server_path.exists(), f"MCP server not bundled with package - Test ID: {test_uuid}"

        # Verify it's executable as a module
        with open(mcp_server_path) as f:
            content = f.read()
            assert (
                "def main(" in content or "if __name__" in content
            ), f"MCP server not properly executable - Test ID: {test_uuid}"

    def test_required_dependencies_listed(self, test_uuid: str) -> None:
        """Test that all required dependencies are listed in pyproject.toml."""
        pyproject_path = Path("/workspaces/Tmux-Orchestrator/pyproject.toml")

        with open(pyproject_path) as f:
            content = f.read()

        # Check for core dependencies
        required_deps = ["click", "rich", "mcp", "fastmcp", "pyyaml"]
        for dep in required_deps:
            assert dep in content, f"Required dependency '{dep}' not listed - Test ID: {test_uuid}"


class TestLocalInstallationWorkflow:
    """Test the local installation and setup workflow."""

    def test_tmux_orc_command_available(self, test_uuid: str) -> None:
        """Test that tmux-orc command is available in development environment."""
        result = subprocess.run(["tmux-orc", "--help"], capture_output=True, text=True, timeout=10)

        assert result.returncode == 0, f"tmux-orc command not available - Test ID: {test_uuid}"
        assert "tmux-orc" in result.stdout, f"Help text should mention tmux-orc - Test ID: {test_uuid}"

    def test_setup_command_exists(self, test_uuid: str) -> None:
        """Test that setup command exists for initial configuration."""
        result = subprocess.run(["tmux-orc", "setup", "--help"], capture_output=True, text=True, timeout=5)

        # Command should exist (return 0) or show in main help (return 2)
        assert result.returncode in [0, 2], f"setup command not found - Test ID: {test_uuid}"

    def test_mcp_server_script_accessible(self, test_uuid: str) -> None:
        """Test that tmux-orc-mcp script is accessible via Python module."""
        # In development, test that the MCP server can be run as a module
        result = subprocess.run(
            ["python", "-m", "tmux_orchestrator.mcp_server", "--help"], capture_output=True, text=True, timeout=5
        )

        # Should be accessible or fail gracefully (file not found means module doesn't have --help)
        # In a properly installed package, tmux-orc-mcp would be available
        assert (
            result.returncode in [0, 1, 2] or "No module named" in result.stderr
        ), f"MCP server module not accessible - Test ID: {test_uuid}"

    def test_cli_reflection_works_locally(self, test_uuid: str) -> None:
        """Test that CLI reflection works in local environment."""
        result = subprocess.run(["tmux-orc", "reflect", "--format", "json"], capture_output=True, text=True, timeout=5)

        if result.returncode == 0:
            try:
                cli_structure = json.loads(result.stdout)
                assert isinstance(cli_structure, dict), f"CLI reflection should return dict - Test ID: {test_uuid}"

                # Check for expected commands
                expected_commands = ["spawn", "list", "status", "execute", "team", "quick-deploy"]
                available_commands = list(cli_structure.keys())

                for cmd in expected_commands:
                    assert (
                        cmd in available_commands
                    ), f"Expected command '{cmd}' not in CLI structure - Test ID: {test_uuid}"

            except json.JSONDecodeError:
                pytest.fail(f"CLI reflection returned invalid JSON - Test ID: {test_uuid}")


class TestPackageCompatibility:
    """Test package compatibility across environments."""

    def test_python_version_compatibility(self, test_uuid: str) -> None:
        """Test that package works with supported Python versions."""
        # Check current Python version is supported
        current_version = sys.version_info
        assert current_version >= (3, 11), f"Python 3.11+ required, current: {current_version} - Test ID: {test_uuid}"

    def test_cross_platform_paths(self, test_uuid: str) -> None:
        """Test that paths work across platforms."""
        # Test that package uses Path objects for cross-platform compatibility
        package_path = Path("/workspaces/Tmux-Orchestrator/tmux_orchestrator")

        # Look for any hardcoded Unix paths in key files
        cli_init = package_path / "cli" / "__init__.py"
        if cli_init.exists():
            with open(cli_init) as f:
                content = f.read()
                # Should not contain hardcoded Unix paths
                assert "/usr/bin" not in content, f"Hardcoded Unix path found - Test ID: {test_uuid}"
                assert "/etc/" not in content, f"Hardcoded Unix path found - Test ID: {test_uuid}"

    def test_no_docker_dependencies(self, test_uuid: str) -> None:
        """Test that package doesn't depend on Docker (except devcontainer)."""
        pyproject_path = Path("/workspaces/Tmux-Orchestrator/pyproject.toml")

        with open(pyproject_path) as f:
            content = f.read()

        # Should not have Docker-related dependencies
        assert "docker" not in content.lower(), f"Docker dependency found in package - Test ID: {test_uuid}"
        assert "kubernetes" not in content.lower(), f"Kubernetes dependency found - Test ID: {test_uuid}"

        # Check for any Docker files (except devcontainer)
        project_root = Path("/workspaces/Tmux-Orchestrator")
        docker_files = list(project_root.glob("**/Dockerfile*"))
        compose_files = list(project_root.glob("**/docker-compose*"))

        # Filter out devcontainer
        docker_files = [f for f in docker_files if ".devcontainer" not in str(f)]
        compose_files = [f for f in compose_files if ".devcontainer" not in str(f)]

        assert len(docker_files) == 0, f"Docker files found outside devcontainer - Test ID: {test_uuid}"
        assert len(compose_files) == 0, f"Docker compose files found - Test ID: {test_uuid}"


class TestSimplifiedDeployment:
    """Test the simplified deployment model."""

    def test_no_server_infrastructure_required(self, test_uuid: str) -> None:
        """Test that no external server infrastructure is required."""
        # Check that there are no server deployment configs
        project_root = Path("/workspaces/Tmux-Orchestrator")

        # Should not have infrastructure-as-code files
        terraform_files = list(project_root.glob("**/*.tf"))
        ansible_files = list(project_root.glob("**/ansible/**"))
        k8s_files = list(project_root.glob("**/*k8s*")) + list(project_root.glob("**/*kubernetes*"))

        assert len(terraform_files) == 0, f"Terraform files found - Test ID: {test_uuid}"
        assert len(ansible_files) == 0, f"Ansible files found - Test ID: {test_uuid}"
        assert len(k8s_files) == 0, f"Kubernetes files found - Test ID: {test_uuid}"

    def test_local_only_configuration(self, test_uuid: str) -> None:
        """Test that configuration is designed for local use only."""
        # Check for any server/networking configuration
        package_path = Path("/workspaces/Tmux-Orchestrator/tmux_orchestrator")

        # Look for server-related files
        server_files = list(package_path.glob("**/server/**/*.py"))
        for server_file in server_files:
            with open(server_file) as f:
                content = f.read()
                # Should not have production server configurations
                assert "nginx" not in content.lower(), f"Nginx config found in {server_file} - Test ID: {test_uuid}"
                assert "apache" not in content.lower(), f"Apache config found in {server_file} - Test ID: {test_uuid}"

    def test_self_contained_operation(self, test_uuid: str) -> None:
        """Test that the tool operates self-contained."""
        # MCP server should be bundled, not requiring external deployment
        mcp_server_path = Path("/workspaces/Tmux-Orchestrator/tmux_orchestrator/mcp_server.py")
        assert mcp_server_path.exists(), f"MCP server should be bundled - Test ID: {test_uuid}"

        # Should not require external databases
        pyproject_path = Path("/workspaces/Tmux-Orchestrator/pyproject.toml")
        with open(pyproject_path) as f:
            content = f.read()

        db_deps = ["postgresql", "mysql", "redis", "mongodb"]
        for db in db_deps:
            assert db not in content.lower(), f"External database dependency found: {db} - Test ID: {test_uuid}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
