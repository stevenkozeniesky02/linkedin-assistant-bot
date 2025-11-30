#!/usr/bin/env python3
"""
LinkedIn Assistant Bot - Main Entry Point

A CLI tool for automated LinkedIn profile management with AI-powered content generation.
"""

import os
import yaml
from datetime import datetime, timedelta
from dotenv import load_dotenv
import click
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from dateutil import parser

# Load environment variables
load_dotenv()

# Import modules
from ai import get_ai_provider
from linkedin import LinkedInClient, PostManager, EngagementManager, ConnectionManager
from database import Database, Post, Comment, Analytics, Connection, Activity, SafetyAlert
from utils import Scheduler, SafetyMonitor
from utils.analytics_engine import AnalyticsEngine
from utils.analytics_visualizer import AnalyticsVisualizer

# Initialize console for rich output
console = Console()


def load_config():
    """Load configuration from config.yaml"""
    with open('config.yaml', 'r') as f:
        return yaml.safe_load(f)


@click.group()
def cli():
    """LinkedIn Assistant Bot - AI-powered LinkedIn profile management"""
    console.print("[bold blue]LinkedIn Assistant Bot[/bold blue]", style="bold")
    console.print("AI-powered LinkedIn automation\n")


@cli.command()
@click.option('--topic', prompt='Post topic', help='Topic for the post')
@click.option('--tone', default='professional', help='Tone: professional, casual, thought_leader, technical')
@click.option('--length', default='medium', help='Length: short, medium, long')
def generate_post(topic, tone, length):
    """Generate a LinkedIn post using AI"""
    try:
        # Load configuration
        config = load_config()
        content_config = config.get('content', {})

        # Initialize AI provider
        console.print(f"\n[cyan]Initializing AI provider ({config['ai_provider']})...[/cyan]")
        ai_provider = get_ai_provider(config)

        # Generate post
        console.print(f"[cyan]Generating post about: {topic}[/cyan]")
        result = ai_provider.generate_post(
            topic=topic,
            tone=tone,
            length=length,
            include_emojis=content_config.get('include_emojis', True),
            include_hashtags=content_config.get('include_hashtags', True),
            max_hashtags=content_config.get('max_hashtags', 5)
        )

        # Display generated post
        console.print("\n" + "="*60)
        console.print("[bold green]GENERATED POST:[/bold green]")
        console.print("="*60)
        console.print(result['content'])
        if result['hashtags']:
            console.print(f"\n[bold]Hashtags:[/bold] {result['hashtags']}")
        console.print("="*60)

        # Ask if user wants to save to database
        save = click.confirm('\nSave this post to database?', default=True)

        if save:
            # Initialize database
            db = Database(config)
            session = db.get_session()

            # Create post record
            post = Post(
                content=result['content'],
                hashtags=result['hashtags'],
                topic=topic,
                tone=tone,
                length=length,
                ai_provider=config['ai_provider'],
                ai_model=config.get(config['ai_provider'], {}).get('model', 'unknown'),
                published=False
            )

            session.add(post)
            session.commit()

            console.print(f"[green]✓ Post saved to database (ID: {post.id})[/green]")

            # Ask if user wants to publish
            publish = click.confirm('\nPublish this post to LinkedIn?', default=False)

            if publish:
                # Initialize LinkedIn client
                console.print("[cyan]Connecting to LinkedIn...[/cyan]")
                client = LinkedInClient(config)
                client.start()
                client.login()

                # Create post manager
                post_manager = PostManager(client)

                # Publish post
                full_content = result['content']
                if result['hashtags']:
                    full_content += f"\n\n{result['hashtags']}"

                success = post_manager.create_post(full_content, wait_for_confirmation=True)

                if success:
                    # Update database
                    post.published = True
                    post.published_at = datetime.utcnow()
                    session.commit()

                    # Create analytics record
                    analytics = Analytics(post_id=post.id)
                    session.add(analytics)
                    session.commit()

                    console.print("[green]✓ Post published successfully![/green]")
                else:
                    console.print("[red]✗ Failed to publish post[/red]")

                client.stop()

            session.close()
            db.close()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
def engage():
    """Engage with LinkedIn posts (like, comment)"""
    try:
        # Load configuration
        config = load_config()
        engagement_config = config.get('engagement', {})

        if not engagement_config.get('enable_auto_comments', True):
            console.print("[yellow]Auto-comments are disabled in config[/yellow]")
            return

        # Initialize LinkedIn client
        console.print("[cyan]Connecting to LinkedIn...[/cyan]")
        client = LinkedInClient(config)
        client.start()
        client.login()

        # Initialize managers
        engagement_manager = EngagementManager(client, config)
        ai_provider = get_ai_provider(config)

        # Get feed posts
        console.print("[cyan]Fetching feed posts...[/cyan]")
        posts = engagement_manager.get_feed_posts(limit=10)

        if not posts:
            console.print("[yellow]No posts found in feed[/yellow]")
            client.stop()
            return

        # Display posts
        def display_posts():
            console.print(f"\n[green]Found {len(posts)} posts[/green]\n")
            for i, post_data in enumerate(posts):
                console.print(f"[bold]{i+1}. {post_data['author']}[/bold]")
                console.print(f"   {post_data['text'][:100]}...")
                console.print()

        # Main engagement loop
        while True:
            display_posts()

            # Ask user which post to engage with
            post_num = click.prompt('Which post to engage with? (number, 0 to exit)', type=int, default=0)

            if post_num == 0:
                console.print("[yellow]Exiting engagement...[/yellow]")
                break

            if post_num < 1 or post_num > len(posts):
                console.print("[red]Invalid post number[/red]")
                continue

            selected_post = posts[post_num - 1]

            # Comment generation loop for selected post
            while True:
                # Generate comment
                console.print("[cyan]Generating comment...[/cyan]")
                comment_text = ai_provider.generate_comment(
                    post_content=selected_post['text'],
                    tone=engagement_config.get('comment_tone', 'supportive'),
                    user_context=config.get('user_profile', {})
                )

                # Show comment preview and ask for confirmation
                console.print("\n" + "="*60)
                console.print("COMMENT PREVIEW:")
                console.print("="*60)
                console.print(comment_text)
                console.print("="*60)

                response = input("\nOptions: (p)ost, (r)egenerate, (d)ifferent post, (e)xit: ").strip().lower()

                if response in ['p', 'post']:
                    # Post the comment
                    success = engagement_manager.comment_on_post(
                        selected_post['element'],
                        comment_text,
                        wait_for_confirmation=False  # Already confirmed
                    )

                    if success:
                        # Save to database
                        db = Database(config)
                        session = db.get_session()

                        comment = Comment(
                            content=comment_text,
                            tone=engagement_config.get('comment_tone', 'supportive'),
                            target_post_author=selected_post['author'],
                            target_post_url=selected_post['url'],
                            target_post_excerpt=selected_post['text'][:200],
                            ai_provider=config['ai_provider'],
                            published=True,
                            published_at=datetime.utcnow()
                        )

                        session.add(comment)
                        session.commit()
                        session.close()
                        db.close()
                        console.print("[green]Comment posted and saved to database![/green]")

                    # After posting, go back to post selection
                    break

                elif response in ['r', 'regenerate']:
                    console.print("[cyan]Regenerating comment...[/cyan]")
                    continue  # Loop again to regenerate

                elif response in ['d', 'different', 'different post']:
                    console.print("[yellow]Selecting different post...[/yellow]")
                    break  # Break to post selection

                elif response in ['e', 'exit']:
                    console.print("[yellow]Exiting engagement...[/yellow]")
                    client.stop()
                    return

                else:
                    console.print("[red]Invalid option. Please choose (p)ost, (r)egenerate, (d)ifferent post, or (e)xit[/red]")

        client.stop()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
