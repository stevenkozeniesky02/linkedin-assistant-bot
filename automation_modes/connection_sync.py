"""Connection Sync Automation Mode

Automatically scrapes and syncs LinkedIn connections to the database.
"""

import logging
import time
from typing import Dict, List, Optional
from datetime import datetime
from automation_modes.base import AutomationMode
from linkedin.connection_manager import ConnectionManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)


class ConnectionSyncMode(AutomationMode):
    """Scrape and sync LinkedIn connections to database"""

    def __init__(self, config: dict, linkedin_client, ai_provider, db_session, safety_monitor):
        super().__init__(
            name='connection_sync',
            config=config,
            linkedin_client=linkedin_client,
            ai_provider=ai_provider,
            db_session=db_session,
            safety_monitor=safety_monitor
        )

        self.connection_manager = ConnectionManager(db_session, {'connections': config})

        # Configuration
        self.max_connections = config.get('max_connections_to_sync', None)  # None = all
        self.scroll_duration = config.get('scroll_duration_minutes', 5)
        self.scroll_delay = config.get('scroll_delay_seconds', 2)

    def validate_config(self) -> bool:
        """Validate configuration"""
        return True

    def run(self) -> Dict:
        """
        Execute connection sync

        Returns:
            Dict with sync results
        """
        self.logger.info("Starting connection sync...")

        results = {
            'started_at': datetime.utcnow().isoformat(),
            'connections_synced': 0,
            'connections_updated': 0,
            'connections_new': 0,
            'errors': 0,
            'success': False
        }

        try:
            # Navigate to connections page
            print("🔗 Navigating to My Network -> Connections...")
            self.client.driver.get("https://www.linkedin.com/mynetwork/invite-connect/connections/")
            time.sleep(5)  # Wait for page to load

            # Scrape connections
            connections_data = self._scrape_all_connections()

            print(f"\n💾 Syncing {len(connections_data)} connections to database...")

            # Sync to database
            for conn_data in connections_data:
                try:
                    # Check if connection already exists
                    from database.models import Connection
                    existing = self.db_session.query(Connection).filter_by(
                        profile_url=conn_data['profile_url']
                    ).first()

                    if existing:
                        # Update existing connection
                        updated = False
                        if existing.title != conn_data.get('title'):
                            existing.title = conn_data.get('title')
                            updated = True
                        if existing.company != conn_data.get('company'):
                            existing.company = conn_data.get('company')
                            updated = True
                        if existing.location != conn_data.get('location'):
                            existing.location = conn_data.get('location')
                            updated = True

                        if updated:
                            existing.updated_at = datetime.utcnow()
                            results['connections_updated'] += 1
                    else:
                        # Add new connection
                        self.connection_manager.add_connection(
                            name=conn_data['name'],
                            profile_url=conn_data['profile_url'],
                            title=conn_data.get('title'),
                            company=conn_data.get('company'),
                            location=conn_data.get('location'),
                            connection_source='automated_sync'
                        )
                        results['connections_new'] += 1

                    results['connections_synced'] += 1

                    # Log progress
                    if results['connections_synced'] % 10 == 0:
                        print(f"  ✓ Synced {results['connections_synced']} connections...")

                except Exception as e:
                    self.logger.error(f"Error syncing connection {conn_data.get('name')}: {e}")
                    results['errors'] += 1
                    continue

            # Commit changes
            self.db_session.commit()

            results['success'] = True
            results['completed_at'] = datetime.utcnow().isoformat()

            print(f"\n✅ Connection sync complete!")
            print(f"   New: {results['connections_new']}")
            print(f"   Updated: {results['connections_updated']}")
            print(f"   Errors: {results['errors']}")

            self.logger.info(
                f"Connection sync complete: {results['connections_new']} new, "
                f"{results['connections_updated']} updated, {results['errors']} errors"
            )

        except Exception as e:
            self.logger.error(f"Connection sync failed: {e}")
            results['error'] = str(e)
            results['success'] = False
            import traceback
            traceback.print_exc()

        return results

    def _scrape_all_connections(self) -> List[Dict]:
        """
        Scrape all connections from LinkedIn

        Returns:
            List of connection dictionaries
        """
        print("🔍 Scrolling through connections...")

        connections = []
        seen_urls = set()

        start_time = time.time()
        duration_seconds = self.scroll_duration * 60
        scroll_attempts = 0
        max_scroll_attempts = 100  # Increased for more connections
        no_new_content_count = 0  # Track consecutive scrolls with no new content
        max_no_new_content = 5  # Stop after 5 scrolls with no new content

        while (time.time() - start_time < duration_seconds and
               scroll_attempts < max_scroll_attempts):

            # Scrape visible connections
            new_connections = self._scrape_visible_connections()

            # Add new connections (avoid duplicates)
            new_count = 0
            for conn in new_connections:
                if conn['profile_url'] not in seen_urls:
                    connections.append(conn)
                    seen_urls.add(conn['profile_url'])
                    new_count += 1

            if new_count > 0:
                print(f"  Found {len(connections)} total connections...")
                no_new_content_count = 0  # Reset counter when we find new content
            else:
                no_new_content_count += 1
                if no_new_content_count >= max_no_new_content:
                    print(f"  No new connections after {max_no_new_content} scrolls - reached end")
                    break

            # Check if we've hit the max limit
            if self.max_connections and len(connections) >= self.max_connections:
                print(f"  Reached max connections limit: {self.max_connections}")
                break

            # Scroll to load more
            scroll_success = self._scroll_to_load_more()

            scroll_attempts += 1
            time.sleep(self.scroll_delay)

        print(f"\n✓ Scraped {len(connections)} connections")
        return connections

    def _scrape_visible_connections(self) -> List[Dict]:
        """
        Scrape connections currently visible on page

        Returns:
            List of connection dictionaries
        """
        connections = []

        try:
            # LinkedIn uses different selectors for connections list
            # Try multiple selectors to handle different layouts
            selectors = [
                'div._4271d129',  # Current LinkedIn selector (2025)
                'div[componentkey^="auto-component-"]',
                'li.mn-connection-card',
                'li.reusable-search__result-container',
                '.mn-connection-card',
                'div[data-view-name="connections-list-item"]'
            ]

            connection_elements = []
            for selector in selectors:
                try:
                    elements = self.client.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        connection_elements = elements
                        self.logger.info(f"Found {len(elements)} elements with selector: {selector}")
                        print(f"  ✓ Found {len(elements)} elements using selector: {selector}")
                        break
                except:
                    continue

            if not connection_elements:
                self.logger.warning("No connection elements found on page")
                # Save page source for debugging
                page_source = self.client.driver.page_source
                with open('debug_connections_page.html', 'w', encoding='utf-8') as f:
                    f.write(page_source)
                print("  ⚠️  Saved page HTML to debug_connections_page.html for inspection")
                return connections

            for element in connection_elements:
                try:
                    conn_data = self._extract_connection_data(element)
                    if conn_data:
                        connections.append(conn_data)
                except Exception as e:
                    self.logger.debug(f"Error extracting connection data: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Error scraping visible connections: {e}")

        return connections

    def _extract_connection_data(self, element) -> Optional[Dict]:
        """
        Extract connection data from a connection element

        Args:
            element: Selenium WebElement

        Returns:
            Dict with connection data or None
        """
        try:
            # Extract profile URL (primary identifier)
            profile_url = None
            try:
                link_elem = element.find_element(By.CSS_SELECTOR, 'a[href*="/in/"]')
                href = link_elem.get_attribute('href')
                if href:
                    # Clean up URL (remove query params)
                    profile_url = href.split('?')[0]
            except:
                # If no link found, skip this connection
                return None

            if not profile_url:
                return None

            # Extract name - try multiple selectors
            name = None
            name_selectors = [
                'a.e9329a8f.fd2b8bc5',  # Current selector
                'p.f006b8b2 a',
                'a[href*="/in/"]'
            ]

            for selector in name_selectors:
                try:
                    name_elem = element.find_element(By.CSS_SELECTOR, selector)
                    name = name_elem.text.strip()
                    if name and name != "Message":  # Filter out button text
                        break
                except:
                    continue

            if not name:
                return None

            # Extract title/description from the second paragraph
            title = None
            try:
                # Find all paragraphs
                paragraphs = element.find_elements(By.CSS_SELECTOR, 'p.f006b8b2')
                # Usually: first is name, second is title, third is "Connected on..."
                for p in paragraphs:
                    text = p.text.strip()
                    # Skip if it's the name or connection date
                    if text and text != name and not text.startswith('Connected on'):
                        title = text
                        break
            except:
                pass

            # Extract company from title (usually "Title at Company")
            company = None
            if title and ' at ' in title:
                parts = title.split(' at ', 1)
                if len(parts) == 2:
                    # Keep full title for now, extract company
                    company = parts[1].strip()

            # Location not readily available in this layout
            location = None

            return {
                'name': name,
                'profile_url': profile_url,
                'title': title,
                'company': company,
                'location': location
            }

        except Exception as e:
            self.logger.debug(f"Error extracting connection data: {e}")
            return None

    def _scroll_to_load_more(self) -> bool:
        """
        Scroll page to load more connections

        Returns:
            True if scroll successful, False if reached end
        """
        try:
            # Get current scroll position
            previous_height = self.client.driver.execute_script("return document.body.scrollHeight")

            # Scroll to bottom
            self.client.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            # Wait for new content to load
            time.sleep(self.scroll_delay)

            # Check if page height changed
            new_height = self.client.driver.execute_script("return document.body.scrollHeight")

            return new_height > previous_height

        except Exception as e:
            self.logger.error(f"Error scrolling: {e}")
            return False
