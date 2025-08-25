"""Agent briefing manager for post-restart briefing restoration.

Provides intelligent briefing restoration with role-specific templates,
context awareness, and project-specific customization. Follows SOLID principles
with comprehensive type annotations and error handling.
"""

import logging
from datetime import datetime
from typing import Any, Optional

from tmux_orchestrator.utils.tmux import TMUXManager


def restore_agent_briefing(
    tmux: TMUXManager,
    target: str,
    agent_role: str,
    project_context: Optional[dict[str, Any | None]] = None,
    custom_briefing: str | None = None,
    logger: logging.Logger | None = None,
) -> tuple[bool, str, dict[str, Any]]:
    """
    Restore agent briefing after restart with role-specific intelligence.

    Provides comprehensive briefing restoration using role templates,
    project context, and custom briefing text. Implements retry logic
    and verification to ensure successful briefing delivery.

    Args:
        tmux: TMUX manager instance for session operations
        target: Target agent in format 'session:window'
        agent_role: Agent role (e.g., 'developer', 'pm', 'qa', 'devops')
        project_context: Optional project context information
        custom_briefing: Custom briefing text to use instead of template
        logger: Optional logger instance for briefing events

    Returns:
        Tuple of (success, message, briefing_data) where:
        - success: Boolean indicating briefing restoration success
        - message: Human-readable result message
        - briefing_data: Dictionary containing briefing metadata

    Raises:
        ValueError: If target format is invalid or role is unrecognized
        RuntimeError: If briefing delivery fails critically
    """
    # Initialize logger if not provided
    if logger is None:
        logger = logging.getLogger(__name__)

    # Validate inputs
    if ":" not in target:
        raise ValueError(f"Invalid target format: {target}. Expected 'session:window'")

    if not custom_briefing and agent_role not in _get_supported_roles():
        raise ValueError(f"Unsupported agent role: {agent_role}. Supported: {_get_supported_roles()}")

    logger.info(f"Starting briefing restoration for {target} (role: {agent_role})")

    # Initialize briefing data
    briefing_data: dict[str, Any] = {
        "target": target,
        "agent_role": agent_role,
        "briefing_time": datetime.now().isoformat(),
        "custom_briefing_used": bool(custom_briefing),
        "project_context_used": bool(project_context),
        "delivery_attempts": 0,
        "delivery_successful": False,
    }

    try:
        # Step 1: Generate or use briefing text
        briefing_text: str

        if custom_briefing:
            briefing_text = custom_briefing
            logger.info(f"Using custom briefing for {target}")
        else:
            briefing_text = _generate_role_briefing(
                agent_role=agent_role,
                target=target,
                project_context=project_context if project_context is not None else {},
                logger=logger,
            )
            logger.info(f"Generated role-based briefing for {target}")

        briefing_data["briefing_length"] = len(briefing_text)
        briefing_data["briefing_preview"] = briefing_text[:100] + "..." if len(briefing_text) > 100 else briefing_text

        # Step 2: Wait for agent to be ready
        logger.info(f"Waiting for agent {target} to be ready for briefing")
        ready_success: bool = _wait_for_agent_ready(tmux, target, logger)

        if not ready_success:
            warning_msg: str = f"Agent {target} may not be fully ready, proceeding with briefing anyway"
            logger.warning(warning_msg)
            briefing_data["ready_check_failed"] = True

        # Step 3: Deliver briefing with retry logic
        delivery_success: bool
        delivery_message: str

        delivery_success, delivery_message = _deliver_briefing(
            tmux=tmux,
            target=target,
            briefing_text=briefing_text,
            max_retries=3,
            logger=logger,
        )

        briefing_data["delivery_successful"] = delivery_success
        briefing_data["delivery_message"] = delivery_message

        # Step 4: Verify briefing delivery (optional verification)
        if delivery_success:
            verification_success: bool = _verify_briefing_delivery(
                tmux=tmux,
                target=target,
                expected_content=briefing_text[:50],  # Check first 50 chars
                logger=logger,
            )
            briefing_data["delivery_verified"] = verification_success

            if verification_success:
                success_msg: str = f"Briefing successfully restored for {target} ({len(briefing_text)} chars)"
                logger.info(success_msg)
                return True, success_msg, briefing_data
            else:
                logger.warning(f"Briefing delivery verification failed for {target}")

        # Return delivery result
        if delivery_success:
            return True, delivery_message, briefing_data
        else:
            return False, delivery_message, briefing_data

    except Exception as e:
        error_msg: str = f"Briefing restoration failed for {target}: {str(e)}"
        logger.error(error_msg)

        briefing_data["restoration_error"] = str(e)
        briefing_data["delivery_successful"] = False

        return False, error_msg, briefing_data


