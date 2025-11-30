#!/usr/bin/env python3
"""Demo script to populate sample data and showcase Safety Monitor & Connection Manager features"""

import yaml
from datetime import datetime, timedelta
import random
from database.db import Database
from utils.safety_monitor import SafetyMonitor
from linkedin.connection_manager import ConnectionManager

def load_config():
    """Load configuration from config.yaml"""
    with open('config.yaml', 'r') as f:
        return yaml.safe_load(f)

def populate_sample_activity(safety_monitor, num_actions=25):
    """Populate sample activity data"""
    print("\n📊 Populating sample activity data...")

    action_types = [
        ('post', 'post'),
        ('comment', 'post'),
        ('like', 'post'),
        ('view', 'profile'),
        ('connection_request', 'profile')
    ]

    # Simulate activities over the past few hours
    now = datetime.utcnow()
    for i in range(num_actions):
        action_type, target_type = random.choice(action_types)

        # Add some time variance (spread over last 3 hours)
        hours_ago = random.uniform(0, 3)

        activity = safety_monitor.log_activity(
            action_type=action_type,
            target_type=target_type,
            target_id=f'target-{i}',
            duration=random.uniform(0.5, 3.0),
            success=random.random() > 0.1  # 90% success rate
        )

    print(f"  ✓ Added {num_actions} sample activities")

def populate_sample_connections(conn_manager, num_connections=15):
    """Populate sample connection data"""
    print("\n🤝 Populating sample connection data...")

    sample_people = [
        ("Sarah Chen", "Senior Data Scientist", "Google", "https://linkedin.com/in/sarahchen"),
        ("Michael Torres", "Machine Learning Engineer", "Meta", "https://linkedin.com/in/michaeltorres"),
        ("Emily Rodriguez", "Software Engineering Manager", "Amazon", "https://linkedin.com/in/emilyrodriguez"),
        ("David Kim", "AI Research Scientist", "OpenAI", "https://linkedin.com/in/davidkim"),
        ("Jessica Wang", "Product Manager", "Microsoft", "https://linkedin.com/in/jessicawang"),
        ("James Anderson", "DevOps Engineer", "Netflix", "https://linkedin.com/in/jamesanderson"),
        ("Maria Garcia", "Backend Developer", "Stripe", "https://linkedin.com/in/mariagarcia"),
        ("Robert Lee", "Frontend Engineer", "Airbnb", "https://linkedin.com/in/robertlee"),
        ("Lisa Patel", "Full Stack Developer", "Uber", "https://linkedin.com/in/lisapatel"),
        ("Kevin Zhang", "Cloud Architect", "AWS", "https://linkedin.com/in/kevinzhang"),
        ("Amanda Johnson", "Security Engineer", "Apple", "https://linkedin.com/in/amandajohnson"),
        ("Chris Brown", "Site Reliability Engineer", "Cloudflare", "https://linkedin.com/in/chrisbrown"),
        ("Nicole Martinez", "Data Engineer", "Snowflake", "https://linkedin.com/in/nicolemartinez"),
        ("Daniel Wilson", "Solutions Architect", "Salesforce", "https://linkedin.com/in/danielwilson"),
        ("Rachel Taylor", "Engineering Director", "LinkedIn", "https://linkedin.com/in/racheltaylor"),
    ]

    for i, (name, title, company, url) in enumerate(sample_people[:num_connections]):
        conn = conn_manager.add_connection(
            name=name,
            profile_url=url,
            title=title,
            company=company,
            connection_source="demo_import"
        )

        # Simulate varying engagement levels
        if i < 3:  # High engagement
            conn_manager.update_engagement(
                profile_url=url,
                messages_sent=random.randint(5, 15),
                messages_received=random.randint(10, 20),
                posts_engaged=random.randint(15, 30)
            )
            conn_manager.mark_target_audience(url, is_target=True, notes="Key connection in tech")

        elif i < 8:  # Medium engagement
            conn_manager.update_engagement(
                profile_url=url,
                messages_sent=random.randint(1, 4),
                messages_received=random.randint(2, 8),
                posts_engaged=random.randint(3, 10)
            )

        # Low/no engagement for the rest

    print(f"  ✓ Added {num_connections} sample connections")

