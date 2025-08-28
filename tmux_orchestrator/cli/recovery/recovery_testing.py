"""Recovery system testing commands."""

import asyncio
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from tmux_orchestrator.utils.tmux import TMUXManager

console = Console()


@click.command("test")
@click.argument("target", required=False)
@click.option("--no-restart", is_flag=True, help="Test detection only, do not restart")
@click.option("--comprehensive", is_flag=True, help="Run comprehensive test suite")
@click.option("--stress-test", is_flag=True, help="Include stress testing")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
def test_recovery(
    target: str | None,
    no_restart: bool,
    comprehensive: bool,
    stress_test: bool,
    verbose: bool,
) -> None:
    """Test recovery system with specific agent or run comprehensive tests.

    TARGET: Agent target in format 'session:window' (e.g., 'tmux-orc-dev:4')
            Optional - if not provided, will auto-discover test agents

    Test Modes:
        Single Agent Test (default):
            • Health check and failure detection
            • Recovery coordination (if enabled)
            • Context preservation
            • Briefing restoration
            • Notification system

        Comprehensive Test Suite (--comprehensive):
            • Failure detection validation
            • Recovery coordination testing
            • Context preservation testing
            • Notification system testing
            • Optional stress testing (--stress-test)

    Examples:
        tmux-orc recovery test tmux-orc-dev:4          # Single agent test
        tmux-orc recovery test --no-restart            # Detection only
        tmux-orc recovery test --comprehensive         # Full test suite
        tmux-orc recovery test --comprehensive --stress-test  # Include stress tests
        tmux-orc recovery test --comprehensive --verbose      # Detailed output

    Use --no-restart to test detection without actually restarting agents.
    Use --comprehensive to run the complete test suite on all available agents.
    """
    if comprehensive:
        # Run comprehensive test suite
        console.print("[blue]Running comprehensive recovery system test suite...[/blue]")

        try:
            from tmux_orchestrator.core.recovery.recovery_test import (
                run_recovery_system_test,
            )

            target_list = [target] if target else None

            # Run async test
            results = asyncio.run(
                run_recovery_system_test(
                    target_agents=target_list,
                    include_stress_test=stress_test,
                )
            )

            # Display comprehensive results
            display_comprehensive_test_results(results)

        except Exception as e:
            console.print(f"[red]Comprehensive test error: {e}[/red]")

        return

    # Single agent test mode
    if not target:
        console.print("[red]Target agent required for single agent test mode[/red]")
        console.print("[dim]Use --comprehensive to test all agents automatically[/dim]")
        return

    from tmux_orchestrator.core.recovery import coordinate_agent_recovery

    console.print(f"[blue]Testing recovery system with agent: {target}[/blue]")

    if no_restart:
        console.print("[yellow]Running in detection-only mode[/yellow]")

    tmux = TMUXManager()

    try:
        # Test recovery coordination
        success, message, data = coordinate_agent_recovery(
            tmux=tmux,
            target=target,
            enable_auto_restart=not no_restart,
            use_structured_logging=True,
        )

        if success:
            console.print(f"[green]✓ Recovery test successful: {message}[/green]")
        else:
            console.print(f"[red]✗ Recovery test failed: {message}[/red]")

        # Display test results
        if data:
            results_table = Table(title="Recovery Test Results")
            results_table.add_column("Component", style="cyan")
            results_table.add_column("Status", style="green")
            results_table.add_column("Details", style="yellow")

            # Health check results
            health_checks = data.get("health_checks", [])
            if health_checks:
                latest_check = health_checks[-1]
                health_status = "✓ Healthy" if latest_check.get("is_healthy") else "✗ Unhealthy"
                results_table.add_row(
                    "Health Check",
                    health_status,
                    latest_check.get("failure_reason", "N/A"),
                )

            # Recovery attempt
            recovery_attempted = data.get("recovery_attempted", False)
            if recovery_attempted:
                recovery_status = "✓ Success" if data.get("recovery_successful") else "✗ Failed"
                duration = data.get("total_duration", 0)
                results_table.add_row("Recovery", recovery_status, f"{duration:.1f}s")

            # Briefing restoration
            restart_results = data.get("restart_results", {})
            if restart_results:
                briefing_status = "✓ Success" if restart_results.get("briefing_restored") else "✗ Failed"
                agent_role = restart_results.get("agent_role", "Unknown")
                results_table.add_row("Briefing", briefing_status, f"Role: {agent_role}")

            console.print(results_table)

    except Exception as e:
        console.print(f"[red]Recovery test error: {e}[/red]")


def display_comprehensive_test_results(results: dict[str, Any]) -> None:
    """Display comprehensive test results in rich format."""
    console.print("\n[bold blue]Comprehensive Recovery Test Results[/bold blue]")

    # Test summary
    summary = results.get("summary", {})
    total_tests = summary.get("total_tests", 0)
    tests_passed = summary.get("tests_passed", 0)
    tests_failed = summary.get("tests_failed", 0)
    success_rate = summary.get("overall_success_rate", 0)

    # Summary panel
    summary_info = (
        f"Tests Run: {total_tests}\nPassed: {tests_passed}\nFailed: {tests_failed}\nSuccess Rate: {success_rate:.1f}%"
    )
    summary_panel = Panel(
        summary_info,
        title="Test Summary",
        border_style="green" if success_rate >= 80 else "yellow" if success_rate >= 60 else "red",
    )
    console.print(summary_panel)

    # Detailed results table
    if "test_breakdown" in summary:
        results_table = Table(title="Test Breakdown")
        results_table.add_column("Test Name", style="cyan")
        results_table.add_column("Passed", style="green")
        results_table.add_column("Failed", style="red")
        results_table.add_column("Success Rate", style="yellow")

        for test_name, breakdown in summary["test_breakdown"].items():
            passed = breakdown["passed"]
            failed = breakdown["failed"]
            rate = breakdown["success_rate"]

            results_table.add_row(
                test_name.replace("_", " ").title(),
                str(passed),
                str(failed),
                f"{rate:.1f}%",
            )

        console.print(results_table)

    # Test metadata
    target_agents = results.get("target_agents", [])
    total_duration = results.get("total_duration", 0)

    console.print(f"\n[dim]Agents Tested: {len(target_agents)}[/dim]")
    console.print(f"[dim]Total Duration: {total_duration:.1f}s[/dim]")
    console.print(f"[dim]Test Session: {results.get('test_session_id', 'unknown')}[/dim]")

    if results.get("test_error"):
        console.print(f"[red]Test Error: {results['test_error']}[/red]")
