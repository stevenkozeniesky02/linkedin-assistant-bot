#!/usr/bin/env python3
"""
Content Research CLI - Research optimal hashtags and content strategies

Usage:
  python content_research_cli.py hashtags --industry "Technology"
  python content_research_cli.py hashtags-for-content "Your post content here"
  python content_research_cli.py analyze-performance --days 90
  python content_research_cli.py content-ideas --num 5
  python content_research_cli.py posting-schedule
"""

import sys
import argparse
import logging
from pathlib import Path
import yaml

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.session import get_session
from utils.hashtag_research import HashtagResearchEngine
from utils.content_strategy import ContentStrategyAnalyzer
from ai.anthropic_client import AnthropicClient
from ai.openai_client import OpenAIClient
from ai.gemini_client import GeminiClient
from ai.local_llm_client import LocalLLMClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config():
    """Load configuration from config.yaml"""
    config_path = Path(__file__).parent.parent / 'config.yaml'
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        return None

    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def get_ai_client(config):
    """Get AI client based on configuration"""
    provider = config.get('ai_provider', 'local')

    try:
        if provider == 'anthropic':
            return AnthropicClient(config.get('anthropic', {}))
        elif provider == 'openai':
            return OpenAIClient(config.get('openai', {}))
        elif provider == 'gemini':
            return GeminiClient(config.get('gemini', {}))
        else:  # local or default
            return LocalLLMClient(config.get('local_llm', {}))
    except Exception as e:
        logger.warning(f"Could not initialize AI client: {e}")
        return None


def cmd_hashtags(args, config, db_session, ai_client):
    """Research trending hashtags for an industry"""
    print("\n🔍 Researching Trending Hashtags\n")

    engine = HashtagResearchEngine(db_session, config, ai_client)

    industry = args.industry or config.get('user_profile', {}).get('industry', 'Technology')
    print(f"Industry: {industry}")
    print(f"Analyzing last {args.days} days\n")

    trending = engine.discover_trending_hashtags(
        industry=industry,
        limit=args.limit,
        days_back=args.days
    )

    if not trending:
        print("No trending hashtags found. Post more content to build historical data!\n")
        return

    print("📊 Trending Hashtags:\n")
    for i, hashtag_data in enumerate(trending, 1):
        hashtag = hashtag_data['hashtag']
        source = hashtag_data['source']
        score = hashtag_data['trend_score']

        print(f"{i}. #{hashtag}")
        print(f"   Source: {source}")
        print(f"   Trend Score: {score:.1f}/100")

        if hashtag_data.get('post_count', 0) > 0:
            print(f"   Used in: {hashtag_data['post_count']} posts")
            print(f"   Avg Engagement: {hashtag_data['avg_engagement']:.1f}")

        print()


def cmd_hashtags_for_content(args, config, db_session, ai_client):
    """Generate hashtag recommendations for specific content"""
    print("\n🎯 Generating Hashtags for Your Content\n")

    engine = HashtagResearchEngine(db_session, config, ai_client)

    content = args.content
    print(f"Content: {content[:100]}{'...' if len(content) > 100 else ''}\n")

    recommendations = engine.get_hashtag_recommendations(
        content=content,
        max_hashtags=args.num
    )

    print("💡 Recommended Hashtags:\n")
    print(recommendations['formatted'])
    print()

    print("📈 Breakdown:")
    for category, hashtags in recommendations['breakdown'].items():
        if hashtags:
            print(f"  {category.title()}: {', '.join('#' + h for h in hashtags)}")

    print(f"\n📝 Explanation:")
    print(f"  {recommendations['explanation']}\n")


def cmd_analyze_performance(args, config, db_session, ai_client):
    """Analyze content performance and get strategic recommendations"""
    print("\n📊 Analyzing Content Performance\n")

    analyzer = ContentStrategyAnalyzer(db_session, config, ai_client)

    print(f"Analyzing last {args.days} days of posts...\n")

    analysis = analyzer.analyze_best_performing_content(days_back=args.days)

    if analysis['analyzed_posts'] == 0:
        print("❌ Not enough data to analyze. Create some posts first!\n")
        return

    print(f"✅ Analyzed {analysis['analyzed_posts']} posts")
    print(f"   Date Range: {analysis['date_range']}\n")

    # Overall metrics
    print("📈 Overall Performance:")
    metrics = analysis['overall_metrics']
    if metrics:
        print(f"   Avg Views: {metrics.get('avg_views', 0):.1f}")
        print(f"   Avg Reactions: {metrics.get('avg_reactions', 0):.1f}")
        print(f"   Avg Comments: {metrics.get('avg_comments', 0):.1f}")
        print(f"   Avg Shares: {metrics.get('avg_shares', 0):.1f}")
        print()

    # Content types
    if analysis['content_types']['types']:
        print("🎭 Best Performing Content Types:")
        for i, content_type in enumerate(analysis['content_types']['types'][:3], 1):
            print(f"   {i}. {content_type['type'].title()}")
            print(f"      Avg Engagement: {content_type['avg_engagement']:.1f}")
            print(f"      Posts: {content_type['count']}")
        print()

    # Topics
    if analysis['topics']['topics']:
        print("📌 Best Performing Topics:")
        for i, topic in enumerate(analysis['topics']['topics'][:3], 1):
            print(f"   {i}. {topic['topic'].title()}")
            print(f"      Avg Engagement: {topic['avg_engagement']:.1f}")
            print(f"      Posts: {topic['count']}")
        print()

    # Timing
    if analysis['posting_times']['time_slots']:
        print("⏰ Best Times to Post:")
        for i, time_slot in enumerate(analysis['posting_times']['time_slots'][:3], 1):
            print(f"   {i}. {time_slot['time_slot'].replace('_', ' ').title()}")
            print(f"      Avg Engagement: {time_slot['avg_engagement']:.1f}")
        print()

    # Days
    if analysis['days_of_week']['days']:
        print("📅 Best Days to Post:")
        for i, day in enumerate(analysis['days_of_week']['days'][:3], 1):
            print(f"   {i}. {day['day']}")
            print(f"      Avg Engagement: {day['avg_engagement']:.1f}")
        print()

    # Recommendations
    print("💡 Strategic Recommendations:")
    for i, rec in enumerate(analysis['recommendations'], 1):
        print(f"   {i}. {rec}")
    print()


