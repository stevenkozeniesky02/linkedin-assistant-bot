"""Base Automation Mode Class

All automation modes inherit from this base class
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from datetime import datetime
import time
import random
import logging


class AutomationMode(ABC):
    """Base class for all LinkedIn automation modes"""

    def __init__(
        self,
        name: str,
        config: dict,
        linkedin_client,
        ai_provider,
        db_session,
        safety_monitor
    ):
        """
        Initialize automation mode

        Args:
            name: Mode name (e.g., 'feed_engagement')
            config: Mode-specific configuration dictionary
            linkedin_client: LinkedInClient instance
            ai_provider: AI provider for content generation
            db_session: Database session
            safety_monitor: SafetyMonitor instance
        """
        self.name = name
        self.config = config
        self.client = linkedin_client
        self.ai_provider = ai_provider
        self.db_session = db_session
        self.safety_monitor = safety_monitor
        self.logger = logging.getLogger(f"automation.{name}")

        # Mode state
        self.enabled = config.get('enabled', False)
        self.running = False
        self.errors = 0
        self.last_run = None
        self.actions_this_session = 0

        # Safety configuration
        self.safety_config = config.get('safety', {})
        self.error_threshold = self.safety_config.get('error_threshold', 3)
        self.pause_on_errors = self.safety_config.get('pause_on_errors', True)

    @abstractmethod
    def run(self) -> Dict:
        """
        Execute the automation mode

        Returns:
            Dictionary with execution results and metrics
        """
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """
        Validate mode-specific configuration

        Returns:
            True if configuration is valid, False otherwise
        """
        pass

    def can_run(self) -> bool:
        """
        Check if mode can run based on safety limits

        Returns:
            True if mode can run, False otherwise
        """
        if not self.enabled:
            self.logger.debug(f"{self.name} is disabled")
            return False

        if self.running:
            self.logger.debug(f"{self.name} is already running")
            return False

        if self.pause_on_errors and self.errors >= self.error_threshold:
            self.logger.warning(f"{self.name} paused due to errors (threshold: {self.error_threshold})")
            return False

        # Check safety monitor limits
        if hasattr(self.safety_monitor, 'can_perform_action'):
            if not self.safety_monitor.can_perform_action(f"{self.name}_run"):
                self.logger.debug(f"{self.name} blocked by safety monitor")
                return False

        return True

    def start(self) -> Dict:
        """
        Start the automation mode with safety checks

        Returns:
            Dictionary with execution results
        """
        if not self.can_run():
            return {
                'success': False,
                'mode': self.name,
                'message': 'Mode cannot run (disabled, already running, or safety limits reached)',
                'actions': 0
            }

        self.running = True
        self.actions_this_session = 0
        start_time = datetime.now()

        try:
            self.logger.info(f"Starting {self.name} mode")
            result = self.run()

            # Record successful run
            if hasattr(self.safety_monitor, 'record_action'):
                self.safety_monitor.record_action(f"{self.name}_run")
            self.last_run = datetime.now()
            self.errors = 0  # Reset error counter on success

            result['success'] = True
            result['mode'] = self.name
            result['duration'] = (datetime.now() - start_time).total_seconds()
            result['actions'] = self.actions_this_session

            self.logger.info(f"{self.name} completed: {self.actions_this_session} actions in {result['duration']:.1f}s")
            return result

        except Exception as e:
            self.logger.error(f"Error in {self.name}: {e}", exc_info=True)
            self.errors += 1

            return {
                'success': False,
                'mode': self.name,
                'error': str(e),
                'actions': self.actions_this_session,
                'duration': (datetime.now() - start_time).total_seconds()
            }

        finally:
            self.running = False

    def human_delay(self, min_seconds: Optional[int] = None, max_seconds: Optional[int] = None):
        """
        Add human-like delay between actions

        Args:
            min_seconds: Minimum delay (defaults to safety config)
            max_seconds: Maximum delay (defaults to safety config)
        """
        if min_seconds is None or max_seconds is None:
            delay_range = self.safety_config.get('delay_range', [5, 30])
            min_seconds = delay_range[0]
            max_seconds = delay_range[1]

        delay = random.uniform(min_seconds, max_seconds)
        self.logger.debug(f"Human delay: {delay:.1f}s")
        time.sleep(delay)

    def record_action(self, action_type: str):
        """
        Record an action for safety monitoring

        Args:
            action_type: Type of action performed
        """
        self.actions_this_session += 1
        if hasattr(self.safety_monitor, 'record_action'):
            self.safety_monitor.record_action(action_type)
        self.logger.debug(f"Action recorded: {action_type} (session total: {self.actions_this_session})")

    def check_safety_limits(self, action_type: str) -> bool:
        """
        Check if an action can be performed within safety limits

        Args:
            action_type: Type of action to check

        Returns:
            True if action is allowed, False otherwise
        """
        if hasattr(self.safety_monitor, 'can_perform_action'):
            return self.safety_monitor.can_perform_action(action_type)
        return True  # Allow if safety monitor doesn't have the method

    def get_stats(self) -> Dict:
        """
        Get mode statistics

        Returns:
            Dictionary with mode stats
        """
        return {
            'name': self.name,
            'enabled': self.enabled,
            'running': self.running,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'errors': self.errors,
            'actions_this_session': self.actions_this_session
        }

    def reset_errors(self):
        """Reset error counter"""
        self.errors = 0
        self.logger.info(f"{self.name} error counter reset")

    def enable(self):
        """Enable the mode"""
        self.enabled = True
        self.logger.info(f"{self.name} enabled")

    def disable(self):
        """Disable the mode"""
        self.enabled = False
        self.logger.info(f"{self.name} disabled")
