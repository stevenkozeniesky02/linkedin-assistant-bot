"""Connection Manager - LinkedIn Network Management and Quality Scoring

Manages LinkedIn connections, tracks engagement, and scores connection quality.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from database.models import Connection, Activity


class ConnectionManager:
    """Manage LinkedIn connections and network analytics"""

    def __init__(self, db_session: Session, config: dict):
        self.db = db_session
        self.config = config.get('connections', {})

        # Quality scoring weights
        self.engagement_weights = {
            'messages_sent': 2.0,
            'messages_received': 3.0,  # Higher weight for received messages
            'posts_engaged': 1.5,
            'mutual_connections': 0.5
        }

    def add_connection(self, name: str, profile_url: str,
                      title: str = None, company: str = None,
                      location: str = None, connection_source: str = "manual") -> Connection:
        """Add a new connection to the database

        Args:
            name: Full name of the connection
            profile_url: LinkedIn profile URL
            title: Job title
            company: Current company
            location: Location
            connection_source: How the connection was made (manual, automated, etc.)

        Returns:
            Connection object
        """
        # Check if connection already exists
        existing = self.db.query(Connection).filter(
            Connection.profile_url == profile_url
        ).first()

        if existing:
            # Update existing connection
            existing.name = name
            existing.title = title
            existing.company = company
            existing.location = location
            existing.updated_at = datetime.utcnow()
            self.db.commit()
            return existing

        # Create new connection
        connection = Connection(
            name=name,
            profile_url=profile_url,
            title=title,
            company=company,
            location=location,
            connection_date=datetime.utcnow(),
            connection_source=connection_source,
            is_active=True
        )

        self.db.add(connection)
        self.db.commit()

        # Calculate initial quality score
        self._update_quality_score(connection)

        return connection

    def update_engagement(self, profile_url: str,
                         messages_sent: int = 0,
                         messages_received: int = 0,
                         posts_engaged: int = 0) -> Optional[Connection]:
        """Update engagement metrics for a connection

        Args:
            profile_url: LinkedIn profile URL
            messages_sent: Number of messages sent to this connection
            messages_received: Number of messages received from this connection
            posts_engaged: Number of their posts we engaged with

        Returns:
            Updated Connection object or None if not found
        """
        connection = self.db.query(Connection).filter(
            Connection.profile_url == profile_url
        ).first()

        if not connection:
            return None

        # Update engagement metrics (increment)
        if messages_sent > 0:
            connection.messages_sent += messages_sent
        if messages_received > 0:
            connection.messages_received += messages_received
        if posts_engaged > 0:
            connection.posts_engaged += posts_engaged

        connection.last_interaction = datetime.utcnow()
        connection.updated_at = datetime.utcnow()

        self.db.commit()

        # Recalculate quality score
        self._update_quality_score(connection)

        return connection

    def _update_quality_score(self, connection: Connection):
        """Calculate and update quality score for a connection (0-10 scale)"""
        # Base score from engagement metrics
        engagement_score = (
            connection.messages_sent * self.engagement_weights['messages_sent'] +
            connection.messages_received * self.engagement_weights['messages_received'] +
            connection.posts_engaged * self.engagement_weights['posts_engaged'] +
            connection.mutual_connections * self.engagement_weights['mutual_connections']
        )

        # Normalize to 0-10 scale (using sigmoid-like function)
        # Cap at 10 for very high engagement
        quality_score = min(10.0, (engagement_score / 10) * 10)

        # Determine engagement level
        if quality_score >= 7.0:
            engagement_level = 'high'
        elif quality_score >= 4.0:
            engagement_level = 'medium'
        elif quality_score > 0:
            engagement_level = 'low'
        else:
            engagement_level = 'none'

        connection.quality_score = round(quality_score, 2)
        connection.engagement_level = engagement_level

        self.db.commit()

    def get_connection(self, profile_url: str) -> Optional[Connection]:
        """Get a connection by profile URL"""
        return self.db.query(Connection).filter(
            Connection.profile_url == profile_url
        ).first()

    def get_all_connections(self, active_only: bool = True) -> List[Connection]:
        """Get all connections

        Args:
            active_only: Only return active connections

        Returns:
            List of Connection objects
        """
        query = self.db.query(Connection)

        if active_only:
            query = query.filter(Connection.is_active == True)

        return query.order_by(desc(Connection.quality_score)).all()

    def get_top_connections(self, limit: int = 10,
                           min_quality_score: float = 0.0) -> List[Connection]:
        """Get top connections by quality score

        Args:
            limit: Maximum number of connections to return
            min_quality_score: Minimum quality score threshold

        Returns:
            List of top Connection objects
        """
        return self.db.query(Connection).filter(
            Connection.is_active == True,
            Connection.quality_score >= min_quality_score
        ).order_by(desc(Connection.quality_score)).limit(limit).all()

    def mark_target_audience(self, profile_url: str, is_target: bool = True,
                            notes: str = None) -> Optional[Connection]:
        """Mark a connection as target audience (relevant to your niche)

        Args:
            profile_url: LinkedIn profile URL
            is_target: Whether this is a target audience member
            notes: Optional notes about why they're target audience

        Returns:
            Updated Connection object or None if not found
        """
        connection = self.db.query(Connection).filter(
            Connection.profile_url == profile_url
        ).first()

        if not connection:
            return None

        connection.is_target_audience = is_target
        if notes:
            connection.notes = notes
        connection.updated_at = datetime.utcnow()

        self.db.commit()
        return connection

    def deactivate_connection(self, profile_url: str) -> Optional[Connection]:
        """Deactivate a connection (e.g., if they disconnected)

        Args:
            profile_url: LinkedIn profile URL

        Returns:
            Updated Connection object or None if not found
        """
        connection = self.db.query(Connection).filter(
            Connection.profile_url == profile_url
        ).first()

        if not connection:
            return None

        connection.is_active = False
        connection.updated_at = datetime.utcnow()

        self.db.commit()
        return connection

    def get_network_analytics(self, days_back: int = 30) -> Dict:
        """Get comprehensive network analytics

        Args:
            days_back: Number of days to analyze

        Returns:
            Dictionary with network analytics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        # Total connections
        total_connections = self.db.query(Connection).filter(
            Connection.is_active == True
        ).count()

        # Recent connections
        recent_connections = self.db.query(Connection).filter(
            Connection.connection_date >= cutoff_date,
            Connection.is_active == True
        ).count()

        # Average quality score
        avg_quality = self.db.query(func.avg(Connection.quality_score)).filter(
            Connection.is_active == True
        ).scalar() or 0.0

        # Engagement level breakdown
        engagement_breakdown = {
            'high': self.db.query(Connection).filter(
                Connection.is_active == True,
                Connection.engagement_level == 'high'
            ).count(),
            'medium': self.db.query(Connection).filter(
                Connection.is_active == True,
                Connection.engagement_level == 'medium'
            ).count(),
            'low': self.db.query(Connection).filter(
                Connection.is_active == True,
                Connection.engagement_level == 'low'
            ).count(),
            'none': self.db.query(Connection).filter(
                Connection.is_active == True,
                Connection.engagement_level == 'none'
            ).count()
        }

        # Target audience count
        target_audience_count = self.db.query(Connection).filter(
            Connection.is_active == True,
            Connection.is_target_audience == True
        ).count()

        # Top companies
        top_companies = self.db.query(
            Connection.company,
            func.count(Connection.id).label('count')
        ).filter(
            Connection.is_active == True,
            Connection.company != None
        ).group_by(Connection.company).order_by(desc('count')).limit(10).all()

        # Recent interactions
        recent_interactions = self.db.query(Connection).filter(
            Connection.is_active == True,
            Connection.last_interaction != None,
            Connection.last_interaction >= cutoff_date
        ).count()

        # Calculate growth rate
        total_days_tracked = self.db.query(
            func.julianday(func.max(Connection.connection_date)) -
            func.julianday(func.min(Connection.connection_date))
        ).scalar() or 1

        growth_rate = total_connections / max(total_days_tracked, 1)

        return {
            'status': 'success',
            'total_connections': total_connections,
            'recent_connections': recent_connections,
            'recent_period_days': days_back,
            'avg_quality_score': round(avg_quality, 2),
            'engagement_breakdown': engagement_breakdown,
            'target_audience_count': target_audience_count,
            'target_audience_percent': round(
                (target_audience_count / total_connections * 100) if total_connections > 0 else 0, 1
            ),
            'top_companies': [
                {'company': company, 'count': count}
                for company, count in top_companies
            ],
            'recent_interactions': recent_interactions,
            'growth_rate_per_day': round(growth_rate, 2),
            'total_days_tracked': int(total_days_tracked)
        }

    def get_connection_recommendations(self) -> Dict:
        """Get recommendations for improving network quality

        Returns:
            Dictionary with actionable recommendations
        """
        analytics = self.get_network_analytics(days_back=30)
        recommendations = []

        # Check engagement levels
        total = analytics['total_connections']
        none_engagement = analytics['engagement_breakdown']['none']

        if total > 0 and (none_engagement / total) > 0.5:
            recommendations.append({
                'priority': 'high',
                'category': 'engagement',
                'message': f'{none_engagement} connections ({round(none_engagement/total*100, 1)}%) have no engagement. Consider reaching out or engaging with their content.',
                'action': 'Start conversations or engage with posts from low-engagement connections'
            })

        # Check target audience percentage
        target_percent = analytics['target_audience_percent']
        if target_percent < 30 and total > 10:
            recommendations.append({
                'priority': 'medium',
                'category': 'targeting',
                'message': f'Only {target_percent}% of connections marked as target audience.',
                'action': 'Review connections and mark relevant professionals as target audience'
            })

        # Check average quality score
        avg_quality = analytics['avg_quality_score']
        if avg_quality < 3.0 and total > 5:
            recommendations.append({
                'priority': 'high',
                'category': 'quality',
                'message': f'Average connection quality score is low ({avg_quality}/10).',
                'action': 'Focus on building deeper relationships with existing connections'
            })

        # Check recent activity
        recent_interactions = analytics['recent_interactions']
        if recent_interactions < 5 and total > 20:
            recommendations.append({
                'priority': 'medium',
                'category': 'activity',
                'message': f'Only {recent_interactions} connections interacted with in the last 30 days.',
                'action': 'Increase engagement frequency with your network'
            })

        # Positive feedback
        if not recommendations:
            recommendations.append({
                'priority': 'info',
                'category': 'status',
                'message': 'Network health looks good!',
                'action': 'Continue maintaining quality connections and engagement'
            })

        return {
            'status': 'success',
            'recommendations': recommendations,
            'overall_score': min(10, avg_quality),
            'health_status': 'good' if avg_quality >= 5 else 'needs_improvement'
        }
