#!/usr/bin/env python3
"""
LinkedIn Assistant Bot - Simple Interactive Menu
Run this to start the bot!
"""

import os
import sys
import yaml
import subprocess
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table

console = Console()

def clear():
    os.system('clear' if os.name != 'nt' else 'cls')

def first_time_check():
    return not Path('linkedin_assistant.db').exists() or not Path('linkedin_session.pkl').exists()

def welcome():
    clear()
    console.print(Panel("[bold cyan]LinkedIn Assistant Bot[/bold cyan]\n\nAutomate your LinkedIn networking!", border_style="cyan"))
    print()

def setup():
    console.print("[bold yellow]First Time Setup[/bold yellow]\n")
    console.print("Checking configuration...")
    
    config = yaml.safe_load(open('config.yaml'))
    if not config.get('network_growth', {}).get('use_automation'):
        console.print("[yellow]Note: Automation is disabled. Enable in config.yaml to use LinkedIn features.[/yellow]\n")
        if not Confirm.ask("Continue in demo mode?"):
            return False
    
    console.print("\n[green]Setup complete![/green]\n")
    input("Press Enter to continue...")
    return True

def menu():
    clear()
    welcome()
    
    table = Table(show_header=False, border_style="cyan")
    table.add_column("", style="cyan", width=2)
    table.add_column("")
    
    table.add_row("1", "Feed Engagement - Like & comment on posts")
    table.add_row("2", "Sync Connections - Import your connections")
    table.add_row("3", "Connection Outreach - Send connection requests")
    table.add_row("4", "Post Response - Reply to your post comments")
    table.add_row("5", "Direct Messages - Send message campaigns")
    table.add_row("6", "Influencer Engagement - Engage with leaders")
    table.add_row("7", "Group Networking - Join & engage in groups")
    table.add_row("8", "Job Research - Monitor jobs & recruiters")
    table.add_row("9", "Full Automation - Run all active modes")
    table.add_row("", "")
    table.add_row("V", "View Network Visualization")
    table.add_row("S", "Settings")
    table.add_row("Q", "Quit")
    
    console.print(table)
    return Prompt.ask("\nSelect", default="1").upper()

def run_mode(cmd):
    try:
        subprocess.run([sys.executable, "scripts/automation_cli.py"] + cmd.split())
        input("\nPress Enter to continue...")
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped[/yellow]")
        input("Press Enter to continue...")

def main():
    if first_time_check():
        welcome()
        if not setup():
            return
    
    while True:
        choice = menu()
        
        if choice == "1":
            clear()
            console.print("[bold cyan]Feed Engagement Settings[/bold cyan]\n")

            # Get duration
            dur = Prompt.ask("Feed duration (minutes)", default="15")

            # Get engagement strategy
            console.print("\n[bold]Engagement Strategy:[/bold]")
            console.print("  1. Conservative (5 likes, 2 comments, 0 shares) - Safest")
            console.print("  2. Balanced (15 likes, 5 comments, 2 shares) - Moderate")
            console.print("  3. Aggressive (30 likes, 10 comments, 5 shares) - High risk")

            strategy_choice = Prompt.ask("\nChoose strategy", choices=["1", "2", "3"], default="2")
            strategy_map = {"1": "conservative", "2": "balanced", "3": "aggressive"}
            strategy = strategy_map[strategy_choice]

            run_mode(f"feed-engagement --duration {dur} --strategy {strategy}")
        elif choice == "2":
            run_mode("connection-sync")
        elif choice == "3":
            run_mode("connection-outreach")
        elif choice == "4":
            run_mode("post-response")
        elif choice == "5":
            run_mode("direct-messaging")
        elif choice == "6":
            run_mode("influencer-engagement")
        elif choice == "7":
            run_mode("group-networking")
        elif choice == "8":
            run_mode("job-research")
        elif choice == "9":
            run_mode("run-all")
        elif choice == "V":
            clear()
            console.print("[cyan]Opening network visualization...[/cyan]\n")
            try:
                subprocess.run([sys.executable, "scripts/generate_network_graph.py"])
                input("\nVisualization complete! Check network.html")
            except KeyboardInterrupt:
                pass
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
            input("\nPress Enter to continue...")
        elif choice == "S":
            clear()
            config = yaml.safe_load(open('config.yaml'))
            console.print("[cyan]Current Settings:[/cyan]\n")
            console.print(f"Automation: {'Enabled' if config.get('network_growth', {}).get('use_automation') else 'Disabled'}")
            console.print(f"Active Modes: {', '.join(config.get('automation_modes', {}).get('active_modes', []))}")
            console.print(f"AI Provider: {config.get('ai_provider')}")

            # Show engagement strategy
            strategy = config.get('automation_modes', {}).get('feed_engagement', {}).get('engagement_strategy', 'balanced')
            console.print(f"\n[bold]Feed Engagement Strategy:[/bold] {strategy.upper()}")

            # Show limits based on strategy
            strategies = {
                'conservative': '5 likes, 2 comments, 0 shares (safest)',
                'balanced': '15 likes, 5 comments, 2 shares (moderate)',
                'aggressive': '30 likes, 10 comments, 5 shares (high risk)'
            }
            if strategy in strategies:
                console.print(f"  {strategies[strategy]}")

            console.print("\n[yellow]Edit config.yaml to change settings[/yellow]")
            console.print("[dim]  engagement_strategy: conservative | balanced | aggressive[/dim]")
            input("\nPress Enter to continue...")
        elif choice == "Q":
            clear()
            console.print("\n[cyan]Thanks for using LinkedIn Assistant Bot![/cyan]\n")
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        clear()
        console.print("\n[yellow]Goodbye![/yellow]\n")
