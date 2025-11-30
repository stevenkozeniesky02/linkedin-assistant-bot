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
from linkedin import LinkedInClient, PostManager, EngagementManager
from database import Database, Post, Comment, Analytics
from utils import Scheduler

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
@click.option('--check-interval', default=None, type=int, help='Override check interval (seconds)')
@click.option('--strategy', type=click.Choice(['conservative', 'balanced', 'aggressive']), help='Engagement strategy')
def autonomous(check_interval, strategy):
    """Run autonomous agent for continuous posting and engagement"""
    try:
        from autonomous_agent import AutonomousAgent

        # Load config
        config = load_config()

        # Override settings if provided
        if check_interval:
            config.setdefault('autonomous_agent', {})['check_interval'] = check_interval

        if strategy:
            config.setdefault('autonomous_agent', {})['engagement_strategy'] = strategy

        # Save modified config temporarily
        with open('config.yaml', 'w') as f:
            yaml.dump(config, f)

        # Initialize and run agent
        agent = AutonomousAgent()
        agent.run()

    except KeyboardInterrupt:
        console.print("\n[yellow]Autonomous agent stopped[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


if __name__ == '__main__':
    cli()
