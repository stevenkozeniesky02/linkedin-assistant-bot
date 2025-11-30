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