def _generate_role_briefing(
    agent_role: str,
    target: str,
    project_context: dict[str, Any | None],
    logger: logging.Logger,
) -> str:
    """Generate role-specific briefing text."""
    # Extract session and project info
    session_name: str = target.split(":")[0]
    from typing import cast

    project_name: str = (
        cast(str, project_context.get("project_name", session_name)) if project_context else session_name
    )

    # Get role template
    role_templates: dict[str, str] = _get_role_templates()
    base_template: str = role_templates.get(agent_role, role_templates["default"])

    # Add project context if available
    context_section: str = ""
    if project_context:
        context_section = _build_context_section(project_context)

    # Build complete briefing
    briefing_parts: list[str] = [
        "🚀 **AGENT RECOVERY BRIEFING** 🚀",
        "",
        "You have been automatically restarted as part of the recovery system.",
        "",
        f"**Target**: {target}",
        f"**Role**: {agent_role.title()}",
        f"**Project**: {project_name}",
        f"**Recovery Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "**Your Responsibilities**:",
        base_template,
    ]

    if context_section:
        briefing_parts.extend(["", "**Project Context**:", context_section])

    briefing_parts.extend(
        [
            "",
            "**Next Steps**:",
            "1. Acknowledge this briefing with a status update",
            "2. Review any available project documentation",
            "3. Check for pending tasks or issues",
            "4. Report your status using the standard format:",
            "",
            "**STATUS UPDATE [Agent-Name]**: ✅ Completed: [task] 🔄 Currently: [work] 🚧 Next: [step] ⏱️ ETA: [time] ❌ Blockers: [issues]",
            "",
            "You are now ready to continue productive work. Please begin immediately.",
        ]
    )

    return "\n".join(briefing_parts)


def _build_context_section(project_context: dict[str, Any]) -> str:
    """Build project context section for briefing."""
    context_lines: list[str] = []

    if "tech_stack" in project_context:
        context_lines.append(f"- **Tech Stack**: {project_context['tech_stack']}")

    if "current_sprint" in project_context:
        context_lines.append(f"- **Current Sprint**: {project_context['current_sprint']}")

    if "priority_tasks" in project_context:
        tasks = project_context["priority_tasks"]
        if isinstance(tasks, list):
            context_lines.append(f"- **Priority Tasks**: {', '.join(tasks[:3])}")
        else:
            context_lines.append(f"- **Priority Tasks**: {tasks}")

    if "last_commit" in project_context:
        context_lines.append(f"- **Last Commit**: {project_context['last_commit']}")

    return "\n".join(context_lines) if context_lines else "No additional context available"


