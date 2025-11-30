#!/usr/bin/env python3
"""Import existing posts and comments into Safety Monitor"""

import yaml
from database.db import Database
from database.models import Post, Comment
from utils.safety_monitor import SafetyMonitor

def load_config():
    with open('config.yaml', 'r') as f:
        return yaml.safe_load(f)

def main():
    print("\n" + "="*60)
    print("Importing Existing Activity Data")
    print("="*60)

    config = load_config()
    db = Database(config)
    session = db.get_session()
    safety_monitor = SafetyMonitor(session, config)

    # Get all posts
    posts = session.query(Post).all()
    print(f"\nFound {len(posts)} posts")

    # Import published posts as activities
    imported_posts = 0
    for post in posts:
        if post.published and post.published_at:
            # Log as post activity with the actual timestamp
            activity = safety_monitor.log_activity(
                action_type='post',
                target_type='post',
                target_id=f'post-{post.id}',
                duration=2.0,  # Estimated
                success=True
            )
            # Update the timestamp to match when it was actually published
            activity.performed_at = post.published_at
            session.commit()
            imported_posts += 1

    print(f"  ✓ Imported {imported_posts} published posts")

    # Get all comments
    comments = session.query(Comment).all()
    print(f"\nFound {len(comments)} comments")

    # Import published comments as activities
    imported_comments = 0
    for comment in comments:
        if comment.published and comment.published_at:
            # Log as comment activity
            activity = safety_monitor.log_activity(
                action_type='comment',
                target_type='post',
                target_id=comment.target_post_url or f'comment-{comment.id}',
                duration=1.5,  # Estimated
                success=True
            )
            # Update the timestamp to match when it was actually published
            activity.performed_at = comment.published_at
            session.commit()
            imported_comments += 1

    print(f"  ✓ Imported {imported_comments} published comments")

    # Show summary
    print("\n" + "="*60)
    print("Import Summary")
    print("="*60)
    print(f"Total activities imported: {imported_posts + imported_comments}")
    print(f"  - Posts: {imported_posts}")
    print(f"  - Comments: {imported_comments}")

    # Get current safety status
    print("\n" + "="*60)
    print("Current Safety Status")
    print("="*60)

    status = safety_monitor.get_safety_status()
    print(f"Status: {status['status'].upper()}")
    print(f"Activity counts:")
    print(f"  - Last hour: {status['activity_counts']['last_hour']}")
    print(f"  - Last 24h: {status['activity_counts']['last_24h']}")
    print(f"  - Last 7 days: {status['activity_counts']['last_7d']}")
    print(f"Risk score: {status['risk_score']:.2f}")
    print(f"Active alerts: {status['active_alerts']}")

    print("\n✓ Import complete! Run 'python3 main.py safety-status' to see details.\n")

    session.close()
    db.close()

if __name__ == "__main__":
    main()
