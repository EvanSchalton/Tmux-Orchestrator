"""Context preservation testing functionality."""

import logging
from typing import Any

from tmux_orchestrator.utils.tmux import TMUXManager


class ContextPreservationTest:
    """Tests for context preservation functionality."""

    def __init__(self, tmux_manager: TMUXManager, logger: logging.Logger):
        """Initialize context preservation test."""
        self.tmux = tmux_manager
        self.logger = logger

    async def test_context_preservation(self, target_agents: list[str]) -> dict[str, Any]:
        """Test context preservation functionality."""
        context_results: dict[str, Any] = {
            "agents_tested": len(target_agents),
            "context_successful": 0,
            "context_failed": 0,
            "agent_results": [],
        }

        for target in target_agents[:1]:  # Only test one agent for context preservation
            try:
                # Capture current context
                original_content = self.tmux.capture_pane(target, lines=100)

                if not original_content:
                    agent_result = {
                        "target": target,
                        "context_preserved": False,
                        "error": "No content to preserve",
                    }
                    context_results["agent_results"].append(agent_result)
                    context_results["context_failed"] += 1
                    continue

                # Test context preservation logic (simulate)
                context_lines = original_content.split("\n")
                preserved_lines = len([line for line in context_lines if line.strip()])

                agent_result = {
                    "target": target,
                    "context_preserved": True,
                    "original_content_lines": len(context_lines),
                    "preserved_lines": preserved_lines,
                    "preservation_ratio": preserved_lines / max(len(context_lines), 1),
                }

                context_results["agent_results"].append(agent_result)
                context_results["context_successful"] += 1

                self.logger.info(f"Context test {target}: ✓ {preserved_lines} lines preserved")

            except Exception as e:
                self.logger.error(f"Context test failed for {target}: {str(e)}")
                context_results["agent_results"].append({"target": target, "context_preserved": False, "error": str(e)})
                context_results["context_failed"] += 1

        return context_results

    def analyze_context_quality(self, target: str, lines: int = 100) -> dict[str, Any]:
        """Analyze the quality of context that can be preserved.

        Args:
            target: Agent target to analyze
            lines: Number of lines to capture for analysis

        Returns:
            Dictionary with context quality analysis
        """
        quality_results: dict[str, Any] = {
            "target": target,
            "total_lines": 0,
            "non_empty_lines": 0,
            "command_lines": 0,
            "output_lines": 0,
            "error_lines": 0,
            "quality_score": 0.0,
        }

        try:
            content = self.tmux.capture_pane(target, lines=lines)
            if not content:
                return quality_results

            lines_list = content.split("\n")
            quality_results["total_lines"] = len(lines_list)

            for line in lines_list:
                stripped_line = line.strip()
                if not stripped_line:
                    continue

                quality_results["non_empty_lines"] += 1

                # Heuristic analysis of line types
                if stripped_line.startswith("$") or stripped_line.startswith(">"):
                    quality_results["command_lines"] += 1
                elif "error" in stripped_line.lower() or "failed" in stripped_line.lower():
                    quality_results["error_lines"] += 1
                else:
                    quality_results["output_lines"] += 1

            # Calculate quality score (0.0 to 1.0)
            if quality_results["total_lines"] > 0:
                non_empty_ratio = quality_results["non_empty_lines"] / quality_results["total_lines"]
                command_ratio = quality_results["command_lines"] / max(quality_results["non_empty_lines"], 1)
                quality_results["quality_score"] = (non_empty_ratio * 0.7) + (command_ratio * 0.3)

        except Exception as e:
            self.logger.error(f"Context quality analysis failed for {target}: {e}")
            quality_results["error"] = str(e)

        return quality_results

    def test_context_restoration(self, target: str, context_data: str) -> dict[str, Any]:
        """Test context restoration functionality (simulation).

        Args:
            target: Agent target
            context_data: Context data to restore

        Returns:
            Dictionary with restoration test results
        """
        restoration_results = {
            "target": target,
            "restoration_successful": False,
            "context_length": len(context_data) if context_data else 0,
            "lines_to_restore": 0,
        }

        try:
            if context_data:
                lines = context_data.split("\n")
                restoration_results["lines_to_restore"] = len(lines)

                # Simulate restoration success based on context quality
                non_empty_lines = len([line for line in lines if line.strip()])
                if non_empty_lines > 0:
                    restoration_results["restoration_successful"] = True
                    self.logger.info(f"Context restoration test {target}: ✓ {non_empty_lines} lines to restore")
                else:
                    self.logger.warning(f"Context restoration test {target}: ✗ No meaningful content to restore")
            else:
                self.logger.warning(f"Context restoration test {target}: ✗ No context data provided")

        except Exception as e:
            self.logger.error(f"Context restoration test failed for {target}: {e}")
            restoration_results["error"] = str(e)

        return restoration_results
