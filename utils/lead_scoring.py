"""Lead Scoring Engine for Network Growth

Scores potential connections 0-100 based on multiple factors:
- Profile quality (completeness, relevance)
- Engagement history (likes, comments on your posts)
- Mutual connections (quality and quantity)
- Company targeting (priority companies)
- Activity level (recent vs dormant)
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database.models import Connection, Activity, Analytics


class LeadScoringEngine:
    """Score potential connections for targeted outreach"""

    def __init__(self, db_session: Session, config: dict):
        """
        Initialize Lead Scoring Engine

        Args:
            db_session: SQLAlchemy database session
            config: Configuration dictionary
        """
        self.db = db_session
        self.config = config
        self.growth_config = config.get('network_growth', {})
        self.user_profile = config.get('user_profile', {})

        # Scoring weights (total = 100)
        self.weights = {
            'profile_quality': 30,      # Title relevance, company, completeness
            'engagement_history': 25,    # Liked/commented on your posts
            'mutual_connections': 20,    # Quality and quantity of shared connections
            'company_targeting': 15,     # From priority company
            'activity_level': 10          # Recent activity vs dormant
        }

        # Target companies (high priority)
        self.target_companies = self.growth_config.get('target_companies', [])

        # Target titles/keywords
        self.target_titles = self.growth_config.get('target_titles', [])
        self.target_industries = self.growth_config.get('target_industries', [])

    def score_prospect(self, prospect: Dict) -> Dict:
        """
        Calculate comprehensive lead score for a prospect

        Args:
            prospect: Dictionary with prospect details
                - name: Full name
                - title: Job title
                - company: Company name
                - industry: Industry
                - location: Location
                - profile_url: LinkedIn profile URL
                - mutual_connections: Number of mutual connections
                - mutual_connection_names: List of mutual connection names (optional)
                - has_profile_photo: Boolean
                - connection_count: Their total connections (if available)
                - recent_activity: Last post/activity date (if available)

        Returns:
            Dictionary with score breakdown and total score
        """
        scores = {
            'profile_quality': self._score_profile_quality(prospect),
            'engagement_history': self._score_engagement_history(prospect),
            'mutual_connections': self._score_mutual_connections(prospect),
            'company_targeting': self._score_company_targeting(prospect),
            'activity_level': self._score_activity_level(prospect)
        }

        # Calculate weighted total score (0-100)
        total_score = sum(
            scores[category] * (self.weights[category] / 100)
            for category in scores
        )

        # Add metadata
        result = {
            'total_score': round(total_score, 1),
            'scores_breakdown': scores,
            'weights_used': self.weights,
            'priority': self._get_priority_tier(total_score),
            'recommendation': self._get_recommendation(total_score, scores)
        }

        return result

    def _score_profile_quality(self, prospect: Dict) -> float:
        """
        Score profile quality (0-100)

        Factors:
        - Has profile photo: +10
        - Title relevance: 0-40
        - Company quality: 0-30
        - Profile completeness indicators: 0-20
        """
        score = 0.0

        # Has profile photo (+10)
        if prospect.get('has_profile_photo', True):
            score += 10

        # Title relevance (0-40)
        title = (prospect.get('title') or '').lower()
        if title:
            # Exact match with target titles
            if any(target.lower() in title for target in self.target_titles):
                score += 40
            # Keywords from your profile (related fields)
            elif any(keyword.lower() in title for keyword in self.user_profile.get('interests', [])):
                score += 20
            # Has a professional title at all
            elif len(title) > 5:
                score += 10

        # Company quality (0-30)
        company = prospect.get('company', '')
        if company:
            # Is a known company (not empty)
            score += 10
            # Has connections > 500 (indicates real company)
            if prospect.get('connection_count', 0) > 500:
                score += 10
            # Company name length (not generic)
            if len(company) > 3:
                score += 10

        # Profile completeness indicators (0-20)
        if prospect.get('location'):
            score += 5
        if prospect.get('industry'):
            score += 5
        if prospect.get('connection_count', 0) > 100:
            score += 10

        return min(score, 100.0)

    def _score_engagement_history(self, prospect: Dict) -> float:
        """
        Score based on past engagement with your content (0-100)

        Checks database for:
        - Likes on your posts
        - Comments on your posts
        - Shares of your posts
        """
        score = 0.0

        profile_url = prospect.get('profile_url')
        if not profile_url:
            return score

        # Check Activity table for engagement from this profile
        # Look for activities where target_id matches their profile
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        # Count likes from this person
        likes = self.db.query(Activity).filter(
            Activity.action_type == 'received_like',
            Activity.target_id == profile_url,
            Activity.performed_at >= thirty_days_ago
        ).count()

        # Count comments from this person
        comments = self.db.query(Activity).filter(
            Activity.action_type == 'received_comment',
            Activity.target_id == profile_url,
            Activity.performed_at >= thirty_days_ago
        ).count()

        # Scoring
        # Each like: +5 points (max 25)
        score += min(likes * 5, 25)

        # Each comment: +15 points (max 60)
        score += min(comments * 15, 60)

        # Bonus for multiple types of engagement (+15)
        if likes > 0 and comments > 0:
            score += 15

        return min(score, 100.0)

    def _score_mutual_connections(self, prospect: Dict) -> float:
        """
        Score based on mutual connections (0-100)

        Factors:
        - Number of mutual connections
        - Quality of mutual connections (if names provided)
        """
        score = 0.0

        mutual_count = prospect.get('mutual_connections', 0)

        # Scoring based on count
        if mutual_count == 0:
            score = 0
        elif mutual_count == 1:
            score = 20
        elif mutual_count == 2:
            score = 35
        elif mutual_count <= 5:
            score = 50
        elif mutual_count <= 10:
            score = 70
        else:
            score = 85

        # Quality bonus (if we know who the mutual connections are)
        mutual_names = prospect.get('mutual_connection_names', [])
        if mutual_names:
            # Check if any are high-quality connections in our database
            high_quality_mutuals = 0
            for name in mutual_names:
                conn = self.db.query(Connection).filter(
                    Connection.name.ilike(f"%{name}%"),
                    Connection.quality_score >= 7.0  # High quality connection
                ).first()
                if conn:
                    high_quality_mutuals += 1

            # Bonus: +5 points per high-quality mutual (max +15)
            score += min(high_quality_mutuals * 5, 15)

        return min(score, 100.0)

    def _score_company_targeting(self, prospect: Dict) -> float:
        """
        Score based on company targeting (0-100)

        Checks if prospect works at a target company or in target industry
        """
        score = 0.0

        company = prospect.get('company', '')
        industry = prospect.get('industry', '')

        # Target company match (+70)
        if company and any(target.lower() in company.lower() for target in self.target_companies):
            score += 70

        # Target industry match (+40)
        if industry and any(target.lower() in industry.lower() for target in self.target_industries):
            score += 40

        # Bonus for both (+30)
        if score >= 70:  # Has both company and industry match
            score += 30

        return min(score, 100.0)

    def _score_activity_level(self, prospect: Dict) -> float:
        """
        Score based on activity level (0-100)

        Recent activity = higher score (more likely to respond)
        Dormant account = lower score
        """
        score = 0.0

        recent_activity = prospect.get('recent_activity')
        if not recent_activity:
            # No activity data - assume average
            return 50.0

        # Calculate days since last activity
        if isinstance(recent_activity, str):
            try:
                recent_activity = datetime.fromisoformat(recent_activity)
            except:
                return 50.0

        days_ago = (datetime.utcnow() - recent_activity).days

        # Scoring by recency
        if days_ago <= 1:
            score = 100  # Posted within last day
        elif days_ago <= 3:
            score = 90
        elif days_ago <= 7:
            score = 80
        elif days_ago <= 14:
            score = 70
        elif days_ago <= 30:
            score = 60
        elif days_ago <= 90:
            score = 40
        else:
            score = 20  # Dormant account (90+ days)

        return score

    def _get_priority_tier(self, total_score: float) -> str:
        """
        Get priority tier based on total score

        Args:
            total_score: Total score (0-100)

        Returns:
            Priority tier: critical, high, medium, low, ignore
        """
        if total_score >= 80:
            return 'critical'  # Top prospects - reach out immediately
        elif total_score >= 60:
            return 'high'      # Strong prospects - prioritize
        elif total_score >= 40:
            return 'medium'    # Worth connecting with
        elif total_score >= 20:
            return 'low'       # Low priority
        else:
            return 'ignore'    # Not worth the effort

    def _get_recommendation(self, total_score: float, scores: Dict) -> str:
        """
        Get actionable recommendation based on score breakdown

        Args:
            total_score: Total lead score
            scores: Score breakdown by category

        Returns:
            Recommendation string
        """
        if total_score >= 80:
            return "🔥 Hot lead! Send personalized connection request ASAP"
        elif total_score >= 60:
            if scores['engagement_history'] >= 50:
                return "💎 Has engaged with your content - mention this in your message"
            elif scores['mutual_connections'] >= 70:
                return "🤝 Strong mutual connections - ask for introduction"
            elif scores['company_targeting'] >= 70:
                return "🎯 Target company employee - personalize around their company"
            else:
                return "✅ High-quality prospect - send personalized request"
        elif total_score >= 40:
            return "📝 Worth connecting - use standard personalized template"
        elif total_score >= 20:
            return "⏸️  Low priority - consider waiting for engagement first"
        else:
            return "⛔ Not recommended - score too low"

    def batch_score_prospects(self, prospects: List[Dict]) -> List[Dict]:
        """
        Score multiple prospects and return sorted by score

        Args:
            prospects: List of prospect dictionaries

        Returns:
            List of prospects with scores, sorted by total_score descending
        """
        scored_prospects = []

        for prospect in prospects:
            score_result = self.score_prospect(prospect)
            prospect_with_score = {
                **prospect,
                **score_result
            }
            scored_prospects.append(prospect_with_score)

        # Sort by total_score descending
        scored_prospects.sort(key=lambda x: x['total_score'], reverse=True)

        return scored_prospects

    def get_score_stats(self, prospects: List[Dict]) -> Dict:
        """
        Get statistics on a batch of scored prospects

        Args:
            prospects: List of prospects with scores

        Returns:
            Dictionary with statistics
        """
        if not prospects:
            return {'error': 'No prospects provided'}

        scores = [p.get('total_score', 0) for p in prospects]

        return {
            'total_prospects': len(prospects),
            'average_score': round(sum(scores) / len(scores), 1),
            'highest_score': max(scores),
            'lowest_score': min(scores),
            'critical_priority': len([p for p in prospects if p.get('priority') == 'critical']),
            'high_priority': len([p for p in prospects if p.get('priority') == 'high']),
            'medium_priority': len([p for p in prospects if p.get('priority') == 'medium']),
            'low_priority': len([p for p in prospects if p.get('priority') == 'low']),
            'ignore': len([p for p in prospects if p.get('priority') == 'ignore'])
        }
