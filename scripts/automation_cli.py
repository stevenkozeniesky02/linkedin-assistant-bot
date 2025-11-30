#!/usr/bin/env python3
"""
CLI for LinkedIn Automation Modes

Individual commands to test each automation mode
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import project modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml
import click
from rich.console import Console
from rich.table import Table
from dotenv import load_dotenv

load_dotenv()

from ai import get_ai_provider
from database import Database
from utils import SafetyMonitor
from automation_modes import (
    AutomationManager,
    FeedEngagementMode,
    PostResponseMode,
    ConnectionSyncMode,
    GroupNetworkingMode,
    ConnectionOutreachMode,
    InfluencerEngagementMode,
    JobMarketResearchMode,
    DirectMessagingMode,
    ContentRepurposingMode,
    PassiveListeningMode
)

console = Console()


def load_config():
    """Load configuration"""
    with open('config.yaml', 'r') as f:
        return yaml.safe_load(f)


def init_components():
    """Initialize common components"""
    config = load_config()
    automation_config = config.get('automation_modes', {})

    # Initialize database
    db = Database(config.get('database', {}))
    session = db.Session()

    # Initialize AI provider
    ai_provider = get_ai_provider(config)

    # Initialize safety monitor
    safety_monitor = SafetyMonitor(session, config.get('safety', {}))

    # LinkedIn client (None for simulation mode)
    linkedin_client = None
    use_automation = config.get('network_growth', {}).get('use_automation', False)

    if use_automation:
        from linkedin import LinkedInClient
        console.print("[yellow]Initializing LinkedIn automation (browser will launch)...[/yellow]")
        linkedin_client = LinkedInClient(config)
        linkedin_client.start()
        if not linkedin_client.is_logged_in():
            console.print("[cyan]Logging into LinkedIn...[/cyan]")
            if not linkedin_client.login():
                console.print("[red]Failed to login - continuing in simulation mode[/red]")
                linkedin_client.stop()
                linkedin_client = None
    else:
        console.print("[yellow]Running in SIMULATION MODE (no LinkedIn browser)[/yellow]")

    return config, automation_config, session, ai_provider, safety_monitor, linkedin_client


def display_result(result: dict):
    """Display automation mode result"""
    mode_name = result.get('mode', 'unknown')
    success = result.get('success', False)

    status = "[green]✓ SUCCESS[/green]" if success else "[red]✗ FAILED[/red]"
    console.print(f"\n{status} - {mode_name}")

    if 'error' in result:
        console.print(f"  [red]Error: {result['error']}[/red]")

    # Show metrics
    for key, value in result.items():
        if key not in ['mode', 'success', 'duration', 'actions', 'error', 'simulated']:
            console.print(f"  {key}: {value}")

    if 'duration' in result:
        console.print(f"  Duration: {result['duration']:.1f}s")

    if result.get('simulated'):
        console.print("  [yellow](Simulated - no LinkedIn client)[/yellow]")

    console.print()


@click.group()
def cli():
    """LinkedIn Automation Modes CLI"""
    console.print("[bold blue]LinkedIn Automation Modes[/bold blue]\n")


@cli.command()
@click.option('--duration', default=15, help='Duration in minutes to scroll feed')
@click.option('--strategy', type=click.Choice(['conservative', 'balanced', 'aggressive']), default=None, help='Engagement strategy')
def feed_engagement(duration, strategy):
    """Engage with LinkedIn feed (likes, comments, shares)"""
    config, auto_config, session, ai, safety, client = init_components()

    # Override duration if provided
    if duration:
        auto_config.setdefault('feed_engagement', {})['scroll_duration_minutes'] = duration

    # Override strategy if provided
    if strategy:
        auto_config.setdefault('feed_engagement', {})['engagement_strategy'] = strategy

    mode = FeedEngagementMode(auto_config, client, ai, session, safety)
    result = mode.start()
    display_result(result)

    if client:
        client.stop()
    session.close()


@cli.command()
def post_response():
    """Monitor and respond to comments on your posts"""
    config, auto_config, session, ai, safety, client = init_components()

    mode = PostResponseMode(auto_config, client, ai, session, safety)
    result = mode.start()
    display_result(result)

    if client:
        client.stop()
    session.close()


@cli.command()
def connection_sync():
    """Sync LinkedIn connections to database"""
    config, auto_config, session, ai, safety, client = init_components()

    if not client:
        console.print("[red]LinkedIn client required - enable use_automation in config[/red]")
        session.close()
        return

    mode = ConnectionSyncMode(auto_config.get('connection_sync', {}), client, ai, session, safety)
    result = mode.start()
    display_result(result)

    if client:
        client.stop()
    session.close()


@cli.command()
def group_networking():
    """Join and engage with LinkedIn groups"""
    config, auto_config, session, ai, safety, client = init_components()

    mode = GroupNetworkingMode(auto_config, client, ai, session, safety)
    result = mode.start()
    display_result(result)

    if client:
        client.stop()
    session.close()


@cli.command()
def connection_outreach():
    """Send targeted connection requests"""
    config, auto_config, session, ai, safety, client = init_components()

    mode = ConnectionOutreachMode(auto_config, client, ai, session, safety)
    result = mode.start()
    display_result(result)

    if client:
        client.stop()
    session.close()


@cli.command()
def influencer_engagement():
    """Engage with industry influencers"""
    config, auto_config, session, ai, safety, client = init_components()

    mode = InfluencerEngagementMode(auto_config, client, ai, session, safety)
    result = mode.start()
    display_result(result)

    if client:
        client.stop()
    session.close()


@cli.command()
def job_research():
    """Monitor job market and engage with recruiters"""
    config, auto_config, session, ai, safety, client = init_components()

    mode = JobMarketResearchMode(auto_config, client, ai, session, safety)
    result = mode.start()
    display_result(result)

    if client:
        client.stop()
    session.close()


@cli.command()
def direct_messaging():
    """Send direct message campaigns"""
    config, auto_config, session, ai, safety, client = init_components()

    mode = DirectMessagingMode(auto_config, client, ai, session, safety)
    result = mode.start()
    display_result(result)

    if client:
        client.stop()
    session.close()


@cli.command()
def content_repurposing():
    """Repurpose and repost successful content"""
    config, auto_config, session, ai, safety, client = init_components()

    mode = ContentRepurposingMode(auto_config, client, ai, session, safety)
    result = mode.start()
    display_result(result)

    if client:
        client.stop()
    session.close()


@cli.command()
def passive_listening():
    """Monitor keywords and track mentions"""
    config, auto_config, session, ai, safety, client = init_components()

    mode = PassiveListeningMode(auto_config, client, ai, session, safety)
    result = mode.start()
    display_result(result)

    if client:
        client.stop()
    session.close()


@cli.command()
def list_modes():
    """List all automation modes and their status"""
    config = load_config()
    auto_config = config.get('automation_modes', {})
    active_modes = auto_config.get('active_modes', [])

    table = Table(title="Automation Modes")
    table.add_column("Mode", style="cyan")
    table.add_column("Enabled", style="green")
    table.add_column("Active", style="yellow")
    table.add_column("Description", style="dim")

    modes_info = [
        ('feed_engagement', 'Engage with LinkedIn feed (likes, comments, shares)'),
        ('post_response', 'Monitor and respond to comments on your posts'),
        ('group_networking', 'Join and engage with LinkedIn groups'),
        ('connection_outreach', 'Send targeted connection requests'),
        ('influencer_engagement', 'Engage with industry influencers'),
        ('job_market_research', 'Monitor job market and recruiters'),
        ('direct_messaging', 'Send direct message campaigns'),
        ('content_repurposing', 'Repurpose and repost successful content'),
        ('passive_listening', 'Monitor keywords and track mentions')
    ]

    for mode_name, description in modes_info:
        mode_config = auto_config.get(mode_name, {})
        enabled = "✓" if mode_config.get('enabled', False) else "✗"
        active = "✓" if mode_name in active_modes else "✗"
        table.add_row(mode_name, enabled, active, description)

    console.print(table)
    console.print(f"\nFull Automation: {auto_config.get('full_automation', False)}")
    console.print(f"Scheduler Enabled: {auto_config.get('scheduler', {}).get('enabled', True)}")


@cli.command()
def run_all():
    """Run all active automation modes"""
    config, auto_config, session, ai, safety, client = init_components()

    # Create manager
    manager = AutomationManager(auto_config, client, ai, session, safety)

    # Register all modes
    modes = [
        FeedEngagementMode(auto_config, client, ai, session, safety),
        PostResponseMode(auto_config, client, ai, session, safety),
        GroupNetworkingMode(auto_config, client, ai, session, safety),
        ConnectionOutreachMode(auto_config, client, ai, session, safety),
        InfluencerEngagementMode(auto_config, client, ai, session, safety),
        JobMarketResearchMode(auto_config, client, ai, session, safety),
        DirectMessagingMode(auto_config, client, ai, session, safety),
        ContentRepurposingMode(auto_config, client, ai, session, safety),
        PassiveListeningMode(auto_config, client, ai, session, safety)
    ]

    for mode in modes:
        manager.register_mode(mode)

    console.print("[bold cyan]Running All Active Modes...[/bold cyan]\n")

    # Run all active modes
    results = manager.run_all_active_modes()

    # Display all results
    for result in results:
        display_result(result)

    # Show stats
    stats = manager.get_stats()
    console.print("[bold cyan]Summary:[/bold cyan]")
    console.print(f"  Total Modes: {stats['manager']['total_modes']}")
    console.print(f"  Active Modes: {stats['manager']['active_modes']}")
    console.print(f"  Modes Run: {len(results)}")

    if client:
        client.stop()
    session.close()


if __name__ == '__main__':
    cli()
