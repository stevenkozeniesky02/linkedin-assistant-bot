"""Post scheduling functionality"""

import time
from datetime import datetime, timedelta
from typing import List, Optional
from database import Database, Post
from linkedin import LinkedInClient, PostManager


class Scheduler:
    """Manages scheduled posts"""

    def __init__(self, config: dict):
        """
        Initialize scheduler

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.db = Database(config)

    def get_scheduled_posts(self) -> List[Post]:
        """
        Get all scheduled posts

        Returns:
            List of scheduled Post objects
        """
        session = self.db.get_session()
        try:
            posts = session.query(Post).filter(
                Post.is_scheduled == True,
                Post.published == False
            ).order_by(Post.scheduled_time).all()
            return posts
        finally:
            session.close()

    def get_pending_posts(self) -> List[Post]:
        """
        Get posts that are due to be posted now

        Returns:
            List of posts that should be posted
        """
        session = self.db.get_session()
        try:
            now = datetime.utcnow()
            posts = session.query(Post).filter(
                Post.is_scheduled == True,
                Post.published == False,
                Post.scheduled_time <= now
            ).all()
            return posts
        finally:
            session.close()

    def schedule_post(self, post_id: int, scheduled_time: datetime) -> bool:
        """
        Schedule a post for future publishing

        Args:
            post_id: ID of the post to schedule
            scheduled_time: When to publish the post

        Returns:
            True if successful, False otherwise
        """
        session = self.db.get_session()
        try:
            post = session.query(Post).filter(Post.id == post_id).first()

            if not post:
                print(f"Post {post_id} not found")
                return False

            if post.published:
                print(f"Post {post_id} is already published")
                return False

            post.scheduled_time = scheduled_time
            post.is_scheduled = True
            session.commit()

            print(f"✓ Post {post_id} scheduled for {scheduled_time.strftime('%Y-%m-%d %H:%M')} UTC")
            return True

        except Exception as e:
            print(f"Error scheduling post: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    def cancel_schedule(self, post_id: int) -> bool:
        """
        Cancel a scheduled post

        Args:
            post_id: ID of the post to cancel

        Returns:
            True if successful, False otherwise
        """
        session = self.db.get_session()
        try:
            post = session.query(Post).filter(Post.id == post_id).first()

            if not post:
                print(f"Post {post_id} not found")
                return False

            post.is_scheduled = False
            post.scheduled_time = None
            session.commit()

            print(f"✓ Schedule cancelled for post {post_id}")
            return True

        except Exception as e:
            print(f"Error cancelling schedule: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    def run_scheduler(self, check_interval: int = 60):
        """
        Run the scheduler in a loop, checking for pending posts

        Args:
            check_interval: How often to check for pending posts (seconds)
        """
        print(f"Scheduler started. Checking every {check_interval} seconds...")

        while True:
            try:
                pending = self.get_pending_posts()

                if pending:
                    print(f"\nFound {len(pending)} pending post(s)")

                    # Initialize LinkedIn client
                    client = LinkedInClient(self.config)
                    client.start()
                    client.login()

                    post_manager = PostManager(client)

                    for post in pending:
                        print(f"\nPosting scheduled post: {post.topic}")

                        # Combine content and hashtags
                        full_content = post.content
                        if post.hashtags:
                            full_content += f"\n\n{post.hashtags}"

                        # Post to LinkedIn (without confirmation for scheduled posts)
                        success = post_manager.create_post(full_content, wait_for_confirmation=False)

                        if success:
                            # Update database
                            session = self.db.get_session()
                            try:
                                post.published = True
                                post.published_at = datetime.utcnow()
                                post.is_scheduled = False
                                session.commit()
                                print(f"✓ Post {post.id} published successfully")
                            finally:
                                session.close()
                        else:
                            print(f"✗ Failed to publish post {post.id}")

                    client.stop()

                # Wait before next check
                time.sleep(check_interval)

            except KeyboardInterrupt:
                print("\nScheduler stopped by user")
                break
            except Exception as e:
                print(f"Error in scheduler: {e}")
                time.sleep(check_interval)

    def suggest_optimal_times(self) -> List[dict]:
        """
        Suggest optimal posting times based on config

        Returns:
            List of suggested times
        """
        schedule_config = self.config.get('schedule', {})
        posting_days = schedule_config.get('posting_days', [1, 2, 3, 4, 5])  # Tue-Sat
        posting_times = schedule_config.get('posting_times', ['08:00', '12:00', '17:00'])

        suggestions = []

        # Get next 7 days
        for i in range(7):
            date = datetime.now() + timedelta(days=i)

            # Check if this day is in posting_days (0=Monday)
            if date.weekday() in posting_days:
                for time_str in posting_times:
                    hour, minute = map(int, time_str.split(':'))
                    suggested_time = date.replace(hour=hour, minute=minute, second=0, microsecond=0)

                    # Only suggest future times
                    if suggested_time > datetime.now():
                        suggestions.append({
                            'time': suggested_time,
                            'formatted': suggested_time.strftime('%A, %B %d at %I:%M %p')
                        })

        return suggestions[:10]  # Return next 10 optimal slots
