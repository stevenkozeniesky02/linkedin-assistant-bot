"""Campaign Manager for Targeted Engagement Campaigns"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_

from database.models import Campaign, CampaignTarget, CampaignActivity, Activity, Connection
from utils.safety_monitor import SafetyMonitor


class CampaignManager:
    """Manage targeted engagement campaigns"""

    def __init__(self, db_session: Session, config: dict):
        """
        Initialize Campaign Manager

        Args:
            db_session: SQLAlchemy database session
            config: Configuration dictionary
        """
        self.db = db_session
        self.config = config.get('campaigns', {})

    def create_campaign(self, name: str, campaign_type: str, description: str = None,
                       targets: List[Dict] = None, engagement_types: List[str] = None,
                       max_actions_per_day: int = 10, target_engagements: int = None,
                       start_date: datetime = None, end_date: datetime = None) -> Campaign:
        """
        Create a new engagement campaign

        Args:
            name: Campaign name
            campaign_type: Type (hashtag, company, influencer, topic)
            description: Campaign description
            targets: List of target dictionaries [{"type": "hashtag", "value": "ai", "priority": "high"}]
            engagement_types: Types of engagement (comment, like, share)
            max_actions_per_day: Daily action limit
            target_engagements: Target number of engagements
            start_date: Campaign start date
            end_date: Campaign end date

        Returns:
            Campaign object
        """
        # Create campaign
        campaign = Campaign(
            name=name,
            description=description,
            campaign_type=campaign_type,
            status='draft',
            start_date=start_date or datetime.utcnow(),
            end_date=end_date,
            target_engagements=target_engagements,
            max_actions_per_day=max_actions_per_day,
            engagement_types=','.join(engagement_types) if engagement_types else 'comment,like'
        )

        self.db.add(campaign)
        self.db.commit()

        # Add targets
        if targets:
            for target_data in targets:
                self.add_campaign_target(
                    campaign_id=campaign.id,
                    target_type=target_data.get('type'),
                    target_value=target_data.get('value'),
                    priority=target_data.get('priority', 'medium')
                )

        return campaign

    def add_campaign_target(self, campaign_id: int, target_type: str,
                           target_value: str, priority: str = 'medium') -> CampaignTarget:
        """
        Add a target to a campaign

        Args:
            campaign_id: Campaign ID
            target_type: Type (hashtag, company, profile, keyword)
            target_value: The actual value (hashtag text, company name, profile URL, keyword)
            priority: Priority level (low, medium, high)

        Returns:
            CampaignTarget object
        """
        target = CampaignTarget(
            campaign_id=campaign_id,
            target_type=target_type,
            target_value=target_value,
            priority=priority,
            is_active=True
        )

        self.db.add(target)
        self.db.commit()

        return target

    def get_campaign(self, campaign_id: int) -> Optional[Campaign]:
        """Get campaign by ID"""
        return self.db.query(Campaign).filter(Campaign.id == campaign_id).first()

    def list_campaigns(self, status: str = None, campaign_type: str = None) -> List[Campaign]:
        """
        List campaigns with optional filtering

        Args:
            status: Filter by status (draft, active, paused, completed)
            campaign_type: Filter by type (hashtag, company, influencer, topic)

        Returns:
            List of Campaign objects
        """
        query = self.db.query(Campaign)

        if status:
            query = query.filter(Campaign.status == status)
        if campaign_type:
            query = query.filter(Campaign.campaign_type == campaign_type)

        return query.order_by(desc(Campaign.created_at)).all()

    def activate_campaign(self, campaign_id: int) -> Campaign:
        """Activate a campaign"""
        campaign = self.get_campaign(campaign_id)
        if campaign:
            campaign.status = 'active'
            if not campaign.start_date:
                campaign.start_date = datetime.utcnow()
            self.db.commit()
        return campaign

    def pause_campaign(self, campaign_id: int) -> Campaign:
        """Pause a campaign"""
        campaign = self.get_campaign(campaign_id)
        if campaign:
            campaign.status = 'paused'
            self.db.commit()
        return campaign

    def complete_campaign(self, campaign_id: int) -> Campaign:
        """Mark campaign as completed"""
        campaign = self.get_campaign(campaign_id)
        if campaign:
            campaign.status = 'completed'
            campaign.end_date = datetime.utcnow()
            self.db.commit()
        return campaign

    def log_campaign_activity(self, campaign_id: int, activity_id: int,
                             target_post_url: str = None, target_author: str = None,
                             action_type: str = None, matched_target: str = None,
                             success: bool = True, error_message: str = None,
                             post_excerpt: str = None, target_author_title: str = None,
                             target_author_company: str = None) -> CampaignActivity:
        """
        Log an activity performed as part of a campaign

        Args:
            campaign_id: Campaign ID
            activity_id: Activity ID (from Activity table)
            target_post_url: URL of post engaged with
            target_author: Author of the post
            action_type: Type of action (comment, like, etc.)
            matched_target: Which target matched (e.g., "#ai" hashtag)
            success: Whether action succeeded
            error_message: Error message if failed
            post_excerpt: Preview of post content
            target_author_title: Author's job title
            target_author_company: Author's company

        Returns:
            CampaignActivity object
        """
        campaign_activity = CampaignActivity(
            campaign_id=campaign_id,
            activity_id=activity_id,
            target_post_url=target_post_url,
            target_author=target_author,
            target_author_title=target_author_title,
            target_author_company=target_author_company,
            action_type=action_type,
            matched_target=matched_target,
            success=success,
            error_message=error_message,
            post_excerpt=post_excerpt
        )

        self.db.add(campaign_activity)

        # Update campaign stats
        campaign = self.get_campaign(campaign_id)
        if campaign:
            campaign.total_engagements += 1
            campaign.total_posts_engaged += 1
            campaign.last_executed = datetime.utcnow()

            # Update success rate
            total_activities = self.db.query(CampaignActivity).filter(
                CampaignActivity.campaign_id == campaign_id
            ).count()

            successful_activities = self.db.query(CampaignActivity).filter(
                and_(
                    CampaignActivity.campaign_id == campaign_id,
                    CampaignActivity.success == True
                )
            ).count()

            campaign.success_rate = (successful_activities / total_activities * 100) if total_activities > 0 else 0

        self.db.commit()

        return campaign_activity

    def get_campaign_analytics(self, campaign_id: int) -> Dict:
        """
        Get comprehensive analytics for a campaign

        Args:
            campaign_id: Campaign ID

        Returns:
            Dictionary with campaign analytics
        """
        campaign = self.get_campaign(campaign_id)
        if not campaign:
            return {}

        # Get all activities
        activities = self.db.query(CampaignActivity).filter(
            CampaignActivity.campaign_id == campaign_id
        ).all()

        # Calculate metrics
        total_activities = len(activities)
        successful_activities = sum(1 for a in activities if a.success)
        failed_activities = total_activities - successful_activities

        # Activities by type
        activities_by_type = {}
        for activity in activities:
            action = activity.action_type
            activities_by_type[action] = activities_by_type.get(action, 0) + 1

        # Activities by target
        activities_by_target = {}
        for activity in activities:
            target = activity.matched_target or 'unknown'
            activities_by_target[target] = activities_by_target.get(target, 0) + 1

        # Top authors engaged
        author_engagement = {}
        for activity in activities:
            if activity.target_author:
                author_engagement[activity.target_author] = author_engagement.get(activity.target_author, 0) + 1

        top_authors = sorted(author_engagement.items(), key=lambda x: x[1], reverse=True)[:10]

        # Timeline data (activities per day)
        if campaign.start_date:
            days_running = (datetime.utcnow() - campaign.start_date).days + 1
            avg_engagements_per_day = total_activities / days_running if days_running > 0 else 0
        else:
            days_running = 0
            avg_engagements_per_day = 0

        # Progress towards goal
        goal_progress = 0
        if campaign.target_engagements:
            goal_progress = (campaign.total_engagements / campaign.target_engagements * 100)

        # Get target performance
        targets = self.db.query(CampaignTarget).filter(
            CampaignTarget.campaign_id == campaign_id
        ).all()

        target_performance = []
        for target in targets:
            target_activities = [a for a in activities if a.matched_target == target.target_value]
            target_performance.append({
                'type': target.target_type,
                'value': target.target_value,
                'priority': target.priority,
                'engagements': len(target_activities),
                'success_rate': (sum(1 for a in target_activities if a.success) / len(target_activities) * 100) if target_activities else 0
            })

        return {
            'campaign_id': campaign.id,
            'campaign_name': campaign.name,
            'campaign_type': campaign.campaign_type,
            'status': campaign.status,
            'start_date': campaign.start_date,
            'end_date': campaign.end_date,
            'days_running': days_running,

            # Goals
            'target_engagements': campaign.target_engagements,
            'goal_progress_percent': min(100, goal_progress),

            # Overall stats
            'total_activities': total_activities,
            'successful_activities': successful_activities,
            'failed_activities': failed_activities,
            'success_rate': campaign.success_rate,
            'total_posts_engaged': campaign.total_posts_engaged,
            'avg_engagements_per_day': round(avg_engagements_per_day, 2),

            # Breakdown
            'activities_by_type': activities_by_type,
            'activities_by_target': activities_by_target,
            'top_authors': [{'author': author, 'count': count} for author, count in top_authors],
            'target_performance': sorted(target_performance, key=lambda x: x['engagements'], reverse=True),

            # Limits
            'max_actions_per_day': campaign.max_actions_per_day,
            'last_executed': campaign.last_executed
        }

    def get_active_campaigns(self) -> List[Campaign]:
        """Get all active campaigns"""
        return self.db.query(Campaign).filter(Campaign.status == 'active').all()

    def check_campaign_limits(self, campaign_id: int) -> Dict:
        """
        Check if campaign can run more actions today

        Args:
            campaign_id: Campaign ID

        Returns:
            Dictionary with limit status
        """
        campaign = self.get_campaign(campaign_id)
        if not campaign:
            return {'allowed': False, 'reason': 'Campaign not found'}

        # Count activities today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        activities_today = self.db.query(CampaignActivity).filter(
            and_(
                CampaignActivity.campaign_id == campaign_id,
                CampaignActivity.performed_at >= today_start
            )
        ).count()

        remaining = campaign.max_actions_per_day - activities_today

        if activities_today >= campaign.max_actions_per_day:
            return {
                'allowed': False,
                'reason': f'Daily limit reached ({campaign.max_actions_per_day} actions)',
                'activities_today': activities_today,
                'remaining': 0
            }

        return {
            'allowed': True,
            'reason': f'{remaining} actions remaining today',
            'activities_today': activities_today,
            'remaining': remaining
        }

    def match_post_to_campaigns(self, post_data: Dict) -> List[Dict]:
        """
        Check if a post matches any active campaign targets

        Args:
            post_data: Dictionary with post information
                {
                    'author': str,
                    'author_title': str,
                    'author_company': str,
                    'content': str,
                    'hashtags': List[str],
                    'url': str
                }

        Returns:
            List of matching campaigns with target details
        """
        active_campaigns = self.get_active_campaigns()
        matches = []

        for campaign in active_campaigns:
            # Check campaign limits
            limit_check = self.check_campaign_limits(campaign.id)
            if not limit_check['allowed']:
                continue

            # Get campaign targets
            targets = self.db.query(CampaignTarget).filter(
                and_(
                    CampaignTarget.campaign_id == campaign.id,
                    CampaignTarget.is_active == True
                )
            ).all()

            for target in targets:
                matched = False
                matched_value = None

                if target.target_type == 'hashtag':
                    # Check if post contains this hashtag
                    post_hashtags = post_data.get('hashtags', [])
                    if any(target.target_value.lower() in hashtag.lower() for hashtag in post_hashtags):
                        matched = True
                        matched_value = target.target_value

                elif target.target_type == 'company':
                    # Check if author works at this company
                    author_company = post_data.get('author_company', '')
                    if target.target_value.lower() in author_company.lower():
                        matched = True
                        matched_value = target.target_value

                elif target.target_type == 'keyword':
                    # Check if post content contains keyword
                    content = post_data.get('content', '')
                    if target.target_value.lower() in content.lower():
                        matched = True
                        matched_value = target.target_value

                elif target.target_type == 'profile':
                    # Check if author matches this profile URL
                    author_url = post_data.get('author_url', '')
                    if target.target_value in author_url:
                        matched = True
                        matched_value = target.target_value

                if matched:
                    matches.append({
                        'campaign': campaign,
                        'target': target,
                        'matched_value': matched_value,
                        'priority': target.priority,
                        'remaining_actions': limit_check['remaining']
                    })

        # Sort by priority (high -> medium -> low)
        priority_order = {'high': 3, 'medium': 2, 'low': 1}
        matches.sort(key=lambda x: priority_order.get(x['priority'], 0), reverse=True)

        return matches

    def get_campaign_recommendations(self, campaign_id: int) -> Dict:
        """
        Get AI-powered recommendations for improving campaign performance

        Args:
            campaign_id: Campaign ID

        Returns:
            Dictionary with recommendations
        """
        analytics = self.get_campaign_analytics(campaign_id)
        recommendations = []

        if not analytics:
            return {'recommendations': []}

        # Check success rate
        if analytics['success_rate'] < 80:
            recommendations.append({
                'type': 'performance',
                'priority': 'high',
                'message': f"Success rate is low ({analytics['success_rate']:.1f}%). Review target criteria.",
                'action': 'Consider refining your target hashtags/companies for better matches'
            })

        # Check daily activity
        if analytics['avg_engagements_per_day'] < analytics['max_actions_per_day'] * 0.5:
            recommendations.append({
                'type': 'activity',
                'priority': 'medium',
                'message': f"Only using {analytics['avg_engagements_per_day']:.1f} of {analytics['max_actions_per_day']} daily actions",
                'action': 'Consider adding more targets or increasing campaign frequency'
            })

        # Check goal progress
        if analytics.get('target_engagements') and analytics['goal_progress_percent'] < 50 and analytics['days_running'] > 7:
            recommendations.append({
                'type': 'goal',
                'priority': 'high',
                'message': f"Only {analytics['goal_progress_percent']:.1f}% towards goal after {analytics['days_running']} days",
                'action': 'Increase daily action limit or extend campaign duration'
            })

        # Check target diversity
        if len(analytics['target_performance']) == 1:
            recommendations.append({
                'type': 'targeting',
                'priority': 'medium',
                'message': 'Campaign has only one target',
                'action': 'Add more hashtags/companies to increase reach'
            })

        # Check underperforming targets
        for target_perf in analytics['target_performance']:
            if target_perf['engagements'] == 0 and analytics['days_running'] > 3:
                recommendations.append({
                    'type': 'target',
                    'priority': 'low',
                    'message': f"Target '{target_perf['value']}' has no engagements",
                    'action': f"Consider removing or replacing '{target_perf['value']}'"
                })

        return {
            'campaign_name': analytics['campaign_name'],
            'status': analytics['status'],
            'recommendations': recommendations[:5]  # Top 5 recommendations
        }
