#!/usr/bin/env python3
"""Standalone CLI for Safety Monitor and Connection Manager"""

import yaml
import click
from rich.console import Console
from rich.table import Table
from database.db import Database
from utils.safety_monitor import SafetyMonitor
from linkedin.connection_manager import ConnectionManager

console = Console()

def load_config():
    """Load configuration from config.yaml"""
    with open('config.yaml', 'r') as f:
        return yaml.safe_load(f)

@click.group()
def cli():
    """LinkedIn Safety & Connection Management Tools"""
    pass

@cli.command()
def safety_status():
    """Check current safety status and activity limits"""
    try:
        config = load_config()
        db = Database(config)
        session = db.get_session()
        safety_monitor = SafetyMonitor(session, config)

        status = safety_monitor.get_safety_status()

        console.print("\n[bold blue]═══ Safety Status ═══[/bold blue]\n")

        # Status indicator
        status_colors = {'safe': 'green', 'warning': 'yellow', 'alerts_active': 'yellow', 'limit_reached': 'red'}
        color = status_colors.get(status['status'], 'white')
        console.print(f"Status: [{color}]{status['status'].replace('_', ' ').upper()}[/{color}]\n")

        # Activity counts
        console.print("[bold cyan]Activity Counts:[/bold cyan]")
        counts_table = Table(show_header=False)
        counts_table.add_column("Metric", style="cyan")
        counts_table.add_column("Count", justify="right", style="white")
        counts_table.add_row("Last Hour", str(status['activity_counts']['last_hour']))
        counts_table.add_row("Last 24 Hours", str(status['activity_counts']['last_24h']))
        counts_table.add_row("Last 7 Days", str(status['activity_counts']['last_7d']))
        console.print(counts_table)
        console.print()

        # Limits
        console.print("[bold cyan]Rate Limits:[/bold cyan]")
        limits_table = Table(show_header=False)
        limits_table.add_column("Limit", style="cyan")
        limits_table.add_column("Max", justify="right", style="white")
        limits_table.add_row("Hourly Max", str(status['limits']['hourly_max']))
        limits_table.add_row("Daily Max", str(status['limits']['daily_max']))
        limits_table.add_row("Posts per Day", str(status['limits']['posts_daily_max']))
        limits_table.add_row("Comments per Day", str(status['limits']['comments_daily_max']))
        limits_table.add_row("Connections per Day", str(status['limits']['connections_daily_max']))
        console.print(limits_table)
        console.print()

        # Utilization
        console.print("[bold cyan]Utilization:[/bold cyan]")
        hourly_util = status['utilization']['hourly_percent']
        daily_util = status['utilization']['daily_percent']
        hourly_color = 'green' if hourly_util < 50 else 'yellow' if hourly_util < 80 else 'red'
        daily_color = 'green' if daily_util < 50 else 'yellow' if daily_util < 80 else 'red'
        console.print(f"  Hourly: [{hourly_color}]{hourly_util}%[/{hourly_color}]")
        console.print(f"  Daily:  [{daily_color}]{daily_util}%[/{daily_color}]")
        console.print()

        # Risk score
        risk_color = 'green' if status['risk_score'] < 0.3 else 'yellow' if status['risk_score'] < 0.6 else 'red'
        console.print(f"[bold]Risk Score:[/bold] [{risk_color}]{status['risk_score']}[/{risk_color}] (0-1 scale)")
        console.print()

        # Active alerts
        if status['active_alerts'] > 0:
            console.print(f"[bold red]Active Alerts: {status['active_alerts']}[/bold red]\n")
            alerts_table = Table(show_header=True, header_style="bold magenta")
            alerts_table.add_column("Type", style="cyan")
            alerts_table.add_column("Severity", style="yellow")
            alerts_table.add_column("Message", width=50)
            for alert in status['alert_details']:
                severity_color = 'yellow' if alert['severity'] == 'medium' else 'red' if alert['severity'] == 'high' else 'white'
                alerts_table.add_row(alert['type'], f"[{severity_color}]{alert['severity']}[/{severity_color}]", alert['message'])
            console.print(alerts_table)
            console.print()
        else:
            console.print("[green]No active alerts[/green]\n")

        session.close()
        db.close()
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