def init():
    """Initialize your LinkedIn Assistant configuration (one-time setup)"""
    import yaml
    from pathlib import Path

    console.print("\n[bold cyan]═══════════════════════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]  LinkedIn Assistant Bot - Initial Setup Wizard[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════════════════════[/bold cyan]\n")

    console.print("This wizard will help you configure your LinkedIn Assistant Bot.")
    console.print("You can always edit config.yaml later to change these settings.\n")

    # User Profile
    console.print("[bold blue]═══ Step 1: Your LinkedIn Profile ═══[/bold blue]\n")
    console.print("This information is used to generate authentic AI comments from YOUR perspective.\n")

    name = input("Your name: ").strip() or "Your Name"
    title = input("Your job title (e.g., 'Data Analyst', 'Software Engineer'): ").strip() or "Professional"
    industry = input("Your industry (e.g., 'Technology', 'Finance', 'Healthcare'): ").strip() or "Technology"
    background = input("Brief background/expertise (e.g., 'Experienced in Python and AI/ML'): ").strip() or "Professional background"

    console.print("\nYour professional interests (comma-separated):")
    console.print("[dim]Example: artificial intelligence, automation, software development[/dim]")
    interests_input = input("Interests: ").strip() or "technology, innovation"
    interests = [i.strip() for i in interests_input.split(',') if i.strip()]

    # AI Provider
    console.print("\n[bold blue]═══ Step 2: AI Provider Selection ═══[/bold blue]\n")
    console.print("Choose which AI provider to use for content generation:\n")
    console.print("  1. OpenAI (GPT-4) - Requires API key")
    console.print("  2. Anthropic (Claude) - Requires API key")
    console.print("  3. Google Gemini - Requires API key")
    console.print("  4. Local LLM (Ollama) - Free, requires local installation\n")

    provider_choice = input("Choose AI provider (1-4, default: 4): ").strip() or "4"

    provider_map = {
        "1": "openai",
        "2": "anthropic",
        "3": "gemini",
        "4": "local"
    }

    ai_provider = provider_map.get(provider_choice, "local")

    console.print(f"\n[green]✓ Selected: {ai_provider}[/green]")

    # Engagement Settings
    console.print("\n[bold blue]═══ Step 3: Engagement Strategy ═══[/bold blue]\n")
    console.print("Choose your engagement strategy:\n")
    console.print("  1. Conservative - Engage with 1 post per cycle (safest)")
    console.print("  2. Balanced - Engage with 2-3 posts per cycle (recommended)")
    console.print("  3. Aggressive - Engage with 4-5 posts per cycle (higher risk)\n")

    strategy_choice = input("Choose strategy (1-3, default: 2): ").strip() or "2"

    strategy_map = {
        "1": "conservative",
        "2": "balanced",
        "3": "aggressive"
    }

    engagement_strategy = strategy_map.get(strategy_choice, "balanced")

    console.print(f"\n[green]✓ Selected: {engagement_strategy}[/green]")

    # Load existing config or use defaults
    config_path = Path('config.yaml')
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    else:
        config = {}

    # Update configuration
    config['ai_provider'] = ai_provider

    # Update user profile
    config['user_profile'] = {
        'name': name,
        'title': title,
        'industry': industry,
        'background': background,
        'interests': interests
    }

    # Update engagement strategy
    if 'autonomous_agent' not in config:
        config['autonomous_agent'] = {}
    config['autonomous_agent']['engagement_strategy'] = engagement_strategy

    # Ensure other essential config sections exist with defaults
    if 'linkedin' not in config:
        config['linkedin'] = {
            'browser': 'chrome',
            'headless': False,
            'save_session': True,
            'session_file': 'linkedin_session.pkl',
            'min_delay_between_actions': 30,
            'max_delay_between_actions': 120
        }

    if 'database' not in config:
        config['database'] = {
            'type': 'sqlite',
            'path': 'linkedin_assistant.db'
        }

    if 'content' not in config:
        config['content'] = {
            'tone': 'professional',
            'default_post_length': 'medium',
            'include_emojis': True,
            'include_hashtags': True,
            'max_hashtags': 5,
            'topics': ['software development', 'technology', 'career growth'],
            'post_types': ['insight', 'achievement', 'question', 'how-to']
        }

    if 'engagement' not in config:
        config['engagement'] = {
            'enable_auto_comments': True,
            'comment_tone': 'supportive',
            'max_comments_per_day': 10,
            'skip_promotional': True,
            'skip_corporate_brands': ['Wells Fargo', 'Bank of America', 'Chase'],
            'engage_with': ['connections', 'industry_leaders', 'trending_posts']
        }

    if 'safety' not in config:
        config['safety'] = {
            'require_approval': True,
            'max_posts_per_day': 3,
            'max_actions_per_hour': 5,
            'prevent_duplicate_content': True,
            'avoid_topics': ['politics', 'religion', 'controversial']
        }

    # Set default autonomous agent settings
    config['autonomous_agent'].setdefault('enable_engagement', True)
    config['autonomous_agent'].setdefault('reply_to_comments', True)
    config['autonomous_agent'].setdefault('auto_post_scheduled', True)
    config['autonomous_agent'].setdefault('check_interval', 300)
    config['autonomous_agent'].setdefault('max_engagements_per_cycle', 3)
    config['autonomous_agent'].setdefault('max_replies_per_cycle', 5)

    # AI provider specific defaults
    if ai_provider == 'openai' and 'openai' not in config:
        config['openai'] = {
            'model': 'gpt-4',
            'temperature': 0.7,
            'max_tokens': 1000
        }
    elif ai_provider == 'anthropic' and 'anthropic' not in config:
        config['anthropic'] = {
            'model': 'claude-3-sonnet-20240229',
            'max_tokens': 1000
        }
    elif ai_provider == 'gemini' and 'gemini' not in config:
        config['gemini'] = {
            'model': 'gemini-pro',
            'temperature': 0.7
        }
    elif ai_provider == 'local' and 'local_llm' not in config:
        config['local_llm'] = {
            'base_url': 'http://localhost:11434',
            'model': 'llama2',
            'temperature': 0.7
        }

    # Save configuration
    with open('config.yaml', 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    # Display summary
    console.print("\n[bold green]═══════════════════════════════════════════════════════[/bold green]")
    console.print("[bold green]  ✓ Configuration Complete![/bold green]")
    console.print("[bold green]═══════════════════════════════════════════════════════[/bold green]\n")

    console.print("[bold]Your Configuration:[/bold]")
    console.print(f"  • Name: {name}")
    console.print(f"  • Title: {title}")
    console.print(f"  • Industry: {industry}")
    console.print(f"  • AI Provider: {ai_provider}")
    console.print(f"  • Engagement Strategy: {engagement_strategy}\n")

    console.print("[bold cyan]Next Steps:[/bold cyan]")
    if ai_provider != 'local':
        console.print(f"  1. Set your {ai_provider.upper()} API key as an environment variable:")
        if ai_provider == 'openai':
            console.print("     export OPENAI_API_KEY='your-key-here'")
        elif ai_provider == 'anthropic':
            console.print("     export ANTHROPIC_API_KEY='your-key-here'")
        elif ai_provider == 'gemini':
            console.print("     export GOOGLE_API_KEY='your-key-here'")
    else:
        console.print("  1. Make sure Ollama is installed and running:")
        console.print("     Visit: https://ollama.ai")
        console.print("     Run: ollama pull llama2")

    console.print("  2. Try generating a post:")
    console.print("     python main.py generate-post")
    console.print("  3. Or engage with feed:")
    console.print("     python main.py engage")
    console.print("  4. Or run autonomous agent:")
    console.print("     python main.py autonomous\n")

    console.print("[dim]You can edit config.yaml anytime to change these settings.[/dim]\n")


@cli.command()
def stats():
    """View analytics and statistics"""
    try:
        # Load configuration
        config = load_config()
        db = Database(config)
        session = db.get_session()

        # Get post statistics
        total_posts = session.query(Post).count()
        published_posts = session.query(Post).filter(Post.published == True).count()
        draft_posts = total_posts - published_posts

        # Get comment statistics
        total_comments = session.query(Comment).count()
        published_comments = session.query(Comment).filter(Comment.published == True).count()

        # Display statistics
        console.print("\n[bold blue]LinkedIn Assistant Bot - Statistics[/bold blue]\n")

        stats_table = Table(show_header=True, header_style="bold magenta")
        stats_table.add_column("Metric", style="cyan", width=30)
        stats_table.add_column("Count", justify="right")

        stats_table.add_row("Total Posts", str(total_posts))
        stats_table.add_row("Published Posts", str(published_posts))
        stats_table.add_row("Draft Posts", str(draft_posts))
        stats_table.add_row("Total Comments", str(total_comments))
        stats_table.add_row("Published Comments", str(published_comments))

        console.print(stats_table)

        # Get recent posts
        recent_posts = session.query(Post).order_by(Post.created_at.desc()).limit(5).all()

        if recent_posts:
            console.print("\n[bold blue]Recent Posts:[/bold blue]\n")

            posts_table = Table(show_header=True, header_style="bold magenta")
            posts_table.add_column("ID", style="cyan", width=5)
            posts_table.add_column("Topic", width=30)
            posts_table.add_column("Status", width=10)
            posts_table.add_column("Created", width=20)

            for post in recent_posts:
                status = "[green]Published[/green]" if post.published else "[yellow]Draft[/yellow]"
                posts_table.add_row(
                    str(post.id),
                    post.topic[:30],
                    status,
                    post.created_at.strftime("%Y-%m-%d %H:%M")
                )

            console.print(posts_table)

        session.close()
        db.close()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
def suggest_topics():
    """Get AI-suggested post topics"""
    try:
        # Load configuration
        config = load_config()
        content_config = config.get('content', {})

        # Get user's industry
        industry = click.prompt('What industry are you in?', default='software development')

        # Initialize AI provider
        console.print(f"\n[cyan]Generating topic suggestions...[/cyan]")
        ai_provider = get_ai_provider(config)

        # Get recent topics from database to avoid repetition
        db = Database(config)
        session = db.get_session()
        recent_posts = session.query(Post).order_by(Post.created_at.desc()).limit(10).all()
        recent_topics = [post.topic for post in recent_posts if post.topic]
        session.close()
        db.close()

        # Generate suggestions
        topics = ai_provider.suggest_topics(industry=industry, recent_posts=recent_topics)

        # Display suggestions
        console.print("\n[bold green]Suggested Topics:[/bold green]\n")

        for i, topic in enumerate(topics, 1):
            console.print(f"  {i}. {topic}")

        console.print()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
@click.option('--post-id', type=int, required=True, help='ID of the post to schedule')
@click.option('--date', help='Date and time (e.g., "2024-12-01 14:30" or "tomorrow 2pm")')
def schedule(post_id, date):
    """Schedule a post for future publishing"""
    try:
        config = load_config()
        scheduler = Scheduler(config)

        # Parse the date
        if date:
            try:
                scheduled_time = parser.parse(date)
            except:
                console.print(f"[red]Could not parse date: {date}[/red]")
                console.print("Try formats like: '2024-12-01 14:30' or 'tomorrow 2pm'")
                return
        else:
            # Show optimal times
            suggestions = scheduler.suggest_optimal_times()
            console.print("\n[bold blue]Suggested optimal posting times:[/bold blue]\n")

            for i, suggestion in enumerate(suggestions, 1):
                console.print(f"  {i}. {suggestion['formatted']}")

            choice = click.prompt('\nChoose a time (number)', type=int, default=1)
            if 1 <= choice <= len(suggestions):
                scheduled_time = suggestions[choice - 1]['time']
            else:
                console.print("[red]Invalid choice[/red]")
                return

        # Schedule the post
        success = scheduler.schedule_post(post_id, scheduled_time)

        if success:
            console.print(f"\n[green]✓ Post {post_id} scheduled for {scheduled_time.strftime('%Y-%m-%d %H:%M')}[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
def view_scheduled():
    """View all scheduled posts"""
    try:
        config = load_config()
        scheduler = Scheduler(config)

        scheduled_posts = scheduler.get_scheduled_posts()

        if not scheduled_posts:
            console.print("\n[yellow]No scheduled posts[/yellow]")
            return

        console.print("\n[bold blue]Scheduled Posts:[/bold blue]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan", width=5)
        table.add_column("Topic", width=30)
        table.add_column("Scheduled For", width=25)
        table.add_column("Status", width=15)

        for post in scheduled_posts:
            time_str = post.scheduled_time.strftime("%Y-%m-%d %H:%M") if post.scheduled_time else "Not set"
            status = "[green]Ready[/green]" if post.scheduled_time <= datetime.utcnow() else "[yellow]Pending[/yellow]"

            table.add_row(
                str(post.id),
                post.topic[:30] if post.topic else "No topic",
                time_str,
                status
            )

        console.print(table)
        console.print()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
@click.option('--interval', default=60, help='Check interval in seconds (default: 60)')
def run_scheduler(interval):
    """Run the scheduler daemon to post scheduled content"""
    try:
        config = load_config()
        scheduler = Scheduler(config)

        console.print(f"\n[bold green]Starting scheduler...[/bold green]")
        console.print(f"Checking for scheduled posts every {interval} seconds")
        console.print("Press Ctrl+C to stop\n")

        scheduler.run_scheduler(check_interval=interval)

    except KeyboardInterrupt:
        console.print("\n[yellow]Scheduler stopped[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
@click.option('--post-id', type=int, required=True, help='ID of the post to cancel')
def cancel_schedule(post_id):
    """Cancel a scheduled post"""
    try:
        config = load_config()
        scheduler = Scheduler(config)

        success = scheduler.cancel_schedule(post_id)

        if success:
            console.print(f"\n[green]✓ Schedule cancelled for post {post_id}[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
@click.option('--count', default=5, help='Number of posts to generate (default: 5, max: 10)')
@click.option('--industry', prompt='Your industry', help='Industry for topic suggestions')
@click.option('--vary-tone', default=True, help='Vary tone and length for diversity')
def bulk_generate(count, industry, vary_tone):
    """Generate multiple posts at once"""
    try:
        # Load configuration
        config = load_config()
        content_config = config.get('content', {})

        # Limit count
        count = min(count, 10)

        # Initialize AI provider
        console.print(f"\n[cyan]Initializing AI provider ({config['ai_provider']})...[/cyan]")
        ai_provider = get_ai_provider(config)

        # Get topics from database to avoid repetition
        db = Database(config)
        session = db.get_session()
        recent_posts = session.query(Post).order_by(Post.created_at.desc()).limit(20).all()
        recent_topics = [post.topic for post in recent_posts if post.topic]

        # Generate topic suggestions
        console.print(f"[cyan]Generating {count} topic suggestions...[/cyan]")
        topics = ai_provider.suggest_topics(industry=industry, recent_posts=recent_topics)

        # Limit to requested count
        topics = topics[:count]

        console.print(f"\n[bold green]Generating {len(topics)} posts...[/bold green]\n")

        # Generate posts in bulk
        posts = ai_provider.generate_bulk_posts(
            topics=topics,
            include_emojis=content_config.get('include_emojis', True),
            include_hashtags=content_config.get('include_hashtags', True),
            max_hashtags=content_config.get('max_hashtags', 5),
            vary_tone=vary_tone
        )

        # Display generated posts
        for i, post_data in enumerate(posts, 1):
            console.print(f"\n[bold]POST {i}/{len(posts)}[/bold] - Topic: {post_data['topic']}")
            console.print(f"Tone: {post_data['tone']} | Length: {post_data['length']}")
            console.print("="*60)
            console.print(post_data['content'])
            if post_data['hashtags']:
                console.print(f"\n[bold]Hashtags:[/bold] {post_data['hashtags']}")
            console.print("="*60)

        # Ask if user wants to save to database
        save = click.confirm(f'\nSave all {len(posts)} posts to database?', default=True)

        if save:
            saved_ids = []

            for post_data in posts:
                # Create post record
                post = Post(
                    content=post_data['content'],
                    hashtags=post_data['hashtags'],
                    topic=post_data['topic'],
                    tone=post_data['tone'],
                    length=post_data['length'],
                    ai_provider=config['ai_provider'],
                    ai_model=config.get(config['ai_provider'], {}).get('model', 'unknown'),
                    published=False
                )

                session.add(post)
                session.commit()
                saved_ids.append(post.id)

            console.print(f"\n[green]✓ Saved {len(saved_ids)} posts to database[/green]")
            console.print(f"Post IDs: {', '.join(map(str, saved_ids))}")

            session.close()
            db.close()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
@click.option('--topic', prompt='Post topic', help='Topic for hashtag research')
@click.option('--industry', prompt='Your industry', help='Your industry/field')
@click.option('--count', default=10, help='Number of hashtags to suggest')
def hashtag_research(topic, industry, count):
    """Research and suggest relevant hashtags for a topic"""
    try:
        # Load configuration
        config = load_config()

        # Initialize AI provider
        console.print(f"\n[cyan]Researching hashtags...[/cyan]")
        ai_provider = get_ai_provider(config)

        # Get hashtag suggestions
        hashtags = ai_provider.suggest_hashtags(
            topic=topic,
            industry=industry,
            count=count
        )

        # Display hashtags
        console.print(f"\n[bold green]Suggested Hashtags for '{topic}':[/bold green]\n")

        for i, hashtag in enumerate(hashtags, 1):
            console.print(f"  {i}. #{hashtag}")

        console.print(f"\n[cyan]Copy-paste format:[/cyan]")
        hashtag_string = " ".join([f"#{tag}" for tag in hashtags])
        console.print(f"\n{hashtag_string}\n")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
def analyze_performance():
    """Analyze post performance and get insights"""
    try:
        # Load configuration
        config = load_config()
        db = Database(config)
        session = db.get_session()

        # Get published posts with analytics
        published_posts = session.query(Post).filter(Post.published == True).all()

        if not published_posts:
            console.print("\n[yellow]No published posts found. Publish some posts first![/yellow]")
            session.close()
            db.close()
            return

        # Calculate performance metrics
        console.print("\n[bold blue]Post Performance Analysis[/bold blue]\n")

        # Group by tone
        tone_stats = {}
        length_stats = {}
        topic_stats = {}

        for post in published_posts:
            # Tone analysis
            if post.tone:
                if post.tone not in tone_stats:
                    tone_stats[post.tone] = {'count': 0, 'total_engagement': 0}
                tone_stats[post.tone]['count'] += 1

            # Length analysis
            if post.length:
                if post.length not in length_stats:
                    length_stats[post.length] = {'count': 0}
                length_stats[post.length]['count'] += 1

            # Topic tracking
            if post.topic:
                if post.topic not in topic_stats:
                    topic_stats[post.topic] = {'count': 1}
                else:
                    topic_stats[post.topic]['count'] += 1

        # Display analysis
        if tone_stats:
            console.print("[bold cyan]Performance by Tone:[/bold cyan]")
            tone_table = Table(show_header=True, header_style="bold magenta")
            tone_table.add_column("Tone", style="cyan")
            tone_table.add_column("Count", justify="right")

            for tone, stats in sorted(tone_stats.items(), key=lambda x: x[1]['count'], reverse=True):
                tone_table.add_row(tone.capitalize(), str(stats['count']))

            console.print(tone_table)
            console.print()

        if length_stats:
            console.print("[bold cyan]Performance by Length:[/bold cyan]")
            length_table = Table(show_header=True, header_style="bold magenta")
            length_table.add_column("Length", style="cyan")
            length_table.add_column("Count", justify="right")

            for length, stats in sorted(length_stats.items(), key=lambda x: x[1]['count'], reverse=True):
                length_table.add_row(length.capitalize(), str(stats['count']))

            console.print(length_table)
            console.print()

        if topic_stats:
            console.print("[bold cyan]Top Topics:[/bold cyan]")
            top_topics = sorted(topic_stats.items(), key=lambda x: x[1]['count'], reverse=True)[:10]

            topic_table = Table(show_header=True, header_style="bold magenta")
            topic_table.add_column("Topic", style="cyan", width=50)
            topic_table.add_column("Posts", justify="right")

            for topic, stats in top_topics:
                topic_table.add_row(topic[:50], str(stats['count']))

            console.print(topic_table)
            console.print()

        # AI-powered insights
        console.print("[bold cyan]AI Insights:[/bold cyan]\n")

        # Get best performing characteristics
        best_tone = max(tone_stats.items(), key=lambda x: x[1]['count'])[0] if tone_stats else "professional"
        best_length = max(length_stats.items(), key=lambda x: x[1]['count'])[0] if length_stats else "medium"

        console.print(f"  • Most used tone: [green]{best_tone}[/green]")
        console.print(f"  • Most used length: [green]{best_length}[/green]")
        console.print(f"  • Total posts published: [green]{len(published_posts)}[/green]")

        if len(topic_stats) > 0:
            console.print(f"  • Unique topics covered: [green]{len(topic_stats)}[/green]")

        console.print()

        session.close()
        db.close()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
@click.option('--topic', prompt='Post topic', help='Topic for the post')
def optimize_post(topic):
    """Generate an optimized post based on past performance"""
    try:
        # Load configuration
        config = load_config()
        content_config = config.get('content', {})
        db = Database(config)
        session = db.get_session()

        # Get past performance data
        published_posts = session.query(Post).filter(Post.published == True).all()

        # Calculate performance metrics
        tone_counts = {}
        length_counts = {}
        top_topics = []

        for post in published_posts:
            if post.tone:
                tone_counts[post.tone] = tone_counts.get(post.tone, 0) + 1
            if post.length:
                length_counts[post.length] = length_counts.get(post.length, 0) + 1
            if post.topic:
                top_topics.append(post.topic)

        # Determine optimal parameters
        if tone_counts:
            optimal_tone = max(tone_counts.items(), key=lambda x: x[1])[0]
        else:
            optimal_tone = "professional"

        if length_counts:
            optimal_length = max(length_counts.items(), key=lambda x: x[1])[0]
        else:
            optimal_length = "medium"

        performance_data = {
            'top_topics': list(set(top_topics))[:5],
            'optimal_tone': optimal_tone,
            'optimal_length': optimal_length,
            'total_posts': len(published_posts)
        }

        console.print(f"\n[cyan]Generating optimized post about: {topic}[/cyan]")
        console.print(f"Using insights from {len(published_posts)} previous posts")
        console.print(f"Optimal tone: {optimal_tone} | Optimal length: {optimal_length}\n")

        # Initialize AI provider
        ai_provider = get_ai_provider(config)

        # Generate post with optimal parameters
        result = ai_provider.generate_post(
            topic=topic,
            tone=optimal_tone,
            length=optimal_length,
            include_emojis=content_config.get('include_emojis', True),
            include_hashtags=content_config.get('include_hashtags', True),
            max_hashtags=content_config.get('max_hashtags', 5)
        )

        # Optionally optimize the content further
        if len(published_posts) >= 3:
            console.print("[cyan]Applying performance-based optimization...[/cyan]")
            optimized_content = ai_provider.optimize_content(
                content=result['content'],
                performance_data=performance_data
            )
            result['content'] = optimized_content

        # Display generated post
        console.print("\n" + "="*60)
        console.print("[bold green]OPTIMIZED POST:[/bold green]")
        console.print("="*60)
        console.print(result['content'])
        if result['hashtags']:
            console.print(f"\n[bold]Hashtags:[/bold] {result['hashtags']}")
        console.print("="*60)

        # Ask if user wants to save
        save = click.confirm('\nSave this post to database?', default=True)

        if save:
            post = Post(
                content=result['content'],
                hashtags=result['hashtags'],
                topic=topic,
                tone=optimal_tone,
                length=optimal_length,
                ai_provider=config['ai_provider'],
                ai_model=config.get(config['ai_provider'], {}).get('model', 'unknown'),
                published=False
            )

            session.add(post)
            session.commit()

            console.print(f"[green]✓ Post saved to database (ID: {post.id})[/green]")

        session.close()
        db.close()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
@click.option('--days', default=30, help='Number of days to analyze (default: 30)')
@click.option('--summary', is_flag=True, help='Show quick summary instead of full dashboard')
@click.option('--with-insights', is_flag=True, help='Generate AI-powered insights (requires AI provider)')
def dashboard(days, summary, with_insights):
    """Display advanced analytics dashboard with performance insights"""
    try:
        # Load configuration
        config = load_config()
        db = Database(config)
        session = db.get_session()

        # Initialize analytics engine
        ai_provider = None
        if with_insights:
            try:
                ai_provider = get_ai_provider(config)
            except Exception as e:
                console.print(f"[yellow]Warning: Could not initialize AI provider for insights: {e}[/yellow]")

        analytics_engine = AnalyticsEngine(session, ai_provider=ai_provider)
        visualizer = AnalyticsVisualizer()

        # Get dashboard data
        console.print(f"\n[cyan]Analyzing last {days} days of performance...[/cyan]\n")
        dashboard_data = analytics_engine.get_complete_dashboard(days_back=days)

        # Display summary or full dashboard
        if summary:
            visualizer.display_quick_summary(dashboard_data)
        else:
            # Generate insights if requested
            insights = None
            if with_insights:
                console.print("[cyan]Generating AI-powered insights...[/cyan]\n")
                insights = analytics_engine.generate_ai_insights(dashboard_data)

            visualizer.display_complete_dashboard(dashboard_data, insights=insights)

        session.close()
        db.close()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()


@cli.command()
@click.option('--check-interval', default=None, type=int, help='Override check interval (seconds)')
@click.option('--max-posts', default=None, type=int, help='Max posts to retrieve per cycle')
@click.option('--max-engagements', default=None, type=int, help='Max engagements per cycle')
def autonomous(check_interval, max_posts, max_engagements):
    """Run autonomous agent v2 with full safety and campaign integration"""
    try:
        from autonomous_agent_v2 import AutonomousAgentV2

        # Load config
        config = load_config()

        # Override settings if provided
        if check_interval:
            config.setdefault('autonomous_agent', {})['check_interval'] = check_interval

        if max_posts:
            config.setdefault('autonomous_agent', {})['max_posts_per_cycle'] = max_posts

        if max_engagements:
            config.setdefault('autonomous_agent', {})['max_engagements_per_cycle'] = max_engagements

        # Save modified config temporarily
        with open('config.yaml', 'w') as f:
            yaml.dump(config, f)

        # Initialize and run agent v2
        console.print("[bold green]Starting Autonomous Agent v2.0...[/bold green]")
        console.print("[dim]Using: SafetyMonitor + CampaignExecutor + ConnectionManager[/dim]\n")

        agent = AutonomousAgentV2()
        agent.run()

    except KeyboardInterrupt:
        console.print("\n[yellow]Autonomous agent stopped[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()


@cli.command()
def safety_status():
    """Check current safety status and activity limits"""
    try:
        # Load configuration
        config = load_config()
        db = Database(config)
        session = db.get_session()

        # Initialize safety monitor
        safety_monitor = SafetyMonitor(session, config)

        # Get safety status
        status = safety_monitor.get_safety_status()

        console.print("\n[bold blue]═══ Safety Status ═══[/bold blue]\n")

        # Status indicator with color
        status_colors = {
            'safe': 'green',
            'warning': 'yellow',
            'alerts_active': 'yellow',
            'limit_reached': 'red'
        }
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
                alerts_table.add_row(
                    alert['type'],
                    f"[{severity_color}]{alert['severity']}[/{severity_color}]",
                    alert['message']
                )

            console.print(alerts_table)
            console.print()
        else:
            console.print("[green]No active alerts[/green]\n")

        session.close()
        db.close()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
@click.option('--action', type=click.Choice(['add', 'list', 'top', 'mark-target']), default='list', help='Action to perform')
@click.option('--name', help='Connection name (for add action)')
@click.option('--url', help='LinkedIn profile URL (for add/mark-target action)')
@click.option('--title', help='Job title (for add action)')
@click.option('--company', help='Company (for add action)')
@click.option('--limit', default=10, help='Limit results (for top action)')
def connections(action, name, url, title, company, limit):
    """Manage LinkedIn connections"""
    try:
        # Load configuration
        config = load_config()
        db = Database(config)
        session = db.get_session()

        # Initialize connection manager
        conn_manager = ConnectionManager(session, config)

        if action == 'add':
            if not name or not url:
                console.print("[red]Error: --name and --url are required for add action[/red]")
                return

            connection = conn_manager.add_connection(
                name=name,
                profile_url=url,
                title=title,
                company=company
            )

            console.print(f"\n[green]✓ Connection added: {connection.name}[/green]")
            console.print(f"  Quality Score: {connection.quality_score}/10")
            console.print()

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

            for conn in connections_list[:50]:  # Limit display to 50
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
                top_table.add_row(
                    f"#{i}",
                    conn.name[:25],
                    (conn.title or "N/A")[:35],
                    f"[bold green]{conn.quality_score:.1f}[/bold green]",
                    str(total_messages)
                )

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
        # Load configuration
        config = load_config()
        db = Database(config)
        session = db.get_session()

        # Initialize connection manager
        conn_manager = ConnectionManager(session, config)

        # Get analytics
        analytics = conn_manager.get_network_analytics(days_back=days)
        recommendations = conn_manager.get_connection_recommendations()

        console.print(f"\n[bold blue]═══ Network Analytics (Last {days} Days) ═══[/bold blue]\n")

        # Overview stats
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
            engagement_table.add_row(
                level.capitalize(),
                str(count),
                f"[{color}]{pct:.1f}%[/{color}]"
            )

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
                companies_table.add_row(
                    f"#{i}",
                    company_data['company'][:40],
                    str(company_data['count'])
                )

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


@cli.command()
@click.option('--action', type=click.Choice(['create', 'list', 'activate', 'pause', 'analytics', 'recommendations']), required=True)
@click.option('--campaign-id', type=int, help='Campaign ID (for activate, pause, analytics, recommendations)')
@click.option('--name', help='Campaign name (for create)')
@click.option('--type', 'campaign_type', type=click.Choice(['hashtag', 'company', 'influencer', 'topic']), help='Campaign type (for create)')
@click.option('--description', help='Campaign description (for create)')
@click.option('--targets', help='Comma-separated targets (for create). E.g., "#ai,#ml" or "Google,Microsoft"')
@click.option('--max-per-day', type=int, default=10, help='Max actions per day (for create)')
@click.option('--target-engagements', type=int, help='Target number of engagements (for create)')
@click.option('--status', type=click.Choice(['draft', 'active', 'paused', 'completed']), help='Filter by status (for list)')
def campaigns(action, campaign_id, name, campaign_type, description, targets, max_per_day, target_engagements, status):
    """Manage engagement campaigns"""
    try:
        config = load_config()
        db = Database(config)
        session = db.get_session()

        from linkedin.campaign_manager import CampaignManager
        campaign_manager = CampaignManager(session, config)

        if action == 'create':
            if not name or not campaign_type or not targets:
                console.print("[red]Error: --name, --type, and --targets are required for create action[/red]")
                return

            # Parse targets
            target_list = []
            target_values = [t.strip() for t in targets.split(',')]

            for target_value in target_values:
                if campaign_type == 'hashtag':
                    # Ensure hashtag format
                    if not target_value.startswith('#'):
                        target_value = f"#{target_value}"
                    target_list.append({'type': 'hashtag', 'value': target_value, 'priority': 'medium'})
                elif campaign_type == 'company':
                    target_list.append({'type': 'company', 'value': target_value, 'priority': 'medium'})
                elif campaign_type == 'influencer':
                    target_list.append({'type': 'profile', 'value': target_value, 'priority': 'high'})
                elif campaign_type == 'topic':
                    target_list.append({'type': 'keyword', 'value': target_value, 'priority': 'medium'})

            campaign = campaign_manager.create_campaign(
                name=name,
                campaign_type=campaign_type,
                description=description,
                targets=target_list,
                max_actions_per_day=max_per_day,
                target_engagements=target_engagements
            )

            console.print(f"\n[green]✓ Campaign created: {campaign.name}[/green]")
            console.print(f"  ID: {campaign.id}")
            console.print(f"  Type: {campaign.campaign_type}")
            console.print(f"  Targets: {len(target_list)}")
            console.print(f"  Status: {campaign.status}")
            console.print(f"\nRun 'python main.py campaigns --action activate --campaign-id {campaign.id}' to activate\n")

        elif action == 'list':
            campaigns_list = campaign_manager.list_campaigns(status=status)

            if not campaigns_list:
                console.print("\n[yellow]No campaigns found[/yellow]")
                return

            console.print(f"\n[bold blue]Campaigns ({len(campaigns_list)} total)[/bold blue]\n")

            campaigns_table = Table(show_header=True, header_style="bold magenta")
            campaigns_table.add_column("ID", justify="center", width=6)
            campaigns_table.add_column("Name", style="cyan", width=25)
            campaigns_table.add_column("Type", width=12)
            campaigns_table.add_column("Status", width=10)
            campaigns_table.add_column("Targets", justify="center", width=8)
            campaigns_table.add_column("Engagements", justify="center", width=12)
            campaigns_table.add_column("Success Rate", justify="center", width=13)

            for campaign in campaigns_list:
                status_color = 'green' if campaign.status == 'active' else 'yellow' if campaign.status == 'paused' else 'white'
                success_color = 'green' if campaign.success_rate >= 80 else 'yellow' if campaign.success_rate >= 60 else 'red'

                campaigns_table.add_row(
                    str(campaign.id),
                    campaign.name[:25],
                    campaign.campaign_type,
                    f"[{status_color}]{campaign.status}[/{status_color}]",
                    str(len(campaign.targets)),
                    str(campaign.total_engagements),
                    f"[{success_color}]{campaign.success_rate:.1f}%[/{success_color}]"
                )

            console.print(campaigns_table)
            console.print()

        elif action == 'activate':
            if not campaign_id:
                console.print("[red]Error: --campaign-id required for activate action[/red]")
                return

            campaign = campaign_manager.activate_campaign(campaign_id)
            if campaign:
                console.print(f"\n[green]✓ Campaign '{campaign.name}' activated[/green]")
                console.print(f"\nRun 'python main.py run-campaigns' to execute active campaigns\n")
            else:
                console.print(f"\n[red]Campaign {campaign_id} not found[/red]\n")

        elif action == 'pause':
            if not campaign_id:
                console.print("[red]Error: --campaign-id required for pause action[/red]")
                return

            campaign = campaign_manager.pause_campaign(campaign_id)
            if campaign:
                console.print(f"\n[green]✓ Campaign '{campaign.name}' paused[/green]\n")
            else:
                console.print(f"\n[red]Campaign {campaign_id} not found[/red]\n")

        elif action == 'analytics':
            if not campaign_id:
                console.print("[red]Error: --campaign-id required for analytics action[/red]")
                return

            analytics = campaign_manager.get_campaign_analytics(campaign_id)

            if not analytics:
                console.print(f"\n[red]Campaign {campaign_id} not found[/red]\n")
                return

            console.print(f"\n[bold blue]═══ Campaign Analytics: {analytics['campaign_name']} ═══[/bold blue]\n")

            # Overview
            console.print("[bold cyan]Overview:[/bold cyan]")
            overview_table = Table(show_header=False)
            overview_table.add_column("Metric", style="cyan", width=25)
            overview_table.add_column("Value", justify="right", style="white")

            overview_table.add_row("Campaign Type", analytics['campaign_type'])
            overview_table.add_row("Status", analytics['status'].upper())
            overview_table.add_row("Days Running", str(analytics['days_running']))
            overview_table.add_row("Total Engagements", str(analytics['total_activities']))
            overview_table.add_row("Success Rate", f"{analytics['success_rate']:.1f}%")
            overview_table.add_row("Posts Engaged", str(analytics['total_posts_engaged']))
            overview_table.add_row("Avg per Day", f"{analytics['avg_engagements_per_day']:.1f}")

            if analytics.get('target_engagements'):
                overview_table.add_row("Goal Progress", f"{analytics['goal_progress_percent']:.1f}%")

            console.print(overview_table)
            console.print()

            # Activities by type
            if analytics['activities_by_type']:
                console.print("[bold cyan]Engagement Types:[/bold cyan]")
                types_table = Table(show_header=True, header_style="bold magenta")
                types_table.add_column("Type", style="cyan")
                types_table.add_column("Count", justify="right")

                for action_type, count in analytics['activities_by_type'].items():
                    types_table.add_row(action_type.capitalize(), str(count))

                console.print(types_table)
                console.print()

            # Target performance
            if analytics['target_performance']:
                console.print("[bold cyan]Target Performance:[/bold cyan]")
                targets_table = Table(show_header=True, header_style="bold magenta")
                targets_table.add_column("Type", style="cyan", width=12)
                targets_table.add_column("Value", width=30)
                targets_table.add_column("Engagements", justify="right", width=12)
                targets_table.add_column("Success Rate", justify="right", width=13)

                for target in analytics['target_performance'][:10]:
                    success_color = 'green' if target['success_rate'] >= 80 else 'yellow' if target['success_rate'] >= 60 else 'red'
                    targets_table.add_row(
                        target['type'],
                        target['value'][:30],
                        str(target['engagements']),
                        f"[{success_color}]{target['success_rate']:.1f}%[/{success_color}]"
                    )

                console.print(targets_table)
                console.print()

            # Top authors
            if analytics['top_authors']:
                console.print("[bold cyan]Top Engaged Authors:[/bold cyan]")
                authors_table = Table(show_header=True, header_style="bold magenta")
                authors_table.add_column("Rank", justify="center", width=6)
                authors_table.add_column("Author", style="cyan", width=35)
                authors_table.add_column("Engagements", justify="right")

                for i, author_data in enumerate(analytics['top_authors'][:10], 1):
                    authors_table.add_row(f"#{i}", author_data['author'][:35], str(author_data['count']))

                console.print(authors_table)
                console.print()

        elif action == 'recommendations':
            if not campaign_id:
                console.print("[red]Error: --campaign-id required for recommendations action[/red]")
                return

            recommendations = campaign_manager.get_campaign_recommendations(campaign_id)

            if not recommendations.get('recommendations'):
                console.print(f"\n[green]Campaign is performing well - no recommendations at this time[/green]\n")
                return

            console.print(f"\n[bold blue]═══ Campaign Recommendations: {recommendations['campaign_name']} ═══[/bold blue]\n")
            console.print(f"Status: {recommendations['status'].upper()}\n")

            for rec in recommendations['recommendations']:
                priority_color = 'red' if rec['priority'] == 'high' else 'yellow' if rec['priority'] == 'medium' else 'blue'
                console.print(f"  [{priority_color}]●[/{priority_color}] [bold]{rec['message']}[/bold]")
                console.print(f"    [dim]→ {rec['action']}[/dim]")
                console.print()

        session.close()
        db.close()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()


@cli.command()
@click.option('--campaign-id', type=int, help='Run specific campaign (optional)')
@click.option('--max-posts', type=int, default=20, help='Max posts to retrieve from feed')
@click.option('--max-engagements', type=int, default=10, help='Max engagements to perform')
def run_campaigns(campaign_id, max_posts, max_engagements):
    """Execute active campaigns"""
    try:
        config = load_config()
        db = Database(config)
        session = db.get_session()

        from linkedin.client import LinkedInClient
        from utils.campaign_executor import CampaignExecutor

        # Initialize LinkedIn client
        client = LinkedInClient(config)

        # Check if logged in
        if not client.is_logged_in():
            console.print("\n[yellow]Not logged in. Please login to LinkedIn first.[/yellow]")
            console.print("Run: python main.py engage\n")
            return

        # Initialize campaign executor
        executor = CampaignExecutor(session, client, config)

        # Execute campaigns
        if campaign_id:
            console.print(f"\n[bold cyan]Executing Campaign ID: {campaign_id}[/bold cyan]")
            result = executor.execute_single_campaign(campaign_id, max_posts=max_posts, max_engagements=max_engagements)
        else:
            console.print(f"\n[bold cyan]Executing All Active Campaigns[/bold cyan]")
            result = executor.execute_campaigns(max_posts=max_posts, max_engagements=max_engagements)

        # Display results
        if result['success']:
            console.print(f"\n[green]✓ {result.get('message', 'Campaign execution completed')}[/green]\n")
        else:
            console.print(f"\n[red]✗ {result.get('error', 'Campaign execution failed')}[/red]\n")

        session.close()
        db.close()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()


@cli.command()
@click.option('--action', type=click.Choice(['send', 'list', 'check']), required=True)
@click.option('--profile-url', help='LinkedIn profile URL (for send action)')
@click.option('--name', help='Target name (for send action)')
@click.option('--title', help='Target job title (for send action)')
@click.option('--company', help='Target company (for send action)')
@click.option('--message', help='Custom message (optional, AI will generate if not provided)')
@click.option('--status', type=click.Choice(['pending', 'accepted', 'declined', 'expired']), help='Filter by status (for list action)')
@click.option('--limit', type=int, default=20, help='Limit results (for list action)')
def connection_requests(action, profile_url, name, title, company, message, status, limit):
    """Manage outgoing connection requests"""
    try:
        config = load_config()
        db = Database(config)
        session = db.get_session()

        from utils.network_growth import NetworkGrowthAutomation
        from linkedin import LinkedInClient

        # Initialize LinkedIn client if automation is enabled in config
        linkedin_client = None
        use_automation = config.get('network_growth', {}).get('use_automation', False)

        if use_automation:
            console.print("[yellow]⚠️  LinkedIn automation is enabled - browser will launch[/yellow]")
            linkedin_client = LinkedInClient(config)
            linkedin_client.start()
            # Login if not already logged in
            if not linkedin_client.is_logged_in():
                console.print("[cyan]Logging into LinkedIn...[/cyan]")
                if not linkedin_client.login():
                    console.print("[red]Failed to login to LinkedIn - continuing without automation[/red]")
                    linkedin_client.stop()
                    linkedin_client = None

        network_growth = NetworkGrowthAutomation(session, linkedin_client, config)

        if action == 'send':
            if not profile_url or not name:
                console.print("[red]Error: --profile-url and --name are required for send action[/red]")
                return

            console.print(f"\n[cyan]Sending connection request to {name}...[/cyan]")

            request = network_growth.send_connection_request(
                profile_url=profile_url,
                name=name,
                title=title,
                company=company,
                custom_message=message
            )

            if request:
                console.print(f"\n[green]✓ Connection request sent![/green]")
                console.print(f"  Target: {request.target_name}")
                console.print(f"  Message: {request.message[:100]}...")
                console.print(f"  Status: {request.status}")
                console.print()
            else:
                console.print(f"\n[red]✗ Failed to send connection request[/red]")
                console.print("Check safety limits or if request already sent\n")

        elif action == 'list':
            from database.models import ConnectionRequest

            query = session.query(ConnectionRequest)

            if status:
                query = query.filter(ConnectionRequest.status == status)

            requests = query.order_by(ConnectionRequest.sent_at.desc()).limit(limit).all()

            if not requests:
                console.print("\n[yellow]No connection requests found[/yellow]")
                return

            console.print(f"\n[bold blue]Connection Requests ({len(requests)} shown)[/bold blue]\n")

            requests_table = Table(show_header=True, header_style="bold magenta")
            requests_table.add_column("ID", justify="center", width=6)
            requests_table.add_column("Name", style="cyan", width=25)
            requests_table.add_column("Title", width=30)
            requests_table.add_column("Status", width=10)
            requests_table.add_column("Sent", width=12)

            for req in requests:
                status_color = 'green' if req.status == 'accepted' else 'yellow' if req.status == 'pending' else 'red'
                sent_date = req.sent_at.strftime("%Y-%m-%d") if req.sent_at else "N/A"

                requests_table.add_row(
                    str(req.id),
                    req.target_name[:25],
                    (req.target_title or "N/A")[:30],
                    f"[{status_color}]{req.status}[/{status_color}]",
                    sent_date
                )

            console.print(requests_table)
            console.print()

        elif action == 'check':
            console.print("\n[cyan]Checking status of pending requests...[/cyan]")

            result = network_growth.check_pending_requests()

            console.print(f"\n[bold blue]Pending Requests Status[/bold blue]")
            console.print(f"  Total checked: {result['total_checked']}")
            console.print(f"  Accepted: [green]{result['accepted']}[/green]")
            console.print(f"  Declined: [red]{result['declined']}[/red]")
            console.print(f"  Still pending: [yellow]{result['still_pending']}[/yellow]")
            console.print()

        session.close()
        db.close()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()


@cli.command()
@click.option('--action', type=click.Choice(['create', 'list', 'enroll', 'stats']), required=True)
@click.option('--sequence-id', type=int, help='Sequence ID (for enroll, stats actions)')
@click.option('--name', help='Sequence name (for create action)')
@click.option('--connection-id', type=int, help='Connection ID to enroll (for enroll action)')
@click.option('--trigger', type=click.Choice(['new_connection', 'manual']), default='new_connection', help='Trigger type (for create action)')
def message_sequences(action, sequence_id, name, connection_id, trigger):
    """Manage automated message sequences"""
    try:
        config = load_config()
        db = Database(config)
        session = db.get_session()

        from utils.network_growth import NetworkGrowthAutomation
        from database.models import MessageSequence, SequenceEnrollment

        # LinkedIn client placeholder (actual automation not implemented yet)
        linkedin_client = None
        network_growth = NetworkGrowthAutomation(session, linkedin_client, config)

        if action == 'create':
            if not name:
                console.print("[red]Error: --name is required for create action[/red]")
                return

            # Default welcome sequence
            steps = [
                {"delay_days": 0, "template": "welcome"},
                {"delay_days": 3, "template": "follow_up"}
            ]

            console.print(f"\n[cyan]Creating message sequence: {name}...[/cyan]")

            sequence = network_growth.create_message_sequence(
                name=name,
                steps=steps,
                trigger_type=trigger
            )

            console.print(f"\n[green]✓ Message sequence created![/green]")
            console.print(f"  ID: {sequence.id}")
            console.print(f"  Name: {sequence.name}")
            console.print(f"  Trigger: {sequence.trigger_type}")
            console.print(f"  Steps: {len(steps)}")
            console.print(f"\nSteps:")
            for i, step in enumerate(steps, 1):
                console.print(f"  {i}. Day {step['delay_days']}: {step['template']}")
            console.print()

        elif action == 'list':
            sequences = session.query(MessageSequence).filter(
                MessageSequence.is_active == True
            ).order_by(MessageSequence.created_at.desc()).all()

            if not sequences:
                console.print("\n[yellow]No message sequences found[/yellow]")
                console.print("Create one with: python main.py message-sequences --action create --name 'Welcome Sequence'\n")
                return

            console.print(f"\n[bold blue]Message Sequences ({len(sequences)} total)[/bold blue]\n")

            sequences_table = Table(show_header=True, header_style="bold magenta")
            sequences_table.add_column("ID", justify="center", width=6)
            sequences_table.add_column("Name", style="cyan", width=30)
            sequences_table.add_column("Trigger", width=15)
            sequences_table.add_column("Enrollments", justify="center", width=12)
            sequences_table.add_column("Response Rate", justify="center", width=14)

            for seq in sequences:
                response_color = 'green' if seq.response_rate >= 20 else 'yellow' if seq.response_rate >= 10 else 'white'

                sequences_table.add_row(
                    str(seq.id),
                    seq.name[:30],
                    seq.trigger_type,
                    str(seq.total_started),
                    f"[{response_color}]{seq.response_rate:.1f}%[/{response_color}]"
                )

            console.print(sequences_table)
            console.print()

        elif action == 'enroll':
            if not sequence_id or not connection_id:
                console.print("[red]Error: --sequence-id and --connection-id are required for enroll action[/red]")
                return

            console.print(f"\n[cyan]Enrolling connection {connection_id} in sequence {sequence_id}...[/cyan]")

            enrollment = network_growth.enroll_in_sequence(
                connection_id=connection_id,
                sequence_id=sequence_id
            )

            if enrollment:
                console.print(f"\n[green]✓ Connection enrolled in sequence![/green]")
                console.print(f"  Enrollment ID: {enrollment.id}")
                console.print(f"  First message: {enrollment.next_message_at.strftime('%Y-%m-%d %H:%M')}")
                console.print()
            else:
                console.print(f"\n[red]✗ Failed to enroll connection[/red]")
                console.print("Check that connection and sequence exist\n")

        elif action == 'stats':
            if not sequence_id:
                console.print("[red]Error: --sequence-id is required for stats action[/red]")
                return

            sequence = session.query(MessageSequence).filter(
                MessageSequence.id == sequence_id
            ).first()

            if not sequence:
                console.print(f"\n[red]Sequence {sequence_id} not found[/red]\n")
                return

            enrollments = session.query(SequenceEnrollment).filter(
                SequenceEnrollment.sequence_id == sequence_id
            ).all()

            console.print(f"\n[bold blue]═══ Sequence Stats: {sequence.name} ═══[/bold blue]\n")

            # Overview
            console.print("[bold cyan]Overview:[/bold cyan]")
            overview_table = Table(show_header=False)
            overview_table.add_column("Metric", style="cyan", width=25)
            overview_table.add_column("Value", justify="right", style="white")

            active_count = len([e for e in enrollments if e.status == 'active'])
            completed_count = len([e for e in enrollments if e.status == 'completed'])

            overview_table.add_row("Total Enrollments", str(sequence.total_started))
            overview_table.add_row("Active", str(active_count))
            overview_table.add_row("Completed", str(completed_count))
            overview_table.add_row("Response Rate", f"{sequence.response_rate:.1f}%")

            console.print(overview_table)
            console.print()

        session.close()
        db.close()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()


@cli.command()
@click.option('--max-requests', type=int, default=5, help='Max incoming requests to process')
def process_incoming(max_requests):
    """Process incoming connection requests (auto-accept with filters)"""
    try:
        config = load_config()
        db = Database(config)
        session = db.get_session()

        from utils.network_growth import NetworkGrowthAutomation
        from linkedin import LinkedInClient

        # Initialize LinkedIn client if automation is enabled in config
        linkedin_client = None
        use_automation = config.get('network_growth', {}).get('use_automation', False)

        if use_automation:
            console.print("[yellow]⚠️  LinkedIn automation is enabled - browser will launch[/yellow]")
            linkedin_client = LinkedInClient(config)
            linkedin_client.start()
            # Login if not already logged in
            if not linkedin_client.is_logged_in():
                console.print("[cyan]Logging into LinkedIn...[/cyan]")
                if not linkedin_client.login():
                    console.print("[red]Failed to login to LinkedIn - continuing without automation[/red]")
                    linkedin_client.stop()
                    linkedin_client = None

        network_growth = NetworkGrowthAutomation(session, linkedin_client, config)

        console.print(f"\n[cyan]Processing incoming connection requests...[/cyan]")
        console.print(f"Max to process: {max_requests}\n")

        result = network_growth.process_incoming_requests(max_requests=max_requests)

        console.print("[bold blue]Processing Results[/bold blue]")
        console.print(f"  Total processed: {result['total_processed']}")
        console.print(f"  Accepted: [green]{result['accepted']}[/green]")
        console.print(f"  Declined: [red]{result['declined']}[/red]")
        console.print(f"  Pending review: [yellow]{result['pending']}[/yellow]")
        console.print()

        if result['accepted_profiles']:
            console.print("[bold cyan]Accepted Connections:[/bold cyan]")
            for profile in result['accepted_profiles']:
                console.print(f"  • {profile}")
            console.print()

        session.close()
        db.close()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()


@cli.command()
def process_sequences():
    """Process due message sequences and send scheduled messages"""
    try:
        config = load_config()
        db = Database(config)
        session = db.get_session()

        from utils.network_growth import NetworkGrowthAutomation
        from linkedin import LinkedInClient

        # Initialize LinkedIn client if automation is enabled in config
        linkedin_client = None
        use_automation = config.get('network_growth', {}).get('use_automation', False)

        if use_automation:
            console.print("[yellow]⚠️  LinkedIn automation is enabled - browser will launch[/yellow]")
            linkedin_client = LinkedInClient(config)
            linkedin_client.start()
            # Login if not already logged in
            if not linkedin_client.is_logged_in():
                console.print("[cyan]Logging into LinkedIn...[/cyan]")
                if not linkedin_client.login():
                    console.print("[red]Failed to login to LinkedIn - continuing without automation[/red]")
                    linkedin_client.stop()
                    linkedin_client = None

        network_growth = NetworkGrowthAutomation(session, linkedin_client, config)

        console.print("\n[cyan]Processing due message sequences...[/cyan]\n")

        result = network_growth.process_due_sequence_messages()

        console.print("[bold blue]Processing Results[/bold blue]")
        console.print(f"  Messages sent: [green]{result['messages_sent']}[/green]")
        console.print(f"  Failed: [red]{result['failed']}[/red]")
        console.print(f"  Sequences completed: {result['completed_sequences']}")
        console.print()

        if result['sent_to']:
            console.print("[bold cyan]Messages Sent To:[/bold cyan]")
            for recipient in result['sent_to']:
                console.print(f"  • {recipient}")
            console.print()

        session.close()
        db.close()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()


@cli.command()
@click.option('--action', type=click.Choice(['create', 'list', 'start', 'stop', 'results', 'analyze', 'recommendations', 'generate-variants']), required=True, help='Action to perform')
@click.option('--test-id', type=int, help='Test ID')
@click.option('--name', type=str, help='Test name')
@click.option('--type', 'test_type', type=click.Choice(['tone', 'length', 'emoji', 'headline', 'cta', 'hashtag']), help='Type of test')
@click.option('--topic', type=str, help='Topic for content generation')
@click.option('--hypothesis', type=str, help='Test hypothesis')
@click.option('--variant-count', type=int, default=3, help='Number of variants to test')
@click.option('--posts-per-variant', type=int, default=30, help='Minimum posts per variant')
@click.option('--duration-days', type=int, default=30, help='Test duration in days')
@click.option('--status', type=str, help='Filter by status (for list action)')
def ab_test(action, test_id, name, test_type, topic, hypothesis, variant_count, posts_per_variant, duration_days, status):
    """Manage A/B tests for content optimization"""
    try:
        config = load_config()
        db = Database(config)
        session = db.get_session()

        from utils.ab_testing_engine import ABTestingEngine
        from utils.variant_generator import VariantGenerator
        from database.models import ABTest, TestVariant

        ab_engine = ABTestingEngine(session, config)
        variant_gen = VariantGenerator(config)

        if action == 'create':
            if not name or not test_type or not topic:
                console.print("[red]Error: --name, --type, and --topic are required for create action[/red]")
                return

            console.print(f"\n[cyan]Creating A/B test: {name}...[/cyan]")
            console.print(f"Type: {test_type}")
            console.print(f"Topic: {topic}\n")

            # Generate variants
            console.print(f"[cyan]Generating {variant_count} variants...[/cyan]")
            variants_config = variant_gen.generate_variants(
                test_type=test_type,
                base_topic=topic,
                variant_count=variant_count,
                industry=config.get('user_profile', {}).get('industry', 'Technology')
            )

            # Create test
            test = ab_engine.create_test(
                name=name,
                test_type=test_type,
                hypothesis=hypothesis or f"Testing {test_type} variations for {topic}",
                description=f"A/B test comparing {variant_count} {test_type} variants",
                variants_config=variants_config,
                minimum_sample_size=posts_per_variant,
                planned_duration_days=duration_days
            )

            console.print(f"\n[green]✓ A/B test created![/green]")
            console.print(f"  Test ID: {test.id}")
            console.print(f"  Name: {test.name}")
            console.print(f"  Type: {test.test_type}")
            console.print(f"  Variants: {len(test.variants)}")
            console.print(f"  Min posts per variant: {posts_per_variant}")
            console.print(f"  Duration: {duration_days} days\n")

            console.print("[bold cyan]Variants:[/bold cyan]")
            for var in test.variants:
                control_label = " [CONTROL]" if var.is_control else ""
                console.print(f"  {var.variant_name}: {var.variant_label}{control_label}")
            console.print()

            console.print("[yellow]Next steps:[/yellow]")
            console.print(f"1. Start test: python main.py ab-test --action start --test-id {test.id}")
            console.print(f"2. Generate posts with variants: python main.py ab-test --action generate-variants --test-id {test.id}")
            console.print()

        elif action == 'list':
            tests = ab_engine.list_tests(status=status)

            if not tests:
                console.print("\n[yellow]No A/B tests found[/yellow]")
                console.print("Create one with: python main.py ab-test --action create --name 'Tone Test' --type tone --topic 'AI trends'\n")
                return

            console.print(f"\n[bold blue]A/B Tests ({len(tests)} total)[/bold blue]\n")

            tests_table = Table(show_header=True, header_style="bold magenta")
            tests_table.add_column("ID", justify="center", width=6)
            tests_table.add_column("Name", style="cyan", width=30)
            tests_table.add_column("Type", width=12)
            tests_table.add_column("Status", width=12)
            tests_table.add_column("Variants", justify="center", width=10)
            tests_table.add_column("Posts", justify="center", width=8)
            tests_table.add_column("Winner", width=15)

            for test in tests:
                status_color = {
                    'draft': 'yellow',
                    'running': 'cyan',
                    'completed': 'green',
                    'cancelled': 'red'
                }.get(test['status'], 'white')

                tests_table.add_row(
                    str(test['id']),
                    test['name'][:30],
                    test['type'],
                    f"[{status_color}]{test['status']}[/{status_color}]",
                    str(test['variants_count']),
                    str(test['total_posts']),
                    test['winner'] or '-'
                )

            console.print(tests_table)
            console.print()

        elif action == 'start':
            if not test_id:
                console.print("[red]Error: --test-id is required for start action[/red]")
                return

            console.print(f"\n[cyan]Starting test {test_id}...[/cyan]")
            result = ab_engine.start_test(test_id)

            if result['success']:
                console.print(f"\n[green]✓ Test started successfully![/green]")
                console.print(f"  Start date: {result['start_date'].strftime('%Y-%m-%d %H:%M')}")
                if result.get('end_date'):
                    console.print(f"  Planned end: {result['end_date'].strftime('%Y-%m-%d %H:%M')}")
                console.print()
            else:
                console.print(f"\n[red]✗ Failed to start test: {result['error']}[/red]\n")

        elif action == 'stop':
            if not test_id:
                console.print("[red]Error: --test-id is required for stop action[/red]")
                return

            console.print(f"\n[cyan]Stopping test {test_id} and analyzing results...[/cyan]")
            result = ab_engine.stop_test(test_id, declare_winner=True)

            if result['success']:
                console.print(f"\n[green]✓ Test stopped![/green]")
                console.print(f"  Completed at: {result['completed_at'].strftime('%Y-%m-%d %H:%M')}")

                if result.get('analysis'):
                    analysis = result['analysis']
                    if analysis.get('winner'):
                        winner = analysis['winner']
                        console.print(f"\n[bold green]Winner: {winner['variant_name']}[/bold green]")
                        console.print(f"  {winner['variant_label']}")
                        console.print(f"  Engagement rate: {winner['avg_engagement_rate']}%")
                    else:
                        console.print(f"\n[yellow]{analysis.get('message', 'No significant winner')}[/yellow]")
                console.print()
            else:
                console.print(f"\n[red]✗ Failed to stop test: {result['error']}[/red]\n")

        elif action == 'results':
            if not test_id:
                console.print("[red]Error: --test-id is required for results action[/red]")
                return

            result = ab_engine.get_test_results(test_id)

            if not result['success']:
                console.print(f"\n[red]Error: {result['error']}[/red]\n")
                return

            test_info = result['test']
            analysis = result['analysis']

            console.print(f"\n[bold blue]═══ Test Results: {test_info['name']} ═══[/bold blue]\n")

            # Test info
            console.print("[bold cyan]Test Info:[/bold cyan]")
            info_table = Table(show_header=False)
            info_table.add_column("Field", style="cyan", width=20)
            info_table.add_column("Value", style="white")

            info_table.add_row("Type", test_info['type'])
            info_table.add_row("Status", test_info['status'])
            info_table.add_row("Hypothesis", test_info['hypothesis'] or '-')
            if test_info['start_date']:
                info_table.add_row("Started", test_info['start_date'].strftime('%Y-%m-%d'))
            if test_info['completed_at']:
                info_table.add_row("Completed", test_info['completed_at'].strftime('%Y-%m-%d'))

            console.print(info_table)
            console.print()

            # Variant results
            if analysis.get('success') and analysis.get('variants'):
                console.print("[bold cyan]Variant Performance:[/bold cyan]")
                results_table = Table(show_header=True, header_style="bold magenta")
                results_table.add_column("Variant", style="cyan", width=20)
                results_table.add_column("Posts", justify="center", width=8)
                results_table.add_column("Avg Eng Rate", justify="center", width=13)
                results_table.add_column("Lift vs Control", justify="center", width=15)
                results_table.add_column("Significant?", justify="center", width=12)

                for var in analysis['variants']:
                    lift_str = '-'
                    if var.get('lift_percent') is not None:
                        lift = var['lift_percent']
                        lift_color = 'green' if lift > 0 else 'red' if lift < 0 else 'white'
                        lift_str = f"[{lift_color}]{lift:+.1f}%[/{lift_color}]"

                    sig_str = '-'
                    if var.get('is_significant') is not None:
                        sig_str = '[green]Yes[/green]' if var['is_significant'] else '[red]No[/red]'

                    results_table.add_row(
                        var['variant_label'][:20],
                        str(var['posts_count']),
                        f"{var['avg_engagement_rate']:.2f}%",
                        lift_str,
                        sig_str
                    )

                console.print(results_table)
                console.print()

                # Winner
                if analysis.get('winner'):
                    winner = analysis['winner']
                    console.print(f"[bold green]🏆 Winner: {winner['variant_name']}[/bold green]")
                    console.print(f"   {winner['variant_label']}")
                    console.print(f"   Avg engagement rate: {winner['avg_engagement_rate']}%\n")
                else:
                    console.print("[yellow]No statistically significant winner yet[/yellow]\n")
            else:
                console.print(f"[yellow]{analysis.get('error', 'Not enough data to analyze')}[/yellow]\n")

        elif action == 'analyze':
            if not test_id:
                console.print("[red]Error: --test-id is required for analyze action[/red]")
                return

            console.print(f"\n[cyan]Analyzing test {test_id}...[/cyan]")
            analysis = ab_engine.analyze_test(test_id)

            if not analysis.get('success'):
                console.print(f"\n[red]Error: {analysis['error']}[/red]\n")
                if analysis.get('current_samples'):
                    console.print("[yellow]Current sample sizes:[/yellow]")
                    for var_name, count in analysis['current_samples'].items():
                        console.print(f"  {var_name}: {count} posts")
                    console.print(f"\nMinimum required: {analysis.get('minimum_required', 30)} posts per variant\n")
                return

            console.print("\n[green]✓ Analysis complete[/green]\n")

            # Show results
            if analysis.get('winner'):
                winner = analysis['winner']
                console.print(f"[bold green]Winner: {winner['variant_name']}[/bold green]")
                console.print(f"  {winner['variant_label']}")
                console.print(f"  Engagement rate: {winner['avg_engagement_rate']}%\n")
            else:
                console.print(f"[yellow]{analysis.get('message', 'No significant winner')}[/yellow]\n")

        elif action == 'recommendations':
            if not test_id:
                console.print("[red]Error: --test-id is required for recommendations action[/red]")
                return

            console.print(f"\n[cyan]Generating AI recommendations for test {test_id}...[/cyan]\n")

            recommendations = ab_engine.generate_ai_recommendations(test_id)

            console.print("[bold blue]AI Recommendations:[/bold blue]\n")
            console.print(recommendations)
            console.print()

        elif action == 'generate-variants':
            if not test_id:
                console.print("[red]Error: --test-id is required for generate-variants action[/red]")
                return

            test = session.query(ABTest).filter(ABTest.id == test_id).first()

            if not test:
                console.print(f"\n[red]Test {test_id} not found[/red]\n")
                return

            if not topic:
                console.print("[red]Error: --topic is required to generate variant posts[/red]")
                return

            console.print(f"\n[cyan]Generating posts for {len(test.variants)} variants...[/cyan]")
            console.print(f"Topic: {topic}\n")

            from database.models import Post

            posts_created = []

            for variant in test.variants:
                console.print(f"\n[cyan]Generating post for: {variant.variant_label}[/cyan]")

                # Parse variant config
                import json
                variant_config = json.loads(variant.variant_config)

                # Generate post
                content = variant_gen.generate_post_from_variant(
                    topic=topic,
                    variant_config=variant_config,
                    industry=config.get('user_profile', {}).get('industry', 'Technology')
                )

                # Create post in database
                post = Post(
                    content=content,
                    topic=topic,
                    tone=variant_config.get('tone', 'professional'),
                    length=variant_config.get('length', 'medium'),
                    ai_provider=config.get('ai_provider', 'openai'),
                    ai_model=config.get('openai', {}).get('model', 'gpt-4')
                )

                session.add(post)
                session.flush()

                # Assign to variant
                ab_engine.assign_post_to_variant(
                    post_id=post.id,
                    variant_id=variant.id,
                    assignment_method='auto_generated'
                )

                posts_created.append((variant.variant_label, post.id))
                console.print(f"  ✓ Post created (ID: {post.id})")

            session.commit()

            console.print(f"\n[green]✓ Generated {len(posts_created)} variant posts![/green]\n")

            console.print("[bold cyan]Created Posts:[/bold cyan]")
            for var_label, post_id in posts_created:
                console.print(f"  {var_label}: Post #{post_id}")
            console.print()

        session.close()
        db.close()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()


@cli.command()
@click.option('--post-ids', type=str, help='Comma-separated post IDs to view (e.g., "12,13,14")')
@click.option('--tone', type=str, help='Filter by tone')
@click.option('--test-id', type=int, help='View posts assigned to a specific test')
@click.option('--limit', type=int, default=10, help='Maximum number of posts to display')
@click.option('--full', is_flag=True, help='Show full content (default: preview only)')
def view_posts(post_ids, tone, test_id, limit, full):
    """View generated posts with optional filters"""
    try:
        config = load_config()
        db = Database(config)
        session = db.get_session()

        from database.models import Post, TestAssignment

        # Build query
        query = session.query(Post)

        # Apply filters
        if post_ids:
            ids = [int(pid.strip()) for pid in post_ids.split(',')]
            query = query.filter(Post.id.in_(ids))

        if tone:
            query = query.filter(Post.tone == tone)

        if test_id:
            # Join with TestAssignment to filter by test
            query = query.join(TestAssignment).filter(TestAssignment.test_id == test_id)

        # Order by most recent and limit
        posts = query.order_by(Post.created_at.desc()).limit(limit).all()

        if not posts:
            console.print("\n[yellow]No posts found matching the criteria[/yellow]\n")
            return

        console.print(f"\n[bold blue]Found {len(posts)} post(s)[/bold blue]\n")

        for post in posts:
            # Show post header
            console.print(f"[bold cyan]{'='*70}[/bold cyan]")
            console.print(f"[bold]Post #{post.id}[/bold]")
            console.print(f"[cyan]Topic:[/cyan] {post.topic or 'N/A'}")
            console.print(f"[cyan]Tone:[/cyan] {post.tone or 'N/A'}")
            console.print(f"[cyan]Length:[/cyan] {post.length or 'N/A'}")
            console.print(f"[cyan]Created:[/cyan] {post.created_at.strftime('%Y-%m-%d %H:%M')}")

            # Check if part of A/B test
            assignment = session.query(TestAssignment).filter(
                TestAssignment.post_id == post.id
            ).first()

            if assignment:
                console.print(f"[cyan]A/B Test:[/cyan] Test #{assignment.test_id}, Variant #{assignment.variant_id}")

            console.print()

            # Show content
            if full:
                console.print("[bold]Content:[/bold]")
                console.print(post.content)
            else:
                # Show preview (first 200 chars)
                preview = post.content[:200] + "..." if len(post.content) > 200 else post.content
                console.print("[bold]Preview:[/bold]")
                console.print(preview)
                if len(post.content) > 200:
                    console.print(f"\n[dim](Use --full flag to see complete content)[/dim]")

            console.print()

        console.print(f"[bold cyan]{'='*70}[/bold cyan]\n")

        session.close()
        db.close()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    cli()
