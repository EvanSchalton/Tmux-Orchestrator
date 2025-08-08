"""Publish/Subscribe commands for inter-agent communication."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
from rich.console import Console
from rich.table import Table

from tmux_orchestrator.utils.tmux import TMUXManager

console = Console()

# Message store location (could be Redis/DB in future)
MESSAGE_STORE = Path.home() / ".tmux-orchestrator" / "messages"


@click.group()
def pubsub() -> None:
    """Publish/subscribe messaging for agent communication.
    
    Provides a higher-level abstraction over direct tmux messaging,
    enabling agents to communicate through CLI commands instead of
    shell scripts. Supports both targeted and broadcast messaging.
    
    Examples:
        tmux-orc publish --session frontend-dev:0 "Please run tests"
        tmux-orc publish --group management "3 agents are idle"
        tmux-orc read --session backend-dev:0 --tail 50
        tmux-orc subscribe --group management --callback ./handle-message.sh
    """
    MESSAGE_STORE.mkdir(parents=True, exist_ok=True)


@pubsub.command()
@click.argument('message')
@click.option('--session', help='Target session:window')
@click.option('--group', help='Broadcast to group (management, development, qa)')
@click.option('--priority', type=click.Choice(['low', 'normal', 'high', 'critical']), default='normal')
@click.option('--tag', multiple=True, help='Tag messages for filtering')
@click.pass_context
def publish(ctx: click.Context, message: str, session: Optional[str], group: Optional[str], 
            priority: str, tag: List[str]) -> None:
    """Publish a message to agents or groups.
    
    MESSAGE: The message content to publish
    
    Examples:
        # Direct message to specific agent
        tmux-orc publish --session pm:0 "Frontend feature complete"
        
        # Broadcast to management group
        tmux-orc publish --group management "System health check needed"
        
        # High priority tagged message
        tmux-orc publish --session qa:0 --priority high --tag bug --tag critical "P0 bug found"
        
        # Status update from daemon
        tmux-orc publish --group management "Agents frontend:0, backend:0 are idle"
    """
    if not session and not group:
        console.print("[red]Error: Must specify either --session or --group[/red]")
        return
        
    if session and group:
        console.print("[red]Error: Cannot specify both --session and --group[/red]")
        return
    
    tmux: TMUXManager = ctx.obj['tmux']
    
    # Create message metadata
    msg_data = {
        'id': datetime.now().isoformat(),
        'message': message,
        'priority': priority,
        'tags': list(tag),
        'sender': ctx.obj.get('current_session', 'orchestrator'),
        'timestamp': datetime.now().isoformat()
    }
    
    # Format message based on priority
    priority_prefixes = {
        'critical': '🚨 CRITICAL',
        'high': '⚠️  HIGH PRIORITY',
        'normal': '📨',
        'low': '💬'
    }
    
    formatted_msg = f"{priority_prefixes[priority]} {message}"
    
    if session:
        # Direct message to specific session
        if tmux.send_message(session, formatted_msg):
            console.print(f"[green]✓ Message sent to {session}[/green]")
            # Log to message store
            _store_message(session, msg_data)
        else:
            console.print(f"[red]✗ Failed to send to {session}[/red]")
    
    elif group:
        # Broadcast to group
        targets = _get_group_members(tmux, group)
        success_count = 0
        
        console.print(f"[blue]Broadcasting to {group} group ({len(targets)} targets)...[/blue]")
        
        for target in targets:
            if tmux.send_message(target, formatted_msg):
                success_count += 1
                _store_message(target, msg_data)
                console.print(f"  [green]✓ {target}[/green]")
            else:
                console.print(f"  [red]✗ {target}[/red]")
        
        console.print(f"\n[bold]Broadcast complete: {success_count}/{len(targets)} successful[/bold]")


@pubsub.command()
@click.option('--session', required=True, help='Session:window to read from')
@click.option('--tail', type=int, default=50, help='Number of lines to read')
@click.option('--since', help='Read messages since timestamp (ISO format)')
@click.option('--filter', help='Filter messages by content')
@click.option('--json', is_flag=True, help='Output in JSON format')
@click.pass_context
def read(ctx: click.Context, session: str, tail: int, since: Optional[str], 
         filter: Optional[str], json: bool) -> None:
    """Read agent output and message history.
    
    Examples:
        # Read last 50 lines from PM
        tmux-orc read --session pm:0 --tail 50
        
        # Read with content filter
        tmux-orc read --session qa:0 --filter "test"
        
        # Read messages since timestamp
        tmux-orc read --session frontend:0 --since "2024-01-01T10:00:00"
        
        # Get JSON output for parsing
        tmux-orc read --session backend:0 --json
    """
    tmux: TMUXManager = ctx.obj['tmux']
    
    # Get current pane content
    pane_content = tmux.capture_pane(session, lines=tail)
    
    if not pane_content:
        console.print(f"[red]✗ Failed to read from {session}[/red]")
        return
    
    # Apply content filter if specified
    if filter:
        lines = pane_content.split('\n')
        filtered_lines = [line for line in lines if filter.lower() in line.lower()]
        pane_content = '\n'.join(filtered_lines)
    
    # Get stored messages for this session
    stored_messages = _get_stored_messages(session, since)
    
    if json:
        import json as json_module
        output = {
            'session': session,
            'timestamp': datetime.now().isoformat(),
            'pane_content': pane_content,
            'stored_messages': stored_messages
        }
        console.print(json_module.dumps(output, indent=2))
    else:
        console.print(f"[bold]📖 Reading from {session}[/bold]")
        console.print(f"[dim]Last {tail} lines:[/dim]\n")
        console.print(pane_content)
        
        if stored_messages:
            console.print(f"\n[bold]📨 Message History ({len(stored_messages)} messages):[/bold]")
            for msg in stored_messages[-10:]:  # Show last 10
                console.print(f"[{msg['timestamp']}] {msg['message']}")


@pubsub.command()
@click.argument('pattern')
@click.option('--all-sessions', is_flag=True, help='Search all sessions')
@click.option('--group', help='Search within group only')
@click.option('--context', type=int, default=2, help='Lines of context around matches')
@click.pass_context
def search(ctx: click.Context, pattern: str, all_sessions: bool, group: Optional[str], context: int) -> None:
    """Search for patterns across agent sessions.
    
    PATTERN: Text pattern to search for
    
    Examples:
        # Search for errors in all sessions
        tmux-orc search "error" --all-sessions
        
        # Search within development group
        tmux-orc search "test" --group development
        
        # Search with more context
        tmux-orc search "failed" --context 5
    """
    tmux: TMUXManager = ctx.obj['tmux']
    
    # Determine search targets
    if all_sessions:
        sessions = tmux.list_sessions()
        targets = []
        for session in sessions:
            windows = tmux.list_windows(session['name'])
            for window in windows:
                targets.append(f"{session['name']}:{window['index']}")
    elif group:
        targets = _get_group_members(tmux, group)
    else:
        console.print("[red]Error: Specify --all-sessions or --group[/red]")
        return
    
    console.print(f"[blue]Searching for '{pattern}' in {len(targets)} targets...[/blue]\n")
    
    matches_found = 0
    for target in targets:
        content = tmux.capture_pane(target, lines=200)
        if content and pattern.lower() in content.lower():
            matches_found += 1
            console.print(f"[green]✓ Found in {target}:[/green]")
            
            # Show matches with context
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if pattern.lower() in line.lower():
                    start = max(0, i - context)
                    end = min(len(lines), i + context + 1)
                    
                    for j in range(start, end):
                        if j == i:
                            console.print(f"  [bold yellow]→ {lines[j]}[/bold yellow]")
                        else:
                            console.print(f"    {lines[j]}")
                    console.print()
    
    console.print(f"\n[bold]Search complete: {matches_found} matches found[/bold]")


@pubsub.command()
@click.option('--format', type=click.Choice(['table', 'json', 'simple']), default='table')
@click.pass_context
def status(ctx: click.Context, format: str) -> None:
    """Show messaging system status and statistics.
    
    Examples:
        tmux-orc status                    # Table format
        tmux-orc status --format json      # JSON output
        tmux-orc status --format simple    # Simple text
    """
    tmux: TMUXManager = ctx.obj['tmux']
    
    # Gather statistics
    sessions = tmux.list_sessions()
    agents = tmux.list_agents()
    
    # Count messages by session
    message_counts: Dict[str, int] = {}
    for msg_file in MESSAGE_STORE.glob("*.json"):
        session_name = msg_file.stem
        with open(msg_file, 'r') as f:
            messages = json.load(f)
            message_counts[session_name] = len(messages)
    
    if format == 'json':
        import json as json_module
        stats = {
            'total_sessions': len(sessions),
            'total_agents': len(agents),
            'active_agents': len([a for a in agents if a['status'] == 'Active']),
            'message_counts': message_counts,
            'groups': {
                'management': len(_get_group_members(tmux, 'management')),
                'development': len(_get_group_members(tmux, 'development')),
                'qa': len(_get_group_members(tmux, 'qa'))
            }
        }
        console.print(json_module.dumps(stats, indent=2))
    
    elif format == 'simple':
        console.print(f"Sessions: {len(sessions)}")
        console.print(f"Agents: {len(agents)}")
        console.print(f"Active: {len([a for a in agents if a['status'] == 'Active'])}")
        console.print(f"Total Messages: {sum(message_counts.values())}")
    
    else:  # table format
        console.print("[bold]📊 Messaging System Status[/bold]\n")
        
        # Summary table
        summary_table = Table()
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="green")
        
        summary_table.add_row("Total Sessions", str(len(sessions)))
        summary_table.add_row("Total Agents", str(len(agents)))
        summary_table.add_row("Active Agents", str(len([a for a in agents if a['status'] == 'Active'])))
        summary_table.add_row("Total Messages", str(sum(message_counts.values())))
        
        console.print(summary_table)
        
        # Message counts by session
        if message_counts:
            console.print("\n[bold]📨 Messages by Session:[/bold]")
            msg_table = Table()
            msg_table.add_column("Session", style="cyan")
            msg_table.add_column("Messages", style="yellow")
            
            for session, count in sorted(message_counts.items(), key=lambda x: x[1], reverse=True):
                msg_table.add_row(session, str(count))
            
            console.print(msg_table)


def _get_group_members(tmux: TMUXManager, group: str) -> List[str]:
    """Get all session:window targets for a group."""
    targets = []
    sessions = tmux.list_sessions()
    
    for session in sessions:
        windows = tmux.list_windows(session['name'])
        for window in windows:
            window_name = window['name'].lower()
            session_name = session['name'].lower()
            target = f"{session['name']}:{window['index']}"
            
            if group == 'management':
                if any(role in window_name for role in ['pm', 'manager', 'orchestrator']):
                    targets.append(target)
            elif group == 'development':
                if any(role in window_name for role in ['dev', 'frontend', 'backend', 'fullstack']):
                    targets.append(target)
            elif group == 'qa':
                if any(role in window_name for role in ['qa', 'test', 'quality']):
                    targets.append(target)
    
    return targets


def _store_message(target: str, msg_data: Dict[str, Any]) -> None:
    """Store message in local file store."""
    session_file = MESSAGE_STORE / f"{target.replace(':', '_')}.json"
    
    if session_file.exists():
        with open(session_file, 'r') as f:
            messages = json.load(f)
    else:
        messages = []
    
    messages.append(msg_data)
    
    # Keep only last 1000 messages
    if len(messages) > 1000:
        messages = messages[-1000:]
    
    with open(session_file, 'w') as f:
        json.dump(messages, f, indent=2)


def _get_stored_messages(session: str, since: Optional[str]) -> List[Dict[str, Any]]:
    """Get stored messages for a session."""
    session_file = MESSAGE_STORE / f"{session.replace(':', '_')}.json"
    
    if not session_file.exists():
        return []
    
    with open(session_file, 'r') as f:
        messages = json.load(f)
    
    if since:
        since_dt = datetime.fromisoformat(since)
        messages = [msg for msg in messages 
                   if datetime.fromisoformat(msg['timestamp']) > since_dt]
    
    return messages