"""Safety Monitor - LinkedIn Activity Tracking and Ban Risk Prevention

Monitors LinkedIn activity, enforces rate limits, and prevents account bans.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from database.models import Activity, SafetyAlert

class SafetyMonitor:
    """Monitor LinkedIn activity for safety and ban prevention"""

    def __init__(self, db_session: Session, config: dict):
        self.db = db_session
        self.config = config.get('safety', {})

        # Default limits
        self.max_actions_per_hour = self.config.get('max_actions_per_hour', 10)
        self.max_actions_per_day = self.config.get('max_actions_per_day', 50)
        self.max_posts_per_day = self.config.get('max_posts_per_day', 3)
        self.max_comments_per_day = self.config.get('max_comments_per_day', 15)
        self.max_connection_requests_per_day = self.config.get('max_connection_requests_per_day', 10)

    def log_activity(self, action_type: str, target_type: str = None,
                     target_id: str = None, duration: float = 0,
                     success: bool = True, error: str = None) -> Activity:
        """Log a LinkedIn activity

        Args:
            action_type: Type of action (post, comment, like, view, connection_request)
            target_type: Type of target (post, profile, company)
            target_id: ID or URL of target
            duration: How long the action took in seconds
            success: Whether the action succeeded
            error: Error message if failed

        Returns:
            Activity object
        """
        # Calculate risk score
        risk_score = self._calculate_risk_score(action_type)

        activity = Activity(
            action_type=action_type,
            target_type=target_type,
            target_id=target_id,
            risk_score=risk_score,
            duration_seconds=duration,
            success=success,
            error_message=error
        )

        self.db.add(activity)
        self.db.commit()

        # Check if we should create alerts
        self._check_rate_limits()

        return activity

    def _calculate_risk_score(self, action_type: str) -> float:
        """Calculate risk score for an action (0-1 scale)"""
        # Higher risk actions get higher scores
        risk_weights = {
            'connection_request': 0.8,
            'message': 0.7,
            'post': 0.5,
            'comment': 0.4,
            'like': 0.2,
            'view': 0.1
        }
        return risk_weights.get(action_type, 0.3)

    def _check_rate_limits(self):
        """Check if rate limits are being approached and create alerts"""
        now = datetime.utcnow()

        # Check hourly limit
        hour_ago = now - timedelta(hours=1)
        hourly_count = self.db.query(Activity).filter(
            Activity.performed_at >= hour_ago,
            Activity.success == True
        ).count()

        if hourly_count >= self.max_actions_per_hour * 0.8:  # 80% threshold
            self._create_alert(
                alert_type='rate_limit_hourly',
                severity='medium' if hourly_count < self.max_actions_per_hour else 'high',
                message=f"Approaching hourly action limit: {hourly_count}/{self.max_actions_per_hour}",
                risk_score=hourly_count / self.max_actions_per_hour,
                recommended_action="Slow down activity. Consider pausing for 30-60 minutes."
            )

        # Check daily limit
        day_ago = now - timedelta(days=1)
        daily_count = self.db.query(Activity).filter(
            Activity.performed_at >= day_ago,
            Activity.success == True
        ).count()

        if daily_count >= self.max_actions_per_day * 0.8:  # 80% threshold
            self._create_alert(
                alert_type='rate_limit_daily',
                severity='medium' if daily_count < self.max_actions_per_day else 'high',
                message=f"Approaching daily action limit: {daily_count}/{self.max_actions_per_day}",
                risk_score=daily_count / self.max_actions_per_day,
                recommended_action="Consider stopping activity for today."
            )

    def _create_alert(self, alert_type: str, severity: str, message: str,
                     risk_score: float, recommended_action: str,
                     triggered_by: str = None):
        """Create a safety alert"""
        # Check if alert already exists and is unresolved
        existing = self.db.query(SafetyAlert).filter(
            SafetyAlert.alert_type == alert_type,
            SafetyAlert.resolved == False
        ).first()

        if existing:
            return  # Don't create duplicate alerts

        alert = SafetyAlert(
            alert_type=alert_type,
            severity=severity,
            message=message,
            risk_score=risk_score,
            recommended_action=recommended_action,
            triggered_by=triggered_by
        )

        self.db.add(alert)
        self.db.commit()

    def check_action_allowed(self, action_type: str) -> Dict:
        """Check if an action is allowed based on current limits

        Returns:
            Dict with 'allowed' bool and 'reason' string
        """
        now = datetime.utcnow()

        # Check hourly limit
        hour_ago = now - timedelta(hours=1)
        hourly_count = self.db.query(Activity).filter(
            Activity.performed_at >= hour_ago,
            Activity.success == True
        ).count()

        if hourly_count >= self.max_actions_per_hour:
            return {
                'allowed': False,
                'reason': f'Hourly limit reached ({hourly_count}/{self.max_actions_per_hour}). Wait until next hour.',
                'wait_minutes': 60
            }

        # Check daily limit
        day_ago = now - timedelta(days=1)
        daily_count = self.db.query(Activity).filter(
            Activity.performed_at >= day_ago,
            Activity.success == True
        ).count()

        if daily_count >= self.max_actions_per_day:
            return {
                'allowed': False,
                'reason': f'Daily limit reached ({daily_count}/{self.max_actions_per_day}). Wait until tomorrow.',
                'wait_hours': 24
            }

        # Check action-specific limits
        if action_type == 'post':
            posts_today = self.db.query(Activity).filter(
                Activity.performed_at >= day_ago,
                Activity.action_type == 'post',
                Activity.success == True
            ).count()

            if posts_today >= self.max_posts_per_day:
                return {
                    'allowed': False,
                    'reason': f'Daily post limit reached ({posts_today}/{self.max_posts_per_day}).',
                    'wait_hours': 24
                }

        elif action_type == 'comment':
            comments_today = self.db.query(Activity).filter(
                Activity.performed_at >= day_ago,
                Activity.action_type == 'comment',
                Activity.success == True
            ).count()

            if comments_today >= self.max_comments_per_day:
                return {
                    'allowed': False,
                    'reason': f'Daily comment limit reached ({comments_today}/{self.max_comments_per_day}).',
                    'wait_hours': 24
                }

        elif action_type == 'connection_request':
            requests_today = self.db.query(Activity).filter(
                Activity.performed_at >= day_ago,
                Activity.action_type == 'connection_request',
                Activity.success == True
            ).count()

            if requests_today >= self.max_connection_requests_per_day:
                return {
                    'allowed': False,
                    'reason': f'Daily connection request limit reached ({requests_today}/{self.max_connection_requests_per_day}).',
                    'wait_hours': 24
                }

        return {'allowed': True, 'reason': 'Action permitted'}

    def get_safety_status(self) -> Dict:
        """Get current safety status and metrics"""
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)

        # Activity counts
        hourly_count = self.db.query(Activity).filter(
            Activity.performed_at >= hour_ago
        ).count()

        daily_count = self.db.query(Activity).filter(
            Activity.performed_at >= day_ago
        ).count()

        weekly_count = self.db.query(Activity).filter(
            Activity.performed_at >= week_ago
        ).count()

        # Calculate utilization
        hourly_util = (hourly_count / self.max_actions_per_hour * 100) if self.max_actions_per_hour > 0 else 0
        daily_util = (daily_count / self.max_actions_per_day * 100) if self.max_actions_per_day > 0 else 0

        # Active alerts
        active_alerts = self.db.query(SafetyAlert).filter(
            SafetyAlert.resolved == False
        ).all()

        # Calculate overall risk score
        recent_activities = self.db.query(Activity).filter(
            Activity.performed_at >= day_ago
        ).all()

        avg_risk = sum(a.risk_score for a in recent_activities) / len(recent_activities) if recent_activities else 0

        # Determine status
        if hourly_util >= 100 or daily_util >= 100:
            status = 'limit_reached'
            status_color = 'red'
        elif hourly_util >= 80 or daily_util >= 80:
            status = 'warning'
            status_color = 'yellow'
        elif len(active_alerts) > 0:
            status = 'alerts_active'
            status_color = 'yellow'
        else:
            status = 'safe'
            status_color = 'green'

        return {
            'status': status,
            'status_color': status_color,
            'activity_counts': {
                'last_hour': hourly_count,
                'last_24h': daily_count,
                'last_7d': weekly_count
            },
            'limits': {
                'hourly_max': self.max_actions_per_hour,
                'daily_max': self.max_actions_per_day,
                'posts_daily_max': self.max_posts_per_day,
                'comments_daily_max': self.max_comments_per_day,
                'connections_daily_max': self.max_connection_requests_per_day
            },
            'utilization': {
                'hourly_percent': round(hourly_util, 1),
                'daily_percent': round(daily_util, 1)
            },
            'risk_score': round(avg_risk, 2),
            'active_alerts': len(active_alerts),
            'alert_details': [
                {
                    'type': a.alert_type,
                    'severity': a.severity,
                    'message': a.message,
                    'created': a.created_at.isoformat()
                }
                for a in active_alerts
            ]
        }

    def acknowledge_alert(self, alert_id: int):
        """Acknowledge a safety alert"""
        alert = self.db.query(SafetyAlert).filter(SafetyAlert.id == alert_id).first()
        if alert:
            alert.acknowledged = True
            alert.acknowledged_at = datetime.utcnow()
            self.db.commit()

    def resolve_alert(self, alert_id: int):
        """Resolve a safety alert"""
        alert = self.db.query(SafetyAlert).filter(SafetyAlert.id == alert_id).first()
        if alert:
            alert.resolved = True
            alert.resolved_at = datetime.utcnow()
            self.db.commit()
