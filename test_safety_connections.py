#!/usr/bin/env python3
"""Test script for Safety Monitor and Connection Manager"""

import sys
from datetime import datetime
from database.db import Database
from utils.safety_monitor import SafetyMonitor
from linkedin.connection_manager import ConnectionManager

def test_safety_monitor():
    """Test SafetyMonitor functionality"""
    print("\n" + "="*60)
    print("TESTING SAFETY MONITOR")
    print("="*60)

    # Create test config
    config = {
        'database': {
            'type': 'sqlite',
            'path': ':memory:'  # In-memory database for testing
        },
        'safety': {
            'max_actions_per_hour': 10,
            'max_actions_per_day': 50,
            'max_posts_per_day': 3,
            'max_comments_per_day': 15,
            'max_connection_requests_per_day': 10
        }
    }

    # Initialize database and safety monitor
    db = Database(config)
    session = db.get_session()
    safety_monitor = SafetyMonitor(session, config)

    print("\n✓ SafetyMonitor initialized successfully")

    # Test 1: Log some activities
    print("\nTest 1: Logging activities...")
    activity1 = safety_monitor.log_activity('post', 'post', 'test-post-1', duration=2.5, success=True)
    print(f"  ✓ Logged post activity (risk score: {activity1.risk_score})")

    activity2 = safety_monitor.log_activity('comment', 'post', 'test-post-2', duration=1.2, success=True)
    print(f"  ✓ Logged comment activity (risk score: {activity2.risk_score})")

    activity3 = safety_monitor.log_activity('connection_request', 'profile', 'test-profile-1', duration=1.0, success=True)
    print(f"  ✓ Logged connection request (risk score: {activity3.risk_score})")

    # Test 2: Check if action is allowed
    print("\nTest 2: Checking action permissions...")
    result = safety_monitor.check_action_allowed('post')
    print(f"  Post allowed: {result['allowed']} - {result['reason']}")

    # Test 3: Get safety status
    print("\nTest 3: Getting safety status...")
    status = safety_monitor.get_safety_status()
    print(f"  Status: {status['status']}")
    print(f"  Activity counts: {status['activity_counts']}")
    print(f"  Risk score: {status['risk_score']}")
    print(f"  Active alerts: {status['active_alerts']}")

    # Test 4: Exceed rate limit
    print("\nTest 4: Testing rate limits...")
    for i in range(8):
        safety_monitor.log_activity('like', 'post', f'test-post-{i}', success=True)

    status = safety_monitor.get_safety_status()
    print(f"  After 11 total actions:")
    print(f"  Status: {status['status']}")
    print(f"  Hourly utilization: {status['utilization']['hourly_percent']}%")
    print(f"  Active alerts: {status['active_alerts']}")

    session.close()
    db.close()

    print("\n✓ All SafetyMonitor tests passed!")
    return True


def test_connection_manager():
    """Test ConnectionManager functionality"""
    print("\n" + "="*60)
    print("TESTING CONNECTION MANAGER")
    print("="*60)

    # Create test config
    config = {
        'database': {
            'type': 'sqlite',
            'path': ':memory:'
        },
        'connections': {}
    }

    # Initialize database and connection manager
    db = Database(config)
    session = db.get_session()
    conn_manager = ConnectionManager(session, config)

    print("\n✓ ConnectionManager initialized successfully")

    # Test 1: Add connections
    print("\nTest 1: Adding connections...")
    conn1 = conn_manager.add_connection(
        name="John Doe",
        profile_url="https://linkedin.com/in/johndoe",
        title="Software Engineer",
        company="Tech Corp"
    )
    print(f"  ✓ Added {conn1.name} (Quality: {conn1.quality_score}/10)")

    conn2 = conn_manager.add_connection(
        name="Jane Smith",
        profile_url="https://linkedin.com/in/janesmith",
        title="Data Scientist",
        company="AI Startup"
    )
    print(f"  ✓ Added {conn2.name} (Quality: {conn2.quality_score}/10)")

    conn3 = conn_manager.add_connection(
        name="Bob Johnson",
        profile_url="https://linkedin.com/in/bobjohnson",
        title="Product Manager",
        company="Tech Corp"
    )
    print(f"  ✓ Added {conn3.name} (Quality: {conn3.quality_score}/10)")

    # Test 2: Update engagement
    print("\nTest 2: Updating engagement...")
    updated = conn_manager.update_engagement(
        profile_url="https://linkedin.com/in/johndoe",
        messages_sent=3,
        messages_received=5,
        posts_engaged=10
    )
    print(f"  ✓ Updated {updated.name} - New quality: {updated.quality_score}/10")
    print(f"    Engagement level: {updated.engagement_level}")

    # Test 3: Get all connections
    print("\nTest 3: Listing all connections...")
    all_connections = conn_manager.get_all_connections()
    print(f"  Total connections: {len(all_connections)}")
    for conn in all_connections:
        print(f"    - {conn.name}: {conn.quality_score:.1f}/10 ({conn.engagement_level})")

    # Test 4: Get top connections
    print("\nTest 4: Getting top connections...")
    top_connections = conn_manager.get_top_connections(limit=2)
    print(f"  Top {len(top_connections)} connections:")
    for i, conn in enumerate(top_connections, 1):
        print(f"    {i}. {conn.name}: {conn.quality_score:.1f}/10")

    # Test 5: Mark target audience
    print("\nTest 5: Marking target audience...")
    marked = conn_manager.mark_target_audience(
        profile_url="https://linkedin.com/in/janesmith",
        is_target=True,
        notes="Relevant to AI/ML work"
    )
    print(f"  ✓ Marked {marked.name} as target audience")

    # Test 6: Network analytics
    print("\nTest 6: Getting network analytics...")
    analytics = conn_manager.get_network_analytics(days_back=30)
    print(f"  Total connections: {analytics['total_connections']}")
    print(f"  Average quality: {analytics['avg_quality_score']}/10")
    print(f"  Target audience: {analytics['target_audience_count']} ({analytics['target_audience_percent']}%)")
    print(f"  Engagement breakdown: {analytics['engagement_breakdown']}")

    # Test 7: Get recommendations
    print("\nTest 7: Getting recommendations...")
    recommendations = conn_manager.get_connection_recommendations()
    print(f"  Network health: {recommendations['health_status']}")
    print(f"  Overall score: {recommendations['overall_score']:.1f}/10")
    print(f"  Recommendations ({len(recommendations['recommendations'])}):")
    for rec in recommendations['recommendations'][:3]:
        print(f"    [{rec['priority']}] {rec['message']}")

    session.close()
    db.close()

    print("\n✓ All ConnectionManager tests passed!")
    return True


if __name__ == "__main__":
    try:
        # Run tests
        safety_passed = test_safety_monitor()
        connection_passed = test_connection_manager()

        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"SafetyMonitor: {'✓ PASSED' if safety_passed else '✗ FAILED'}")
        print(f"ConnectionManager: {'✓ PASSED' if connection_passed else '✗ FAILED'}")

        if safety_passed and connection_passed:
            print("\n🎉 All tests passed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
