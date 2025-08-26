"""
Context Management Tools

Implements native MCP tools for context and documentation access with exact parameter
signatures from API Designer's specifications.
"""

import logging
from typing import Any, Dict, Optional

from .shared_logic import (
    CommandExecutor,
    ContextValidator,
    ExecutionError,
    ValidationError,
    format_error_response,
    format_success_response,
)

logger = logging.getLogger(__name__)


async def show_context(context_name: str) -> Dict[str, Any]:
    """
    Show context information.

    Implements context retrieval with validation and formatting.

    Args:
        context_name: Name of context to show ("orc", "pm", "mcp", "tmux-comms")

    Returns:
        Structured response with context data
    """
    try:
        # Validate context name using shared validator
        ContextValidator.validate_context_name(context_name)

        # Build command
        cmd = ["tmux-orc", "context", "show", context_name]

        # Execute command (context show returns markdown, not JSON)
        executor = CommandExecutor()
        result = executor.execute(cmd, expect_json=False)

        if result["success"]:
            # Structure response with metadata
            response_data = {
                "context_name": context_name,
                "context_content": result["stdout"],
                "content_length": len(result["stdout"]) if result["stdout"] else 0,
                "format": "markdown",
            }

            return format_success_response(
                response_data, result["command"], f"Context {context_name} retrieved successfully"
            )
        else:
            return format_error_response(
                result.get("stderr", f"Failed to show context {context_name}"),
                result["command"],
                [
                    f"Check that context '{context_name}' exists",
                    "Verify context files are accessible",
                    "Ensure tmux-orc service has proper permissions",
                ],
            )

    except ValidationError as e:
        return format_error_response(str(e), f"show context {context_name}")
    except ExecutionError as e:
        return format_error_response(str(e), f"show context {context_name}")
    except Exception as e:
        logger.error(f"Unexpected error in show_context: {e}")
        return format_error_response(f"Unexpected error: {e}", f"show context {context_name}")


async def list_contexts() -> Dict[str, Any]:
    """
    List all available contexts.

    Convenience function for context discovery.

    Returns:
        Structured response with context list
    """
    try:
        # Build command
        cmd = ["tmux-orc", "context", "list"]

        # Execute command
        executor = CommandExecutor()
        result = executor.execute(cmd, expect_json=True)

        if result["success"]:
            data = result["data"]

            # Structure response with metadata
            response_data = {
                "contexts": data.get("contexts", []) if isinstance(data, dict) else [],
                "context_count": len(data.get("contexts", [])) if isinstance(data, dict) else 0,
                "available_contexts": ["orc", "pm", "mcp", "tmux-comms"],  # Known contexts
                "format": "json",
            }

            return format_success_response(
                response_data, result["command"], f"Retrieved {response_data['context_count']} contexts"
            )
        else:
            return format_error_response(
                result.get("stderr", "Failed to list contexts"),
                result["command"],
                [
                    "Check if context files are accessible",
                    "Verify tmux-orc service is running",
                    "Ensure proper file permissions",
                ],
            )

    except ExecutionError as e:
        return format_error_response(str(e), "list contexts")
    except Exception as e:
        logger.error(f"Unexpected error in list_contexts: {e}")
        return format_error_response(f"Unexpected error: {e}", "list contexts")


async def search_context(
    query: str, context_name: Optional[str] = None, case_sensitive: bool = False
) -> Dict[str, Any]:
    """
    Search for content within contexts.

    Advanced function for context content search.

    Args:
        query: Search query string
        context_name: Specific context to search (searches all if None)
        case_sensitive: Perform case-sensitive search

    Returns:
        Structured response with search results
    """
    try:
        # Validate query
        if not query or not query.strip():
            return format_error_response(
                "Search query cannot be empty", "search context", ["Provide a non-empty search query"]
            )

        # Validate context name if provided
        if context_name:
            ContextValidator.validate_context_name(context_name)

        # Build command
        cmd = ["tmux-orc", "context", "search", query]

        # Add specific context if provided
        if context_name:
            cmd.extend(["--context", context_name])

        # Add case sensitivity flag
        if case_sensitive:
            cmd.append("--case-sensitive")

        # Execute command
        executor = CommandExecutor()
        result = executor.execute(cmd, expect_json=True)

        if result["success"]:
            data = result["data"]

            # Structure response with metadata
            response_data = {
                "query": query,
                "context_name": context_name,
                "case_sensitive": case_sensitive,
                "search_results": data.get("results", []) if isinstance(data, dict) else [],
                "result_count": len(data.get("results", [])) if isinstance(data, dict) else 0,
                "contexts_searched": data.get("contexts_searched", []) if isinstance(data, dict) else [],
            }

            return format_success_response(
                response_data, result["command"], f"Found {response_data['result_count']} matches for '{query}'"
            )
        else:
            return format_error_response(
                result.get("stderr", f"Failed to search contexts for '{query}'"),
                result["command"],
                [
                    suggestion
                    for suggestion in [
                        "Check that search query is valid",
                        "Verify context files are accessible",
                        f"Ensure context '{context_name}' exists" if context_name else None,
                    ]
                    if suggestion is not None
                ],
            )

    except ValidationError as e:
        return format_error_response(str(e), f"search context '{query}'")
    except ExecutionError as e:
        return format_error_response(str(e), f"search context '{query}'")
    except Exception as e:
        logger.error(f"Unexpected error in search_context: {e}")
        return format_error_response(f"Unexpected error: {e}", f"search context '{query}'")


