"""Automation Manager

Coordinates multiple automation modes and handles scheduling
"""

from typing import Dict, List, Optional
from datetime import datetime, time as dt_time
import logging
import threading
import time


class AutomationManager:
    """Manages and coordinates multiple automation modes"""

    def __init__(
        self,
        config: dict,
        linkedin_client,
        ai_provider,
        db_session,
        safety_monitor
    ):
        """
        Initialize Automation Manager

        Args:
            config: Full automation modes configuration
            linkedin_client: LinkedInClient instance
            ai_provider: AI provider for content generation
            db_session: Database session
            safety_monitor: SafetyMonitor instance
        """
        self.config = config
        self.client = linkedin_client
        self.ai_provider = ai_provider
        self.db_session = db_session
        self.safety_monitor = safety_monitor
        self.logger = logging.getLogger("automation.manager")

        # Registered modes
        self.modes: Dict[str, 'AutomationMode'] = {}

        # Manager state
        self.running = False
        self.full_automation = config.get('full_automation', False)
        self.active_mode_names = config.get('active_modes', [])

        # Scheduler configuration
        self.scheduler_config = config.get('scheduler', {})
        self.scheduler_enabled = self.scheduler_config.get('enabled', True)
        self.mode_rotation = self.scheduler_config.get('mode_rotation', 'balanced')
        self.time_windows = self.scheduler_config.get('time_windows', {})
        self.preferred_times = self.scheduler_config.get('preferred_times', {})

        # Thread for background automation
        self.automation_thread = None

    def register_mode(self, mode: 'AutomationMode'):
        """
        Register an automation mode

        Args:
            mode: AutomationMode instance
        """
        self.modes[mode.name] = mode
        self.logger.info(f"Registered automation mode: {mode.name}")

    def unregister_mode(self, mode_name: str):
        """
        Unregister an automation mode

        Args:
            mode_name: Name of mode to unregister
        """
        if mode_name in self.modes:
            del self.modes[mode_name]
            self.logger.info(f"Unregistered automation mode: {mode_name}")

    def get_mode(self, mode_name: str) -> Optional['AutomationMode']:
        """
        Get a registered mode by name

        Args:
            mode_name: Name of mode to retrieve

        Returns:
            AutomationMode instance or None
        """
        return self.modes.get(mode_name)

    def get_active_modes(self) -> List['AutomationMode']:
        """
        Get list of active modes based on configuration

        Returns:
            List of active AutomationMode instances
        """
        if self.full_automation:
            # Return all enabled modes
            return [mode for mode in self.modes.values() if mode.enabled]
        else:
            # Return only explicitly active modes
            return [
                self.modes[name]
                for name in self.active_mode_names
                if name in self.modes and self.modes[name].enabled
            ]

    def run_mode(self, mode_name: str) -> Dict:
        """
        Run a specific automation mode

        Args:
            mode_name: Name of mode to run

        Returns:
            Dictionary with execution results
        """
        mode = self.get_mode(mode_name)
        if not mode:
            return {
                'success': False,
                'mode': mode_name,
                'error': 'Mode not found'
            }

        self.logger.info(f"Running mode: {mode_name}")
        return mode.start()

    def run_all_active_modes(self) -> List[Dict]:
        """
        Run all active modes

        Returns:
            List of results from each mode
        """
        active_modes = self.get_active_modes()
        results = []

        for mode in active_modes:
            self.logger.info(f"Running active mode: {mode.name}")
            result = mode.start()
            results.append(result)

            # Add delay between modes for safety
            if len(active_modes) > 1:
                delay = self.config.get('safety', {}).get('delay_range', [5, 30])[1]
                self.logger.debug(f"Delay between modes: {delay}s")
                time.sleep(delay)

        return results

    def is_within_time_window(self, window_name: str) -> bool:
        """
        Check if current time is within a time window

        Args:
            window_name: Name of time window (morning, midday, evening)

        Returns:
            True if within window, False otherwise
        """
        if window_name not in self.time_windows:
            return True  # No restriction if window not defined

        window = self.time_windows[window_name]
        current_hour = datetime.now().hour

        start_hour, end_hour = window
        return start_hour <= current_hour < end_hour

    def get_preferred_modes_for_current_time(self) -> List['AutomationMode']:
        """
        Get modes that are preferred for the current time window

        Returns:
            List of AutomationMode instances
        """
        current_windows = []
        for window_name in self.time_windows.keys():
            if self.is_within_time_window(window_name):
                current_windows.append(window_name)

        if not current_windows:
            return self.get_active_modes()

        # Filter modes by preferred times
        preferred_modes = []
        for mode in self.get_active_modes():
            mode_preferences = self.preferred_times.get(mode.name, [])

            # If no preferences set, mode can run anytime
            if not mode_preferences:
                preferred_modes.append(mode)
                continue

            # Check if any current window matches mode preferences
            for window in current_windows:
                if window in mode_preferences:
                    preferred_modes.append(mode)
                    break

        return preferred_modes if preferred_modes else self.get_active_modes()

    def start_background_automation(self):
        """Start automation in background thread"""
        if self.running:
            self.logger.warning("Background automation already running")
            return

        self.running = True
        self.automation_thread = threading.Thread(
            target=self._automation_loop,
            daemon=True
        )
        self.automation_thread.start()
        self.logger.info("Background automation started")

    def stop_background_automation(self):
        """Stop background automation"""
        self.running = False
        if self.automation_thread:
            self.automation_thread.join(timeout=5)
        self.logger.info("Background automation stopped")

    def _automation_loop(self):
        """Main automation loop (runs in background thread)"""
        check_interval = 60  # Check every minute

        while self.running:
            try:
                if self.scheduler_enabled:
                    # Get modes preferred for current time
                    modes_to_run = self.get_preferred_modes_for_current_time()

                    for mode in modes_to_run:
                        if not self.running:
                            break

                        # Check if mode should run based on frequency
                        if self._should_mode_run(mode):
                            self.logger.info(f"Scheduler triggering mode: {mode.name}")
                            mode.start()

                            # Delay between modes
                            if self.running:
                                time.sleep(30)

                # Sleep before next check
                time.sleep(check_interval)

            except Exception as e:
                self.logger.error(f"Error in automation loop: {e}", exc_info=True)
                time.sleep(check_interval)

    def _should_mode_run(self, mode: 'AutomationMode') -> bool:
        """
        Determine if a mode should run based on its frequency settings

        Args:
            mode: AutomationMode instance

        Returns:
            True if mode should run, False otherwise
        """
        if not mode.can_run():
            return False

        # Get mode-specific frequency configuration
        frequency = mode.config.get('engagement_frequency', 'daily')

        if frequency == 'hourly':
            # Run every hour if last run was more than 1 hour ago
            if not mode.last_run:
                return True
            hours_since = (datetime.now() - mode.last_run).total_seconds() / 3600
            return hours_since >= 1

        elif frequency == 'twice_daily':
            # Run twice per day
            if not mode.last_run:
                return True
            hours_since = (datetime.now() - mode.last_run).total_seconds() / 3600
            return hours_since >= 12

        elif frequency == 'daily':
            # Run once per day
            if not mode.last_run:
                return True
            hours_since = (datetime.now() - mode.last_run).total_seconds() / 3600
            return hours_since >= 24

        return False

    def get_stats(self) -> Dict:
        """
        Get statistics for all modes

        Returns:
            Dictionary with manager and mode stats
        """
        return {
            'manager': {
                'running': self.running,
                'full_automation': self.full_automation,
                'scheduler_enabled': self.scheduler_enabled,
                'mode_rotation': self.mode_rotation,
                'total_modes': len(self.modes),
                'active_modes': len(self.get_active_modes())
            },
            'modes': {
                name: mode.get_stats()
                for name, mode in self.modes.items()
            }
        }

    def enable_mode(self, mode_name: str):
        """Enable a specific mode"""
        mode = self.get_mode(mode_name)
        if mode:
            mode.enable()
            if mode_name not in self.active_mode_names:
                self.active_mode_names.append(mode_name)

    def disable_mode(self, mode_name: str):
        """Disable a specific mode"""
        mode = self.get_mode(mode_name)
        if mode:
            mode.disable()
            if mode_name in self.active_mode_names:
                self.active_mode_names.remove(mode_name)

    def reset_all_errors(self):
        """Reset error counters for all modes"""
        for mode in self.modes.values():
            mode.reset_errors()
        self.logger.info("All mode error counters reset")
