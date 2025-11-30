#!/usr/bin/env python3
"""
Profile Optimizer CLI - Analyze and optimize your LinkedIn profile

Usage:
  python profile_optimizer_cli.py analyze --profile profile.json
  python profile_optimizer_cli.py generate-headline --role "Software Engineer" --industry "Technology"
  python profile_optimizer_cli.py generate-summary --role "Data Scientist" --industry "Data Science"
  python profile_optimizer_cli.py recommend-skills --role "Software Engineer" --skills "Python,JavaScript" --num 10
  python profile_optimizer_cli.py compare --my-profile my_profile.json --competitor-profiles comp1.json comp2.json comp3.json
"""

import sys
import argparse
import logging
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.profile_optimizer import ProfileOptimizer
from ai.anthropic_provider import AnthropicProvider
from ai.openai_provider import OpenAIProvider
from ai.gemini_provider import GeminiProvider
from ai.local_llm_provider import LocalLLMProvider
import yaml

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
            return AnthropicProvider(config.get('anthropic', {}))
        elif provider == 'openai':
            return OpenAIProvider(config.get('openai', {}))
        elif provider == 'gemini':
            return GeminiProvider(config.get('gemini', {}))
        else:  # local or default
            return LocalLLMProvider(config.get('local_llm', {}))
    except Exception as e:
        logger.warning(f"Could not initialize AI client: {e}")
        return None


def cmd_analyze(args, config, ai_client):
    """Analyze a LinkedIn profile"""
    print("\n🔍 Analyzing LinkedIn Profile\n")

    # Load profile data
    profile_path = Path(args.profile)
    if not profile_path.exists():
        print(f"❌ Profile file not found: {args.profile}")
        print("\nCreate a JSON file with your profile data:")
        print(json.dumps({
            "headline": "Your current headline",
            "summary": "Your current summary/about section",
            "industry": "Technology",
            "experience": [
                {
                    "title": "Software Engineer",
                    "company": "Tech Corp",
                    "description": "Built scalable systems..."
                }
            ],
            "skills": ["Python", "JavaScript", "React", "AWS"]
        }, indent=2))
        return

    with open(profile_path, 'r') as f:
        profile_data = json.load(f)

    # Analyze profile
    optimizer = ProfileOptimizer(ai_client, config)
    analysis = optimizer.analyze_profile(profile_data)

    # Display results
    print(f"📊 Overall Score: {analysis['overall_score']}/100\n")

    # Score interpretation
    if analysis['overall_score'] >= 80:
        print("🟢 Excellent! Your profile is well-optimized.\n")
    elif analysis['overall_score'] >= 60:
        print("🟡 Good progress! Some improvements needed.\n")
    elif analysis['overall_score'] >= 40:
        print("🟠 Needs work. Follow the recommendations below.\n")
    else:
        print("🔴 Critical improvements needed.\n")

    # Section scores
    print("📋 Section Scores:")
    print(f"   Headline: {analysis['headline']['score']}/100")
    print(f"   Summary: {analysis['summary']['score']}/100")
    print(f"   Experience: {analysis['experience']['score']}/100")
    print(f"   Skills: {analysis['skills']['score']}/100\n")

    # Headline analysis
    print("💼 Headline Analysis:")
    headline_data = analysis['headline']
    if headline_data.get('text'):
        print(f"   Current: \"{headline_data['text']}\"")
    print(f"   Length: {headline_data['length']} chars")
    print(f"   Keywords found: {headline_data['keyword_count']}")
    if headline_data.get('keywords_found'):
        print(f"   Keywords: {', '.join(headline_data['keywords_found'][:5])}")
    if headline_data.get('issues'):
        print(f"   ⚠️  Issues: {', '.join(headline_data['issues'])}")
    print()

    # Summary analysis
    print("📝 Summary Analysis:")
    summary_data = analysis['summary']
    print(f"   Length: {summary_data['length']} chars ({summary_data.get('word_count', 0)} words)")
    print(f"   Paragraphs: {summary_data.get('paragraph_count', 0)}")
    print(f"   Keywords: {summary_data['keyword_count']}")
    print(f"   Has CTA: {'✓' if summary_data.get('has_cta') else '✗'}")
    if summary_data.get('issues'):
        print(f"   ⚠️  Issues: {', '.join(summary_data['issues'])}")
    print()

    # Experience analysis
    print("💼 Experience Analysis:")
    exp_data = analysis['experience']
    print(f"   Entries: {exp_data['entry_count']}")
    print(f"   Avg keywords per entry: {exp_data.get('avg_keywords_per_entry', 0)}")
    print(f"   Entries with achievements: {exp_data.get('entries_with_achievements', 0)}")
    if exp_data.get('issues'):
        print(f"   ⚠️  Issues: {', '.join(exp_data['issues'])}")
    print()

    # Skills analysis
    print("🎯 Skills Analysis:")
    skills_data = analysis['skills']
    print(f"   Total skills: {skills_data['skill_count']}")
    print(f"   Industry-relevant: {skills_data['matching_skills']}")
    if skills_data.get('matched_keywords'):
        print(f"   Top matches: {', '.join(skills_data['matched_keywords'][:8])}")
    if skills_data.get('issues'):
        print(f"   ⚠️  Issues: {', '.join(skills_data['issues'])}")
    print()

    # Recommendations
    print("💡 Recommendations:")
    for i, rec in enumerate(analysis['recommendations'], 1):
        print(f"   {rec}")
    print()


