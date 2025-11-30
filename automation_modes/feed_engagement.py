"""Feed Engagement Automation Mode

Scrolls through LinkedIn feed and engages with relevant posts
"""

from typing import Dict, List
from .base import AutomationMode
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


class FeedEngagementMode(AutomationMode):
    """Engage with LinkedIn feed posts (likes, comments, shares)"""

    def __init__(self, config, linkedin_client, ai_provider, db_session, safety_monitor):
        super().__init__(
            name='feed_engagement',
            config=config.get('feed_engagement', {}),
            linkedin_client=linkedin_client,
            ai_provider=ai_provider,
            db_session=db_session,
            safety_monitor=safety_monitor
        )

        # Feed engagement settings
        self.scroll_duration = self.config.get('scroll_duration_minutes', 15)
        self.max_likes = self.config.get('max_likes_per_session', 10)
        self.max_comments = self.config.get('max_comments_per_session', 3)
        self.max_shares = self.config.get('max_shares_per_session', 1)
        self.max_skips_before_engage = self.config.get('max_skips_before_engage', 8)
        self.target_keywords = self.config.get('target_keywords', [])
        self.avoid_keywords = self.config.get('avoid_keywords', [])

        # Counters
        self.likes_count = 0
        self.comments_count = 0
        self.shares_count = 0
        self.consecutive_skips = 0

    def validate_config(self) -> bool:
        """Validate configuration"""
        if self.scroll_duration <= 0:
            self.logger.error("scroll_duration must be positive")
            return False
        return True

    def run(self) -> Dict:
        """Execute feed engagement automation"""
        if not self.validate_config():
            return {'error': 'Invalid configuration'}

        if not self.client:
            self.logger.warning("LinkedIn client not available - simulation mode")
            return self._simulate_engagement()

        print(f"📱 Opening LinkedIn feed... ready to engage for {self.scroll_duration} minutes")

        # Reset counters
        self.likes_count = 0
        self.comments_count = 0
        self.shares_count = 0
        self.consecutive_skips = 0

        # Navigate to LinkedIn feed
        self.client.driver.get("https://www.linkedin.com/feed/")
        time.sleep(3)
        print("👀 Browsing feed, looking for interesting posts...")

        start_time = time.time()
        duration_seconds = self.scroll_duration * 60
        posts_processed = 0

        while time.time() - start_time < duration_seconds:
            # Get feed posts
            posts = self._get_feed_posts()

            for post in posts[:5]:  # Process up to 5 posts per scroll
                if time.time() - start_time >= duration_seconds:
                    break

                # Analyze and engage with post
                self._engage_with_post(post)
                posts_processed += 1

                # Check if we've hit limits
                if (self.likes_count >= self.max_likes and
                    self.comments_count >= self.max_comments and
                    self.shares_count >= self.max_shares):
                    print("\n✋ Reached engagement limits for this session, wrapping up...")
                    self.logger.info("Engagement limits reached")
                    break

                self.human_delay(10, 20)

            # Scroll down for more posts
            print("📜 Scrolling to see more posts...")
            self.client.driver.execute_script("window.scrollBy(0, 800);")
            time.sleep(2)

        print(f"\n✅ Finished browsing! Engaged with {posts_processed} posts")
        print(f"   💙 {self.likes_count} likes")
        print(f"   💬 {self.comments_count} comments")
        print(f"   🔄 {self.shares_count} shares")

        return {
            'posts_processed': posts_processed,
            'likes': self.likes_count,
            'comments': self.comments_count,
            'shares': self.shares_count
        }

    def _get_feed_posts(self) -> List:
        """
        Get visible posts from feed

        Returns:
            List of post elements
        """
        try:
            posts = self.client.driver.find_elements(
                By.CSS_SELECTOR,
                ".feed-shared-update-v2"
            )
            return posts
        except Exception as e:
            self.logger.error(f"Error getting feed posts: {e}")
            return []

    def _get_post_text(self, post_element) -> str:
        """Extract text content from post"""
        try:
            text_elem = post_element.find_element(
                By.CSS_SELECTOR,
                ".feed-shared-text, .feed-shared-update-v2__description"
            )
            return text_elem.text
        except:
            return ""

    def _should_engage_with_post(self, post_text: str) -> bool:
        """
        Determine if we should engage with a post based on keywords

        Args:
            post_text: Post content text

        Returns:
            True if should engage, False otherwise
        """
        post_text_lower = post_text.lower()

        # Check avoid keywords first
        for keyword in self.avoid_keywords:
            if keyword.lower() in post_text_lower:
                self.logger.debug(f"Avoiding post containing: {keyword}")
                return False

        # Check target keywords
        if not self.target_keywords:
            return True  # Engage with all if no keywords specified

        for keyword in self.target_keywords:
            if keyword.lower() in post_text_lower:
                self.logger.debug(f"Post matches keyword: {keyword}")
                return True

        return False

    def _engage_with_post(self, post_element):
        """
        Engage with a post (like, comment, or share)

        Args:
            post_element: Selenium WebElement for the post
        """
        try:
            # Get post text
            post_text = self._get_post_text(post_element)

            if post_text:
                print("   📖 Reading this post...")

            # Check if we should engage based on keywords
            should_engage = self._should_engage_with_post(post_text)

            # If not relevant, check skip counter
            if not should_engage:
                self.consecutive_skips += 1

                # If we've skipped too many, engage anyway
                if self.consecutive_skips >= self.max_skips_before_engage:
                    print(f"   🤷 Skipped {self.consecutive_skips} posts, this one looks good enough!")
                    self.consecutive_skips = 0  # Reset counter
                else:
                    print("   ⏭️  Not quite relevant, moving on...")
                    return

            # If we're engaging, reset skip counter
            if should_engage:
                self.consecutive_skips = 0

            # Like the post
            if self.likes_count < self.max_likes:
                if self._like_post(post_element):
                    self.likes_count += 1
                    self.record_action('feed_like')

            # Comment on post (less frequent)
            if self.comments_count < self.max_comments and len(post_text) > 50:
                if self.check_safety_limits('feed_comment'):
                    if self._comment_on_post(post_element, post_text):
                        self.comments_count += 1
                        self.record_action('feed_comment')

        except Exception as e:
            self.logger.error(f"Error engaging with post: {e}")

    def _like_post(self, post_element) -> bool:
        """Like a post"""
        try:
            like_button = post_element.find_element(
                By.CSS_SELECTOR,
                "button.react-button__trigger, button[aria-label*='Like']"
            )

            # Check if already liked
            aria_pressed = like_button.get_attribute('aria-pressed')
            if aria_pressed == 'true':
                return False

            like_button.click()
            print("   💙 This looks interesting, giving it a like...")
            return True

        except Exception as e:
            return False

    def _comment_on_post(self, post_element, post_text: str) -> bool:
        """Comment on a post with AI-generated comment"""
        try:
            print("   🤔 Hmm, thinking of what to comment...")

            # Generate comment using AI
            comment = self.ai_provider.generate_comment(
                post_content=post_text,
                tone='supportive',
                max_length=200
            )

            # Click comment button to open comment box
            comment_button = None
            try:
                comment_selectors = [
                    "button[aria-label*='Comment']",
                    "button.social-actions-button.comment-button",
                    "button.comment-button"
                ]

                for selector in comment_selectors:
                    try:
                        comment_button = post_element.find_element(By.CSS_SELECTOR, selector)
                        self.logger.debug(f"Found comment button with: {selector}")
                        break
                    except:
                        continue

                if not comment_button:
                    self.logger.error("Could not find comment button on post")
                    return False

                comment_button.click()
                time.sleep(2)

            except Exception as e:
                self.logger.error(f"Failed to click comment button: {e}")
                return False

            # Find comment editor
            comment_editor = None
            try:
                editor_selectors = [
                    "div.ql-editor[contenteditable='true']",
                    "div[contenteditable='true']",
                    "div.comments-comment-box__form div[contenteditable='true']",
                    "div[role='textbox'][contenteditable='true']"
                ]

                for selector in editor_selectors:
                    try:
                        comment_editor = post_element.find_element(By.CSS_SELECTOR, selector)
                        self.logger.debug(f"Found comment editor with: {selector}")
                        break
                    except:
                        continue

                if not comment_editor:
                    self.logger.error("Could not find comment editor")
                    return False

            except Exception as e:
                self.logger.error(f"Failed to find comment editor: {e}")
                return False

            # Show abbreviated comment
            comment_preview = comment[:60] + "..." if len(comment) > 60 else comment
            print(f"   💬 Typing comment: \"{comment_preview}\"")

            # Use JavaScript to set the content (handles emojis and special characters)
            try:
                comment_editor.click()
                time.sleep(0.5)

                # JavaScript injection - bypasses ChromeDriver BMP limitations
                self.client.driver.execute_script(
                    "arguments[0].innerHTML = arguments[1];",
                    comment_editor,
                    comment
                )
                time.sleep(1)

            except Exception as e:
                self.logger.error(f"Failed to type comment: {e}")
                return False

            # Submit comment - LinkedIn uses dynamic Ember class names
            print("   📤 Looking for submit button...")
            try:
                submit_button = None
                selectors = [
                    # Based on your exact HTML structure
                    "button.comments-comment-box__submit-button--cr.artdeco-button--primary",  # Exact match
                    "button.comments-comment-box__submit-button--cr",  # Class with --cr suffix
                    "button[class*='comments-comment-box__submit-button']",  # Flexible wildcard
                    "button.artdeco-button--primary span.artdeco-button__text",  # Find by text content
                ]

                for selector in selectors:
                    try:
                        # Special handling for text-based selector
                        if 'span' in selector:
                            spans = self.client.driver.find_elements(By.CSS_SELECTOR, selector)
                            for span in spans:
                                if span.text.strip() == 'Comment' and span.is_displayed():
                                    # Get parent button
                                    parent = span.find_element(By.XPATH, '..')
                                    if parent.tag_name == 'button' and parent.is_enabled():
                                        submit_button = parent
                                        self.logger.debug("Found submit button via text content")
                                        break
                        else:
                            buttons = self.client.driver.find_elements(By.CSS_SELECTOR, selector)
                            # Find visible and enabled submit button with "Comment" text
                            for btn in buttons:
                                if btn.is_displayed() and btn.is_enabled():
                                    btn_text = btn.text.strip()
                                    if 'Comment' in btn_text:
                                        submit_button = btn
                                        self.logger.debug(f"Found submit button with selector: {selector}")
                                        break

                        if submit_button:
                            break
                    except Exception as e:
                        self.logger.debug(f"Selector {selector} failed: {e}")
                        continue

                if not submit_button:
                    self.logger.error("Could not find enabled comment submit button")
                    print("   ❌ Could not find submit button")
                    return False

                submit_button.click()
                time.sleep(1)
                print("   ✅ Comment posted!")

                self.logger.info(f"Successfully commented on post: {comment[:50]}...")
                return True

            except Exception as e:
                self.logger.error(f"Failed to submit comment: {e}")
                print(f"   ❌ Failed to submit: {str(e)[:50]}")
                return False

        except Exception as e:
            self.logger.error(f"Error in _comment_on_post: {e}")
            print(f"   ❌ Comment failed: {str(e)[:50]}")
            return False

    def _simulate_engagement(self) -> Dict:
        """Simulate engagement when client is not available"""
        import random

        simulated_posts = random.randint(10, 20)
        simulated_likes = min(random.randint(5, 15), self.max_likes)
        simulated_comments = min(random.randint(1, 4), self.max_comments)

        self.logger.info("SIMULATION: Feed engagement")
        self.logger.info(f"  Posts processed: {simulated_posts}")
        self.logger.info(f"  Likes: {simulated_likes}")
        self.logger.info(f"  Comments: {simulated_comments}")

        return {
            'posts_processed': simulated_posts,
            'likes': simulated_likes,
            'comments': simulated_comments,
            'shares': 0,
            'simulated': True
        }
