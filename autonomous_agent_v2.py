#!/usr/bin/env python3
"""
Autonomous LinkedIn Agent v2.0
Fully integrated automation system with:
- SafetyMonitor: Rate limiting and risk management
- CampaignExecutor: Targeted engagement campaigns
- NetworkGrowthAutomation: Connection requests and message sequences
- ConnectionManager: Network quality tracking

Runs continuously to:
- Post scheduled content
- Execute active campaigns
- Process incoming connection requests
- Send automated message sequences
- Track performance across all activities
"""

import time
import yaml
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import random
from rich.console import Console
from rich.table import Table

from database.db import Database
from database.models import Post, Comment
from linkedin.client import LinkedInClient
from linkedin.post_manager import PostManager
from utils.safety_monitor import SafetyMonitor
from utils.campaign_executor import CampaignExecutor
from utils.network_growth import NetworkGrowthAutomation
from linkedin.connection_manager import ConnectionManager
from linkedin.campaign_manager import CampaignManager

console = Console()


class AutonomousAgentV2:
    """Autonomous LinkedIn agent with full safety and campaign integration"""

    def __init__(self, config_path: str = 'config.yaml'):
        """
        Initialize the autonomous agent v2

        Args:
            config_path: Path to configuration file
        """
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        # Initialize database
        self.db = Database(self.config)

        # Get autonomous agent config
        self.agent_config = self.config.get('autonomous_agent', {})

        # Settings
        self.check_interval = self.agent_config.get('check_interval', 300)  # 5 minutes
        self.auto_post_scheduled = self.agent_config.get('auto_post_scheduled', True)
        self.enable_campaigns = self.agent_config.get('enable_campaigns', True)
        self.enable_network_growth = self.agent_config.get('enable_network_growth', True)

        # Campaign execution settings
        self.max_posts_per_cycle = self.agent_config.get('max_posts_per_cycle', 20)
        self.max_engagements_per_cycle = self.agent_config.get('max_engagements_per_cycle', 10)

        # Network growth settings
        self.max_connection_requests_per_cycle = self.agent_config.get('max_connection_requests_per_cycle', 3)
        self.max_incoming_requests_per_cycle = self.agent_config.get('max_incoming_requests_per_cycle', 5)
        self.process_message_sequences = self.agent_config.get('process_message_sequences', True)

        # LinkedIn client (will be initialized when needed)
        self.client = None
        self.post_manager = None

        # Managers (initialized per session)
        self.safety_monitor = None
        self.campaign_executor = None
        self.connection_manager = None
        self.campaign_manager = None
        self.network_growth = None

        # Tracking
        self.cycle_count = 0
        self.total_posts_published = 0
        self.total_campaign_engagements = 0
        self.total_connection_requests_sent = 0
        self.total_incoming_requests_processed = 0
        self.total_sequence_messages_sent = 0
        self.last_safety_pause = None
        self.consecutive_errors = 0

    def initialize_session(self):
        """Initialize database session and managers"""
        session = self.db.get_session()

        # Initialize managers
        self.safety_monitor = SafetyMonitor(session, self.config)
        self.campaign_manager = CampaignManager(session, self.config)
        self.connection_manager = ConnectionManager(session, self.config)
        self.network_growth = NetworkGrowthAutomation(session, self.config)

        return session

    def initialize_linkedin(self):
        """Initialize LinkedIn client and managers"""
        if self.client is None:
            console.print("[cyan]Initializing LinkedIn connection...[/cyan]")
            self.client = LinkedInClient(self.config)
            self.client.start()
            self.client.login()
            self.post_manager = PostManager(self.client)
            console.print("[green]✓ LinkedIn connected[/green]")

    def close_linkedin(self):
        """Close LinkedIn connection"""
        if self.client:
            try:
                self.client.stop()
            except:
                pass
            finally:
                self.client = None
                self.post_manager = None

    def check_safety_status(self, session) -> Dict:
        """
        Check safety status before performing actions

        Returns:
            Dict with safety status and whether to proceed
        """
        status = self.safety_monitor.get_safety_status()

        if status['status'] == 'limit_reached':
            console.print(f"\n[red]⛔ Safety Limit Reached[/red]")
            console.print(f"Reason: {status.get('message', 'Rate limits exceeded')}")
            console.print(f"Hourly: {status['activity_counts']['last_hour']}/{status['limits']['hourly_max']}")
            console.print(f"Daily: {status['activity_counts']['last_24h']}/{status['limits']['daily_max']}")

            self.last_safety_pause = datetime.utcnow()
            return {'proceed': False, 'status': status}

        elif status['status'] == 'alerts_active':
            console.print(f"\n[yellow]⚠️  Safety Alerts Active ({status['active_alerts']})[/yellow]")
            for alert in status.get('alert_details', [])[:3]:
                console.print(f"  - [{alert['severity']}] {alert['message']}")

        return {'proceed': True, 'status': status}

    def check_and_post_scheduled(self, session) -> int:
        """
        Check for scheduled posts and publish them

        Returns:
            Number of posts published
        """
        if not self.auto_post_scheduled:
            return 0

        # Check safety first
        safety_check = self.check_safety_status(session)
        if not safety_check['proceed']:
            console.print("[yellow]Skipping scheduled posts due to safety limits[/yellow]")
            return 0

        # Get posts due to be posted
        now = datetime.utcnow()
        due_posts = session.query(Post).filter(
            Post.is_scheduled == True,
            Post.published == False,
            Post.scheduled_time <= now
        ).all()

        if not due_posts:
            return 0

        console.print(f"\n[bold green]📅 Found {len(due_posts)} scheduled post(s) to publish[/bold green]")

        self.initialize_linkedin()
        published_count = 0

        for post in due_posts:
            # Double-check safety before each post
            if not self.safety_monitor.check_action_allowed('post')['allowed']:
                console.print(f"[yellow]⚠️  Safety limit reached, stopping scheduled posts[/yellow]")
                break

            console.print(f"\n[cyan]Publishing: {post.topic}[/cyan]")

            # Combine content and hashtags
            full_content = post.content
            if post.hashtags:
                full_content += f"\n\n{post.hashtags}"

            try:
                # Post to LinkedIn
                success = self.post_manager.create_post(full_content, wait_for_confirmation=False)

                if success:
                    # Update database
                    post.published = True
                    post.published_at = datetime.utcnow()
                    post.is_scheduled = False
                    session.commit()

                    # Log to safety monitor
                    self.safety_monitor.log_activity(
                        action_type='post',
                        target_type='post',
                        target_id=f'post-{post.id}',
                        duration=5.0,
                        success=True
                    )

                    published_count += 1
                    self.total_posts_published += 1
                    console.print(f"[green]✓ Post published successfully[/green]")
                else:
                    console.print(f"[yellow]⚠️  Failed to publish post[/yellow]")

                # Human-like delay between posts
                if len(due_posts) > 1 and published_count < len(due_posts):
                    delay = random.randint(60, 180)
                    console.print(f"[dim]Waiting {delay}s before next post...[/dim]")
                    time.sleep(delay)

            except Exception as e:
                console.print(f"[red]Error publishing post: {e}[/red]")
                self.consecutive_errors += 1
                continue

        return published_count

    def execute_campaigns(self, session) -> Dict:
        """
        Execute active campaigns

        Returns:
            Dict with execution results
        """
        if not self.enable_campaigns:
            return {'success': True, 'engagements': 0, 'message': 'Campaigns disabled'}

        # Check safety first
        safety_check = self.check_safety_status(session)
        if not safety_check['proceed']:
            console.print("[yellow]Skipping campaigns due to safety limits[/yellow]")
            return {'success': False, 'engagements': 0, 'message': 'Safety limits reached'}

        # Get active campaigns
        active_campaigns = self.campaign_manager.get_active_campaigns()

        if not active_campaigns:
            console.print("[dim]No active campaigns to execute[/dim]")
            return {'success': True, 'engagements': 0, 'message': 'No active campaigns'}

        console.print(f"\n[bold cyan]🎯 Executing {len(active_campaigns)} Active Campaign(s)[/bold cyan]")
        for campaign in active_campaigns:
            console.print(f"  - {campaign.name} ({campaign.campaign_type})")

        # Initialize campaign executor
        self.initialize_linkedin()
        self.campaign_executor = CampaignExecutor(session, self.client, self.config)

        try:
            # Execute campaigns
            result = self.campaign_executor.execute_campaigns(
                max_posts=self.max_posts_per_cycle,
                max_engagements=self.max_engagements_per_cycle
            )

            if result['success']:
                self.total_campaign_engagements += result.get('engagements_performed', 0)
                self.consecutive_errors = 0  # Reset error counter on success

                console.print(f"\n[green]✓ Campaign execution completed[/green]")
                console.print(f"  Posts matched: {result.get('posts_matched', 0)}")
                console.print(f"  Engagements: {result.get('engagements_performed', 0)}")
            else:
                console.print(f"\n[yellow]⚠️  Campaign execution had issues: {result.get('error', 'Unknown')}[/yellow]")

            return result

        except Exception as e:
            console.print(f"[red]Error executing campaigns: {e}[/red]")
            self.consecutive_errors += 1
            return {'success': False, 'engagements': 0, 'error': str(e)}

    def process_network_growth(self, session) -> Dict:
        """
        Process network growth activities

        Returns:
            Dict with network growth results
        """
        if not self.enable_network_growth:
            return {
                'success': True,
                'incoming_processed': 0,
                'sequences_sent': 0,
                'message': 'Network growth disabled'
            }

        # Check safety first
        safety_check = self.check_safety_status(session)
        if not safety_check['proceed']:
            console.print("[yellow]Skipping network growth due to safety limits[/yellow]")
            return {
                'success': False,
                'incoming_processed': 0,
                'sequences_sent': 0,
                'message': 'Safety limits reached'
            }

        console.print(f"\n[bold cyan]🌱 Processing Network Growth Activities[/bold cyan]")

        incoming_processed = 0
        sequences_sent = 0

        try:
            # Process incoming connection requests (auto-accept)
            console.print("\n[cyan]Processing incoming connection requests...[/cyan]")
            incoming_result = self.network_growth.process_incoming_requests(
                max_requests=self.max_incoming_requests_per_cycle
            )

            incoming_processed = incoming_result.get('accepted', 0)

            if incoming_result['total_processed'] > 0:
                console.print(f"  Processed: {incoming_result['total_processed']}")
                console.print(f"  Accepted: [green]{incoming_result['accepted']}[/green]")
                console.print(f"  Declined: [red]{incoming_result['declined']}[/red]")
                console.print(f"  Pending: [yellow]{incoming_result['pending']}[/yellow]")

                self.total_incoming_requests_processed += incoming_result['accepted']
            else:
                console.print("[dim]  No incoming requests to process[/dim]")

            # Process message sequences
            if self.process_message_sequences:
                console.print("\n[cyan]Processing message sequences...[/cyan]")
                sequence_result = self.network_growth.process_due_sequence_messages()

                sequences_sent = sequence_result.get('messages_sent', 0)

                if sequences_sent > 0:
                    console.print(f"  Messages sent: [green]{sequences_sent}[/green]")
                    console.print(f"  Failed: [red]{sequence_result.get('failed', 0)}[/red]")

                    self.total_sequence_messages_sent += sequences_sent

                    if sequence_result.get('sent_to'):
                        console.print(f"  [dim]Sent to: {', '.join(sequence_result['sent_to'][:3])}{'...' if len(sequence_result['sent_to']) > 3 else ''}[/dim]")
                else:
                    console.print("[dim]  No due messages to send[/dim]")

            self.consecutive_errors = 0  # Reset error counter on success
            console.print(f"\n[green]✓ Network growth processing completed[/green]")

            return {
                'success': True,
                'incoming_processed': incoming_processed,
                'sequences_sent': sequences_sent,
                'message': f'Processed {incoming_processed} requests, sent {sequences_sent} messages'
            }

        except Exception as e:
            console.print(f"[red]Error processing network growth: {e}[/red]")
            self.consecutive_errors += 1
            return {
                'success': False,
                'incoming_processed': incoming_processed,
                'sequences_sent': sequences_sent,
                'error': str(e)
            }

    def display_cycle_summary(self, session, posts_published: int, campaign_result: Dict, network_growth_result: Dict = None):
        """Display summary of current cycle"""
        console.print(f"\n[bold blue]{'='*60}[/bold blue]")
        console.print(f"[bold blue]Cycle {self.cycle_count} Summary[/bold blue]")
        console.print(f"[bold blue]{'='*60}[/bold blue]")

        # Safety status
        safety_status = self.safety_monitor.get_safety_status()
        status_color = {
            'safe': 'green',
            'warning': 'yellow',
            'alerts_active': 'yellow',
            'limit_reached': 'red'
        }.get(safety_status['status'], 'white')

        console.print(f"\n[bold]Safety Status:[/bold] [{status_color}]{safety_status['status'].upper()}[/{status_color}]")
        console.print(f"  Hourly: {safety_status['activity_counts']['last_hour']}/{safety_status['limits']['hourly_max']} ({safety_status['utilization']['hourly_percent']}%)")
        console.print(f"  Daily: {safety_status['activity_counts']['last_24h']}/{safety_status['limits']['daily_max']} ({safety_status['utilization']['daily_percent']}%)")
        console.print(f"  Risk Score: {safety_status['risk_score']:.2f}")

        # This cycle
        console.print(f"\n[bold]This Cycle:[/bold]")
        console.print(f"  Scheduled posts published: {posts_published}")
        console.print(f"  Campaign engagements: {campaign_result.get('engagements_performed', 0)}")
        console.print(f"  Campaigns executed: {campaign_result.get('campaigns_executed', 0)}")

        if network_growth_result:
            console.print(f"  Incoming requests accepted: {network_growth_result.get('incoming_processed', 0)}")
            console.print(f"  Sequence messages sent: {network_growth_result.get('sequences_sent', 0)}")

        # Totals
        console.print(f"\n[bold]Session Totals:[/bold]")
        console.print(f"  Total cycles: {self.cycle_count}")
        console.print(f"  Total posts: {self.total_posts_published}")
        console.print(f"  Total engagements: {self.total_campaign_engagements}")
        console.print(f"  Total connections accepted: {self.total_incoming_requests_processed}")
        console.print(f"  Total sequence messages: {self.total_sequence_messages_sent}")

        # Network stats
        network_stats = self.connection_manager.get_network_analytics(days_back=7)
        console.print(f"\n[bold]Network (7 days):[/bold]")
        console.print(f"  Total connections: {network_stats['total_connections']}")
        console.print(f"  Avg quality score: {network_stats['avg_quality_score']:.1f}/10")
        console.print(f"  Recent interactions: {network_stats['recent_interactions']}")

        # Active campaigns
        active_campaigns = self.campaign_manager.get_active_campaigns()
        if active_campaigns:
            console.print(f"\n[bold]Active Campaigns:[/bold]")
            for campaign in active_campaigns:
                console.print(f"  - {campaign.name}: {campaign.total_engagements} engagements ({campaign.success_rate:.1f}% success)")

    def run_cycle(self):
        """Run one cycle of autonomous operations"""
        self.cycle_count += 1
        session = None

        try:
            console.print(f"\n{'='*70}")
            console.print(f"[bold cyan]🤖 Autonomous Agent v2.0 - Cycle {self.cycle_count}[/bold cyan]")
            console.print(f"[bold cyan]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/bold cyan]")
            console.print(f"{'='*70}")

            # Initialize session and managers
            session = self.initialize_session()

            # Check overall safety status
            safety_check = self.check_safety_status(session)

            # If we're in safety pause, wait longer
            if not safety_check['proceed']:
                if self.last_safety_pause:
                    time_since_pause = (datetime.utcnow() - self.last_safety_pause).seconds / 60
                    console.print(f"[yellow]Paused for {time_since_pause:.1f} minutes due to safety limits[/yellow]")

                # Skip this cycle but show status
                posts_published = 0
                campaign_result = {'success': False, 'engagements_performed': 0, 'message': 'Safety limits reached'}
                network_growth_result = {'success': False, 'incoming_processed': 0, 'sequences_sent': 0, 'message': 'Safety limits reached'}
            else:
                # Check and post scheduled content
                console.print(f"\n[bold]1. Checking scheduled posts...[/bold]")
                posts_published = self.check_and_post_scheduled(session)

                # Execute campaigns
                console.print(f"\n[bold]2. Executing campaigns...[/bold]")
                campaign_result = self.execute_campaigns(session)

                # Process network growth
                console.print(f"\n[bold]3. Processing network growth...[/bold]")
                network_growth_result = self.process_network_growth(session)

            # Display cycle summary
            self.display_cycle_summary(session, posts_published, campaign_result, network_growth_result)

            console.print(f"\n[green]✓ Cycle {self.cycle_count} completed[/green]")

            # Reset consecutive errors on successful cycle
            if safety_check['proceed']:
                self.consecutive_errors = 0

        except KeyboardInterrupt:
            raise  # Re-raise to handle in main loop
        except Exception as e:
            console.print(f"[red]Error in cycle: {e}[/red]")
            self.consecutive_errors += 1

            # If too many consecutive errors, pause longer
            if self.consecutive_errors >= 3:
                console.print(f"[red]⚠️  {self.consecutive_errors} consecutive errors. Extending pause...[/red]")

            import traceback
            traceback.print_exc()

        finally:
            # Always close session and LinkedIn
            if session:
                try:
                    session.close()
                except:
                    pass

            self.close_linkedin()

    def run(self):
        """Run the autonomous agent continuously"""
        console.print(f"\n[bold green]{'='*70}[/bold green]")
        console.print(f"[bold green]🤖 Autonomous LinkedIn Agent v2.0 - Starting[/bold green]")
        console.print(f"[bold green]{'='*70}[/bold green]")

        # Display configuration
        console.print(f"\n[bold cyan]Configuration:[/bold cyan]")
        console.print(f"  Check interval: {self.check_interval}s ({self.check_interval/60:.1f} minutes)")
        console.print(f"  Scheduled posts: {'✓ Enabled' if self.auto_post_scheduled else '✗ Disabled'}")
        console.print(f"  Campaigns: {'✓ Enabled' if self.enable_campaigns else '✗ Disabled'}")
        console.print(f"  Network growth: {'✓ Enabled' if self.enable_network_growth else '✗ Disabled'}")
        console.print(f"\n[bold cyan]Per-Cycle Limits:[/bold cyan]")
        console.print(f"  Max posts: {self.max_posts_per_cycle}")
        console.print(f"  Max engagements: {self.max_engagements_per_cycle}")
        console.print(f"  Max incoming requests: {self.max_incoming_requests_per_cycle}")
        console.print(f"  Process sequences: {'✓ Yes' if self.process_message_sequences else '✗ No'}")

        # Display active campaigns
        session = self.initialize_session()
        campaign_manager = CampaignManager(session, self.config)
        active_campaigns = campaign_manager.get_active_campaigns()

        if active_campaigns:
            console.print(f"\n[bold cyan]Active Campaigns ({len(active_campaigns)}):[/bold cyan]")
            for campaign in active_campaigns:
                console.print(f"  - {campaign.name} ({campaign.campaign_type})")
                console.print(f"    Targets: {len(campaign.targets)} | Max/day: {campaign.max_actions_per_day}")
        else:
            console.print(f"\n[yellow]No active campaigns[/yellow]")
            console.print(f"[dim]Create and activate campaigns with: python main.py campaigns --action create[/dim]")

        session.close()

        console.print(f"\n[bold]Press Ctrl+C to stop[/bold]\n")

        try:
            while True:
                self.run_cycle()

                # Calculate sleep time (longer if consecutive errors)
                sleep_time = self.check_interval
                if self.consecutive_errors >= 3:
                    sleep_time = self.check_interval * 2  # Double sleep time on errors
                    console.print(f"\n[yellow]⚠️  Extended pause due to errors[/yellow]")

                console.print(f"\n[dim]💤 Sleeping for {sleep_time}s ({sleep_time/60:.1f} minutes)...[/dim]")
                console.print(f"[dim]Next cycle at {(datetime.now() + timedelta(seconds=sleep_time)).strftime('%H:%M:%S')}[/dim]")
                time.sleep(sleep_time)

        except KeyboardInterrupt:
            console.print(f"\n\n[yellow]{'='*70}[/yellow]")
            console.print(f"[yellow]🛑 Autonomous agent stopped by user[/yellow]")
            console.print(f"[yellow]{'='*70}[/yellow]")

            # Display final statistics
            console.print(f"\n[bold cyan]Session Statistics:[/bold cyan]")
            console.print(f"  Total cycles: {self.cycle_count}")
            console.print(f"  Posts published: {self.total_posts_published}")
            console.print(f"  Campaign engagements: {self.total_campaign_engagements}")
            console.print(f"  Connections accepted: {self.total_incoming_requests_processed}")
            console.print(f"  Sequence messages sent: {self.total_sequence_messages_sent}")
            console.print(f"\n[green]✓ Shutdown complete[/green]\n")

            self.close_linkedin()


if __name__ == '__main__':
    agent = AutonomousAgentV2()
    agent.run()