def cmd_generate_headline(args, config, ai_client):
    """Generate an optimized headline"""
    print("\n✨ Generating Optimized Headline\n")

    if not ai_client:
        print("❌ AI client required for headline generation")
        print("   Configure an AI provider in config.yaml\n")
        return

    optimizer = ProfileOptimizer(ai_client, config)

    # Get inputs
    role = args.role
    industry = args.industry or config.get('user_profile', {}).get('industry', 'Technology')
    current = args.current or ""
    skills = args.skills.split(',') if args.skills else []

    print(f"Role: {role}")
    print(f"Industry: {industry}")
    if current:
        print(f"Current headline: {current}")
    print(f"Skills: {', '.join(skills)}\n")

    print("Generating...\n")

    # Generate headline
    optimized = optimizer.generate_optimized_headline(current, role, industry, skills)

    print("🎯 Optimized Headline:")
    print(f"   {optimized}\n")

    # Analyze it
    analysis = optimizer._analyze_headline(optimized, industry)
    print(f"Score: {analysis['score']}/100")
    print(f"Length: {analysis['length']} chars")
    print(f"Keywords: {analysis['keyword_count']}\n")


def cmd_generate_summary(args, config, ai_client):
    """Generate an optimized summary"""
    print("\n✨ Generating Optimized Summary\n")

    if not ai_client:
        print("❌ AI client required for summary generation")
        print("   Configure an AI provider in config.yaml\n")
        return

    optimizer = ProfileOptimizer(ai_client, config)

    # Get inputs
    role = args.role
    industry = args.industry or config.get('user_profile', {}).get('industry', 'Technology')
    current = args.current or ""
    achievements = args.achievements.split('|') if args.achievements else []
    skills = args.skills.split(',') if args.skills else []

    print(f"Role: {role}")
    print(f"Industry: {industry}")
    if achievements:
        print(f"Achievements: {len(achievements)} provided")
    print(f"Skills: {', '.join(skills[:5])}\n")

    print("Generating... (this may take a moment)\n")

    # Generate summary
    optimized = optimizer.generate_optimized_summary(current, role, industry, achievements, skills)

    print("🎯 Optimized Summary:")
    print("=" * 60)
    print(optimized)
    print("=" * 60)
    print()

    # Analyze it
    analysis = optimizer._analyze_summary(optimized, industry)
    print(f"Score: {analysis['score']}/100")
    print(f"Length: {analysis['length']} chars ({analysis['word_count']} words)")
    print(f"Keywords: {analysis['keyword_count']}\n")


