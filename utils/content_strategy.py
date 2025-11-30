"""
Content Strategy Analyzer - Researches and recommends optimal content strategies

Features:
- Best performing content types analysis (how-to, insights, stories, etc.)
- Optimal posting times based on engagement data
- Topic trend analysis
- Industry-specific content recommendations
- A/B testing for content formats
- Engagement pattern analysis
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta, time as datetime_time
from collections import defaultdict, Counter
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
import statistics

logger = logging.getLogger(__name__)


class ContentStrategyAnalyzer:
    """
    Analyzes content performance and provides strategic recommendations.
    """

    def __init__(self, db_session: Session, config: dict, ai_client=None):
        self.db = db_session
        self.config = config
        self.ai_client = ai_client
        self.user_industry = config.get('user_profile', {}).get('industry', 'Technology')
        self.user_topics = config.get('content', {}).get('topics', [])

        # Content type definitions
        self.content_types = {
            'insight': ['think', 'perspective', 'opinion', 'insight', 'observation'],
            'achievement': ['proud', 'excited', 'achieved', 'milestone', 'success'],
            'question': ['?', 'what do you think', 'how do you', 'would you'],
            'how-to': ['how to', 'guide', 'tutorial', 'steps', 'learn'],
            'story': ['story', 'experience', 'journey', 'lesson learned'],
            'list': ['top', 'best', 'ways to', 'things', 'tips'],
            'announcement': ['announcing', 'excited to share', 'happy to announce'],
            'motivational': ['motivation', 'inspire', 'success', 'growth mindset']
        }

        # Industry-specific topic recommendations
        self.industry_topics = {
            'Technology': [
                'emerging technologies', 'innovation', 'digital transformation',
                'best practices', 'case studies', 'lessons learned', 'career tips'
            ],
            'Artificial Intelligence': [
                'AI applications', 'machine learning insights', 'AI ethics',
                'model training', 'real-world AI', 'AI tools', 'future of AI'
            ],
            'Software Development': [
                'coding best practices', 'software architecture', 'debugging tips',
                'productivity hacks', 'tool recommendations', 'code reviews'
            ],
            'Data Science': [
                'data insights', 'analytics techniques', 'visualization tips',
                'statistical methods', 'data storytelling', 'tool comparisons'
            ],
            'Career Growth': [
                'career advancement', 'skill development', 'networking tips',
                'interview preparation', 'salary negotiation', 'leadership'
            ]
        }

    def analyze_best_performing_content(self,
                                       days_back: int = 90,
                                       min_posts: int = 5) -> Dict:
        """
        Analyze which content types and topics perform best.

        Returns comprehensive analysis of content performance.
        """
        logger.info(f"Analyzing content performance for last {days_back} days")

        try:
            from database.models import Post

            cutoff_date = datetime.utcnow() - timedelta(days=days_back)

            # Query posts with metrics
            posts = self.db.query(Post).filter(
                Post.created_at >= cutoff_date,
                Post.content.isnot(None)
            ).all()

            if len(posts) < min_posts:
                logger.warning(f"Not enough posts ({len(posts)}) for analysis")
                return self._get_default_recommendations()

            # Analyze by content type
            type_performance = self._analyze_by_content_type(posts)

            # Analyze by topic
            topic_performance = self._analyze_by_topic(posts)

            # Analyze by time of day
            time_performance = self._analyze_by_posting_time(posts)

            # Analyze by day of week
            day_performance = self._analyze_by_day_of_week(posts)

            # Analyze post length
            length_analysis = self._analyze_post_length(posts)

            # Overall metrics
            overall_metrics = self._calculate_overall_metrics(posts)

            return {
                'overall_metrics': overall_metrics,
                'content_types': type_performance,
                'topics': topic_performance,
                'posting_times': time_performance,
                'days_of_week': day_performance,
                'post_length': length_analysis,
                'recommendations': self._generate_strategic_recommendations(
                    type_performance, topic_performance, time_performance,
                    day_performance, length_analysis
                ),
                'analyzed_posts': len(posts),
                'date_range': f"{cutoff_date.strftime('%Y-%m-%d')} to {datetime.utcnow().strftime('%Y-%m-%d')}"
            }

        except Exception as e:
            logger.error(f"Error analyzing content performance: {e}")
            return self._get_default_recommendations()

    def _analyze_by_content_type(self, posts: List) -> Dict:
        """Analyze performance by content type."""
        type_metrics = defaultdict(lambda: {
            'count': 0,
            'total_views': 0,
            'total_reactions': 0,
            'total_comments': 0,
            'total_shares': 0,
            'engagement_scores': []
        })

        for post in posts:
            content_type = self._classify_content_type(post.content)
            engagement = self._calculate_engagement_score(post)

            # Get metrics from Analytics relationship
            if post.analytics:
                views = post.analytics.views or 0
                reactions = post.analytics.likes or 0
                comments = post.analytics.comments_count or 0
                shares = post.analytics.shares or 0
            else:
                views = reactions = comments = shares = 0

            type_metrics[content_type]['count'] += 1
            type_metrics[content_type]['total_views'] += views
            type_metrics[content_type]['total_reactions'] += reactions
            type_metrics[content_type]['total_comments'] += comments
            type_metrics[content_type]['total_shares'] += shares
            type_metrics[content_type]['engagement_scores'].append(engagement)

        # Calculate averages and sort
        results = []
        for content_type, metrics in type_metrics.items():
            if metrics['count'] > 0:
                avg_engagement = statistics.mean(metrics['engagement_scores'])
                results.append({
                    'type': content_type,
                    'count': metrics['count'],
                    'avg_views': metrics['total_views'] / metrics['count'],
                    'avg_reactions': metrics['total_reactions'] / metrics['count'],
                    'avg_comments': metrics['total_comments'] / metrics['count'],
                    'avg_shares': metrics['total_shares'] / metrics['count'],
                    'avg_engagement': avg_engagement,
                    'performance_score': avg_engagement * (1 + (metrics['count'] / 10))
                })

        results.sort(key=lambda x: x['performance_score'], reverse=True)
        return {'types': results, 'best_type': results[0]['type'] if results else 'insight'}

    def _classify_content_type(self, content: str) -> str:
        """Classify a post into a content type."""
        if not content:
            return 'other'

        content_lower = content.lower()

        # Check each content type
        for content_type, keywords in self.content_types.items():
            if any(keyword in content_lower for keyword in keywords):
                return content_type

        return 'other'

    def _calculate_engagement_score(self, post) -> float:
        """Calculate weighted engagement score for a post."""
        # Get metrics from Analytics relationship
        if post.analytics:
            views = post.analytics.views or 0
            reactions = post.analytics.likes or 0
            comments = post.analytics.comments_count or 0
            shares = post.analytics.shares or 0
        else:
            views = reactions = comments = shares = 0

        # Weighted scoring: comments > shares > reactions > views
        score = (views * 0.1) + (reactions * 1.0) + (comments * 3.0) + (shares * 2.0)
        return score

    def _analyze_by_topic(self, posts: List) -> Dict:
        """Analyze performance by topic keywords."""
        # Get user's topics from config
        user_topics = self.user_topics or self.industry_topics.get(self.user_industry, [])

        topic_metrics = defaultdict(lambda: {
            'count': 0,
            'engagement_scores': []
        })

        for post in posts:
            content_lower = post.content.lower() if post.content else ''
            engagement = self._calculate_engagement_score(post)

            # Check which topics appear in the post
            found_topic = False
            for topic in user_topics:
                if topic.lower() in content_lower:
                    topic_metrics[topic]['count'] += 1
                    topic_metrics[topic]['engagement_scores'].append(engagement)
                    found_topic = True

            if not found_topic:
                topic_metrics['general']['count'] += 1
                topic_metrics['general']['engagement_scores'].append(engagement)

        # Calculate averages
        results = []
        for topic, metrics in topic_metrics.items():
            if metrics['count'] > 0 and metrics['engagement_scores']:
                avg_engagement = statistics.mean(metrics['engagement_scores'])
                results.append({
                    'topic': topic,
                    'count': metrics['count'],
                    'avg_engagement': avg_engagement
                })

        results.sort(key=lambda x: x['avg_engagement'], reverse=True)
        return {'topics': results, 'best_topic': results[0]['topic'] if results else 'general'}

    def _analyze_by_posting_time(self, posts: List) -> Dict:
        """Analyze performance by time of day."""
        time_slots = {
            'early_morning': (5, 8),   # 5am-8am
            'morning': (8, 12),         # 8am-12pm
            'midday': (12, 14),         # 12pm-2pm
            'afternoon': (14, 17),      # 2pm-5pm
            'evening': (17, 21),        # 5pm-9pm
            'night': (21, 24)           # 9pm-12am
        }

        slot_metrics = defaultdict(lambda: {
            'count': 0,
            'engagement_scores': []
        })

        for post in posts:
            if not post.created_at:
                continue

            hour = post.created_at.hour
            engagement = self._calculate_engagement_score(post)

            # Find matching time slot
            for slot_name, (start, end) in time_slots.items():
                if start <= hour < end:
                    slot_metrics[slot_name]['count'] += 1
                    slot_metrics[slot_name]['engagement_scores'].append(engagement)
                    break

        # Calculate averages
        results = []
        for slot, metrics in slot_metrics.items():
            if metrics['count'] > 0 and metrics['engagement_scores']:
                avg_engagement = statistics.mean(metrics['engagement_scores'])
                results.append({
                    'time_slot': slot,
                    'count': metrics['count'],
                    'avg_engagement': avg_engagement
                })

        results.sort(key=lambda x: x['avg_engagement'], reverse=True)
        return {'time_slots': results, 'best_time': results[0]['time_slot'] if results else 'morning'}

    def _analyze_by_day_of_week(self, posts: List) -> Dict:
        """Analyze performance by day of week."""
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

        day_metrics = defaultdict(lambda: {
            'count': 0,
            'engagement_scores': []
        })

        for post in posts:
            if not post.created_at:
                continue

            day_name = day_names[post.created_at.weekday()]
            engagement = self._calculate_engagement_score(post)

            day_metrics[day_name]['count'] += 1
            day_metrics[day_name]['engagement_scores'].append(engagement)

        # Calculate averages
        results = []
        for day, metrics in day_metrics.items():
            if metrics['count'] > 0 and metrics['engagement_scores']:
                avg_engagement = statistics.mean(metrics['engagement_scores'])
                results.append({
                    'day': day,
                    'count': metrics['count'],
                    'avg_engagement': avg_engagement
                })

        results.sort(key=lambda x: x['avg_engagement'], reverse=True)
        return {'days': results, 'best_day': results[0]['day'] if results else 'Tuesday'}

    def _analyze_post_length(self, posts: List) -> Dict:
        """Analyze optimal post length."""
        length_buckets = {
            'short': (0, 500),      # < 500 chars
            'medium': (500, 1000),  # 500-1000 chars
            'long': (1000, 2000),   # 1000-2000 chars
            'very_long': (2000, 10000)  # > 2000 chars
        }

        length_metrics = defaultdict(lambda: {
            'count': 0,
            'engagement_scores': []
        })

        for post in posts:
            if not post.content:
                continue

            post_length = len(post.content)
            engagement = self._calculate_engagement_score(post)

            # Find matching length bucket
            for bucket_name, (min_len, max_len) in length_buckets.items():
                if min_len <= post_length < max_len:
                    length_metrics[bucket_name]['count'] += 1
                    length_metrics[bucket_name]['engagement_scores'].append(engagement)
                    break

        # Calculate averages
        results = []
        for bucket, metrics in length_metrics.items():
            if metrics['count'] > 0 and metrics['engagement_scores']:
                avg_engagement = statistics.mean(metrics['engagement_scores'])
                results.append({
                    'length_category': bucket,
                    'count': metrics['count'],
                    'avg_engagement': avg_engagement
                })

        results.sort(key=lambda x: x['avg_engagement'], reverse=True)
        return {'lengths': results, 'optimal_length': results[0]['length_category'] if results else 'medium'}

    def _calculate_overall_metrics(self, posts: List) -> Dict:
        """Calculate overall performance metrics."""
        total_views = 0
        total_reactions = 0
        total_comments = 0
        total_shares = 0

        for p in posts:
            if p.analytics:
                total_views += p.analytics.views or 0
                total_reactions += p.analytics.likes or 0
                total_comments += p.analytics.comments_count or 0
                total_shares += p.analytics.shares or 0

        count = len(posts)

        return {
            'total_posts': count,
            'avg_views': total_views / count if count > 0 else 0,
            'avg_reactions': total_reactions / count if count > 0 else 0,
            'avg_comments': total_comments / count if count > 0 else 0,
            'avg_shares': total_shares / count if count > 0 else 0,
            'total_engagement': total_views + total_reactions + total_comments + total_shares
        }

    def _generate_strategic_recommendations(self,
                                           type_perf: Dict,
                                           topic_perf: Dict,
                                           time_perf: Dict,
                                           day_perf: Dict,
                                           length_perf: Dict) -> List[str]:
        """Generate actionable strategic recommendations."""
        recommendations = []

        # Content type recommendation
        if type_perf['types']:
            best_type = type_perf['best_type']
            recommendations.append(
                f"Focus on '{best_type}' content - it performs best with your audience"
            )

        # Topic recommendation
        if topic_perf['topics']:
            best_topic = topic_perf['best_topic']
            recommendations.append(
                f"Posts about '{best_topic}' get the highest engagement"
            )

        # Timing recommendation
        if time_perf['time_slots']:
            best_time = time_perf['best_time']
            recommendations.append(
                f"Post during '{best_time}' for optimal engagement"
            )

        # Day recommendation
        if day_perf['days']:
            best_day = day_perf['best_day']
            recommendations.append(
                f"'{best_day}' posts tend to perform best"
            )

        # Length recommendation
        if length_perf['lengths']:
            optimal_length = length_perf['optimal_length']
            recommendations.append(
                f"'{optimal_length}' posts get the most engagement"
            )

        return recommendations

    def _get_default_recommendations(self) -> Dict:
        """Return default recommendations when not enough data."""
        return {
            'overall_metrics': {},
            'content_types': {'types': [], 'best_type': 'insight'},
            'topics': {'topics': [], 'best_topic': 'general'},
            'posting_times': {'time_slots': [], 'best_time': 'morning'},
            'days_of_week': {'days': [], 'best_day': 'Tuesday'},
            'post_length': {'lengths': [], 'optimal_length': 'medium'},
            'recommendations': [
                "Not enough data yet - continue posting consistently",
                "Try posting in the morning (8am-12pm)",
                "Aim for medium-length posts (500-1000 characters)",
                "Post on weekdays for professional content"
            ],
            'analyzed_posts': 0,
            'date_range': 'No data available'
        }

    def get_content_ideas(self,
                         industry: str = None,
                         num_ideas: int = 5) -> List[Dict]:
        """
        Generate content ideas based on industry and trends.

        Uses AI if available, otherwise returns template ideas.
        """
        industry = industry or self.user_industry

        if self.ai_client:
            return self._generate_ai_content_ideas(industry, num_ideas)
        else:
            return self._get_template_content_ideas(industry, num_ideas)

    def _generate_ai_content_ideas(self, industry: str, num_ideas: int) -> List[Dict]:
        """Generate content ideas using AI."""
        try:
            prompt = f"""Generate {num_ideas} LinkedIn post ideas for someone in the {industry} industry.

