"""LinkedIn Browser Automation Client"""

import os
import time
import random
import pickle
from typing import Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions


class LinkedInClient:
    """Handles browser automation and session management for LinkedIn"""

    def __init__(self, config: dict):
        """
        Initialize LinkedIn client

        Args:
            config: Configuration dictionary from config.yaml
        """
        self.config = config
        self.linkedin_config = config.get('linkedin', {})

        # Browser settings
        self.headless = self.linkedin_config.get('headless', False)
        self.browser_type = self.linkedin_config.get('browser', 'chrome')

        # Rate limiting
        self.min_delay = self.linkedin_config.get('min_delay_between_actions', 30)
        self.max_delay = self.linkedin_config.get('max_delay_between_actions', 120)

        # Session management
        self.save_session = self.linkedin_config.get('save_session', True)
        self.session_file = self.linkedin_config.get('session_file', 'linkedin_session.pkl')

        # Browser driver
        self.driver = None
        self.logged_in = False

    def _get_driver(self):
        """Initialize and return the appropriate browser driver"""

        if self.browser_type.lower() == 'chrome':
            options = ChromeOptions()
            if self.headless:
                options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)

            # Add user agent to appear more human
            options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

            driver = webdriver.Chrome(options=options)

        elif self.browser_type.lower() == 'firefox':
            options = FirefoxOptions()
            if self.headless:
                options.add_argument('--headless')

            driver = webdriver.Firefox(options=options)

        else:
            raise ValueError(f"Unsupported browser: {self.browser_type}")

        # Set implicit wait
        driver.implicitly_wait(10)

        return driver

    def start(self):
        """Start the browser session"""
        if self.driver is None:
            self.driver = self._get_driver()
            print("Browser session started")

    def stop(self):
        """Stop the browser session"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.logged_in = False
            print("Browser session stopped")

    def _save_cookies(self):
        """Save cookies to file for session persistence"""
        if self.save_session and self.driver:
            try:
                cookies = self.driver.get_cookies()
                with open(self.session_file, 'wb') as f:
                    pickle.dump(cookies, f)
                print(f"Session saved to {self.session_file}")
            except Exception as e:
                print(f"Error saving session: {e}")

    def _load_cookies(self):
        """Load cookies from file to restore session"""
        if self.save_session and os.path.exists(self.session_file):
            try:
                with open(self.session_file, 'rb') as f:
                    cookies = pickle.load(f)

                # Need to be on LinkedIn domain to add cookies
                self.driver.get("https://www.linkedin.com")
                time.sleep(2)

                for cookie in cookies:
                    # Remove expiry if present (can cause issues)
                    if 'expiry' in cookie:
                        del cookie['expiry']
                    try:
                        self.driver.add_cookie(cookie)
                    except Exception as e:
                        print(f"Could not add cookie: {e}")

                # Refresh to apply cookies
                self.driver.refresh()
                time.sleep(3)

                print(f"Session loaded from {self.session_file}")
                return True
            except Exception as e:
                print(f"Error loading session: {e}")
                return False
        return False

    def login(self, email: Optional[str] = None, password: Optional[str] = None):
        """
        Login to LinkedIn

        Args:
            email: LinkedIn email (uses env var if not provided)
            password: LinkedIn password (uses env var if not provided)
        """
        if not self.driver:
            self.start()

        # Try to load existing session first
        if self._load_cookies():
            # Check if still logged in
            self.driver.get("https://www.linkedin.com/feed/")
            time.sleep(3)

            # If we see the feed, we're logged in
            if "feed" in self.driver.current_url:
                self.logged_in = True
                print("Successfully logged in using saved session")
                return True

        # Get credentials
        email = email or os.getenv('LINKEDIN_EMAIL')
        password = password or os.getenv('LINKEDIN_PASSWORD')

        if not email or not password:
            raise ValueError("LinkedIn email and password required (set in .env or pass as arguments)")

        # Go to login page
        self.driver.get("https://www.linkedin.com/login")
        time.sleep(2)

        try:
            # Find and fill email
            email_field = self.driver.find_element(By.ID, "username")
            email_field.clear()
            email_field.send_keys(email)

            # Find and fill password
            password_field = self.driver.find_element(By.ID, "password")
            password_field.clear()
            password_field.send_keys(password)

            # Click login button
            login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()

            # Wait for navigation
            time.sleep(5)

            # Check if login was successful
            if "feed" in self.driver.current_url or "mynetwork" in self.driver.current_url:
                self.logged_in = True
                self._save_cookies()
                print("Successfully logged in")
                return True
            else:
                # Check for security challenge
                if "checkpoint" in self.driver.current_url or "challenge" in self.driver.current_url:
                    print("\n⚠️  LinkedIn security challenge detected!")
                    print("Please complete the security verification in the browser window.")
                    print("Waiting for you to complete the challenge...")

                    # Wait up to 5 minutes for user to complete challenge
                    wait_time = 300
                    start_time = time.time()

                    while time.time() - start_time < wait_time:
                        if "feed" in self.driver.current_url:
                            self.logged_in = True
                            self._save_cookies()
                            print("Security challenge completed successfully!")
                            return True
                        time.sleep(5)

                    print("Timeout waiting for security challenge completion")
                    return False
                else:
                    print("Login failed - please check credentials")
                    return False

        except Exception as e:
            print(f"Error during login: {e}")
            return False

    def is_logged_in(self) -> bool:
        """Check if currently logged in"""
        return self.logged_in

    def random_delay(self, min_seconds: Optional[int] = None, max_seconds: Optional[int] = None):
        """
        Add a random delay to appear more human

        Args:
            min_seconds: Minimum delay (uses config if not provided)
            max_seconds: Maximum delay (uses config if not provided)
        """
        min_s = min_seconds or self.min_delay
        max_s = max_seconds or self.max_delay

        delay = random.uniform(min_s, max_s)
        print(f"Waiting {delay:.1f} seconds...")
        time.sleep(delay)

    def get_feed_url(self) -> str:
        """Get the LinkedIn feed URL"""
        return "https://www.linkedin.com/feed/"

    def navigate_to_feed(self):
        """Navigate to the LinkedIn feed"""
        if not self.logged_in:
            raise Exception("Must be logged in to navigate to feed")

        self.driver.get(self.get_feed_url())
        time.sleep(3)

    # ========================================
    # CONNECTION REQUEST METHODS
    # ========================================

    def send_connection_request(self, profile_url: str, message: Optional[str] = None) -> bool:
        """
        Send a connection request to a LinkedIn profile

        Args:
            profile_url: The LinkedIn profile URL
            message: Optional personalized message (max 300 characters)

        Returns:
            True if successful, False otherwise
        """
        if not self.logged_in:
            raise Exception("Must be logged in to send connection requests")

        try:
            # Navigate to profile
            self.driver.get(profile_url)
            time.sleep(3)

            # Look for "Connect" button
            connect_button = None
            try:
                # Try different selectors for the Connect button
                connect_selectors = [
                    "//button[contains(@aria-label, 'Invite') and contains(@aria-label, 'to connect')]",
                    "//button[.//span[contains(text(), 'Connect')]]",
                    "//button[@aria-label='Connect']",
                    "//span[text()='Connect']/ancestor::button"
                ]

                for selector in connect_selectors:
                    try:
                        connect_button = self.driver.find_element(By.XPATH, selector)
                        if connect_button:
                            break
                    except NoSuchElementException:
                        continue

            except Exception as e:
                print(f"Error finding Connect button: {e}")
                return False

            if not connect_button:
                print("Could not find Connect button - user may already be a connection or pending")
                return False

            # Click the Connect button
            connect_button.click()
            time.sleep(2)

            # If there's a message, add it
            if message:
                try:
                    # Look for "Add a note" button
                    add_note_button = self.driver.find_element(
                        By.XPATH,
                        "//button[@aria-label='Add a note' or contains(text(), 'Add a note')]"
                    )
                    add_note_button.click()
                    time.sleep(1)

                    # Find the message textarea
                    message_box = self.driver.find_element(
                        By.XPATH,
                        "//textarea[@name='message' or @id='custom-message']"
                    )

                    # LinkedIn has a 300 character limit for connection messages
                    truncated_message = message[:300] if len(message) > 300 else message
                    message_box.send_keys(truncated_message)
                    time.sleep(1)

                except Exception as e:
                    print(f"Warning: Could not add personalized message: {e}")

            # Click Send button
            try:
                send_button = self.driver.find_element(
                    By.XPATH,
                    "//button[@aria-label='Send now' or contains(@aria-label, 'Send invitation') or .//span[contains(text(), 'Send')]]"
                )
                send_button.click()
                time.sleep(2)

                print(f"✓ Connection request sent to {profile_url}")
                return True

            except Exception as e:
                print(f"Error clicking Send button: {e}")
                # Try to close any modal that might be open
                try:
                    dismiss_button = self.driver.find_element(By.XPATH, "//button[@aria-label='Dismiss']")
                    dismiss_button.click()
                except:
                    pass
                return False

        except Exception as e:
            print(f"Error sending connection request: {e}")
            return False

    def get_incoming_connection_requests(self) -> list:
        """
        Get list of incoming (pending) connection requests

        Returns:
            List of dictionaries with request details:
            [{
                'name': str,
                'title': str,
                'company': str,
                'profile_url': str,
                'mutual_connections': int,
                'request_id': str
            }, ...]
        """
        if not self.logged_in:
            raise Exception("Must be logged in to get connection requests")

        try:
            # Navigate to My Network page (where pending requests are shown)
            self.driver.get("https://www.linkedin.com/mynetwork/invitation-manager/")
            time.sleep(3)

            requests = []

            # Find all invitation cards
            try:
                invitation_cards = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    ".invitation-card, .mn-invitation-card"
                )

                for card in invitation_cards[:20]:  # Limit to first 20
                    try:
                        request_data = {}

                        # Get name
                        try:
                            name_elem = card.find_element(By.CSS_SELECTOR, ".invitation-card__name, .mn-invitation-card__name")
                            request_data['name'] = name_elem.text.strip()
                        except:
                            request_data['name'] = "Unknown"

                        # Get title
                        try:
                            title_elem = card.find_element(By.CSS_SELECTOR, ".invitation-card__subtitle, .mn-invitation-card__subtitle")
                            request_data['title'] = title_elem.text.strip()
                        except:
                            request_data['title'] = None

                        # Get profile URL
                        try:
                            link_elem = card.find_element(By.CSS_SELECTOR, "a[href*='/in/']")
                            request_data['profile_url'] = link_elem.get_attribute('href')
                        except:
                            request_data['profile_url'] = None

                        # Get mutual connections count
                        try:
                            mutual_elem = card.find_element(By.XPATH, ".//*[contains(text(), 'mutual connection')]")
                            mutual_text = mutual_elem.text
                            # Extract number from text like "5 mutual connections"
                            import re
                            match = re.search(r'(\d+)', mutual_text)
                            request_data['mutual_connections'] = int(match.group(1)) if match else 0
                        except:
                            request_data['mutual_connections'] = 0

                        # Get company (parse from subtitle if available)
                        if request_data.get('title') and ' at ' in request_data.get('title', ''):
                            parts = request_data['title'].split(' at ')
                            if len(parts) > 1:
                                request_data['company'] = parts[1].strip()
                                request_data['title'] = parts[0].strip()
                        else:
                            request_data['company'] = None

                        # Generate a pseudo request_id from profile URL
                        if request_data.get('profile_url'):
                            request_data['request_id'] = request_data['profile_url'].split('/in/')[-1].split('/')[0]
                        else:
                            request_data['request_id'] = None

                        requests.append(request_data)

                    except Exception as e:
                        print(f"Error parsing invitation card: {e}")
                        continue

            except Exception as e:
                print(f"Error finding invitation cards: {e}")

            return requests

        except Exception as e:
            print(f"Error getting incoming requests: {e}")
            return []

    def accept_connection_request(self, request_id: str) -> bool:
        """
        Accept an incoming connection request

        Args:
            request_id: The request ID (profile username)

        Returns:
            True if successful, False otherwise
        """
        if not self.logged_in:
            raise Exception("Must be logged in to accept connections")

        try:
            # Navigate to invitation manager
            self.driver.get("https://www.linkedin.com/mynetwork/invitation-manager/")
            time.sleep(3)

            # Find the invitation card for this profile
            try:
                # Find Accept button associated with this profile
                accept_button = self.driver.find_element(
                    By.XPATH,
                    f"//a[contains(@href, '/in/{request_id}')]/ancestor::li//button[@aria-label='Accept' or contains(@aria-label, 'Accept')]"
                )
                accept_button.click()
                time.sleep(2)

                print(f"✓ Accepted connection request from {request_id}")
                return True

            except NoSuchElementException:
                print(f"Could not find Accept button for {request_id}")
                return False

        except Exception as e:
            print(f"Error accepting connection request: {e}")
            return False

    def decline_connection_request(self, request_id: str) -> bool:
        """
        Decline an incoming connection request

        Args:
            request_id: The request ID (profile username)

        Returns:
            True if successful, False otherwise
        """
        if not self.logged_in:
            raise Exception("Must be logged in to decline connections")

        try:
            # Navigate to invitation manager
            self.driver.get("https://www.linkedin.com/mynetwork/invitation-manager/")
            time.sleep(3)

            try:
                # Find Ignore/Decline button
                ignore_button = self.driver.find_element(
                    By.XPATH,
                    f"//a[contains(@href, '/in/{request_id}')]/ancestor::li//button[@aria-label='Ignore' or contains(@aria-label, 'Ignore')]"
                )
                ignore_button.click()
                time.sleep(2)

                print(f"✓ Declined connection request from {request_id}")
                return True

            except NoSuchElementException:
                print(f"Could not find Ignore button for {request_id}")
                return False

        except Exception as e:
            print(f"Error declining connection request: {e}")
            return False

    # ========================================
    # MESSAGING METHODS
    # ========================================

    def send_message(self, profile_url: str, message_text: str) -> bool:
        """
        Send a direct message to a connection

        Args:
            profile_url: LinkedIn profile URL of the recipient
            message_text: The message text to send

        Returns:
            True if successful, False otherwise
        """
        if not self.logged_in:
            raise Exception("Must be logged in to send messages")

        try:
            # Navigate to profile
            self.driver.get(profile_url)
            time.sleep(3)

            # Click the Message button
            try:
                message_button = self.driver.find_element(
                    By.XPATH,
                    "//button[contains(@aria-label, 'Message') or .//span[text()='Message']]"
                )
                message_button.click()
                time.sleep(2)

            except NoSuchElementException:
                print("Could not find Message button - user may not be a connection")
                return False

            # Find the message input box
            try:
                # Wait for message box to appear
                message_box = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((
                        By.CSS_SELECTOR,
                        "div.msg-form__contenteditable, div[role='textbox']"
                    ))
                )

                # Type the message
                message_box.click()
                time.sleep(0.5)
                message_box.send_keys(message_text)
                time.sleep(1)

                # Find and click Send button
                send_button = self.driver.find_element(
                    By.XPATH,
                    "//button[contains(@class, 'msg-form__send-button') or @type='submit']"
                )
                send_button.click()
                time.sleep(2)

                print(f"✓ Message sent to {profile_url}")
                return True

            except Exception as e:
                print(f"Error sending message: {e}")
                return False

        except Exception as e:
            print(f"Error in send_message: {e}")
            return False

    def close_messaging_overlay(self):
        """Close the messaging overlay if it's open"""
        try:
            close_button = self.driver.find_element(
                By.XPATH,
                "//button[@aria-label='Close' or contains(@class, 'msg-overlay-bubble-header__control--close')]"
            )
            close_button.click()
            time.sleep(1)
        except:
            pass  # No overlay to close
