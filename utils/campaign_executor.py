"""Campaign Execution Engine"""

import time
import random
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from linkedin.campaign_manager import CampaignManager
from linkedin.engagement_manager import EngagementManager
from linkedin.connection_manager import ConnectionManager
from utils.safety_monitor import SafetyMonitor
from database.models import Activity
from ai import get_ai_provider


class CampaignExecutor:
    """Execute targeted engagement campaigns with safety monitoring"""

    def __init__(self, db_session: Session, linkedin_client, config: dict):
        """
        Initialize Campaign Executor

        Args:
            db_session: SQLAlchemy database session
            linkedin_client: LinkedInClient instance
            config: Configuration dictionary
        """
        self.db = db_session
        self.client = linkedin_client
        self.config = config

        # Initialize managers
        self.campaign_manager = CampaignManager(db_session, config)
        self.engagement_manager = EngagementManager(linkedin_client, config)
        self.connection_manager = ConnectionManager(db_session, config)
        self.safety_monitor = SafetyMonitor(db_session, config)

        # Initialize AI provider
        self.ai_provider = get_ai_provider(config)

    def execute_campaigns(self, max_posts: int = 20, max_engagements: int = 10) -> Dict:
        """
        Execute all active campaigns

        Args:
            max_posts: Maximum posts to retrieve from feed
            max_engagements: Maximum engagements to perform across all campaigns

        Returns:
            Dictionary with execution summary
        """
        print("\n" + "="*60)
        print("Campaign Execution - Starting")
        print("="*60)

        # Check if login is required
        if not self.client.is_logged_in():
            print("\nNot logged in to LinkedIn. Please login first.")
            return {
                'success': False,
                'error': 'Not logged in',
                'campaigns_executed': 0,
                'posts_matched': 0,
                'engagements_performed': 0
            }

        # Get active campaigns
        active_campaigns = self.campaign_manager.get_active_campaigns()

        if not active_campaigns:
            print("\nNo active campaigns found.")
            return {
                'success': True,
                'campaigns_executed': 0,
                'posts_matched': 0,
                'engagements_performed': 0,
                'message': 'No active campaigns'
            }

        print(f"\nFound {len(active_campaigns)} active campaign(s):")
        for campaign in active_campaigns:
            print(f"  - {campaign.name} ({campaign.campaign_type})")

        # Check overall safety status
        safety_status = self.safety_monitor.get_safety_status()
        if safety_status['status'] == 'limit_reached':
            print(f"\n⛔ Safety Monitor: {safety_status['status'].upper()}")
            print("Daily or hourly limits reached. Cannot execute campaigns now.")
            return {
                'success': False,
                'error': 'Rate limits reached',
                'campaigns_executed': 0,
                'posts_matched': 0,
                'engagements_performed': 0
            }

        # Get feed posts
        print(f"\nRetrieving up to {max_posts} posts from feed...")
        try:
            feed_posts = self.engagement_manager.get_feed_posts(limit=max_posts)
            print(f"Retrieved {len(feed_posts)} quality posts from feed")
        except Exception as e:
            print(f"\n✗ Error retrieving feed posts: {e}")
            return {
                'success': False,
                'error': str(e),
                'campaigns_executed': 0,
                'posts_matched': 0,
                'engagements_performed': 0
            }

        # Match posts to campaigns
        print(f"\nMatching posts to campaign targets...")
        post_matches = []

        for post in feed_posts:
            # Extract hashtags from post content
            hashtags = self._extract_hashtags(post.get('content', ''))

            post_data = {
                'author': post.get('author', ''),
                'author_title': post.get('author_title', ''),
                'author_company': post.get('author_company', ''),
                'content': post.get('content', ''),
                'hashtags': hashtags,
                'url': post.get('url', ''),
                'author_url': post.get('author_url', '')
            }

            # Check if this post matches any campaign
            matches = self.campaign_manager.match_post_to_campaigns(post_data)

            if matches:
                for match in matches:
                    post_matches.append({
                        'post': post,
                        'post_data': post_data,
                        'campaign': match['campaign'],
                        'target': match['target'],
                        'matched_value': match['matched_value'],
                        'priority': match['priority']
                    })
                    print(f"  ✓ Matched: {post.get('author')} → Campaign '{match['campaign'].name}' (target: {match['matched_value']})")

        print(f"\n{len(post_matches)} post-campaign matches found")

        if not post_matches:
            return {
                'success': True,
                'campaigns_executed': len(active_campaigns),
                'posts_matched': 0,
                'engagements_performed': 0,
                'message': 'No matching posts found for active campaigns'
            }

        # Execute engagements (up to max_engagements)
        engagements_performed = 0
        campaigns_engaged = set()

        for match in post_matches[:max_engagements]:
            # Check if we can still engage
            safety_check = self.safety_monitor.check_action_allowed('comment')
            if not safety_check['allowed']:
                print(f"\n⛔ Safety limit reached: {safety_check['reason']}")
                break

            # Check campaign-specific limits
            campaign_limit_check = self.campaign_manager.check_campaign_limits(match['campaign'].id)
            if not campaign_limit_check['allowed']:
                print(f"\n⚠️  Campaign '{match['campaign'].name}' limit reached: {campaign_limit_check['reason']}")
                continue

            # Perform engagement
            print(f"\n{'='*60}")
            print(f"Engaging with post from {match['post'].get('author')}")
            print(f"Campaign: {match['campaign'].name}")
            print(f"Matched target: {match['matched_value']}")
            print(f"{'='*60}")

            try:
                # Get engagement types from campaign
                engagement_types = match['campaign'].engagement_types.split(',')

                # For now, we'll focus on comments (most valuable engagement)
                if 'comment' in engagement_types:
                    success = self._engage_with_comment(match)
                elif 'like' in engagement_types:
                    success = self._engage_with_like(match)
                else:
                    print(f"Skipping - no supported engagement type configured")
                    continue

                if success:
                    engagements_performed += 1
                    campaigns_engaged.add(match['campaign'].id)
                    print(f"✓ Engagement successful!")

                    # Random delay to appear human
                    delay = random.uniform(15, 45)
                    print(f"\nWaiting {delay:.1f}s before next action...")
                    time.sleep(delay)
                else:
                    print(f"✗ Engagement failed")

            except Exception as e:
                print(f"\n✗ Error during engagement: {e}")
                continue

        print("\n" + "="*60)
        print("Campaign Execution - Complete")
        print("="*60)
        print(f"Campaigns executed: {len(campaigns_engaged)}")
        print(f"Posts matched: {len(post_matches)}")
        print(f"Engagements performed: {engagements_performed}")

        return {
            'success': True,
            'campaigns_executed': len(campaigns_engaged),
            'posts_matched': len(post_matches),
            'engagements_performed': engagements_performed,
            'message': f'Successfully executed {engagements_performed} engagements across {len(campaigns_engaged)} campaigns'
        }

    def _extract_hashtags(self, content: str) -> List[str]:
        """Extract hashtags from post content"""
        import re
        hashtags = re.findall(r'#(\w+)', content)
        return [f"#{tag}" for tag in hashtags]

    def _engage_with_comment(self, match: Dict) -> bool:
        """
        Engage with a post by commenting

        Args:
            match: Post-campaign match dictionary

        Returns:
            Boolean indicating success
        """
        post = match['post']
        campaign = match['campaign']
        target = match['target']

        # Generate AI comment
        print("\nGenerating AI comment...")

        user_profile = self.config.get('user_profile', {})
        comment_tone = self.config.get('engagement', {}).get('comment_tone', 'supportive')

        try:
            comment_prompt = f"""You are {user_profile.get('name', 'a professional')}, a {user_profile.get('title', 'professional')} with expertise in {', '.join(user_profile.get('interests', ['technology']))}.

Generate a thoughtful, human-like comment for this LinkedIn post. The comment should:
- Be authentic and conversational (NO emojis, NO exclamation marks unless truly warranted)
- Reflect your expertise: {user_profile.get('background', 'professional experience')}
- Tone: {comment_tone}
- Length: 2-3 sentences
- Sound like a real person, not an AI

Post content:
"{post.get('content', '')[:500]}"

Author: {post.get('author', 'Unknown')}
Author title: {post.get('author_title', 'Professional')}

Generate only the comment text, nothing else."""

            comment_content = self.ai_provider.generate_text(
                prompt=comment_prompt,
                max_tokens=150
            )

            print(f"\nGenerated comment:\n{comment_content}")

            # Post the comment
            print("\nPosting comment...")
            comment_result = self.engagement_manager.post_comment(
                post_url=post.get('url'),
                comment_text=comment_content
            )

            if comment_result:
                # Log to safety monitor
                activity = self.safety_monitor.log_activity(
                    action_type='comment',
                    target_type='post',
                    target_id=post.get('url'),
                    duration=5.0,
                    success=True
                )

                # Log to campaign manager
                self.campaign_manager.log_campaign_activity(
                    campaign_id=campaign.id,
                    activity_id=activity.id,
                    target_post_url=post.get('url'),
                    target_author=post.get('author'),
                    target_author_title=post.get('author_title'),
                    target_author_company=post.get('author_company'),
                    action_type='comment',
                    matched_target=match['matched_value'],
                    success=True,
                    post_excerpt=post.get('content', '')[:200]
                )

                # Update connection quality if author is in our network
                if post.get('author_url'):
                    self.connection_manager.update_engagement(
                        profile_url=post.get('author_url'),
                        posts_engaged=1
                    )

                return True

        except Exception as e:
            print(f"Error generating/posting comment: {e}")

            # Log failed activity
            activity = self.safety_monitor.log_activity(
                action_type='comment',
                target_type='post',
                target_id=post.get('url'),
                duration=2.0,
                success=False,
                error=str(e)
            )

            self.campaign_manager.log_campaign_activity(
                campaign_id=campaign.id,
                activity_id=activity.id,
                target_post_url=post.get('url'),
                target_author=post.get('author'),
                action_type='comment',
                matched_target=match['matched_value'],
                success=False,
                error_message=str(e),
                post_excerpt=post.get('content', '')[:200]
            )

        return False

    def _engage_with_like(self, match: Dict) -> bool:
        """
        Engage with a post by liking

        Args:
            match: Post-campaign match dictionary

        Returns:
            Boolean indicating success
        """
        post = match['post']
        campaign = match['campaign']

        try:
            print("\nLiking post...")
            like_result = self.engagement_manager.like_post(post.get('url'))

            if like_result:
                # Log to safety monitor
                activity = self.safety_monitor.log_activity(
                    action_type='like',
                    target_type='post',
                    target_id=post.get('url'),
                    duration=2.0,
                    success=True
                )

                # Log to campaign manager
                self.campaign_manager.log_campaign_activity(
                    campaign_id=campaign.id,
                    activity_id=activity.id,
                    target_post_url=post.get('url'),
                    target_author=post.get('author'),
                    target_author_title=post.get('author_title'),
                    target_author_company=post.get('author_company'),
                    action_type='like',
                    matched_target=match['matched_value'],
                    success=True,
                    post_excerpt=post.get('content', '')[:200]
                )

                # Update connection quality
                if post.get('author_url'):
                    self.connection_manager.update_engagement(
                        profile_url=post.get('author_url'),
                        posts_engaged=1
                    )

                return True

        except Exception as e:
            print(f"Error liking post: {e}")

            # Log failed activity
            activity = self.safety_monitor.log_activity(
                action_type='like',
                target_type='post',
                target_id=post.get('url'),
                duration=1.0,
                success=False,
                error=str(e)
            )

            self.campaign_manager.log_campaign_activity(
                campaign_id=campaign.id,
                activity_id=activity.id,
                target_post_url=post.get('url'),
                target_author=post.get('author'),
                action_type='like',
                matched_target=match['matched_value'],
                success=False,
                error_message=str(e)
            )

        return False

    def execute_single_campaign(self, campaign_id: int, max_posts: int = 20,
                                max_engagements: int = 5) -> Dict:
        """
        Execute a specific campaign by ID

        Args:
            campaign_id: Campaign ID to execute
            max_posts: Maximum posts to retrieve
            max_engagements: Maximum engagements for this campaign

        Returns:
            Dictionary with execution summary
        """
        campaign = self.campaign_manager.get_campaign(campaign_id)

        if not campaign:
            return {
                'success': False,
                'error': f'Campaign {campaign_id} not found'
            }

        if campaign.status != 'active':
            return {
                'success': False,
                'error': f'Campaign is not active (status: {campaign.status})'
            }

        print(f"\nExecuting campaign: {campaign.name}")
        print(f"Type: {campaign.campaign_type}")
        print(f"Targets: {len(campaign.targets)}")

        # Temporarily make this the only active campaign
        original_statuses = {}
        for other_campaign in self.campaign_manager.get_active_campaigns():
            if other_campaign.id != campaign_id:
                original_statuses[other_campaign.id] = other_campaign.status
                other_campaign.status = 'paused'

        self.db.commit()

        # Execute
        result = self.execute_campaigns(max_posts=max_posts, max_engagements=max_engagements)

        # Restore campaign statuses
        for camp_id, status in original_statuses.items():
            camp = self.campaign_manager.get_campaign(camp_id)
            if camp:
                camp.status = status

        self.db.commit()

        return result