User topics of interest: {', '.join(self.user_topics)}

For each idea, provide:
1. Post type (insight, how-to, question, story, etc.)
2. Topic/angle
3. Brief description

Format each idea as:
TYPE: [type]
TOPIC: [topic]
DESCRIPTION: [description]
---"""

            response = self.ai_client.generate(prompt, max_tokens=500)

            # Parse response into structured ideas
            ideas = []
            idea_blocks = response.split('---')

            for block in idea_blocks[:num_ideas]:
                if not block.strip():
                    continue

                idea = {
                    'type': 'insight',
                    'topic': 'General',
                    'description': block.strip()
                }

                # Extract structured fields if present
                if 'TYPE:' in block:
                    type_match = block.split('TYPE:')[1].split('\n')[0].strip()
                    idea['type'] = type_match.lower()

                if 'TOPIC:' in block:
                    topic_match = block.split('TOPIC:')[1].split('\n')[0].strip()
                    idea['topic'] = topic_match

                if 'DESCRIPTION:' in block:
                    desc_match = block.split('DESCRIPTION:')[1].strip()
                    idea['description'] = desc_match

                ideas.append(idea)

            return ideas[:num_ideas]

        except Exception as e:
            logger.error(f"Error generating AI content ideas: {e}")
            return self._get_template_content_ideas(industry, num_ideas)

    def _get_template_content_ideas(self, industry: str, num_ideas: int) -> List[Dict]:
        """Get template content ideas based on industry."""
        templates = {
            'Technology': [
                {
                    'type': 'insight',
                    'topic': 'Emerging trends',
                    'description': 'Share your perspective on a new technology or trend'
                },
                {
                    'type': 'how-to',
                    'topic': 'Best practices',
                    'description': 'Teach something valuable you learned recently'
                },
                {
                    'type': 'story',
                    'topic': 'Lessons learned',
                    'description': 'Share a challenge you overcame and what you learned'
                },
                {
                    'type': 'question',
                    'topic': 'Community engagement',
                    'description': 'Ask your network about their experiences with a tool/technique'
                },
                {
                    'type': 'list',
                    'topic': 'Tool recommendations',
                    'description': 'Share your favorite tools or resources for your work'
                }
            ]
        }

        industry_templates = templates.get(industry, templates['Technology'])
        return industry_templates[:num_ideas]

    def get_posting_schedule_recommendation(self) -> Dict:
        """
        Get recommended posting schedule based on performance data.
        """
        analysis = self.analyze_best_performing_content(days_back=90)

        return {
            'recommended_days': [
                analysis['days_of_week']['best_day'],
                analysis['days_of_week']['days'][1]['day'] if len(analysis['days_of_week']['days']) > 1 else 'Thursday',
                analysis['days_of_week']['days'][2]['day'] if len(analysis['days_of_week']['days']) > 2 else 'Tuesday'
            ],
            'recommended_time': analysis['posting_times']['best_time'],
            'frequency': '2-3 times per week',
            'content_mix': {
                'primary_type': analysis['content_types']['best_type'],
                'secondary_types': [t['type'] for t in analysis['content_types']['types'][1:3]] if len(analysis['content_types']['types']) > 1 else []
            }
        }