async def context_diff(context1: str, context2: str, format: str = "unified") -> Dict[str, Any]:
    """
    Compare two contexts.

    Advanced function for context comparison and diff analysis.

    Args:
        context1: First context name to compare
        context2: Second context name to compare
        format: Diff format ("unified", "context", "side-by-side")

    Returns:
        Structured response with diff results
    """
    try:
        # Validate both context names
        ContextValidator.validate_context_name(context1)
        ContextValidator.validate_context_name(context2)

        # Validate format
        valid_formats = {"unified", "context", "side-by-side"}
        if format not in valid_formats:
            return format_error_response(
                f"Invalid diff format '{format}'. Valid formats: {', '.join(valid_formats)}",
                f"context diff {context1} {context2}",
                [f"Use one of: {', '.join(valid_formats)}"],
            )

        # Build command
        cmd = ["tmux-orc", "context", "diff", context1, context2]

        # Add format if not default
        if format != "unified":
            cmd.extend(["--format", format])

        # Execute command
        executor = CommandExecutor()
        result = executor.execute(cmd, expect_json=False)  # Diff output is typically text

        if result["success"]:
            # Structure response with metadata
            response_data = {
                "context1": context1,
                "context2": context2,
                "format": format,
                "diff_content": result["stdout"],
                "diff_lines": len(result["stdout"].split("\n")) if result["stdout"] else 0,
                "has_differences": bool(result["stdout"] and result["stdout"].strip()),
            }

            return format_success_response(
                response_data, result["command"], f"Diff completed between {context1} and {context2}"
            )
        else:
            return format_error_response(
                result.get("stderr", f"Failed to diff contexts {context1} and {context2}"),
                result["command"],
                [
                    f"Check that context '{context1}' exists",
                    f"Check that context '{context2}' exists",
                    "Verify context files are accessible",
                ],
            )

    except ValidationError as e:
        return format_error_response(str(e), f"context diff {context1} {context2}")
    except ExecutionError as e:
        return format_error_response(str(e), f"context diff {context1} {context2}")
    except Exception as e:
        logger.error(f"Unexpected error in context_diff: {e}")
        return format_error_response(f"Unexpected error: {e}", f"context diff {context1} {context2}")


async def context_validate(context_name: str, check_links: bool = True, check_syntax: bool = True) -> Dict[str, Any]:
    """
    Validate context content.

    Advanced function for context quality assurance.

    Args:
        context_name: Context name to validate
        check_links: Check for broken links in content
        check_syntax: Check markdown syntax validity

    Returns:
        Structured response with validation results
    """
    try:
        # Validate context name
        ContextValidator.validate_context_name(context_name)

        # Build command
        cmd = ["tmux-orc", "context", "validate", context_name]

        # Add link checking flag
        if check_links:
            cmd.append("--check-links")

        # Add syntax checking flag
        if check_syntax:
            cmd.append("--check-syntax")

        # Execute command
        executor = CommandExecutor()
        result = executor.execute(cmd, expect_json=True)

        if result["success"]:
            data = result["data"]

            # Structure response with metadata
            response_data = {
                "context_name": context_name,
                "check_links": check_links,
                "check_syntax": check_syntax,
                "validation_results": data if isinstance(data, dict) else {"valid": True},
                "errors": data.get("errors", []) if isinstance(data, dict) else [],
                "warnings": data.get("warnings", []) if isinstance(data, dict) else [],
                "is_valid": data.get("is_valid", True) if isinstance(data, dict) else True,
            }

            error_count = len(response_data["errors"]) if isinstance(response_data["errors"], list) else 0
            warning_count = len(response_data["warnings"]) if isinstance(response_data["warnings"], list) else 0

            if error_count == 0 and warning_count == 0:
                message = f"Context {context_name} validation passed"
            else:
                message = (
                    f"Context {context_name} validation completed with {error_count} errors, {warning_count} warnings"
                )

            return format_success_response(response_data, result["command"], message)
        else:
            return format_error_response(
                result.get("stderr", f"Failed to validate context {context_name}"),
                result["command"],
                [
                    f"Check that context '{context_name}' exists",
                    "Verify context file is accessible",
                    "Ensure validation tools are available",
                ],
            )

    except ValidationError as e:
        return format_error_response(str(e), f"context validate {context_name}")
    except ExecutionError as e:
        return format_error_response(str(e), f"context validate {context_name}")
    except Exception as e:
        logger.error(f"Unexpected error in context_validate: {e}")
        return format_error_response(f"Unexpected error: {e}", f"context validate {context_name}")
