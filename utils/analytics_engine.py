"""Advanced Analytics Engine for LinkedIn Assistant Bot

Provides comprehensive analytics and insights:
- Optimal posting time analysis
- Performance trend tracking
- Engagement rate analysis by various dimensions
- AI-powered insights and recommendations
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, Counter
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from database.models import Post, Analytics, Comment


class AnalyticsEngine:
    """Advanced analytics engine for post performance analysis"""

    def __init__(self, db_session: Session, ai_provider=None):
        """Initialize analytics engine

        Args:
            db_session: SQLAlchemy database session
            ai_provider: Optional AI provider for generating insights
        """
        self.db = db_session
        self.ai_provider = ai_provider

    def get_optimal_posting_times(self, days_back: int = 30) -> Dict:
        """Analyze when posts get best engagement

        Args:
            days_back: Number of days to look back for analysis

        Returns:
            Dictionary with optimal posting times and analysis
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        # Get all published posts with analytics
        posts = (
            self.db.query(Post, Analytics)
            .join(Analytics)
            .filter(
                and_(
                    Post.published == True,
                    Post.published_at >= cutoff_date,
                    Analytics.views > 0
                )
            )
            .all()
        )

        if not posts:
            return {
                "status": "insufficient_data",
                "message": "Not enough published posts to analyze",
                "recommendations": []
            }

        # Group by hour of day and day of week
        hourly_performance = defaultdict(lambda: {"total_engagement": 0, "count": 0, "avg_views": 0})
        daily_performance = defaultdict(lambda: {"total_engagement": 0, "count": 0, "avg_views": 0})

        for post, analytics in posts:
            hour = post.published_at.hour
            day = post.published_at.strftime("%A")

            total_engagement = analytics.likes + analytics.comments_count + analytics.shares

            # Hour stats
            hourly_performance[hour]["total_engagement"] += total_engagement
            hourly_performance[hour]["count"] += 1
            hourly_performance[hour]["avg_views"] += analytics.views

            # Day stats
            daily_performance[day]["total_engagement"] += total_engagement
            daily_performance[day]["count"] += 1
            daily_performance[day]["avg_views"] += analytics.views

        # Calculate averages
        hourly_avg = {}
        for hour, data in hourly_performance.items():
            avg_engagement = data["total_engagement"] / data["count"] if data["count"] > 0 else 0
            avg_views = data["avg_views"] / data["count"] if data["count"] > 0 else 0
            hourly_avg[hour] = {
                "avg_engagement": round(avg_engagement, 2),
                "avg_views": round(avg_views, 2),
                "post_count": data["count"]
            }

        daily_avg = {}
        for day, data in daily_performance.items():
            avg_engagement = data["total_engagement"] / data["count"] if data["count"] > 0 else 0
            avg_views = data["avg_views"] / data["count"] if data["count"] > 0 else 0
            daily_avg[day] = {
                "avg_engagement": round(avg_engagement, 2),
                "avg_views": round(avg_views, 2),
                "post_count": data["count"]
            }

        # Find best times
        best_hours = sorted(hourly_avg.items(), key=lambda x: x[1]["avg_engagement"], reverse=True)[:3]
        best_days = sorted(daily_avg.items(), key=lambda x: x[1]["avg_engagement"], reverse=True)[:3]

        return {
            "status": "success",
            "analysis_period_days": days_back,
            "total_posts_analyzed": len(posts),
            "best_hours": [
                {
                    "hour": f"{hour}:00",
                    "avg_engagement": data["avg_engagement"],
                    "avg_views": data["avg_views"],
                    "post_count": data["post_count"]
                }
                for hour, data in best_hours
            ],
            "best_days": [
                {
                    "day": day,
                    "avg_engagement": data["avg_engagement"],
                    "avg_views": data["avg_views"],
                    "post_count": data["post_count"]
                }
                for day, data in best_days
            ],
            "hourly_breakdown": hourly_avg,
            "daily_breakdown": daily_avg
        }

    def analyze_performance_trends(self, days_back: int = 90) -> Dict:
        """Track performance trends over time

        Args:
            days_back: Number of days to analyze

        Returns:
            Dictionary with trend analysis
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        posts = (
            self.db.query(Post, Analytics)
            .join(Analytics)
            .filter(
                and_(
                    Post.published == True,
                    Post.published_at >= cutoff_date
                )
            )
            .order_by(Post.published_at)
            .all()
        )

        if not posts:
            return {
                "status": "insufficient_data",
                "message": "Not enough published posts to analyze trends"
            }

        # Weekly trends
        weekly_data = defaultdict(lambda: {
            "views": 0, "likes": 0, "comments": 0, "shares": 0, "posts": 0
        })

        for post, analytics in posts:
            week_start = post.published_at - timedelta(days=post.published_at.weekday())
            week_key = week_start.strftime("%Y-%m-%d")

            weekly_data[week_key]["views"] += analytics.views
            weekly_data[week_key]["likes"] += analytics.likes
            weekly_data[week_key]["comments"] += analytics.comments_count
            weekly_data[week_key]["shares"] += analytics.shares
            weekly_data[week_key]["posts"] += 1

        # Calculate week-over-week changes
        weeks = sorted(weekly_data.keys())
        trends = []

        for i in range(len(weeks)):
            week = weeks[i]
            data = weekly_data[week]

            # Calculate averages
            avg_views = data["views"] / data["posts"] if data["posts"] > 0 else 0
            avg_engagement = (data["likes"] + data["comments"] + data["shares"]) / data["posts"] if data["posts"] > 0 else 0

            week_trend = {
                "week_starting": week,
                "posts_published": data["posts"],
                "total_views": data["views"],
                "total_engagement": data["likes"] + data["comments"] + data["shares"],
                "avg_views_per_post": round(avg_views, 2),
                "avg_engagement_per_post": round(avg_engagement, 2)
            }

            # Calculate change from previous week
            if i > 0:
                prev_week = weeks[i-1]
                prev_data = weekly_data[prev_week]
                prev_avg_views = prev_data["views"] / prev_data["posts"] if prev_data["posts"] > 0 else 0
                prev_avg_engagement = (prev_data["likes"] + prev_data["comments"] + prev_data["shares"]) / prev_data["posts"] if prev_data["posts"] > 0 else 0

                if prev_avg_views > 0:
                    views_change = ((avg_views - prev_avg_views) / prev_avg_views) * 100
                    week_trend["views_change_pct"] = round(views_change, 1)

                if prev_avg_engagement > 0:
                    engagement_change = ((avg_engagement - prev_avg_engagement) / prev_avg_engagement) * 100
                    week_trend["engagement_change_pct"] = round(engagement_change, 1)

            trends.append(week_trend)

        # Overall trend direction
        if len(trends) >= 2:
            first_week_engagement = trends[0]["avg_engagement_per_post"]
            last_week_engagement = trends[-1]["avg_engagement_per_post"]

            if last_week_engagement > first_week_engagement:
                trend_direction = "improving"
            elif last_week_engagement < first_week_engagement:
                trend_direction = "declining"
            else:
                trend_direction = "stable"
        else:
            trend_direction = "insufficient_data"

        return {
            "status": "success",
            "analysis_period_days": days_back,
            "total_posts": len(posts),
            "weekly_trends": trends,
            "overall_trend": trend_direction
        }

    def analyze_content_performance(self) -> Dict:
        """Analyze performance by content attributes (tone, length, topic)

        Returns:
            Dictionary with content performance breakdown
        """
        posts = (
            self.db.query(Post, Analytics)
            .join(Analytics)
            .filter(Post.published == True)
            .all()
        )

        if not posts:
            return {
                "status": "insufficient_data",
                "message": "No published posts to analyze"
            }

        # Group by tone
        tone_performance = defaultdict(lambda: {"views": [], "engagement": [], "count": 0})
        length_performance = defaultdict(lambda: {"views": [], "engagement": [], "count": 0})
        topic_performance = defaultdict(lambda: {"views": [], "engagement": [], "count": 0})

        for post, analytics in posts:
            total_engagement = analytics.likes + analytics.comments_count + analytics.shares

            if post.tone:
                tone_performance[post.tone]["views"].append(analytics.views)
                tone_performance[post.tone]["engagement"].append(total_engagement)
                tone_performance[post.tone]["count"] += 1

            if post.length:
                length_performance[post.length]["views"].append(analytics.views)
                length_performance[post.length]["engagement"].append(total_engagement)
                length_performance[post.length]["count"] += 1

            if post.topic:
                topic_performance[post.topic]["views"].append(analytics.views)
                topic_performance[post.topic]["engagement"].append(total_engagement)
                topic_performance[post.topic]["count"] += 1

        # Calculate averages
        def calc_avg(data_dict):
            result = {}
            for key, data in data_dict.items():
                avg_views = sum(data["views"]) / len(data["views"]) if data["views"] else 0
                avg_engagement = sum(data["engagement"]) / len(data["engagement"]) if data["engagement"] else 0
                engagement_rate = (avg_engagement / avg_views * 100) if avg_views > 0 else 0

                result[key] = {
                    "post_count": data["count"],
                    "avg_views": round(avg_views, 2),
                    "avg_engagement": round(avg_engagement, 2),
                    "engagement_rate": round(engagement_rate, 2)
                }
            return result

        tone_avg = calc_avg(tone_performance)
        length_avg = calc_avg(length_performance)
        topic_avg = calc_avg(topic_performance)

        # Find best performers
        best_tone = max(tone_avg.items(), key=lambda x: x[1]["avg_engagement"]) if tone_avg else None
        best_length = max(length_avg.items(), key=lambda x: x[1]["avg_engagement"]) if length_avg else None
        best_topics = sorted(topic_avg.items(), key=lambda x: x[1]["avg_engagement"], reverse=True)[:5]

        return {
            "status": "success",
            "total_posts": len(posts),
            "by_tone": tone_avg,
            "by_length": length_avg,
            "by_topic": topic_avg,
            "top_performers": {
                "best_tone": {
                    "tone": best_tone[0],
                    "stats": best_tone[1]
                } if best_tone else None,
                "best_length": {
                    "length": best_length[0],
                    "stats": best_length[1]
                } if best_length else None,
                "top_topics": [
                    {
                        "topic": topic,
                        "stats": stats
                    }
                    for topic, stats in best_topics
                ]
            }
        }

    def calculate_engagement_rates(self) -> Dict:
        """Calculate various engagement rate metrics

        Returns:
            Dictionary with engagement rate analysis
        """
        posts = (
            self.db.query(Post, Analytics)
            .join(Analytics)
            .filter(
                and_(
                    Post.published == True,
                    Analytics.views > 0
                )
            )
            .all()
        )

        if not posts:
            return {
                "status": "insufficient_data",
                "message": "No posts with view data to analyze"
            }

        total_views = 0
        total_likes = 0
        total_comments = 0
        total_shares = 0
        total_profile_views = 0
        engagement_rates = []

        for post, analytics in posts:
            total_views += analytics.views
            total_likes += analytics.likes
            total_comments += analytics.comments_count
            total_shares += analytics.shares
            total_profile_views += analytics.profile_views

            # Calculate individual post engagement rate
            total_engagement = analytics.likes + analytics.comments_count + analytics.shares
            if analytics.views > 0:
                rate = (total_engagement / analytics.views) * 100
                engagement_rates.append(rate)

        # Overall metrics
        total_engagement = total_likes + total_comments + total_shares
        overall_engagement_rate = (total_engagement / total_views * 100) if total_views > 0 else 0
        avg_engagement_rate = sum(engagement_rates) / len(engagement_rates) if engagement_rates else 0

        # Breakdown by engagement type
        like_rate = (total_likes / total_views * 100) if total_views > 0 else 0
        comment_rate = (total_comments / total_views * 100) if total_views > 0 else 0
        share_rate = (total_shares / total_views * 100) if total_views > 0 else 0
        profile_click_rate = (total_profile_views / total_views * 100) if total_views > 0 else 0

        return {
            "status": "success",
            "total_posts": len(posts),
            "overall_metrics": {
                "total_views": total_views,
                "total_engagement": total_engagement,
                "total_likes": total_likes,
                "total_comments": total_comments,
                "total_shares": total_shares,
                "total_profile_views": total_profile_views
            },
            "engagement_rates": {
                "overall_rate": round(overall_engagement_rate, 2),
                "average_rate": round(avg_engagement_rate, 2),
                "like_rate": round(like_rate, 2),
                "comment_rate": round(comment_rate, 2),
                "share_rate": round(share_rate, 2),
                "profile_click_rate": round(profile_click_rate, 2)
            },
            "benchmarks": {
                "excellent": "Above 5%",
                "good": "3-5%",
                "average": "1-3%",
                "needs_improvement": "Below 1%",
                "your_status": self._get_engagement_status(overall_engagement_rate)
            }
        }

    def _get_engagement_status(self, rate: float) -> str:
        """Determine engagement status based on rate"""
        if rate >= 5:
            return "excellent"
        elif rate >= 3:
            return "good"
        elif rate >= 1:
            return "average"
        else:
            return "needs_improvement"

    def analyze_comment_activity(self, days_back: int = 30) -> Dict:
        """Analyze commenting activity and engagement

        Args:
            days_back: Number of days to analyze

        Returns:
            Dictionary with comment activity analysis
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        # Get all comments
        all_comments = self.db.query(Comment).all()
        recent_comments = self.db.query(Comment).filter(
            Comment.created_at >= cutoff_date
        ).all()

        if not all_comments:
            return {
                "status": "no_data",
                "message": "No comments found"
            }

        # Calculate statistics
        total_comments = len(all_comments)
        recent_count = len(recent_comments)
        published_comments = [c for c in all_comments if c.published]
        recent_published = [c for c in recent_comments if c.published]

        # Analyze by tone
        tone_breakdown = defaultdict(int)
        for comment in all_comments:
            if comment.tone:
                tone_breakdown[comment.tone] += 1

        # Calculate publish rate
        publish_rate = (len(published_comments) / total_comments * 100) if total_comments > 0 else 0
        recent_publish_rate = (len(recent_published) / recent_count * 100) if recent_count > 0 else 0

        # Analyze target authors (who we're engaging with)
        target_authors = defaultdict(int)
        for comment in published_comments:
            if comment.target_post_author:
                target_authors[comment.target_post_author] += 1

        top_authors = sorted(target_authors.items(), key=lambda x: x[1], reverse=True)[:10]

        # Daily activity
        daily_activity = defaultdict(int)
        for comment in recent_comments:
            day = comment.created_at.strftime("%Y-%m-%d")
            daily_activity[day] += 1

        avg_daily = sum(daily_activity.values()) / len(daily_activity) if daily_activity else 0

        return {
            "status": "success",
            "analysis_period_days": days_back,
            "total_comments": total_comments,
            "recent_comments": recent_count,
            "published_comments": len(published_comments),
            "recent_published": len(recent_published),
            "publish_rate": round(publish_rate, 1),
            "recent_publish_rate": round(recent_publish_rate, 1),
            "avg_daily_comments": round(avg_daily, 1),
            "by_tone": dict(tone_breakdown),
            "top_authors_engaged": [
                {"author": author, "comment_count": count}
                for author, count in top_authors
            ]
        }

    def get_complete_dashboard(self, days_back: int = 30) -> Dict:
        """Get complete analytics dashboard data

        Args:
            days_back: Number of days for time-based analysis

        Returns:
            Complete dashboard data
        """
        return {
            "optimal_times": self.get_optimal_posting_times(days_back),
            "performance_trends": self.analyze_performance_trends(days_back),
            "content_performance": self.analyze_content_performance(),
            "engagement_rates": self.calculate_engagement_rates(),
            "comment_activity": self.analyze_comment_activity(days_back)
        }

    def generate_ai_insights(self, dashboard_data: Dict) -> List[str]:
        """Generate AI-powered insights from analytics data

        Args:
            dashboard_data: Complete dashboard data

        Returns:
            List of actionable insights
        """
        if not self.ai_provider:
            return [
                "AI insights require an AI provider to be configured",
                "Set up OpenAI, Anthropic, Gemini, or Local LLM to get personalized recommendations"
            ]

        # Build context for AI
        insights_prompt = f"""Analyze this LinkedIn performance data and provide 5-7 actionable insights and recommendations:

OPTIMAL POSTING TIMES:
{self._format_posting_times(dashboard_data.get('optimal_times', {}))}

PERFORMANCE TRENDS:
{self._format_trends(dashboard_data.get('performance_trends', {}))}

CONTENT PERFORMANCE:
{self._format_content_performance(dashboard_data.get('content_performance', {}))}

ENGAGEMENT RATES:
{self._format_engagement_rates(dashboard_data.get('engagement_rates', {}))}

Provide specific, actionable insights that will help improve LinkedIn performance. Focus on:
1. What's working well (double down on these)
2. What's not working (what to change)
3. Specific recommendations for improvement
4. Content strategy suggestions
5. Posting schedule optimization

Return 5-7 bullet points, each starting with a dash (-). Be specific and actionable."""

        try:
            # Generate insights using AI
            insights_text = self.ai_provider.generate_comment(
                post_content=insights_prompt,
                tone="analytical",
                max_length=1000
            )

            # Parse into list
            insights = [
                line.strip().lstrip('-').strip()
                for line in insights_text.split('\n')
                if line.strip() and line.strip().startswith('-')
            ]

            return insights if insights else ["Unable to generate insights from AI response"]

        except Exception as e:
            return [f"Error generating AI insights: {str(e)}"]

    def _format_posting_times(self, data: Dict) -> str:
        """Format posting times data for AI prompt"""
        if data.get("status") != "success":
            return "Insufficient data"

        best_hours = data.get("best_hours", [])
        best_days = data.get("best_days", [])

        hours_str = "\n".join([
            f"  - {h['hour']}: {h['avg_engagement']} avg engagement ({h['post_count']} posts)"
            for h in best_hours[:3]
        ])

        days_str = "\n".join([
            f"  - {d['day']}: {d['avg_engagement']} avg engagement ({d['post_count']} posts)"
            for d in best_days[:3]
        ])

        return f"Best hours:\n{hours_str}\n\nBest days:\n{days_str}"

    def _format_trends(self, data: Dict) -> str:
        """Format trends data for AI prompt"""
        if data.get("status") != "success":
            return "Insufficient data"

        trends = data.get("weekly_trends", [])[-4:]  # Last 4 weeks
        direction = data.get("overall_trend", "unknown")

        trends_str = "\n".join([
            f"  - Week of {t['week_starting']}: {t['avg_engagement_per_post']} avg engagement/post"
            + (f" ({t.get('engagement_change_pct', 0):+.1f}%)" if 'engagement_change_pct' in t else "")
            for t in trends
        ])

        return f"Overall trend: {direction}\n\nRecent weeks:\n{trends_str}"

    def _format_content_performance(self, data: Dict) -> str:
        """Format content performance data for AI prompt"""
        if data.get("status") != "success":
            return "Insufficient data"

        top = data.get("top_performers", {})
        best_tone = top.get("best_tone")
        best_length = top.get("best_length")
        top_topics = top.get("top_topics", [])[:3]

        result = ""
        if best_tone:
            result += f"Best tone: {best_tone['tone']} ({best_tone['stats']['avg_engagement']} avg engagement)\n"
        if best_length:
            result += f"Best length: {best_length['length']} ({best_length['stats']['avg_engagement']} avg engagement)\n"

        if top_topics:
            topics_str = "\n".join([
                f"  - {t['topic']}: {t['stats']['avg_engagement']} avg engagement"
                for t in top_topics
            ])
            result += f"\nTop topics:\n{topics_str}"

        return result

    def _format_engagement_rates(self, data: Dict) -> str:
        """Format engagement rates for AI prompt"""
        if data.get("status") != "success":
            return "Insufficient data"

        rates = data.get("engagement_rates", {})
        overall = rates.get("overall_rate", 0)
        status = data.get("benchmarks", {}).get("your_status", "unknown")

        return f"""Overall engagement rate: {overall}% ({status})
Like rate: {rates.get('like_rate', 0)}%
Comment rate: {rates.get('comment_rate', 0)}%
Share rate: {rates.get('share_rate', 0)}%"""