def main():
    print("\n" + "="*70)
    print("🚀 LinkedIn Assistant Bot - Safety & Connections Demo")
    print("="*70)

    # Load config
    config = load_config()
    db = Database(config)
    session = db.get_session()

    # Initialize managers
    safety_monitor = SafetyMonitor(session, config)
    conn_manager = ConnectionManager(session, config)

    # Populate sample data
    print("\n📝 Step 1: Populating sample data...")
    populate_sample_activity(safety_monitor, num_actions=25)
    populate_sample_connections(conn_manager, num_connections=15)

    # Demo Safety Monitor
    print("\n" + "="*70)
    print("🛡️  SAFETY MONITOR DEMO")
    print("="*70)

    status = safety_monitor.get_safety_status()

    print(f"\nCurrent Status: {status['status'].upper()}")
    print(f"\n📈 Activity Summary:")
    print(f"  • Last Hour:    {status['activity_counts']['last_hour']} actions")
    print(f"  • Last 24h:     {status['activity_counts']['last_24h']} actions")
    print(f"  • Last 7 days:  {status['activity_counts']['last_7d']} actions")

    print(f"\n⚠️  Rate Limits:")
    print(f"  • Hourly: {status['activity_counts']['last_hour']}/{status['limits']['hourly_max']} ({status['utilization']['hourly_percent']}%)")
    print(f"  • Daily:  {status['activity_counts']['last_24h']}/{status['limits']['daily_max']} ({status['utilization']['daily_percent']}%)")

    print(f"\n🎯 Risk Score: {status['risk_score']:.2f} (0-1 scale)")

    if status['active_alerts'] > 0:
        print(f"\n🚨 Active Alerts: {status['active_alerts']}")
        for alert in status['alert_details']:
            print(f"  [{alert['severity'].upper()}] {alert['message']}")
    else:
        print(f"\n✅ No active safety alerts")

    # Check if next action is allowed
    print(f"\n🔍 Action Check:")
    check = safety_monitor.check_action_allowed('post')
    if check['allowed']:
        print(f"  ✅ Post action: ALLOWED - {check['reason']}")
    else:
        print(f"  ⛔ Post action: BLOCKED - {check['reason']}")

    # Demo Connection Manager
    print("\n" + "="*70)
    print("🤝 CONNECTION MANAGER DEMO")
    print("="*70)

    analytics = conn_manager.get_network_analytics(days_back=30)

    print(f"\n📊 Network Overview:")
    print(f"  • Total Connections:     {analytics['total_connections']}")
    print(f"  • Average Quality Score: {analytics['avg_quality_score']:.1f}/10")
    print(f"  • Target Audience:       {analytics['target_audience_count']} ({analytics['target_audience_percent']}%)")
    print(f"  • Growth Rate:           {analytics['growth_rate_per_day']:.2f} per day")

    print(f"\n📈 Engagement Breakdown:")
    for level in ['high', 'medium', 'low', 'none']:
        count = analytics['engagement_breakdown'][level]
        pct = (count / analytics['total_connections'] * 100) if analytics['total_connections'] > 0 else 0
        print(f"  • {level.capitalize():8}: {count:2} ({pct:.1f}%)")

    # Top connections
    print(f"\n🏆 Top 5 Connections by Quality:")
    top_conns = conn_manager.get_top_connections(limit=5)
    for i, conn in enumerate(top_conns, 1):
        total_messages = conn.messages_sent + conn.messages_received
        print(f"  {i}. {conn.name:25} | Quality: {conn.quality_score:.1f}/10 | Messages: {total_messages}")

    # Top companies
    if analytics['top_companies']:
        print(f"\n🏢 Top Companies in Network:")
        for i, company in enumerate(analytics['top_companies'][:5], 1):
            print(f"  {i}. {company['company']:25} | {company['count']} connections")

    # Recommendations
    recommendations = conn_manager.get_connection_recommendations()
    print(f"\n💡 Network Health: {recommendations['health_status'].upper()}")
    print(f"   Overall Score: {recommendations['overall_score']:.1f}/10")

    print(f"\n📝 Recommendations:")
    for rec in recommendations['recommendations'][:3]:
        priority_icon = "🔴" if rec['priority'] == 'high' else "🟡" if rec['priority'] == 'medium' else "🔵"
        print(f"  {priority_icon} {rec['message']}")
        print(f"     → {rec['action']}")

    # How to use CLI
    print("\n" + "="*70)
    print("🎯 Next Steps - Try These CLI Commands:")
    print("="*70)
    print("\n# Check safety status anytime:")
    print("  python3 main.py safety-status")

    print("\n# View your connections:")
    print("  python3 main.py connections --action list")
    print("  python3 main.py connections --action top --limit 10")

    print("\n# Add a new connection:")
    print("  python3 main.py connections --action add \\")
    print("    --name \"Your Connection\" \\")
    print("    --url \"https://linkedin.com/in/username\" \\")
    print("    --title \"Their Title\" \\")
    print("    --company \"Their Company\"")

    print("\n# View network analytics:")
    print("  python3 main.py network-analytics")
    print("  python3 main.py network-analytics --days 90")

    print("\n" + "="*70)
    print("✅ Demo complete! Your database now has sample data to explore.")
    print("="*70 + "\n")

    session.close()
    db.close()

if __name__ == "__main__":
    main()
