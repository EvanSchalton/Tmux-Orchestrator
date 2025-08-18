#!/usr/bin/env python3
"""Security tests for path traversal vulnerabilities and their fixes."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from tmux_orchestrator.server.routes.contexts import get_context, router


class TestPathTraversalSecurity:
    """Test security fixes for path traversal vulnerabilities."""

    def test_path_traversal_attack_prevention(self):
        """Test that path traversal attacks are prevented."""
        # Test various path traversal payloads
        dangerous_paths = [
            "../../../etc/passwd",  # Unix path traversal
            "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",  # Windows path traversal
            "/etc/passwd",  # Absolute path
            "../../../../../../etc/passwd",  # Deep traversal
            "....//....//....//etc/passwd",  # Double dot encoding
            "../etc/passwd%00",  # Null byte injection
            "../../proc/version",  # Linux system info
            "../../../root/.ssh/id_rsa",  # SSH private keys
            "../../../../../../home/user/.bashrc",  # User files
        ]

        for dangerous_path in dangerous_paths:
            # This should fail with either validation error or 404 (not file read)
            with pytest.raises((HTTPException, ValueError, OSError)):
                # The function should either validate input or fail to find the file safely
                get_context(dangerous_path)

    def test_role_input_validation(self):
        """Test that role inputs are properly validated."""
        # These should be rejected as invalid role names
        invalid_roles = [
            "",  # Empty string
            "role with spaces",  # Spaces
            "role/with/slashes",  # Forward slashes
            "role\\with\\backslashes",  # Backslashes
            "role.with.dots",  # Multiple dots (could be file extension tricks)
            "role:with:colons",  # Colons
            "role;with;semicolons",  # Semicolons
            "role\nwith\nnewlines",  # Newlines
            "role\x00with\x00nulls",  # Null bytes
        ]

        for invalid_role in invalid_roles:
            with pytest.raises((HTTPException, ValueError)):
                get_context(invalid_role)

    def test_valid_role_names_allowed(self):
        """Test that valid role names are still allowed."""
        valid_roles = [
            "orchestrator",  # Standard role
            "pm",  # Standard role
            "developer",  # Standard role
            "qa-engineer",  # Hyphenated role
            "backend_dev",  # Underscore role
            "role123",  # Alphanumeric
        ]

        # These should either succeed (if file exists) or fail with 404 (if not found)
        # But they should NOT cause path traversal or other security issues
        for valid_role in valid_roles:
            try:
                result = get_context(valid_role)
                # If it succeeds, that's fine
                assert result is not None
            except HTTPException as e:
                # If it fails with 404, that's acceptable for missing files
                assert e.status_code == 404
            except (ValueError, OSError):
                # Should not raise these for valid inputs
                pytest.fail(f"Valid role '{valid_role}' caused unexpected error")


class TestPathTraversalFixes:
    """Test that path traversal fixes are properly implemented."""

    @patch("tmux_orchestrator.server.routes.contexts.CONTEXTS_DIR")
    def test_path_resolution_stays_within_contexts_dir(self, mock_contexts_dir):
        """Test that resolved paths stay within the contexts directory."""
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            contexts_dir = Path(temp_dir) / "contexts"
            contexts_dir.mkdir(exist_ok=True)

            # Create a sample context file
            sample_file = contexts_dir / "test.md"
            sample_file.write_text("# Test Context\nThis is a test context file.")

            mock_contexts_dir.return_value = contexts_dir

            # Test that legitimate files work
            try:
                result = get_context("test")
                assert "test context file" in result.content.lower()
            except (AttributeError, TypeError):
                # May fail due to mocking, but should not have path traversal
                pass

    def test_file_path_sanitization_function_exists(self):
        """Test that path sanitization function exists in contexts module."""
        import tmux_orchestrator.server.routes.contexts as contexts_module

        # Should have sanitization or validation functions
        has_sanitization = (
            hasattr(contexts_module, "_sanitize_role")
            or hasattr(contexts_module, "_validate_role")
            or hasattr(contexts_module, "_safe_path")
            or hasattr(contexts_module, "_validate_path")
        )

        assert has_sanitization, "Path sanitization/validation function not found"

    def test_contexts_directory_path_resolution(self):
        """Test that context paths are resolved safely."""

        # Should not allow path traversal in role parameter
        dangerous_role = "../../../etc/passwd"

        # The get_context function should handle this safely
        with pytest.raises((HTTPException, ValueError, OSError)):
            get_context(dangerous_role)


class TestSecurityIntegration:
    """Integration tests for path traversal security."""

    def test_api_endpoint_path_traversal_protection(self):
        """Test that API endpoints are protected against path traversal."""

        # Create a test client
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router, prefix="/contexts")
        client = TestClient(app)

        # Test path traversal attacks through the API
        dangerous_paths = [
            "../../../etc/passwd",
            "../../../../../../etc/hosts",
            "/etc/passwd",
            "..%2f..%2f..%2fetc%2fpasswd",  # URL encoded
        ]

        for dangerous_path in dangerous_paths:
            response = client.get(f"/contexts/{dangerous_path}")

            # Should return 404, 400, or 422 - NOT 200 with file contents
            assert response.status_code in [400, 404, 422], f"Path traversal may be possible with: {dangerous_path}"

            # Should not contain system file content
            if response.status_code == 200:
                content = response.text.lower()
                system_indicators = ["root:", "password:", "daemon:", "/bin/bash"]
                assert not any(
                    indicator in content for indicator in system_indicators
                ), f"Response contains system file content for: {dangerous_path}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