def cmd_content_ideas(args, config, db_session, ai_client):
    """Generate content ideas based on industry"""
    print("\n💡 Generating Content Ideas\n")

    analyzer = ContentStrategyAnalyzer(db_session, config, ai_client)

    industry = args.industry or config.get('user_profile', {}).get('industry', 'Technology')
    print(f"Industry: {industry}")
    print(f"Generating {args.num} content ideas...\n")

    ideas = analyzer.get_content_ideas(industry=industry, num_ideas=args.num)

    for i, idea in enumerate(ideas, 1):
        print(f"{i}. [{idea['type'].upper()}] {idea['topic']}")
        print(f"   {idea['description']}\n")


def cmd_posting_schedule(args, config, db_session, ai_client):
    """Get recommended posting schedule"""
    print("\n📅 Recommended Posting Schedule\n")

    analyzer = ContentStrategyAnalyzer(db_session, config, ai_client)

    schedule = analyzer.get_posting_schedule_recommendation()

    print("🎯 Optimal Schedule:")
    print(f"\nFrequency: {schedule['frequency']}")
    print(f"\nBest Days:")
    for day in schedule['recommended_days']:
        print(f"  • {day}")

    print(f"\nBest Time: {schedule['recommended_time'].replace('_', ' ').title()}")

    print(f"\n📝 Content Mix:")
    print(f"  Primary: {schedule['content_mix']['primary_type'].title()}")
    if schedule['content_mix']['secondary_types']:
        print(f"  Secondary: {', '.join(t.title() for t in schedule['content_mix']['secondary_types'])}")

    print()


def cmd_best_hashtags(args, config, db_session, ai_client):
    """Show best performing hashtags from historical data"""
    print("\n🏆 Best Performing Hashtags\n")

    engine = HashtagResearchEngine(db_session, config, ai_client)

    print(f"Analyzing last {args.days} days...\n")

    best = engine.get_best_performing_hashtags(
        days_back=args.days,
        min_posts=args.min_posts,
        limit=args.limit
    )

    if not best:
        print("No hashtag performance data yet. Use hashtags in your posts to build history!\n")
        return

    print("📊 Top Performing Hashtags:\n")
    for i, hashtag_data in enumerate(best, 1):
        print(f"{i}. #{hashtag_data['hashtag']}")
        print(f"   Posts: {hashtag_data['post_count']}")
        print(f"   Avg Engagement: {hashtag_data['avg_engagement']:.1f}")
        print(f"   Avg Views: {hashtag_data['avg_views']:.1f}")
        print(f"   Avg Reactions: {hashtag_data['avg_reactions']:.1f}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description='LinkedIn Content Research Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Hashtags command
    hashtags_parser = subparsers.add_parser('hashtags', help='Research trending hashtags')
    hashtags_parser.add_argument('--industry', type=str, help='Industry to research')
    hashtags_parser.add_argument('--days', type=int, default=30, help='Days to analyze (default: 30)')
    hashtags_parser.add_argument('--limit', type=int, default=20, help='Number of hashtags (default: 20)')

    # Hashtags for content
    content_parser = subparsers.add_parser('hashtags-for-content', help='Get hashtags for specific content')
    content_parser.add_argument('content', type=str, help='Your post content')
    content_parser.add_argument('--num', type=int, default=5, help='Number of hashtags (default: 5)')

    # Analyze performance
    analyze_parser = subparsers.add_parser('analyze-performance', help='Analyze content performance')
    analyze_parser.add_argument('--days', type=int, default=90, help='Days to analyze (default: 90)')

    # Content ideas
    ideas_parser = subparsers.add_parser('content-ideas', help='Generate content ideas')
    ideas_parser.add_argument('--industry', type=str, help='Industry')
    ideas_parser.add_argument('--num', type=int, default=5, help='Number of ideas (default: 5)')

    # Posting schedule
    subparsers.add_parser('posting-schedule', help='Get recommended posting schedule')

    # Best hashtags
    best_parser = subparsers.add_parser('best-hashtags', help='Show best performing hashtags')
    best_parser.add_argument('--days', type=int, default=90, help='Days to analyze (default: 90)')
    best_parser.add_argument('--min-posts', type=int, default=3, help='Min posts required (default: 3)')
    best_parser.add_argument('--limit', type=int, default=10, help='Number of hashtags (default: 10)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Load config
    config = load_config()
    if not config:
        return

    # Get database session
    db_session = get_session()

    # Get AI client
    ai_client = get_ai_client(config)

    # Execute command
    commands = {
        'hashtags': cmd_hashtags,
        'hashtags-for-content': cmd_hashtags_for_content,
        'analyze-performance': cmd_analyze_performance,
        'content-ideas': cmd_content_ideas,
        'posting-schedule': cmd_posting_schedule,
        'best-hashtags': cmd_best_hashtags
    }

    if args.command in commands:
        try:
            commands[args.command](args, config, db_session, ai_client)
        except Exception as e:
            logger.error(f"Command failed: {e}", exc_info=True)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
