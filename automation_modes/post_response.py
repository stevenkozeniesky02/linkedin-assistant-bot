"""Post Response Automation Mode

Monitors and responds to comments on your posts
"""

from typing import Dict, List
from .base import AutomationMode
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from database.models import Activity
import time


class PostResponseMode(AutomationMode):
    """Auto-respond to comments on your LinkedIn posts"""

    def __init__(self, config, linkedin_client, ai_provider, db_session, safety_monitor):
        super().__init__(
            name='post_response',
            config=config.get('post_response', {}),
            linkedin_client=linkedin_client,
            ai_provider=ai_provider,
            db_session=db_session,
            safety_monitor=safety_monitor
        )

        self.check_interval = self.config.get('check_interval_minutes', 60)
        self.auto_reply = self.config.get('auto_reply', True)
        self.max_replies = self.config.get('max_replies_per_check', 5)

    def validate_config(self) -> bool:
        """Validate configuration"""
        return self.check_interval > 0

    def run(self) -> Dict:
        """Check and respond to post comments"""
        if not self.client:
            return self._simulate()

        print(f"📬 Checking your posts for new comments...")
        self.logger.info("Checking for new comments on posts")

        # Navigate to your recent activity
        self.client.driver.get("https://www.linkedin.com/in/me/recent-activity/all/")
        time.sleep(3)

        print("📋 Looking through your recent posts...")

        # Scroll to load posts
        self.client.driver.execute_script("window.scrollTo(0, 800);")
        time.sleep(2)

        # Get posts with comments
        posts_with_comments = self._get_posts_with_comments()
        posts_checked = len(posts_with_comments)

        print(f"   Found {posts_checked} posts with comments")

        comments_found = 0
        replies_sent = 0

        # Process each post with comments
        for i, post_info in enumerate(posts_with_comments[:5]):
            if replies_sent >= self.max_replies:
                print(f"\n✋ Reached max replies limit ({self.max_replies}), stopping...")
                break

            print(f"\n📝 Opening post {i+1} to check comments...")

            # Click the comment button to expand comments inline
            try:
                # Scroll into view to avoid interception
                btn = post_info['comment_button']
                self.client.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                time.sleep(0.5)

                # Use JavaScript click to avoid interception (expands comments on same page)
                self.client.driver.execute_script("arguments[0].click();", btn)
                time.sleep(2)  # Wait for comments to expand

                # Now comments should be expanded inline - find them
                comments = self._get_post_comments()

                if comments:
                    print(f"   💬 Found {len(comments)} comment(s)")
                    comments_found += len(comments)

                    # Reply to comments
                    for comment in comments:
                        if replies_sent >= self.max_replies:
                            break

                        if self._should_reply_to_comment(comment):
                            if self._reply_to_comment(comment):
                                replies_sent += 1
                                self.record_action('post_reply')
                                print(f"   ✅ Replied! ({replies_sent}/{self.max_replies})")

                            self.human_delay(10, 20)
                else:
                    print("   ⚠️ Comments didn't expand - trying again...")

                # Scroll back to top for next post
                self.client.driver.execute_script("window.scrollTo(0, 800);")
                time.sleep(1)

            except Exception as e:
                self.logger.error(f"Error processing post {i+1}: {e}")
                continue

        print(f"\n✅ Finished checking posts!")
        print(f"   📊 Posts checked: {posts_checked}")
        print(f"   💬 Comments found: {comments_found}")
        print(f"   💙 Replies sent: {replies_sent}")

        return {
            'posts_checked': posts_checked,
            'comments_found': comments_found,
            'replies_sent': replies_sent
        }

    def _get_posts_with_comments(self) -> List:
        """Find posts that have comments"""
        posts_with_comments = []
        try:
            # Find all comment count buttons (generic selector)
            comment_buttons = self.client.driver.find_elements(
                By.CSS_SELECTOR,
                "button[aria-label*='comment on']"
            )

            for btn in comment_buttons:
                if btn.is_displayed() and "comment" in btn.text.lower():
                    posts_with_comments.append({
                        'comment_button': btn,
                        'comment_count': btn.text
                    })

            return posts_with_comments
        except Exception as e:
            self.logger.error(f"Error finding posts with comments: {e}")
            return []

    def _get_post_comments(self) -> List:
        """Get comments from current post page by finding Reply buttons"""
        try:
            time.sleep(2)  # Wait for comments to load

            # Find all Reply buttons - each one represents a comment
            reply_buttons = self.client.driver.find_elements(
                By.CSS_SELECTOR,
                "button.comments-comment-social-bar__reply-action-button--cr"
            )

            if not reply_buttons:
                # Fallback to aria-label selector
                reply_buttons = self.client.driver.find_elements(
                    By.CSS_SELECTOR,
                    "button[aria-label*='Reply to']"
                )

            if reply_buttons:
                self.logger.debug(f"Found {len(reply_buttons)} comments (via Reply buttons)")
                # Get parent elements containing each comment
                comment_containers = []
                for btn in reply_buttons:
                    # Get the parent container (go up a few levels to get the whole comment)
                    parent = btn
                    for _ in range(5):  # Go up 5 levels to get comment container
                        parent = parent.find_element(By.XPATH, "..")
                    comment_containers.append(parent)
                return comment_containers

            self.logger.warning("No comments found")
            return []
        except Exception as e:
            self.logger.error(f"Error getting comments: {e}")
            return []

    def _get_comment_text(self, comment_element) -> str:
        """Extract text from comment"""
        try:
            # Try multiple selectors for comment text (LinkedIn-specific)
            selectors = [
                # Most specific selectors first
                "span.comments-comment-item-content-body__text",
                ".comments-comment-item__main-content span",
                ".comments-comment-item-content-body",
                ".comments-comment-item__inline-show-more-text",
                # Broader selectors
                ".comments-comment-item__main-content",
                ".comments-comment-item-content",
                "div[dir='ltr']",  # LinkedIn uses dir='ltr' for text content
                ".feed-shared-text",
                "span.break-words",
                # Find any span that's not a button
                "span:not([class*='button']):not([class*='social'])"
            ]

            for selector in selectors:
                try:
                    # Try to find all matching elements
                    text_elems = comment_element.find_elements(By.CSS_SELECTOR, selector)
                    for text_elem in text_elems:
                        text = text_elem.text.strip()
                        # Check that it's actual comment text, not "Like", "Reply", etc.
                        if text and len(text) > 10 and text.lower() not in ['like', 'reply', 'react']:
                            self.logger.debug(f"Found comment text with selector: {selector}")
                            return text
                except:
                    continue

            # If nothing found, get all text but filter out common button text
            full_text = comment_element.text.strip()
            if full_text:
                # Split by lines and filter out button text
                lines = [line.strip() for line in full_text.split('\n')]
                # Filter out common UI elements
                filtered_lines = [
                    line for line in lines
                    if line and
                    line.lower() not in ['like', 'reply', 'react', 'see more', 'see less'] and
                    not line.isdigit() and  # Filter out reaction counts like "1", "2"
                    len(line) > 3  # Must be longer than 3 chars
                ]
                if filtered_lines:
                    # Join and return the longest line (likely the comment)
                    comment_text = max(filtered_lines, key=len)
                    self.logger.debug(f"Using filtered text: {comment_text[:50]}")
                    return comment_text

            return ""
        except Exception as e:
            self.logger.error(f"Error extracting comment text: {e}")
            return ""

    def _get_comment_author(self, comment_element) -> str:
        """Extract author name from comment"""
        try:
            # Try multiple selectors for author name
            selectors = [
                ".comments-post-meta__name-text",
                "span.hoverable-link-text",
                "a[href*='/in/']",  # Profile links
                ".comment-author"
            ]

            for selector in selectors:
                try:
                    author_elem = comment_element.find_element(By.CSS_SELECTOR, selector)
                    author = author_elem.text.strip()
                    if author:
                        return author
                except:
                    continue

            return "Someone"
        except:
            return "Someone"

    def _should_reply_to_comment(self, comment_element) -> bool:
        """Determine if we should reply to this comment"""
        try:
            # Get comment ID to track if we've replied
            comment_id = comment_element.get_attribute("data-id")
            if not comment_id:
                comment_text = self._get_comment_text(comment_element)
                comment_id = str(hash(comment_text)) if comment_text else None

            if not comment_id:
                return False

            # Check database for existing reply
            existing_reply = self.db_session.query(Activity).filter_by(
                action_type='post_reply',
                target_id=comment_id
            ).first()

            if existing_reply:
                self.logger.info(f"Already replied to comment {comment_id}, skipping")
                return False

            # Check if it's your own comment
            comment_text = self._get_comment_text(comment_element)
            if not comment_text or len(comment_text) < 5:
                return False

            return True
        except Exception as e:
            self.logger.error(f"Error checking if should reply: {e}")
            return False

    def _reply_to_comment(self, comment_element) -> bool:
        """Reply to a comment"""
        try:
            comment_text = self._get_comment_text(comment_element)
            author = self._get_comment_author(comment_element)

            if not comment_text:
                return False

            print(f"   👤 {author} commented: \"{comment_text[:50]}...\"")
            print("   🤔 Thinking of a reply...")

            # Generate reply using AI
            reply = self.ai_provider.generate_comment(
                post_content=comment_text,
                tone='friendly',
                max_length=150
            )

            # Show reply preview
            reply_preview = reply[:60] + "..." if len(reply) > 60 else reply
            print(f"   💬 Replying: \"{reply_preview}\"")

            # Find reply button for this comment (from user's HTML)
            try:
                # Look for "Reply" button within this comment
                reply_button = comment_element.find_element(
                    By.CSS_SELECTOR,
                    "button.comments-comment-social-bar__reply-action-button--cr"
                )
                reply_button.click()
                time.sleep(1.5)
            except Exception as e:
                # Fallback to aria-label selector
                try:
                    reply_button = comment_element.find_element(
                        By.CSS_SELECTOR,
                        "button[aria-label*='Reply to']"
                    )
                    reply_button.click()
                    time.sleep(1.5)
                except Exception as e2:
                    self.logger.error(f"Could not find reply button: {e2}")
                    return False

            # Find reply editor (should appear WITHIN this comment after clicking Reply)
            try:
                time.sleep(1)  # Wait for reply box to appear

                # Find the editor within the comment element's context
                reply_editor = None
                try:
                    # Look for editor within this specific comment
                    reply_editor = comment_element.find_element(
                        By.CSS_SELECTOR,
                        "div.ql-editor[contenteditable='true']"
                    )
                except:
                    # Fallback: find the most recently appeared editor
                    editors = self.client.driver.find_elements(
                        By.CSS_SELECTOR,
                        "div.ql-editor[contenteditable='true']"
                    )
                    # Get the last visible one (most recent)
                    for editor in reversed(editors):
                        if editor.is_displayed():
                            reply_editor = editor
                            break

                if not reply_editor:
                    self.logger.error("Could not find reply editor")
                    return False

                # Click to focus
                reply_editor.click()
                time.sleep(0.5)

                # Use JavaScript to set the content
                self.client.driver.execute_script(
                    "arguments[0].innerHTML = arguments[1];",
                    reply_editor,
                    reply
                )
                time.sleep(1)

            except Exception as e:
                self.logger.error(f"Failed to type reply: {e}")
                return False

            # Submit reply - look for "Reply" text, not "Comment"
            try:
                submit_button = None
                selectors = [
                    "button.comments-comment-box__submit-button--cr",
                    "button[class*='comments-comment-box__submit-button']",
                ]

                for selector in selectors:
                    try:
                        buttons = self.client.driver.find_elements(By.CSS_SELECTOR, selector)
                        for btn in buttons:
                            if btn.is_displayed() and btn.is_enabled():
                                btn_text = btn.text.strip()
                                # Look for "Reply" text specifically
                                if 'Reply' in btn_text:
                                    submit_button = btn
                                    break
                        if submit_button:
                            break
                    except:
                        continue

                if not submit_button:
                    self.logger.error("Could not find submit button")
                    return False

                submit_button.click()
                time.sleep(1.5)

                # Mark as replied in database
                comment_id = comment_element.get_attribute("data-id")
                if not comment_id:
                    comment_id = str(hash(comment_text))

                # Create activity record
                activity = Activity(
                    action_type='post_reply',
                    target_type='comment',
                    target_id=comment_id,
                    success=True
                )
                self.db_session.add(activity)
                self.db_session.commit()

                self.logger.info(f"Successfully replied to comment from {author}")
                return True

            except Exception as e:
                self.logger.error(f"Failed to submit reply: {e}")
                return False

        except Exception as e:
            self.logger.error(f"Error replying to comment: {e}")
            return False

    def _simulate(self) -> Dict:
        """Simulate post response"""
        self.logger.info("SIMULATION: Post response mode")
        return {
            'posts_checked': 5,
            'comments_found': 3,
            'replies_sent': 2,
            'simulated': True
        }