def cmd_recommend_skills(args, config, ai_client):
    """Recommend skills to add to profile"""
    print("\n💡 Skill Recommendations\n")

    optimizer = ProfileOptimizer(ai_client, config)

    # Get inputs
    industry = args.industry or config.get('user_profile', {}).get('industry', 'Technology')
    role = args.role or None
    current_skills = args.skills.split(',') if args.skills else []

    print(f"Industry: {industry}")
    if role:
        print(f"Role: {role}")
    print(f"Current skills: {len(current_skills)}")
    if current_skills:
        print(f"   {', '.join(current_skills[:8])}{'...' if len(current_skills) > 8 else ''}\n")
    else:
        print()

    # Get recommendations
    recommendations = optimizer.get_skill_recommendations(
        current_skills=current_skills,
        industry=industry,
        role=role,
        max_suggestions=args.num
    )

    print(f"📊 Analysis:")
    print(f"   Current skills: {recommendations['total_current']}")
    print(f"   Missing industry keywords: {recommendations['missing_industry_keywords']}\n")

    # High priority
    if recommendations['high_priority']:
        print("🔴 High Priority (Add These First):")
        for skill in recommendations['high_priority']:
            print(f"   • {skill}")
        print()

    # Medium priority
    if recommendations['medium_priority']:
        print("🟡 Medium Priority (Strengthen Profile):")
        for skill in recommendations['medium_priority']:
            print(f"   • {skill}")
        print()

    # Nice to have
    if recommendations['nice_to_have']:
        print("🟢 Nice to Have (Round Out Skills):")
        for skill in recommendations['nice_to_have']:
            print(f"   • {skill}")
        print()

    # AI suggestions
    if recommendations['ai_suggested']:
        print("🤖 AI-Powered Suggestions:")
        for skill in recommendations['ai_suggested']:
            print(f"   • {skill}")
        print()