def _get_role_templates() -> dict[str, str]:
    """Get role-specific briefing templates."""
    return {
        "developer": """
- Write high-quality, well-tested code following project conventions
- Implement features and fix bugs according to priority
- Maintain code documentation and comments
- Collaborate with team members on technical decisions
- Follow git commit discipline (commit every 30 minutes)
- Run tests and ensure code quality before commits""",
        "pm": """
- Monitor team progress and coordinate development activities
- Track task completion and identify blockers
- Maintain high quality standards across all deliverables
- Facilitate communication between team members
- Update project status and report to orchestrator
- Ensure adherence to project timelines and requirements""",
        "qa": """
- Create comprehensive test plans for new features
- Execute manual and automated testing procedures
- Report bugs with detailed reproduction steps
- Verify bug fixes and feature completeness
- Maintain test documentation and quality metrics
- Collaborate with developers on testing best practices""",
        "devops": """
- Manage deployment pipelines and infrastructure
- Monitor system health and performance metrics
- Implement and maintain CI/CD processes
- Handle environment configuration and scaling
- Ensure security and compliance requirements
- Troubleshoot production issues and incidents""",
        "orchestrator": """
- Coordinate high-level project management and team oversight
- Monitor system health and agent performance
- Make architectural decisions and resolve conflicts
- Ensure quality standards are maintained across teams
- Manage resource allocation and priorities
- Provide strategic direction and guidance""",
        "default": """
- Follow project conventions and best practices
- Collaborate effectively with team members
- Maintain high quality standards in all work
- Communicate progress and blockers clearly
- Take ownership of assigned tasks and deliverables
- Contribute to project success through diligent work""",
    }


def _get_supported_roles() -> list[str]:
    """Get list of supported agent roles."""
    return list(_get_role_templates().keys())


def _wait_for_agent_ready(tmux: TMUXManager, target: str, logger: logging.Logger, timeout: int = 10) -> bool:
    """Wait for agent to be ready to receive briefing."""
    import time

    logger.info(f"Waiting up to {timeout}s for agent {target} to be ready")

    for attempt in range(timeout):
        try:
            # Check if we can capture content (indicates agent is responsive)
            content: str = tmux.capture_pane(target, lines=5)

            # Look for Claude prompt or other indicators agent is ready
            if content and any(indicator in content.lower() for indicator in ["claude", ">", "$", "ready"]):
                logger.info(f"Agent {target} appears ready after {attempt + 1}s")
                return True

        except Exception as e:
            logger.debug(f"Agent readiness check attempt {attempt + 1} failed: {str(e)}")

        time.sleep(1)

    logger.warning(f"Agent {target} readiness timeout after {timeout}s")
    return False


def _deliver_briefing(
    tmux: TMUXManager,
    target: str,
    briefing_text: str,
    max_retries: int,
    logger: logging.Logger,
) -> tuple[bool, str]:
    """Deliver briefing to agent with retry logic."""
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Briefing delivery attempt {attempt}/{max_retries} for {target}")

            import subprocess

            result = subprocess.run(
                ["tmux-orc", "agent", "send", target, briefing_text],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                success_msg: str = f"Briefing delivered successfully to {target} (attempt {attempt})"
                logger.info(success_msg)
                return True, success_msg
            else:
                error_msg: str = f"Briefing script failed: {result.stderr}"
                logger.warning(error_msg)

        except subprocess.TimeoutExpired:
            timeout_msg: str = f"Briefing delivery timeout for {target} (attempt {attempt})"
            logger.warning(timeout_msg)
        except Exception as e:
            exception_msg: str = f"Briefing delivery exception: {str(e)}"
            logger.warning(exception_msg)

        # Wait before retry (except on last attempt)
        if attempt < max_retries:
            import time

            time.sleep(2)

    final_error: str = f"Briefing delivery failed for {target} after {max_retries} attempts"
    logger.error(final_error)
    return False, final_error


def _verify_briefing_delivery(
    tmux: TMUXManager,
    target: str,
    expected_content: str,
    logger: logging.Logger,
    timeout: int = 5,
) -> bool:
    """Verify that briefing was delivered successfully."""
    import time

    # Wait briefly for briefing to appear
    time.sleep(2)

    try:
        # Capture recent content
        content: str = tmux.capture_pane(target, lines=20)

        # Check if briefing content appears (simple check)
        if content and "AGENT RECOVERY BRIEFING" in content:
            logger.info(f"Briefing delivery verified for {target}")
            return True
        else:
            logger.debug(f"Briefing content not found in {target} output")
            return False

    except Exception as e:
        logger.warning(f"Briefing verification failed for {target}: {str(e)}")
        return False