@cli.command()
@click.option('--action', type=click.Choice(['add', 'list', 'top', 'mark-target']), default='list')
@click.option('--name', help='Connection name (for add action)')
@click.option('--url', help='LinkedIn profile URL (for add/mark-target action)')
@click.option('--title', help='Job title (for add action)')
@click.option('--company', help='Company (for add action)')
@click.option('--limit', default=10, help='Limit results (for top action)')
def connections(action, name, url, title, company, limit):
    """Manage LinkedIn connections"""
    try:
        config = load_config()
        db = Database(config)
        session = db.get_session()
        conn_manager = ConnectionManager(session, config)

        if action == 'add':
            if not name or not url:
                console.print("[red]Error: --name and --url are required for add action[/red]")
                return
            connection = conn_manager.add_connection(name=name, profile_url=url, title=title, company=company)
            console.print(f"\n[green]✓ Connection added: {connection.name}[/green]")
            console.print(f"  Quality Score: {connection.quality_score}/10\n")

        elif action == 'list':
            connections_list = conn_manager.get_all_connections(active_only=True)
            if not connections_list:
                console.print("\n[yellow]No connections found[/yellow]")
                return
            console.print(f"\n[bold blue]Your Connections ({len(connections_list)} total)[/bold blue]\n")
            conn_table = Table(show_header=True, header_style="bold magenta")
            conn_table.add_column("Name", style="cyan", width=25)
            conn_table.add_column("Title", width=30)
            conn_table.add_column("Company", width=20)
            conn_table.add_column("Quality", justify="center", width=8)
            conn_table.add_column("Engagement", width=10)
            for conn in connections_list[:50]:
                quality_color = 'green' if conn.quality_score >= 7 else 'yellow' if conn.quality_score >= 4 else 'red'
                conn_table.add_row(
                    conn.name[:25],
                    (conn.title or "N/A")[:30],
                    (conn.company or "N/A")[:20],
                    f"[{quality_color}]{conn.quality_score:.1f}[/{quality_color}]",
                    conn.engagement_level or "none"
                )
            console.print(conn_table)
            console.print()

        elif action == 'top':
            top_connections = conn_manager.get_top_connections(limit=limit)
            if not top_connections:
                console.print("\n[yellow]No connections found[/yellow]")
                return
            console.print(f"\n[bold green]Top {len(top_connections)} Connections[/bold green]\n")
            top_table = Table(show_header=True, header_style="bold magenta")
            top_table.add_column("Rank", justify="center", width=6)
            top_table.add_column("Name", style="cyan", width=25)
            top_table.add_column("Title", width=35)
            top_table.add_column("Quality", justify="center", width=8)
            top_table.add_column("Messages", justify="center", width=10)
            for i, conn in enumerate(top_connections, 1):
                total_messages = conn.messages_sent + conn.messages_received
                top_table.add_row(f"#{i}", conn.name[:25], (conn.title or "N/A")[:35],
                                f"[bold green]{conn.quality_score:.1f}[/bold green]", str(total_messages))
            console.print(top_table)
            console.print()

        elif action == 'mark-target':
            if not url:
                console.print("[red]Error: --url is required for mark-target action[/red]")
                return
            connection = conn_manager.mark_target_audience(url, is_target=True)
            if connection:
                console.print(f"\n[green]✓ {connection.name} marked as target audience[/green]\n")
            else:
                console.print(f"\n[red]Connection not found: {url}[/red]\n")

        session.close()
        db.close()
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

@cli.command()
@click.option('--days', default=30, help='Number of days to analyze (default: 30)')
def network_analytics(days):
    """View network analytics and growth metrics"""
    try:
        config = load_config()
        db = Database(config)
        session = db.get_session()
        conn_manager = ConnectionManager(session, config)

        analytics = conn_manager.get_network_analytics(days_back=days)
        recommendations = conn_manager.get_connection_recommendations()

        console.print(f"\n[bold blue]═══ Network Analytics (Last {days} Days) ═══[/bold blue]\n")

        # Overview
        console.print("[bold cyan]Network Overview:[/bold cyan]")
        overview_table = Table(show_header=False)
        overview_table.add_column("Metric", style="cyan", width=30)
        overview_table.add_column("Value", justify="right", style="white")
        overview_table.add_row("Total Connections", str(analytics['total_connections']))
        overview_table.add_row("New Connections", str(analytics['recent_connections']))
        overview_table.add_row("Average Quality Score", f"{analytics['avg_quality_score']}/10")
        overview_table.add_row("Target Audience", f"{analytics['target_audience_count']} ({analytics['target_audience_percent']}%)")
        overview_table.add_row("Recent Interactions", str(analytics['recent_interactions']))
        overview_table.add_row("Growth Rate", f"{analytics['growth_rate_per_day']:.2f} per day")
        console.print(overview_table)
        console.print()

        # Engagement breakdown
        console.print("[bold cyan]Engagement Levels:[/bold cyan]")
        engagement_table = Table(show_header=True, header_style="bold magenta")
        engagement_table.add_column("Level", style="cyan")
        engagement_table.add_column("Count", justify="right")
        engagement_table.add_column("Percentage", justify="right")
        total = analytics['total_connections']
        for level in ['high', 'medium', 'low', 'none']:
            count = analytics['engagement_breakdown'][level]
            pct = (count / total * 100) if total > 0 else 0
            color = 'green' if level == 'high' else 'yellow' if level == 'medium' else 'white'
            engagement_table.add_row(level.capitalize(), str(count), f"[{color}]{pct:.1f}%[/{color}]")
        console.print(engagement_table)
        console.print()

        # Top companies
        if analytics['top_companies']:
            console.print("[bold cyan]Top Companies:[/bold cyan]")
            companies_table = Table(show_header=True, header_style="bold magenta")
            companies_table.add_column("Rank", justify="center", width=6)
            companies_table.add_column("Company", style="cyan", width=40)
            companies_table.add_column("Connections", justify="right")
            for i, company_data in enumerate(analytics['top_companies'][:10], 1):
                companies_table.add_row(f"#{i}", company_data['company'][:40], str(company_data['count']))
            console.print(companies_table)
            console.print()

        # Recommendations
        console.print("[bold cyan]Recommendations:[/bold cyan]")
        health_color = 'green' if recommendations['health_status'] == 'good' else 'yellow'
        console.print(f"Network Health: [{health_color}]{recommendations['health_status'].upper()}[/{health_color}]")
        console.print(f"Overall Score: {recommendations['overall_score']:.1f}/10\n")
        for rec in recommendations['recommendations']:
            priority_color = 'red' if rec['priority'] == 'high' else 'yellow' if rec['priority'] == 'medium' else 'blue'
            console.print(f"  [{priority_color}]●[/{priority_color}] {rec['message']}")
            console.print(f"    [dim]→ {rec['action']}[/dim]")
            console.print()

        session.close()
        db.close()
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

if __name__ == '__main__':
    cli()
