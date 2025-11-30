#!/usr/bin/env python3
"""
Demo script for testing automation modes system
"""

import yaml
from datetime import datetime
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

# Load environment variables
load_dotenv()

# Import modules
from ai import get_ai_provider
from database import Database
from utils import SafetyMonitor

# Import automation modes
from automation_modes import (
    AutomationManager,
    FeedEngagementMode,
    PostResponseMode,
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


def main():
    """Demo automation modes"""
    console.print("[bold blue]LinkedIn Automation Modes - Demo[/bold blue]\n")

    # Load config
    config = load_config()
    automation_config = config.get('automation_modes', {})

    # Initialize components
    db = Database(config.get('database', {}))
    session = db.Session()

    ai_provider = get_ai_provider(config)
    safety_monitor = SafetyMonitor(
        session,
        config.get('safety', {})
    )

    # LinkedIn client is None for simulation mode
    linkedin_client = None

    console.print("[yellow]Running in SIMULATION MODE (no LinkedIn browser)[/yellow]\n")

    # Create automation manager
    manager = AutomationManager(
        config=automation_config,
        linkedin_client=linkedin_client,
        ai_provider=ai_provider,
        db_session=session,
        safety_monitor=safety_monitor
    )

    console.print("[bold cyan]Registering Automation Modes...[/bold cyan]")

    # Register all modes
    modes_to_register = [
        FeedEngagementMode(automation_config, linkedin_client, ai_provider, session, safety_monitor),
        PostResponseMode(automation_config, linkedin_client, ai_provider, session, safety_monitor),
        GroupNetworkingMode(automation_config, linkedin_client, ai_provider, session, safety_monitor),
        ConnectionOutreachMode(automation_config, linkedin_client, ai_provider, session, safety_monitor),
        InfluencerEngagementMode(automation_config, linkedin_client, ai_provider, session, safety_monitor),
        JobMarketResearchMode(automation_config, linkedin_client, ai_provider, session, safety_monitor),
        DirectMessagingMode(automation_config, linkedin_client, ai_provider, session, safety_monitor),
        ContentRepurposingMode(automation_config, linkedin_client, ai_provider, session, safety_monitor),
        PassiveListeningMode(automation_config, linkedin_client, ai_provider, session, safety_monitor)
    ]

    for mode in modes_to_register:
        manager.register_mode(mode)
        console.print(f"  ✓ Registered: {mode.name}")

    console.print()

    # Show configuration
    table = Table(title="Automation Modes Configuration")
    table.add_column("Mode", style="cyan")
    table.add_column("Enabled", style="green")
    table.add_column("Active", style="yellow")

    active_mode_names = automation_config.get('active_modes', [])

    for mode in modes_to_register:
        enabled = "✓" if mode.enabled else "✗"
        active = "✓" if mode.name in active_mode_names else "✗"
        table.add_row(mode.name, enabled, active)

    console.print(table)
    console.print()

    # Run active modes
    console.print("[bold cyan]Running Active Modes...[/bold cyan]\n")

    results = manager.run_all_active_modes()

    # Display results
    for result in results:
        mode_name = result.get('mode', 'unknown')
        success = result.get('success', False)
        status = "[green]✓ SUCCESS[/green]" if success else "[red]✗ FAILED[/red]"

        console.print(f"{status} - {mode_name}")

        # Show metrics
        for key, value in result.items():
            if key not in ['mode', 'success', 'duration', 'actions', 'error', 'simulated']:
                console.print(f"    {key}: {value}")

        if 'simulated' in result:
            console.print("    [yellow](Simulated - no LinkedIn client)[/yellow]")

        console.print()

    # Show manager stats
    console.print("[bold cyan]Manager Statistics:[/bold cyan]")
    stats = manager.get_stats()

    manager_stats = stats['manager']
    console.print(f"  Total Modes: {manager_stats['total_modes']}")
    console.print(f"  Active Modes: {manager_stats['active_modes']}")
    console.print(f"  Full Automation: {manager_stats['full_automation']}")
    console.print(f"  Scheduler Enabled: {manager_stats['scheduler_enabled']}")

    console.print("\n[bold green]Demo Complete![/bold green]")
    console.print("\n[dim]To enable real automation, set 'use_automation: true' in config.yaml")
    console.print("and enable specific modes under 'automation_modes' section.[/dim]", markup=False)

    session.close()


if __name__ == "__main__":
    main()
