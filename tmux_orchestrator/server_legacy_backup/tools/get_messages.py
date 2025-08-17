"""Business logic for retrieving messages from Claude agent conversations."""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from tmux_orchestrator.utils.tmux import TMUXManager


@dataclass
class GetMessagesRequest:
    """Request parameters for retrieving messages."""

    target: str  # Can be session:window or just session (for all windows)
    lines: int = 50  # Number of lines to retrieve
    filter_pattern: Optional[str] = None  # Optional regex pattern to filter messages
    include_timestamps: bool = True
    since_timestamp: Optional[datetime] = None  # Only get messages after this time
    role_filter: Optional[str] = None  # Filter by role (human, assistant, system)


@dataclass
class Message:
    """Represents a single message in the conversation."""

    role: str  # 'human', 'assistant', or 'system'
    content: str
    timestamp: Optional[datetime] = None


@dataclass
class GetMessagesResult:
    """Result of retrieving messages operation."""

    success: bool
    target: str
    messages: list[Message]
    total_lines_captured: int
    error_message: Optional[str] = None


def get_messages(tmux: TMUXManager, request: GetMessagesRequest) -> GetMessagesResult:
    """
    Retrieve messages from a Claude agent conversation.

    Args:
        tmux: TMUXManager instance for tmux operations
        request: GetMessagesRequest with target and retrieval options

    Returns:
        GetMessagesResult with parsed messages from the conversation

    Raises:
        ValueError: If target format is invalid
    """
    # Validate target format
    if ":" not in request.target:
        return GetMessagesResult(
            success=False,
            target=request.target,
            messages=[],
            total_lines_captured=0,
            error_message="Target must be in format 'session:window' or 'session:window.pane'",
        )

    # Extract session name and validate it exists
    session_name = request.target.split(":")[0]
    if not tmux.has_session(session_name):
        return GetMessagesResult(
            success=False,
            target=request.target,
            messages=[],
            total_lines_captured=0,
            error_message=f"Session '{session_name}' not found",
        )

    try:
        # Capture pane content
        content = tmux.capture_pane(request.target, lines=request.lines)
        if not content:
            return GetMessagesResult(
                success=True,
                target=request.target,
                messages=[],
                total_lines_captured=0,
                error_message="No content found in target pane",
            )

        # Parse messages from content
        lines = content.strip().split("\n")
        messages = _parse_messages(lines, request.filter_pattern)

        # Apply role filter if specified
        if request.role_filter:
            messages = [m for m in messages if m.role == request.role_filter]

        # Apply timestamp filter if specified
        if request.since_timestamp and request.include_timestamps:
            filtered_messages = []
            for msg in messages:
                if msg.timestamp and msg.timestamp >= request.since_timestamp:
                    filtered_messages.append(msg)
            messages = filtered_messages

        return GetMessagesResult(
            success=True,
            target=request.target,
            messages=messages,
            total_lines_captured=len(lines),
        )

    except Exception as e:
        return GetMessagesResult(
            success=False,
            target=request.target,
            messages=[],
            total_lines_captured=0,
            error_message=f"Unexpected error retrieving messages: {str(e)}",
        )


def _parse_messages(lines: list[str], filter_pattern: Optional[str] = None) -> list[Message]:
    """Parse messages from terminal content lines."""
    messages = []
    current_message = None
    current_role = None
    current_content: list[str] = []
    current_timestamp = None

    # Apply filter if provided
    if filter_pattern:
        pattern = re.compile(filter_pattern, re.IGNORECASE)
        filtered_lines = []
        for line in lines:
            if pattern.search(line):
                filtered_lines.append(line)
        lines = filtered_lines

    for line in lines:
        # Try to extract timestamp from this line
        line_timestamp = _extract_timestamp(line)
        if line_timestamp and not current_timestamp:
            current_timestamp = line_timestamp

        # Detect Human message start
        if line.strip().startswith("Human:") or "│ >" in line:
            # Save previous message if exists
            if current_message and current_content:
                current_message.content = "\n".join(current_content).strip()
                messages.append(current_message)

            # Start new human message
            current_role = "human"
            current_message = Message(role="human", content="", timestamp=current_timestamp)
            current_content = []
            current_timestamp = None  # Reset for next message

            # Extract content from prompt line
            if "│ >" in line:
                content = line.split("│ >", 1)[1].strip() if "│ >" in line else ""
                if content:
                    current_content.append(content)
            elif line.strip().startswith("Human:"):
                content = line.split("Human:", 1)[1].strip()
                if content:
                    current_content.append(content)

        # Detect Assistant message start
        elif line.strip().startswith("Assistant:") or line.strip().startswith("Claude:"):
            # Save previous message if exists
            if current_message and current_content:
                current_message.content = "\n".join(current_content).strip()
                messages.append(current_message)

            # Start new assistant message
            current_role = "assistant"
            current_message = Message(role="assistant", content="", timestamp=current_timestamp)
            current_content = []
            current_timestamp = None  # Reset for next message

            # Extract content
            if line.strip().startswith("Assistant:"):
                content = line.split("Assistant:", 1)[1].strip()
            else:
                content = line.split("Claude:", 1)[1].strip()
            if content:
                current_content.append(content)

        # System message detection
        elif line.strip().startswith("System:") or "🚀" in line or "⚠️" in line:
            # Save previous message if exists
            if current_message and current_content:
                current_message.content = "\n".join(current_content).strip()
                messages.append(current_message)

            # Extract timestamp from the line itself if not already captured
            if not current_timestamp:
                current_timestamp = _extract_timestamp(line)

            # Create system message with timestamp if available
            current_message = Message(role="system", content=line.strip(), timestamp=current_timestamp)
            messages.append(current_message)
            current_message = None
            current_content = []
            current_role = None
            current_timestamp = None  # Reset for next message

        # Continue current message
        elif current_role and line.strip():
            # Skip UI borders and empty lines
            if not any(border in line for border in ["╭─", "╰─", "├─", "│─"]):
                # For human messages in Claude UI, check if line is part of input box
                if current_role == "human" and "│" in line:
                    # Extract content between box borders
                    if line.strip().startswith("│") and line.strip().endswith("│"):
                        inner_content = line.strip()[1:-1].strip()
                        if inner_content:
                            current_content.append(inner_content)
                else:
                    current_content.append(line.strip())

    # Save last message if exists
    if current_message and current_content:
        current_message.content = "\n".join(current_content).strip()
        messages.append(current_message)

    return messages


def _extract_timestamp(line: str) -> Optional[datetime]:
    """Extract timestamp from a line if present."""
    # Common timestamp patterns
    patterns = [
        (r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]", "%Y-%m-%d %H:%M:%S"),
        (r"\[(\d{2}:\d{2}:\d{2})\]", "%H:%M:%S"),
        (r"\[(\d{2}:\d{2})\]", "%H:%M"),  # Added pattern for [14:31]
        (r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", "%Y-%m-%d %H:%M:%S"),
        (r"@(\d{2}:\d{2})", "%H:%M"),
    ]

    for pattern, fmt in patterns:
        match = re.search(pattern, line)
        if match:
            try:
                if fmt == "%H:%M:%S" or fmt == "%H:%M":
                    # For time-only formats, use today's date
                    today = datetime.now().date()
                    time_str = match.group(1)
                    return datetime.strptime(f"{today} {time_str}", f"%Y-%m-%d {fmt}")
                else:
                    return datetime.strptime(match.group(1), fmt)
            except ValueError:
                continue

    return None
