"""
Hashtag Research Engine - Analyzes and recommends optimal hashtags for LinkedIn posts

Features:
- Industry-specific hashtag discovery
- Trend analysis and popularity tracking
- Engagement metrics per hashtag
- AI-powered hashtag generation based on content
- Historical performance tracking
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
import re

logger = logging.getLogger(__name__)


class HashtagResearchEngine:
    """
    Researches and recommends optimal hashtags based on industry, content, and performance data.
    """

    def __init__(self, db_session: Session, config: dict, ai_client=None):
        self.db = db_session
        self.config = config
        self.ai_client = ai_client
        self.user_industry = config.get('user_profile', {}).get('industry', 'Technology')
        self.user_topics = config.get('content', {}).get('topics', [])

        # Industry-specific hashtag seeds
        self.industry_hashtags = {
            'Technology': [
                'technology', 'tech', 'innovation', 'digital', 'ai', 'machinelearning',
                'software', 'coding', 'programming', 'developer', 'opensource',
                'cloud', 'cybersecurity', 'data', 'analytics'
            ],
            'Artificial Intelligence': [
                'ai', 'artificialintelligence', 'machinelearning', 'deeplearning',
                'datascience', 'ml', 'nlp', 'computervision', 'automation',
                'neuralnetworks', 'aiethics', 'generativeai', 'llm'
            ],
            'Software Development': [
                'softwareengineering', 'coding', 'programming', 'developer',
                'webdev', 'frontend', 'backend', 'fullstack', 'devops',
                'agile', 'opensource', 'github', 'python', 'javascript'
            ],
            'Data Science': [
                'datascience', 'bigdata', 'analytics', 'dataanalytics',
                'machinelearning', 'statistics', 'python', 'sql', 'datavisualization',
                'businessintelligence', 'predictiveanalytics', 'ai'
            ],
            'Career Growth': [
                'career', 'careeradvice', 'careerdevelopment', 'leadership',
                'professionaldevelopment', 'jobsearch', 'networking', 'personalbrand',
                'careertips', 'growthmindset', 'success', 'motivation'
            ],
            'Default': [
                'linkedin', 'professional', 'business', 'career', 'networking',
                'industry', 'insights', 'growth', 'innovation', 'future'
            ]
        }

    def get_industry_hashtags(self, industry: str = None) -> List[str]:
        """Get base hashtags for a specific industry."""
        industry = industry or self.user_industry
        return self.industry_hashtags.get(industry, self.industry_hashtags['Default'])

    def discover_trending_hashtags(self,
                                   industry: str = None,
                                   limit: int = 20,
                                   days_back: int = 30) -> List[Dict]:
        """
        Discover trending hashtags by researching online trends and analyzing historical data.

        Uses AI to research what's currently trending on LinkedIn for the given industry.
        """
        logger.info(f"Discovering trending hashtags for industry: {industry or self.user_industry}")

        # Get base hashtags for the industry
        base_hashtags = self.get_industry_hashtags(industry)

        # Research trending hashtags online using AI
        online_trending = self._research_online_trends(industry, limit=limit//2)

        # Analyze historical performance from our database
        historical_performance = self._analyze_historical_hashtag_performance(days_back)

        # Combine all sources
        trending = []
        seen_hashtags = set()

        # Priority 1: Online trending hashtags (most current)
        for hashtag_data in online_trending:
            if hashtag_data['hashtag'] not in seen_hashtags:
                trending.append(hashtag_data)
                seen_hashtags.add(hashtag_data['hashtag'])

        # Priority 2: High-performing historical hashtags
        for hashtag, metrics in historical_performance[:limit//3]:
            if hashtag not in seen_hashtags:
                trending.append({
                    'hashtag': hashtag,
                    'source': 'historical_data',
                    'avg_engagement': metrics['avg_engagement'],
                    'post_count': metrics['post_count'],
                    'trend_score': metrics['trend_score']
                })
                seen_hashtags.add(hashtag)

        # Priority 3: Industry-relevant hashtags (fallback)
        remaining = limit - len(trending)
        for hashtag in base_hashtags[:remaining]:
            if hashtag not in seen_hashtags:
                trending.append({
                    'hashtag': hashtag,
                    'source': 'industry_recommended',
                    'avg_engagement': 0,
                    'post_count': 0,
                    'trend_score': 50  # Default moderate score
                })
                seen_hashtags.add(hashtag)

        return trending[:limit]

    def _research_online_trends(self, industry: str = None, limit: int = 10) -> List[Dict]:
        """
        Research trending hashtags online using AI.

        Uses the AI client to research what's currently trending on LinkedIn
        for the given industry.
        """
        if not self.ai_client:
            logger.warning("No AI client available for online trend research")
            return []

        industry = industry or self.user_industry
        logger.info(f"Researching online trends for {industry} using AI")

        try:
            prompt = f"""Research and identify the top {limit} trending hashtags on LinkedIn right now for the {industry} industry.

