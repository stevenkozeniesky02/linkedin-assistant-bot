#!/usr/bin/env python3
"""
Autonomous LinkedIn Agent
Runs continuously to post, engage, and reply to comments automatically
"""

import time
import yaml
from datetime import datetime, timedelta
from typing import List, Dict
import random
from rich.console import Console

from database import Database, Post, Comment
from linkedin import LinkedInClient, PostManager, EngagementManager
from ai import get_ai_provider

console = Console()


class AutonomousAgent:
    """Autonomous LinkedIn agent that posts and engages automatically"""

    def __init__(self, config_path: str = 'config.yaml'):
        """
        Initialize the autonomous agent

        Args:
            config_path: Path to configuration file
        """
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.db = Database(self.config)
        self.ai_provider = get_ai_provider(self.config)

        # Get autonomous agent config
        self.agent_config = self.config.get('autonomous_agent', {})

        # Engagement settings
        self.check_interval = self.agent_config.get('check_interval', 300)  # 5 minutes
        self.engagement_enabled = self.agent_config.get('enable_engagement', True)
        self.reply_to_comments = self.agent_config.get('reply_to_comments', True)
        self.auto_post_scheduled = self.agent_config.get('auto_post_scheduled', True)

        # Limits to avoid spam detection
        self.max_engagements_per_cycle = self.agent_config.get('max_engagements_per_cycle', 3)
        self.max_replies_per_cycle = self.agent_config.get('max_replies_per_cycle', 5)

        # Engagement strategy
        self.engagement_strategy = self.agent_config.get('engagement_strategy', 'balanced')  # conservative, balanced, aggressive

        # LinkedIn client (will be initialized when needed)
        self.client = None
        self.post_manager = None
        self.engagement_manager = None

        # Track last activity times
        self.last_post_check = None
        self.last_engagement_check = None
        self.last_comment_check = None

    def initialize_linkedin(self):
        """Initialize LinkedIn client and managers"""
        if self.client is None:
            console.print("[cyan]Initializing LinkedIn connection...[/cyan]")
            self.client = LinkedInClient(self.config)
            self.client.start()
            self.client.login()
            self.post_manager = PostManager(self.client)
            self.engagement_manager = EngagementManager(self.client, self.config)
            console.print("[green]✓ LinkedIn connected[/green]")

    def close_linkedin(self):
        """Close LinkedIn connection"""
        if self.client:
            self.client.stop()
            self.client = None
            self.post_manager = None
            self.engagement_manager = None

    def check_and_post_scheduled(self):
        """Check for scheduled posts and publish them"""
        if not self.auto_post_scheduled:
            return

        session = self.db.get_session()
        try:
            # Get posts due to be posted
            now = datetime.utcnow()
            due_posts = session.query(Post).filter(
                Post.is_scheduled == True,
                Post.published == False,
                Post.scheduled_time <= now
            ).all()

            if not due_posts:
                return

            console.print(f"\n[bold green]Found {len(due_posts)} scheduled post(s) to publish[/bold green]")

            self.initialize_linkedin()

            for post in due_posts:
                console.print(f"\n[cyan]Publishing scheduled post: {post.topic}[/cyan]")

                # Combine content and hashtags
                full_content = post.content
                if post.hashtags:
                    full_content += f"\n\n{post.hashtags}"

                # Post to LinkedIn
                success = self.post_manager.create_post(full_content, wait_for_confirmation=False)

                if success:
                    # Update database
                    post.published = True
                    post.published_at = datetime.utcnow()
                    post.is_scheduled = False
                    session.commit()

                    console.print(f"[green]✓ Post {post.id} published successfully[/green]")
                else:
                    console.print(f"[yellow]⚠ Failed to publish post {post.id}[/yellow]")

                # Add random delay between posts to appear more human
                if len(due_posts) > 1:
                    delay = random.randint(60, 180)
                    console.print(f"[dim]Waiting {delay}s before next post...[/dim]")
                    time.sleep(delay)

        finally:
            session.close()

    def engage_with_feed(self):
        """Engage with posts in LinkedIn feed"""
        if not self.engagement_enabled:
            console.print("[dim]Engagement disabled in config[/dim]")
            return

        console.print("\n[bold cyan]Checking feed for engagement opportunities...[/bold cyan]")

        self.initialize_linkedin()

        # Get feed posts
        console.print("[dim]Fetching posts from feed...[/dim]")
        posts = self.engagement_manager.get_feed_posts(limit=20)

        if not posts:
            console.print("[yellow]No posts found in feed (posts may have been filtered out)[/yellow]")
            console.print("[dim]Tip: Posts with <10 characters are automatically skipped[/dim]")
            return

        console.print(f"[green]Found {len(posts)} valid posts to potentially engage with[/green]")

        # Determine how many to engage with based on strategy
        engagement_count = self._get_engagement_count(len(posts))
        console.print(f"[cyan]Strategy '{self.engagement_strategy}' → Will engage with {engagement_count} post(s)[/cyan]")

        # Use AI to rank posts by engagement potential
        ranked_posts = self._rank_posts_with_ai(posts)

        # Select top-ranked posts instead of random selection
        selected_posts = ranked_posts[:engagement_count]

        console.print(f"\n[bold green]Selected {len(selected_posts)} top-ranked post(s) for engagement[/bold green]")

        session = self.db.get_session()

        for idx, post_data in enumerate(selected_posts, 1):
            try:
                console.print(f"\n[cyan]Engaging with post {idx}/{len(selected_posts)} by {post_data['author']}[/cyan]")
                console.print(f"[dim]{post_data['text'][:100]}...[/dim]")

                # Generate comment
                console.print(f"[dim]Generating AI comment ({self.config['ai_provider']})...[/dim]")
                comment_text = self.ai_provider.generate_comment(
                    post_content=post_data['text'],
                    tone=self.config.get('engagement', {}).get('comment_tone', 'supportive'),
                    user_context=self.config.get('user_profile', {})
                )
                console.print(f"[dim]Generated: {comment_text[:50]}...[/dim]")

                # Post comment
                console.print(f"[dim]Attempting to post comment...[/dim]")
                success = self.engagement_manager.comment_on_post(
                    post_data['element'],
                    comment_text,
                    wait_for_confirmation=False
                )

                if success:
                    # Save to database
                    comment = Comment(
                        content=comment_text,
                        tone=self.config.get('engagement', {}).get('comment_tone', 'supportive'),
                        target_post_author=post_data['author'],
                        target_post_url=post_data.get('url', ''),
                        target_post_excerpt=post_data['text'][:200],
                        ai_provider=self.config['ai_provider'],
                        published=True,
                        published_at=datetime.utcnow()
                    )

                    session.add(comment)
                    session.commit()

                    console.print(f"[green]✓ Comment posted successfully[/green]")
                else:
                    console.print(f"[yellow]⚠ Failed to post comment[/yellow]")

                # Random delay between engagements (appear human)
                delay = random.randint(30, 90)
                console.print(f"[dim]Waiting {delay}s...[/dim]")
                time.sleep(delay)

            except Exception as e:
                console.print(f"[red]Error engaging with post: {e}[/red]")
                continue

        session.close()

    def reply_to_own_comments(self):
        """Reply to comments on user's own posts"""
        if not self.reply_to_comments:
            return

        console.print("\n[bold cyan]Checking for comments to reply to...[/bold cyan]")

        # This would require additional LinkedIn scraping functionality
        # to fetch comments on user's posts. For now, we'll implement
        # the structure and you can add the LinkedIn API calls later.

        # Placeholder for fetching comments on user's posts
        # In a real implementation, you'd:
        # 1. Get user's recent published posts
        # 2. For each post, fetch comments
        # 3. Check which comments haven't been replied to
        # 4. Generate and post replies

        session = self.db.get_session()
        try:
            # Get user's published posts
            published_posts = session.query(Post).filter(
                Post.published == True
            ).order_by(Post.published_at.desc()).limit(10).all()

            if not published_posts:
                console.print("[yellow]No published posts to check for comments[/yellow]")
                return

            console.print(f"[dim]Checking {len(published_posts)} recent posts for comments...[/dim]")

            # TODO: Implement comment fetching and replying
            # For now, just log that we checked
            console.print("[dim]Comment reply system ready (requires LinkedIn comment API integration)[/dim]")

        finally:
            session.close()

    def _rank_posts_with_ai(self, posts: List[Dict]) -> List[Dict]:
        """
        Use AI to analyze and rank posts for engagement potential

        Args:
            posts: List of post data dictionaries

        Returns:
            Posts sorted by engagement potential (best first)
        """
        console.print(f"[dim]Analyzing {len(posts)} posts with AI to find best engagement opportunities...[/dim]")

        user_profile = self.config.get('user_profile', {})
        user_interests = user_profile.get('interests', [])
        user_industry = user_profile.get('industry', '')

        scored_posts = []

        for post_data in posts:
            try:
                # Create a prompt to score this post
                analysis_prompt = f"""Score this LinkedIn post from 1-10 for engagement potential.

POST AUTHOR: {post_data['author']}
POST CONTENT: {post_data['text'][:300]}

YOUR PROFILE:
- Title: {user_profile.get('title', 'Professional')}
- Industry: {user_industry}
- Interests: {', '.join(user_interests)}

Rate 1-10 based on:
- Relevance to your expertise
- Quality and authenticity
- Opportunity for valuable comment

IMPORTANT: Reply with ONLY the number (1-10). No explanation. Just the number."""

                # Get AI score
                try:
                    score_text = self.ai_provider._generate(
                        prompt=analysis_prompt,
                        system_prompt="Return only a single digit number from 1-10. No words, no explanation, just the number."
                    ).strip()
                except AttributeError:
                    # If _generate doesn't exist, use generate_comment and parse from it
                    score_text = "5"
                    console.print(f"[dim]Note: Using fallback scoring for {post_data['author']}[/dim]")

                # Extract numeric score with better parsing
                import re
                try:
                    # Try to extract first number from response
                    numbers = re.findall(r'\d+\.?\d*', score_text)
                    if numbers:
                        score = float(numbers[0])
                        # Clamp score to 1-10 range
                        score = max(1, min(10, score))
                    else:
                        score = 5.0
                        console.print(f"[dim]No number found in AI response for {post_data['author']}: '{score_text[:50]}', using default[/dim]")
                except:
                    # If parsing fails, use default mid-range score
                    score = 5.0
                    console.print(f"[dim]Could not parse AI score for {post_data['author']}, using default[/dim]")

                post_data['ai_score'] = score
                scored_posts.append(post_data)

                console.print(f"[dim]Post by {post_data['author']}: Score {score}/10[/dim]")

            except Exception as e:
                console.print(f"[yellow]Warning: Error scoring post by {post_data['author']}: {e}[/yellow]")
                # If scoring fails, assign neutral score
                post_data['ai_score'] = 5.0
                scored_posts.append(post_data)

        # Sort by AI score (highest first)
        ranked_posts = sorted(scored_posts, key=lambda x: x['ai_score'], reverse=True)

        console.print(f"\n[cyan]AI Post Ranking (Top 5):[/cyan]")
        for i, post in enumerate(ranked_posts[:5], 1):
            console.print(f"  {i}. {post['author']} - Score: {post['ai_score']:.1f}/10")
            console.print(f"     {post['text'][:80]}...")

        return ranked_posts

    def _get_engagement_count(self, available_posts: int) -> int:
        """
        Determine how many posts to engage with based on strategy

        Args:
            available_posts: Number of posts available in feed

        Returns:
            Number of posts to engage with
        """
        if self.engagement_strategy == 'conservative':
            return min(1, available_posts, self.max_engagements_per_cycle)
        elif self.engagement_strategy == 'aggressive':
            return min(5, available_posts, self.max_engagements_per_cycle)
        else:  # balanced
            return min(3, available_posts, self.max_engagements_per_cycle)

    def run_cycle(self):
        """Run one cycle of autonomous operations"""
        try:
            console.print(f"\n{'='*60}")
            console.print(f"[bold blue]Autonomous Agent Cycle - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/bold blue]")
            console.print(f"{'='*60}")

            # Check and post scheduled content
            self.check_and_post_scheduled()

            # Engage with feed
            self.engage_with_feed()

            # Reply to comments
            self.reply_to_own_comments()

            console.print(f"\n[green]✓ Cycle completed[/green]")

        except Exception as e:
            console.print(f"[red]Error in cycle: {e}[/red]")

        finally:
            # Close LinkedIn connection to avoid keeping browser open
            self.close_linkedin()

    def run(self):
        """Run the autonomous agent continuously"""
        console.print("\n[bold green]Starting Autonomous LinkedIn Agent[/bold green]")
        console.print(f"Check interval: {self.check_interval} seconds")
        console.print(f"Engagement: {'Enabled' if self.engagement_enabled else 'Disabled'}")
        console.print(f"Comment replies: {'Enabled' if self.reply_to_comments else 'Disabled'}")
        console.print(f"Auto-post scheduled: {'Enabled' if self.auto_post_scheduled else 'Disabled'}")
        console.print(f"Engagement strategy: {self.engagement_strategy}")
        console.print("\nPress Ctrl+C to stop\n")

        try:
            while True:
                self.run_cycle()

                # Wait for next cycle
                console.print(f"\n[dim]Sleeping for {self.check_interval} seconds...[/dim]")
                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            console.print("\n\n[yellow]Autonomous agent stopped by user[/yellow]")
            self.close_linkedin()


if __name__ == '__main__':
    agent = AutonomousAgent()
    agent.run()
