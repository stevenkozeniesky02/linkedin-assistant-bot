"""LinkedIn Engagement Management"""

import time
from typing import List, Dict, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class EngagementManager:
    """Manages LinkedIn engagement (comments, likes, connections)"""

    def __init__(self, client, config=None):
        """
        Initialize EngagementManager

        Args:
            client: LinkedInClient instance
            config: Configuration dictionary (optional)
        """
        self.client = client
        self.driver = client.driver
        self.config = config or {}

    def _is_promotional_or_low_quality(self, text: str, author: str) -> bool:
        """Check if a post is promotional or low-quality"""
        engagement_config = self.config.get('engagement', {})

        # Check if promotional filtering is enabled
        if not engagement_config.get('skip_promotional', True):
            return False  # Filtering disabled

        # Skip promotional content
        promo_keywords = [
            'earn $', 'get $', 'save $', 'bonus', 'discount', 'deal',
            'limited time', 'buy now', 'click here', 'sign up now',
            'register now', 'apply now', 'download now'
        ]
        text_lower = text.lower()
        for keyword in promo_keywords:
            if keyword in text_lower:
                return True

        # Skip posts from major corporate brands (from config)
        corporate_brands = engagement_config.get('skip_corporate_brands', [])
        corporate_indicators = corporate_brands + [
            'Get Started >>', 'Learn More >>', 'Apply Now >>'
        ]

        for indicator in corporate_indicators:
            if indicator in author or indicator in text:
                return True

        return False

    def get_feed_posts(self, limit: int = 10) -> List[Dict]:
        """
        Get posts from the LinkedIn feed, filtering out promotional and low-quality content

        Args:
            limit: Maximum number of quality posts to retrieve

        Returns:
            List of post data dictionaries
        """
        if not self.client.is_logged_in():
            raise Exception("Must be logged in to get feed posts")

        try:
            # Navigate to feed
            self.client.navigate_to_feed()
            time.sleep(3)

            posts = []
            scroll_attempts = 0
            max_scroll_attempts = 10  # Don't scroll forever
            seen_urls = set()  # Track unique posts by URL to avoid duplicates

            # Keep scrolling until we have enough quality posts
            while len(posts) < limit and scroll_attempts < max_scroll_attempts:
                # Scroll to load more posts
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                scroll_attempts += 1

                # Get all visible posts
                post_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.feed-shared-update-v2")

                print(f"Scroll {scroll_attempts}: Found {len(post_elements)} total posts in feed")

                for idx, post_elem in enumerate(post_elements):
                    # Stop if we have enough quality posts
                    if len(posts) >= limit:
                        break

                    try:
                        # Extract post author - updated selector
                        author = "Unknown"
                        try:
                            # Try new LinkedIn structure first
                            author_elem = post_elem.find_element(By.CSS_SELECTOR, ".update-components-actor__title")
                            author = author_elem.text.strip() if author_elem else "Unknown"
                        except:
                            try:
                                # Fallback to old structure
                                author_elem = post_elem.find_element(By.CSS_SELECTOR, ".feed-shared-actor__name")
                                author = author_elem.text.strip() if author_elem else "Unknown"
                            except:
                                pass

                        # Extract post text - updated selector
                        text = ""
                        try:
                            # Try new structure
                            text_elem = post_elem.find_element(By.CSS_SELECTOR, ".update-components-text")
                            text = text_elem.text.strip() if text_elem else ""
                        except:
                            try:
                                # Fallback to old structure
                                text_elem = post_elem.find_element(By.CSS_SELECTOR, ".feed-shared-text")
                                text = text_elem.text.strip() if text_elem else ""
                            except:
                                pass

                        # Skip posts with no text (images/videos only, or ads)
                        if not text or len(text) < 10:
                            print(f"Skipping post {idx} - no text content")
                            continue

                        # Get post URL (for reference and deduplication)
                        post_url = ""
                        try:
                            time_elem = post_elem.find_element(By.CSS_SELECTOR, "a.update-components-actor__meta-link")
                            post_url = time_elem.get_attribute("href") if time_elem else ""
                        except:
                            pass

                        # Skip duplicate posts
                        if post_url and post_url in seen_urls:
                            print(f"Skipping post {idx} - duplicate")
                            continue
                        if post_url:
                            seen_urls.add(post_url)

                        # Filter out promotional and low-quality posts
                        if self._is_promotional_or_low_quality(text, author):
                            print(f"Skipping post {idx} by {author} - promotional/low-quality")
                            continue

                        posts.append({
                            "index": len(posts),  # Use sequential index for quality posts
                            "author": author,
                            "text": text,
                            "url": post_url,
                            "element": post_elem
                        })

                        print(f"✓ Extracted quality post {len(posts)} by {author}")

                    except Exception as e:
                        print(f"Error extracting post {idx} data: {e}")
                        continue

            print(f"Successfully extracted {len(posts)} quality posts (filtered from {len(post_elements)} total)")
            return posts

        except Exception as e:
            print(f"Error getting feed posts: {e}")
            import traceback
            traceback.print_exc()
            return []

    def comment_on_post(self, post_element, comment_text: str, wait_for_confirmation: bool = True) -> bool:
        """
        Comment on a specific post

        Args:
            post_element: The Selenium WebElement representing the post
            comment_text: The comment to post
            wait_for_confirmation: If True, wait for user confirmation

        Returns:
            True if comment was posted successfully, False otherwise
        """
        if not self.client.is_logged_in():
            raise Exception("Must be logged in to comment")

        try:
            # Scroll post into view
            self.driver.execute_script("arguments[0].scrollIntoView(true);", post_element)
            time.sleep(1)

            # Find the comment button
            comment_button = None
            try:
                # Try multiple selectors for comment button
                selectors = [
                    "button[aria-label*='Comment']",
                    "button[aria-label*='comment']",
                    "button.social-actions-button[aria-label*='Comment']"
                ]

                for selector in selectors:
                    try:
                        comment_button = post_element.find_element(By.CSS_SELECTOR, selector)
                        print(f"Found comment button using selector: {selector}")
                        break
                    except NoSuchElementException:
                        continue

                if not comment_button:
                    raise NoSuchElementException("Comment button not found with any selector")

            except NoSuchElementException:
                print("Could not find comment button with any selector")
                print("Available buttons in post:")
                try:
                    buttons = post_element.find_elements(By.TAG_NAME, "button")
                    for btn in buttons[:5]:  # Show first 5 buttons
                        print(f"  - {btn.get_attribute('aria-label')} (class: {btn.get_attribute('class')})")
                except:
                    pass
                return False

            # Click to open comment box
            print("Clicking comment button...")
            comment_button.click()
            time.sleep(2)

            # Find the comment editor
            comment_editor = None
            try:
                # Try multiple selectors for comment editor
                selectors = [
                    "div.ql-editor[contenteditable='true']",
                    "div[contenteditable='true']",
                    "div.comments-comment-box__form div[contenteditable='true']",
                    "div[role='textbox'][contenteditable='true']"
                ]

                for selector in selectors:
                    try:
                        comment_editor = post_element.find_element(By.CSS_SELECTOR, selector)
                        print(f"Found comment editor using selector: {selector}")
                        break
                    except NoSuchElementException:
                        continue

                if not comment_editor:
                    raise NoSuchElementException("Comment editor not found with any selector")

            except NoSuchElementException:
                print("Could not find comment editor with any selector")
                print("Available contenteditable elements:")
                try:
                    editables = post_element.find_elements(By.CSS_SELECTOR, "[contenteditable='true']")
                    print(f"  Found {len(editables)} contenteditable elements")
                    for elem in editables[:3]:  # Show first 3
                        print(f"  - {elem.get_attribute('class')} (role: {elem.get_attribute('role')})")
                except:
                    pass
                return False

            # Show preview if confirmation required
            if wait_for_confirmation:
                print("\n" + "="*60)
                print("COMMENT PREVIEW:")
                print("="*60)
                print(comment_text)
                print("="*60)

                response = input("\nPost this comment? (yes/no): ").strip().lower()

                if response not in ['yes', 'y']:
                    print("Comment cancelled by user")
                    # Press Escape to cancel
                    comment_editor.send_keys(Keys.ESCAPE)
                    return False

            # Type the comment using JavaScript to avoid ChromeDriver encoding issues
            print("Typing comment into editor...")
            comment_editor.click()
            time.sleep(0.5)

            # Use JavaScript to set the content (handles emojis and special characters)
            self.driver.execute_script(
                "arguments[0].innerHTML = arguments[1];",
                comment_editor,
                comment_text
            )
            time.sleep(1)

            # Find and click the Post comment button
            post_comment_button = None
            try:
                # Try multiple selectors for post button
                # Note: LinkedIn uses dynamic classes like 'comments-comment-box__submit-button--cr'
                selectors = [
                    "button[class*='comments-comment-box__submit-button']",  # Partial class match
                    "button.artdeco-button--primary:has(span:contains('Comment'))",  # Has "Comment" text
                    "button.artdeco-button.artdeco-button--primary",  # Generic LinkedIn button
                    "button[type='submit']",
                    "button[aria-label*='Post']"
                ]

                for selector in selectors:
                    try:
                        # For the "contains" selector, we need to use XPath instead
                        if 'contains' in selector:
                            post_comment_button = post_element.find_element(By.XPATH,
                                ".//button[contains(@class, 'artdeco-button--primary')]//span[contains(text(), 'Comment')]/parent::button")
                        else:
                            post_comment_button = post_element.find_element(By.CSS_SELECTOR, selector)
                        print(f"Found post button using selector: {selector}")
                        break
                    except NoSuchElementException:
                        continue

                if not post_comment_button:
                    raise NoSuchElementException("Post comment button not found with any selector")

            except NoSuchElementException:
                print("Could not find post comment button with any selector")
                print("Available submit buttons:")
                try:
                    submit_buttons = post_element.find_elements(By.CSS_SELECTOR, "button[type='submit']")
                    print(f"  Found {len(submit_buttons)} submit buttons")
                    all_buttons = post_element.find_elements(By.TAG_NAME, "button")
                    print(f"  Total buttons in post area: {len(all_buttons)}")
                except:
                    pass
                return False

            # Click to post the comment
            print("Clicking post button...")
            post_comment_button.click()
            time.sleep(3)

            print("✓ Comment posted successfully!")
            return True

        except Exception as e:
            print(f"Error posting comment: {e}")
            return False

    def like_post(self, post_element) -> bool:
        """
        Like a specific post

        Args:
            post_element: The Selenium WebElement representing the post

        Returns:
            True if post was liked successfully, False otherwise
        """
        if not self.client.is_logged_in():
            raise Exception("Must be logged in to like posts")

        try:
            # Scroll post into view
            self.driver.execute_script("arguments[0].scrollIntoView(true);", post_element)
            time.sleep(1)

            # Find the like button
            like_button = None
            try:
                # Try to find the like button (it might already be liked)
                like_button = post_element.find_element(By.CSS_SELECTOR, "button[aria-label*='React']")
            except NoSuchElementException:
                print("Could not find like button")
                return False

            # Check if already liked
            aria_pressed = like_button.get_attribute("aria-pressed")
            if aria_pressed == "true":
                print("Post already liked")
                return True

            # Click the like button
            like_button.click()
            time.sleep(1)

            print("✓ Post liked successfully!")
            return True

        except Exception as e:
            print(f"Error liking post: {e}")
            return False

    def search_groups(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search for LinkedIn groups

        Args:
            query: Search query for groups
            limit: Maximum number of groups to return

        Returns:
            List of group data dictionaries
        """
        if not self.client.is_logged_in():
            raise Exception("Must be logged in to search groups")

        try:
            # Navigate to groups search
            search_url = f"https://www.linkedin.com/search/results/groups/?keywords={query}"
            self.driver.get(search_url)
            time.sleep(3)

            groups = []

            # Find group elements
            group_elements = self.driver.find_elements(By.CSS_SELECTOR, ".search-result")[:limit]

            for group_elem in group_elements:
                try:
                    # Extract group name
                    try:
                        name_elem = group_elem.find_element(By.CSS_SELECTOR, ".search-result__title")
                        name = name_elem.text if name_elem else "Unknown"
                    except:
                        name = "Unknown"

                    # Extract group member count
                    try:
                        member_elem = group_elem.find_element(By.CSS_SELECTOR, ".search-result__snippets")
                        members = member_elem.text if member_elem else "Unknown"
                    except:
                        members = "Unknown"

                    # Get group URL
                    try:
                        link_elem = group_elem.find_element(By.CSS_SELECTOR, "a.search-result__result-link")
                        url = link_elem.get_attribute("href") if link_elem else ""
                    except:
                        url = ""

                    groups.append({
                        "name": name,
                        "members": members,
                        "url": url,
                        "element": group_elem
                    })

                except Exception as e:
                    print(f"Error extracting group data: {e}")
                    continue

            return groups

        except Exception as e:
            print(f"Error searching groups: {e}")
            return []

    def join_group(self, group_url: str) -> bool:
        """
        Join a LinkedIn group

        Args:
            group_url: URL of the group to join

        Returns:
            True if joined successfully, False otherwise
        """
        if not self.client.is_logged_in():
            raise Exception("Must be logged in to join groups")

        try:
            # Navigate to group page
            self.driver.get(group_url)
            time.sleep(3)

            # Find join button
            join_button = None
            try:
                join_button = self.driver.find_element(By.CSS_SELECTOR, "button[aria-label*='Request to join']")
            except NoSuchElementException:
                try:
                    join_button = self.driver.find_element(By.CSS_SELECTOR, "button.group-actions__join-button")
                except NoSuchElementException:
                    print("Could not find join button (may already be a member)")
                    return False

            # Click join
            join_button.click()
            time.sleep(2)

            print("✓ Group join request sent!")
            return True

        except Exception as e:
            print(f"Error joining group: {e}")
            return False