For each hashtag, provide:
1. The hashtag (without #)
2. Why it's trending
3. Estimated trend score (0-100 based on current popularity)

Focus on hashtags that are:
- Currently popular and widely used
- Relevant to {industry} professionals
- Generating high engagement on LinkedIn posts
- Part of current industry conversations and trends

Return the results as a JSON array with this format:
[
  {{"hashtag": "hashtag_name", "reason": "why it's trending", "trend_score": 85}},
  ...
]

Only return the JSON array, no other text."""

            response = self.ai_client.generate_text(prompt)

            # Parse the JSON response
            import json
            # Extract JSON from response (handle cases where AI adds explanation text)
            response_text = response.strip()
            if '```json' in response_text:
                response_text = response_text.split('```json')[1].split('```')[0].strip()
            elif '```' in response_text:
                response_text = response_text.split('```')[1].split('```')[0].strip()

            trending_data = json.loads(response_text)

            # Format the results
            results = []
            for item in trending_data[:limit]:
                results.append({
                    'hashtag': item['hashtag'].lower().replace('#', ''),
                    'source': 'ai_research',
                    'trend_score': item.get('trend_score', 70),
                    'reason': item.get('reason', ''),
                    'avg_engagement': 0,  # Unknown for online research
                    'post_count': 0
                })

            logger.info(f"Successfully researched {len(results)} trending hashtags online")
            return results

        except Exception as e:
            logger.error(f"Error researching online trends: {e}")
            return []

    def _analyze_historical_hashtag_performance(self, days_back: int = 30) -> List[Tuple[str, Dict]]:
        """
        Analyze hashtag performance from historical post data in database.

        Returns list of (hashtag, metrics_dict) tuples sorted by performance.
        """
        try:
            from database.models import Post

            cutoff_date = datetime.utcnow() - timedelta(days=days_back)

            # Query posts with engagement metrics
            posts = self.db.query(Post).filter(
                Post.created_at >= cutoff_date,
                Post.content.isnot(None)
            ).all()

            # Extract hashtags and calculate metrics
            hashtag_metrics = defaultdict(lambda: {
                'total_engagement': 0,
                'post_count': 0,
                'views': 0,
                'reactions': 0,
                'comments': 0
            })

            for post in posts:
                hashtags = self._extract_hashtags(post.content)

                # Get metrics from Analytics relationship
                if post.analytics:
                    views = post.analytics.views or 0
                    likes = post.analytics.likes or 0
                    comments = post.analytics.comments_count or 0
                    shares = post.analytics.shares or 0
                    engagement = views + (likes * 2) + (comments * 3) + (shares * 4)
                else:
                    views = likes = comments = shares = engagement = 0

                for hashtag in hashtags:
                    hashtag_metrics[hashtag]['total_engagement'] += engagement
                    hashtag_metrics[hashtag]['post_count'] += 1
                    hashtag_metrics[hashtag]['views'] += views
                    hashtag_metrics[hashtag]['reactions'] += likes
                    hashtag_metrics[hashtag]['comments'] += comments

            # Calculate scores and sort
            scored_hashtags = []
            for hashtag, metrics in hashtag_metrics.items():
                if metrics['post_count'] >= 2:  # Require at least 2 posts
                    avg_engagement = metrics['total_engagement'] / metrics['post_count']

                    # Calculate average views/reactions/comments for more granular scoring
                    avg_views = metrics['views'] / metrics['post_count']
                    avg_reactions = metrics['reactions'] / metrics['post_count']
                    avg_comments = metrics['comments'] / metrics['post_count']

                    # Trend score: weighted combination of metrics
                    # If no analytics data exists, use frequency-based scoring
                    if avg_engagement == 0:
                        # Frequency-based: more usage = higher trend
                        trend_score = min(100, 40 + (metrics['post_count'] * 10))
                    else:
                        # Engagement-based: views * 0.1 + reactions * 2 + comments * 5 + frequency bonus
                        engagement_score = (avg_views * 0.1) + (avg_reactions * 2) + (avg_comments * 5)
                        frequency_bonus = metrics['post_count'] * 3
                        trend_score = min(100, engagement_score + frequency_bonus)

                    scored_hashtags.append((
                        hashtag,
                        {
                            'avg_engagement': avg_engagement,
                            'post_count': metrics['post_count'],
                            'trend_score': trend_score,
                            'total_views': metrics['views'],
                            'total_reactions': metrics['reactions'],
                            'total_comments': metrics['comments'],
                            'avg_views': avg_views,
                            'avg_reactions': avg_reactions,
                            'avg_comments': avg_comments
                        }
                    ))

            # Sort by trend score
            scored_hashtags.sort(key=lambda x: x[1]['trend_score'], reverse=True)
            return scored_hashtags

        except Exception as e:
            logger.warning(f"Could not analyze historical hashtag performance: {e}")
            return []

    def _extract_hashtags(self, content: str) -> List[str]:
        """Extract hashtags from post content."""
        if not content:
            return []

        # Find all hashtags (words starting with #)
        hashtags = re.findall(r'#(\w+)', content.lower())
        return hashtags

    def generate_hashtags_for_content(self,
                                     content: str,
                                     num_hashtags: int = 5,
                                     include_trending: bool = True) -> List[str]:
        """
        Generate optimal hashtags for specific content using AI.

        Args:
            content: The post content to analyze
            num_hashtags: Number of hashtags to generate
            include_trending: Whether to prioritize trending hashtags

        Returns:
            List of recommended hashtags (without # prefix)
        """
        if not self.ai_client:
            logger.warning("No AI client available, using industry defaults")
            return self.get_industry_hashtags()[:num_hashtags]

        try:
            # Get trending hashtags for context
            trending = []
            if include_trending:
                trending_data = self.discover_trending_hashtags(limit=10)
                trending = [h['hashtag'] for h in trending_data]

            # Create AI prompt
            prompt = f"""Analyze this LinkedIn post and recommend {num_hashtags} optimal hashtags.

Post content:
{content}

Industry: {self.user_industry}
User topics: {', '.join(self.user_topics)}

Currently trending hashtags in this industry: {', '.join(trending) if trending else 'N/A'}

Requirements:
1. Mix of popular and niche hashtags
2. Relevant to the content and industry
3. Balance reach (popular) with targeting (specific)
4. Use trending hashtags where appropriate
5. Avoid overly generic hashtags

Return ONLY a comma-separated list of hashtags without the # symbol.
Example format: technology, ai, innovation, coding, python"""

            response = self.ai_client.generate(prompt, max_tokens=100)

            # Parse response
            hashtags = [h.strip().lower() for h in response.split(',')]
            hashtags = [h.replace('#', '') for h in hashtags]  # Remove # if present

            # Filter and validate
            hashtags = [h for h in hashtags if h and len(h) > 2 and len(h) < 30]

            return hashtags[:num_hashtags]

        except Exception as e:
            logger.error(f"Error generating hashtags with AI: {e}")
            return self.get_industry_hashtags()[:num_hashtags]

    def get_hashtag_mix(self,
                       content: str = None,
                       num_popular: int = 2,
                       num_trending: int = 2,
                       num_niche: int = 1) -> Dict[str, List[str]]:
        """
        Get a balanced mix of hashtag types for optimal reach and engagement.

        Returns:
            Dict with 'popular', 'trending', and 'niche' hashtag lists
        """
        result = {
            'popular': [],
            'trending': [],
            'niche': []
        }

        # Get trending hashtags
        trending_data = self.discover_trending_hashtags(limit=20)

        # Categorize hashtags by trend score
        popular = [h for h in trending_data if h['trend_score'] >= 70]
        trending = [h for h in trending_data if 40 <= h['trend_score'] < 70]
        niche = [h for h in trending_data if h['trend_score'] < 40]

        result['popular'] = [h['hashtag'] for h in popular[:num_popular]]
        result['trending'] = [h['hashtag'] for h in trending[:num_trending]]
        result['niche'] = [h['hashtag'] for h in niche[:num_niche]]

        # If we have content, use AI to enhance niche hashtags
        if content and self.ai_client and len(result['niche']) < num_niche:
            ai_hashtags = self.generate_hashtags_for_content(content, num_hashtags=num_niche)
            for hashtag in ai_hashtags:
                if hashtag not in result['popular'] and hashtag not in result['trending']:
                    result['niche'].append(hashtag)
                    if len(result['niche']) >= num_niche:
                        break

        return result

    def get_hashtag_recommendations(self,
                                   content: str,
                                   max_hashtags: int = 5) -> Dict:
        """
        Get comprehensive hashtag recommendations for a post.

        Returns detailed recommendations with explanations.
        """
        # Get mixed hashtags
        mix = self.get_hashtag_mix(content, num_popular=2, num_trending=2, num_niche=1)

        # Flatten into single list
        all_hashtags = mix['popular'] + mix['trending'] + mix['niche']
        all_hashtags = all_hashtags[:max_hashtags]

        # Get trending data for context
        trending_data = {h['hashtag']: h for h in self.discover_trending_hashtags(limit=20)}

        recommendations = {
            'hashtags': all_hashtags,
            'formatted': ' '.join([f'#{h}' for h in all_hashtags]),
            'breakdown': {
                'popular': mix['popular'],
                'trending': mix['trending'],
                'niche': mix['niche']
            },
            'metrics': {},
            'explanation': self._generate_explanation(mix, trending_data)
        }

        # Add metrics for each hashtag
        for hashtag in all_hashtags:
            if hashtag in trending_data:
                recommendations['metrics'][hashtag] = trending_data[hashtag]

        return recommendations

    def _generate_explanation(self, mix: Dict, trending_data: Dict) -> str:
        """Generate explanation for hashtag recommendations."""
        explanations = []

        if mix['popular']:
            explanations.append(
                f"Popular hashtags ({', '.join(mix['popular'])}) for broad reach"
            )

        if mix['trending']:
            explanations.append(
                f"Trending hashtags ({', '.join(mix['trending'])}) for current relevance"
            )

        if mix['niche']:
            explanations.append(
                f"Niche hashtags ({', '.join(mix['niche'])}) for targeted engagement"
            )

        return ". ".join(explanations) + "."

    def track_hashtag_performance(self, post_id: int, hashtags: List[str]):
        """
        Track hashtag performance for a specific post.
        This is called after a post is published to associate hashtags with the post.
        """
        try:
            from database.models import HashtagPerformance

            for hashtag in hashtags:
                perf = HashtagPerformance(
                    post_id=post_id,
                    hashtag=hashtag.lower().replace('#', ''),
                    recorded_at=datetime.utcnow()
                )
                self.db.add(perf)

            self.db.commit()
            logger.info(f"Tracked {len(hashtags)} hashtags for post {post_id}")

        except Exception as e:
            logger.error(f"Error tracking hashtag performance: {e}")
            self.db.rollback()

    def get_best_performing_hashtags(self,
                                    days_back: int = 90,
                                    min_posts: int = 3,
                                    limit: int = 10) -> List[Dict]:
        """
        Get the best performing hashtags based on historical data.

        Returns hashtags with their average engagement metrics.
        """
        historical = self._analyze_historical_hashtag_performance(days_back)

        # Filter by minimum post count
        filtered = [
            {
                'hashtag': hashtag,
                'avg_engagement': metrics['avg_engagement'],
                'post_count': metrics['post_count'],
                'trend_score': metrics['trend_score'],
                'avg_views': metrics['total_views'] / metrics['post_count'],
                'avg_reactions': metrics['total_reactions'] / metrics['post_count'],
                'avg_comments': metrics['total_comments'] / metrics['post_count']
            }
            for hashtag, metrics in historical
            if metrics['post_count'] >= min_posts
        ]

        return filtered[:limit]
