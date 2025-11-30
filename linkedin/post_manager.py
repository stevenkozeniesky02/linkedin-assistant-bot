"""LinkedIn Post Management"""

import time
from typing import Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class PostManager:
    """Manages LinkedIn post creation and publishing"""

    def __init__(self, client):
        """
        Initialize PostManager

        Args:
            client: LinkedInClient instance
        """
        self.client = client
        self.driver = client.driver

    def create_post(self, content: str, wait_for_confirmation: bool = True) -> bool:
        """
        Create and publish a LinkedIn post

        Args:
            content: The post content to publish
            wait_for_confirmation: If True, wait for user to confirm before posting

        Returns:
            True if post was published successfully, False otherwise
        """
        if not self.client.is_logged_in():
            raise Exception("Must be logged in to create posts")

        try:
            # Navigate to feed
            self.client.navigate_to_feed()
            time.sleep(3)

            # Find and click the "Start a post" button
            # LinkedIn has multiple ways to start a post, try different selectors
            post_button = None
            selectors = [
                "button.artdeco-button--muted",
                "button.share-box-feed-entry__trigger",
                "button[aria-label*='Start a post']",
                ".share-box-feed-entry__trigger"
            ]

            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        if "start a post" in elem.text.lower():
                            post_button = elem
                            break
                    if post_button:
                        break
                except NoSuchElementException:
                    continue

            if not post_button:
                print("Could not find 'Start a post' button")
                return False

            # Scroll element into view
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", post_button)
            time.sleep(1)

            # Use JavaScript click to avoid interception
            try:
                self.driver.execute_script("arguments[0].click();", post_button)
            except Exception as e:
                # Fallback to regular click
                try:
                    post_button.click()
                except Exception as e2:
                    print(f"Could not click 'Start a post' button: {e2}")
                    return False

            time.sleep(3)

            # Find the text editor
            # LinkedIn uses a contenteditable div
            editor = None
            editor_selectors = [
                "div.ql-editor[contenteditable='true']",
                "div[aria-label*='Text editor']",
                "div.ql-editor",
                "div[contenteditable='true'][role='textbox']"
            ]

            for selector in editor_selectors:
                try:
                    editor = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    if editor:
                        print(f"Found editor with selector: {selector}")
                        break
                except TimeoutException:
                    continue

            if not editor:
                print("Could not find post editor")
                return False

            # Scroll editor into view and click
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", editor)
            time.sleep(1)

            # Click to focus
            self.driver.execute_script("arguments[0].click();", editor)
            time.sleep(1)

            # Type the content using JavaScript for more reliable input
            # This avoids issues with contenteditable divs
            self.driver.execute_script(
                "arguments[0].innerHTML = arguments[1];",
                editor,
                content.replace('\n', '<br>')
            )
            time.sleep(2)

            # Show preview to user if confirmation required
            if wait_for_confirmation:
                print("\n" + "="*60)
                print("POST PREVIEW:")
                print("="*60)
                print(content)
                print("="*60)

                response = input("\nPost this to LinkedIn? (yes/no): ").strip().lower()

                if response not in ['yes', 'y']:
                    print("Post cancelled by user")

                    # Close the post dialog
                    try:
                        close_button = self.driver.find_element(By.CSS_SELECTOR, "button[aria-label*='Dismiss']")
                        close_button.click()
                    except:
                        # Press Escape as fallback
                        editor.send_keys(Keys.ESCAPE)

                    return False

            # Find and click the Post button
            post_publish_button = None
            publish_selectors = [
                "button.share-actions__primary-action",
                "button[aria-label*='Post']",
                "button[data-test-share-box-post-button]",
                ".share-actions__primary-action"
            ]

            for selector in publish_selectors:
                try:
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for btn in buttons:
                        # Look for button with "Post" text
                        if btn.is_displayed() and ("post" in btn.text.lower() or btn.get_attribute("aria-label")):
                            post_publish_button = btn
                            break
                    if post_publish_button:
                        break
                except NoSuchElementException:
                    continue

            if not post_publish_button:
                print("Could not find Post button")
                return False

            # Scroll into view and use JavaScript click
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", post_publish_button)
            time.sleep(1)

            try:
                self.driver.execute_script("arguments[0].click();", post_publish_button)
            except Exception as e:
                # Fallback to regular click
                try:
                    post_publish_button.click()
                except Exception as e2:
                    print(f"Could not click Post button: {e2}")
                    return False

            time.sleep(5)

            print("✓ Post published successfully!")
            return True

        except Exception as e:
            print(f"Error creating post: {e}")
            return False

    def get_recent_posts(self, limit: int = 5) -> list:
        """
        Get recent posts from user's profile

        Args:
            limit: Maximum number of posts to retrieve

        Returns:
            List of post data dictionaries
        """
        if not self.client.is_logged_in():
            raise Exception("Must be logged in to get posts")

        try:
            # Navigate to own profile
            self.driver.get("https://www.linkedin.com/in/me/")
            time.sleep(3)

            # Scroll to posts section
            self.driver.execute_script("window.scrollTo(0, 800);")
            time.sleep(2)

            posts = []

            # Find post elements (this is a simplified version)
            post_elements = self.driver.find_elements(By.CSS_SELECTOR, ".feed-shared-update-v2")[:limit]

            for post_elem in post_elements:
                try:
                    # Extract post text
                    text_elem = post_elem.find_element(By.CSS_SELECTOR, ".feed-shared-text")
                    text = text_elem.text if text_elem else ""

                    # Extract engagement metrics (simplified)
                    posts.append({
                        "text": text,
                        "element": post_elem
                    })
                except:
                    continue

            return posts

        except Exception as e:
            print(f"Error getting recent posts: {e}")
            return []

    def delete_post(self, post_url: str) -> bool:
        """
        Delete a post (placeholder - requires more complex logic)

        Args:
            post_url: URL of the post to delete

        Returns:
            True if successful, False otherwise
        """
        print("Delete functionality not yet implemented")
        return False
