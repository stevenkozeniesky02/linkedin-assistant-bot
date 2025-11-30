"""
Competitor Monitoring System

Track competitor activity on LinkedIn including:
- Posting frequency
- Engagement metrics
- Content analysis
- Performance trends
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

from database.models import Competitor, CompetitorSnapshot
from database.session import get_session

logger = logging.getLogger(__name__)


class CompetitorMonitor:
    """Monitor and analyze competitor activity on LinkedIn"""

    def __init__(self):
        self.session = get_session()

    def add_competitor(
        self,
        name: str,
        profile_url: str,
        title: Optional[str] = None,
        company: Optional[str] = None,
        industry: Optional[str] = None,
        priority: str = 'medium',
        tags: Optional[List[str]] = None,
        notes: Optional[str] = None
    ) -> Competitor:
        """
        Add a new competitor to monitor.

        Args:
            name: Competitor name
            profile_url: LinkedIn profile URL
            title: Job title
            company: Company name
            industry: Industry
            priority: Priority level (low, medium, high)
            tags: List of tags for categorization
            notes: Additional notes

        Returns:
            Competitor object
        """
        logger.info(f"Adding competitor: {name}")

        # Check if already exists
        existing = self.session.query(Competitor).filter_by(profile_url=profile_url).first()
        if existing:
            logger.warning(f"Competitor already exists: {name}")
            return existing

        competitor = Competitor(
            name=name,
            profile_url=profile_url,
            title=title,
            company=company,
            industry=industry,
            priority=priority,
            tags=','.join(tags) if tags else None,
            notes=notes,
            is_active=True
        )

        self.session.add(competitor)
        self.session.commit()

        logger.info(f"Added competitor: {name} (ID: {competitor.id})")
        return competitor

    def update_competitor(self, competitor_id: int, **kwargs) -> Optional[Competitor]:
        """
        Update competitor information.

        Args:
            competitor_id: Competitor ID
            **kwargs: Fields to update

        Returns:
            Updated Competitor object or None
        """
        competitor = self.session.query(Competitor).filter_by(id=competitor_id).first()
        if not competitor:
            logger.error(f"Competitor not found: {competitor_id}")
            return None

        for key, value in kwargs.items():
            if hasattr(competitor, key):
                setattr(competitor, key, value)

        competitor.updated_at = datetime.utcnow()
        self.session.commit()

        logger.info(f"Updated competitor: {competitor.name}")
        return competitor

    def deactivate_competitor(self, competitor_id: int) -> bool:
        """
        Deactivate a competitor (stop monitoring).

        Args:
            competitor_id: Competitor ID

        Returns:
            Success status
        """
        competitor = self.session.query(Competitor).filter_by(id=competitor_id).first()
        if not competitor:
            logger.error(f"Competitor not found: {competitor_id}")
            return False

        competitor.is_active = False
        competitor.updated_at = datetime.utcnow()
        self.session.commit()

        logger.info(f"Deactivated competitor: {competitor.name}")
        return True

    def get_active_competitors(self) -> List[Competitor]:
        """
        Get all active competitors.

        Returns:
            List of active Competitor objects
        """
        return self.session.query(Competitor).filter_by(is_active=True).all()

    def get_competitor(self, competitor_id: int) -> Optional[Competitor]:
        """
        Get competitor by ID.

        Args:
            competitor_id: Competitor ID

        Returns:
            Competitor object or None
        """
        return self.session.query(Competitor).filter_by(id=competitor_id).first()

    def record_snapshot(
        self,
        competitor_id: int,
        followers_count: int = 0,
        connections_count: int = 0,
        posts_count: int = 0,
        posts_last_week: int = 0,
        posts_last_month: int = 0,
        engagement_data: Optional[Dict] = None
    ) -> CompetitorSnapshot:
        """
        Record a snapshot of competitor metrics.

        Args:
            competitor_id: Competitor ID
            followers_count: Number of followers
            connections_count: Number of connections
            posts_count: Total posts
            posts_last_week: Posts in last 7 days
            posts_last_month: Posts in last 30 days
            engagement_data: Dict with engagement metrics

        Returns:
            CompetitorSnapshot object
        """
        logger.info(f"Recording snapshot for competitor ID: {competitor_id}")

        engagement_data = engagement_data or {}

        # Calculate metrics
        posting_frequency = posts_last_week  # posts per week
        avg_engagement_rate = engagement_data.get('avg_engagement_rate', 0.0)
        avg_likes_per_post = engagement_data.get('avg_likes', 0.0)
        avg_comments_per_post = engagement_data.get('avg_comments', 0.0)

        snapshot = CompetitorSnapshot(
            competitor_id=competitor_id,
            followers_count=followers_count,
            connections_count=connections_count,
            posts_count=posts_count,
            posts_last_week=posts_last_week,
            posts_last_month=posts_last_month,
            total_likes=engagement_data.get('total_likes', 0),
            total_comments=engagement_data.get('total_comments', 0),
            total_shares=engagement_data.get('total_shares', 0),
            total_views=engagement_data.get('total_views', 0),
            avg_engagement_rate=avg_engagement_rate,
            avg_likes_per_post=avg_likes_per_post,
            avg_comments_per_post=avg_comments_per_post,
            posting_frequency=posting_frequency,
            top_hashtags=json.dumps(engagement_data.get('top_hashtags', [])),
            top_topics=json.dumps(engagement_data.get('top_topics', [])),
            content_types=json.dumps(engagement_data.get('content_types', {})),
            sample_size=engagement_data.get('sample_size', 0),
            snapshot_date=datetime.utcnow()
        )

        self.session.add(snapshot)

        # Update competitor's current stats
        competitor = self.get_competitor(competitor_id)
        if competitor:
            competitor.followers_count = followers_count
            competitor.connections_count = connections_count
            competitor.posts_count = posts_count
            competitor.avg_posting_frequency = posting_frequency
            competitor.avg_engagement_rate = avg_engagement_rate
            competitor.avg_likes_per_post = avg_likes_per_post
            competitor.avg_comments_per_post = avg_comments_per_post
            competitor.last_checked = datetime.utcnow()

        self.session.commit()

        logger.info(f"Recorded snapshot for competitor ID: {competitor_id}")
        return snapshot

    def get_snapshots(
        self,
        competitor_id: int,
        limit: int = 30,
        days: Optional[int] = None
    ) -> List[CompetitorSnapshot]:
        """
        Get historical snapshots for a competitor.

        Args:
            competitor_id: Competitor ID
            limit: Maximum number of snapshots to return
            days: Only return snapshots from last N days

        Returns:
            List of CompetitorSnapshot objects
        """
        query = self.session.query(CompetitorSnapshot).filter_by(
            competitor_id=competitor_id
        )

        if days:
            cutoff = datetime.utcnow() - timedelta(days=days)
            query = query.filter(CompetitorSnapshot.snapshot_date >= cutoff)

        return query.order_by(CompetitorSnapshot.snapshot_date.desc()).limit(limit).all()

    def get_trends(self, competitor_id: int, days: int = 30) -> Dict:
        """
        Analyze competitor trends over time.

        Args:
            competitor_id: Competitor ID
            days: Number of days to analyze

        Returns:
            Dictionary with trend analysis
        """
        snapshots = self.get_snapshots(competitor_id, days=days)

        if len(snapshots) < 2:
            return {
                'error': 'Not enough data',
                'snapshots_count': len(snapshots)
            }

        # Sort chronologically (oldest first)
        snapshots.sort(key=lambda x: x.snapshot_date)

        first = snapshots[0]
        latest = snapshots[-1]

        # Calculate changes
        follower_change = latest.followers_count - first.followers_count
        follower_change_pct = (follower_change / first.followers_count * 100) if first.followers_count > 0 else 0

        posts_change = latest.posts_count - first.posts_count
        avg_posting_freq = sum(s.posting_frequency for s in snapshots) / len(snapshots)

        engagement_trend = [s.avg_engagement_rate for s in snapshots]
        avg_engagement = sum(engagement_trend) / len(engagement_trend)

        return {
            'period_days': days,
            'snapshots_analyzed': len(snapshots),
            'follower_growth': {
                'absolute': follower_change,
                'percentage': round(follower_change_pct, 2),
                'start': first.followers_count,
                'end': latest.followers_count
            },
            'posting_activity': {
                'total_posts': posts_change,
                'avg_per_week': round(avg_posting_freq, 2),
                'recent_week': latest.posts_last_week,
                'recent_month': latest.posts_last_month
            },
            'engagement': {
                'avg_rate': round(avg_engagement, 2),
                'latest_rate': round(latest.avg_engagement_rate, 2),
                'avg_likes_per_post': round(latest.avg_likes_per_post, 2),
                'avg_comments_per_post': round(latest.avg_comments_per_post, 2)
            },
            'content_analysis': {
                'top_hashtags': json.loads(latest.top_hashtags) if latest.top_hashtags else [],
                'top_topics': json.loads(latest.top_topics) if latest.top_topics else [],
                'content_types': json.loads(latest.content_types) if latest.content_types else {}
            }
        }

    def compare_competitors(self, competitor_ids: List[int]) -> Dict:
        """
        Compare multiple competitors.

        Args:
            competitor_ids: List of competitor IDs to compare

        Returns:
            Comparison analysis
        """
        competitors = [self.get_competitor(cid) for cid in competitor_ids]
        competitors = [c for c in competitors if c]  # Filter out None

        if len(competitors) < 2:
            return {
                'error': 'Need at least 2 competitors to compare',
                'found': len(competitors)
            }

        comparison = {
            'competitors': [],
            'rankings': {}
        }

        # Collect data for each competitor
        for comp in competitors:
            comparison['competitors'].append({
                'id': comp.id,
                'name': comp.name,
                'followers': comp.followers_count,
                'posting_frequency': comp.avg_posting_frequency,
                'engagement_rate': comp.avg_engagement_rate,
                'likes_per_post': comp.avg_likes_per_post,
                'comments_per_post': comp.avg_comments_per_post
            })

        # Rank by different metrics
        comparison['rankings']['by_followers'] = sorted(
            comparison['competitors'],
            key=lambda x: x['followers'],
            reverse=True
        )

        comparison['rankings']['by_posting_frequency'] = sorted(
            comparison['competitors'],
            key=lambda x: x['posting_frequency'],
            reverse=True
        )

        comparison['rankings']['by_engagement'] = sorted(
            comparison['competitors'],
            key=lambda x: x['engagement_rate'],
            reverse=True
        )

        # Calculate averages
        comparison['averages'] = {
            'followers': sum(c['followers'] for c in comparison['competitors']) / len(competitors),
            'posting_frequency': sum(c['posting_frequency'] for c in comparison['competitors']) / len(competitors),
            'engagement_rate': sum(c['engagement_rate'] for c in comparison['competitors']) / len(competitors)
        }

        return comparison

    def get_recommendations(self, competitor_id: int, my_stats: Dict) -> List[str]:
        """
        Get recommendations based on competitor analysis.

        Args:
            competitor_id: Competitor ID
            my_stats: Dictionary with your own stats for comparison

        Returns:
            List of actionable recommendations
        """
        competitor = self.get_competitor(competitor_id)
        if not competitor:
            return ["Competitor not found"]

        recommendations = []

        # Posting frequency
        my_freq = my_stats.get('posting_frequency', 0)
        if competitor.avg_posting_frequency > my_freq * 1.5:
            recommendations.append(
                f"Increase posting frequency: {competitor.name} posts {competitor.avg_posting_frequency:.1f} times/week vs your {my_freq:.1f}"
            )

        # Engagement rate
        my_engagement = my_stats.get('engagement_rate', 0)
        if competitor.avg_engagement_rate > my_engagement * 1.3:
            recommendations.append(
                f"Improve engagement: {competitor.name} has {competitor.avg_engagement_rate:.1f}% engagement vs your {my_engagement:.1f}%"
            )

        # Content analysis
        latest_snapshot = self.get_snapshots(competitor_id, limit=1)
        if latest_snapshot:
            snap = latest_snapshot[0]
            if snap.top_hashtags:
                hashtags = json.loads(snap.top_hashtags)[:5]
                recommendations.append(
                    f"Consider using popular hashtags: {', '.join(['#' + h for h in hashtags])}"
                )

        return recommendations if recommendations else ["Performance is comparable to this competitor"]