def cmd_compare(args, config, ai_client):
    """Compare your profile against competitors"""
    print("\n⚖️  Profile Comparison vs Competitors\n")

    optimizer = ProfileOptimizer(ai_client, config)

    # Load my profile
    my_profile_path = Path(args.my_profile)
    if not my_profile_path.exists():
        print(f"❌ Your profile file not found: {args.my_profile}\n")
        return

    with open(my_profile_path, 'r') as f:
        my_profile = json.load(f)

    # Load competitor profiles
    competitor_profiles = []
    for comp_path in args.competitor_profiles:
        comp_path_obj = Path(comp_path)
        if not comp_path_obj.exists():
            print(f"⚠️  Skipping missing file: {comp_path}")
            continue
        with open(comp_path_obj, 'r') as f:
            competitor_profiles.append(json.load(f))

    if not competitor_profiles:
        print("❌ No valid competitor profiles found\n")
        return

    print(f"Comparing your profile against {len(competitor_profiles)} competitors...\n")

    # Compare profiles
    comparison = optimizer.compare_profiles(my_profile, competitor_profiles)

    # Display results
    print("📊 Overall Comparison:")
    print(f"   Your Score: {comparison['my_score']}/100")
    print(f"   Competitor Average: {comparison['competitor_average']:.1f}/100")
    print(f"   Gap: {comparison['gap']:+.1f} points")
    print(f"   Percentile: {comparison['percentile']:.0f}th (better than {comparison['better_than']}/{comparison['total_compared']} competitors)\n")

    # Competitive position
    if comparison['percentile'] >= 75:
        print("🟢 Strong Position - You're in the top 25%\n")
    elif comparison['percentile'] >= 50:
        print("🟡 Average Position - Room for improvement\n")
    else:
        print("🔴 Weak Position - Significant improvements needed\n")

    # Section comparison
    print("📋 Section-by-Section Comparison:")
    for section in ['headline', 'summary', 'experience', 'skills']:
        gap = comparison['section_gaps'][section]
        avg = comparison['section_averages'][section]
        icon = "✅" if gap > 0 else "❌"
        print(f"   {icon} {section.title()}: {gap:+.1f} (avg: {avg:.1f})")
    print()

    # Strengths
    if comparison['strengths']:
        print("💪 Your Strengths:")
        for strength in comparison['strengths']:
            print(f"   • {strength}")
        print()

    # Weaknesses
    if comparison['weaknesses']:
        print("⚠️  Your Weaknesses:")
        for weakness in comparison['weaknesses']:
            print(f"   • {weakness}")
        print()

    # Skill comparison
    skill_comp = comparison['skill_comparison']
    print("🎯 Skills Analysis:")
    print(f"   Common skills: {skill_comp['common_skills']}")
    print(f"   Missing skills: {skill_comp['missing_skills']}")
    print(f"   Unique skills: {skill_comp['unique_skills']}")

    if skill_comp['top_missing']:
        print(f"\n   Top skills competitors have that you don't:")
        for skill in skill_comp['top_missing'][:5]:
            print(f"      • {skill}")

    if skill_comp['top_unique']:
        print(f"\n   Your unique skills (competitors don't have):")
        for skill in skill_comp['top_unique'][:5]:
            print(f"      • {skill}")
    print()

    # Recommendations
    print("💡 Competitive Recommendations:")
    for i, rec in enumerate(comparison['recommendations'], 1):
        print(f"   {rec}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description='LinkedIn Profile Optimizer',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze your LinkedIn profile')
    analyze_parser.add_argument('--profile', type=str, required=True, help='Path to profile JSON file')

    # Generate headline
    headline_parser = subparsers.add_parser('generate-headline', help='Generate optimized headline')
    headline_parser.add_argument('--role', type=str, required=True, help='Your role/title')
    headline_parser.add_argument('--industry', type=str, help='Your industry')
    headline_parser.add_argument('--current', type=str, help='Your current headline')
    headline_parser.add_argument('--skills', type=str, help='Comma-separated skills')

    # Generate summary
    summary_parser = subparsers.add_parser('generate-summary', help='Generate optimized summary')
    summary_parser.add_argument('--role', type=str, required=True, help='Your role/title')
    summary_parser.add_argument('--industry', type=str, help='Your industry')
    summary_parser.add_argument('--current', type=str, help='Your current summary')
    summary_parser.add_argument('--achievements', type=str, help='Pipe-separated achievements')
    summary_parser.add_argument('--skills', type=str, help='Comma-separated skills')

    # Recommend skills
    skills_parser = subparsers.add_parser('recommend-skills', help='Get skill recommendations')
    skills_parser.add_argument('--industry', type=str, help='Your industry')
    skills_parser.add_argument('--role', type=str, help='Your role/title')
    skills_parser.add_argument('--skills', type=str, help='Comma-separated current skills')
    skills_parser.add_argument('--num', type=int, default=10, help='Number of AI suggestions (default: 10)')

    # Compare profiles
    compare_parser = subparsers.add_parser('compare', help='Compare your profile vs competitors')
    compare_parser.add_argument('--my-profile', type=str, required=True, help='Path to your profile JSON')
    compare_parser.add_argument('--competitor-profiles', type=str, nargs='+', required=True, help='Paths to competitor profile JSON files')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Load config
    config = load_config()
    if not config:
        return

    # Get AI client
    ai_client = get_ai_client(config)

    # Execute command
    commands = {
        'analyze': cmd_analyze,
        'generate-headline': cmd_generate_headline,
        'generate-summary': cmd_generate_summary,
        'recommend-skills': cmd_recommend_skills,
        'compare': cmd_compare
    }

    if args.command in commands:
        try:
            commands[args.command](args, config, ai_client)
        except Exception as e:
            logger.error(f"Command failed: {e}", exc_info=True)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
