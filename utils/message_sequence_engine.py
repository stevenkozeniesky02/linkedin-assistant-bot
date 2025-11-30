"""Enhanced Message Sequence Engine

Advanced features:
- A/B testing for message variations
- Behavioral triggers (profile views, post engagement)
- Sequence branching (different paths based on response)
- Timezone-based scheduling
- Response rate tracking and optimization
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
import json
import pytz

from database.models import (
    MessageSequence, SequenceEnrollment, SequenceMessage,
    Connection, Activity
)


class MessageSequenceEngine:
    """Enhanced message sequence management with A/B testing and branching"""

    def __init__(self, db_session: Session, config: dict):
        """
        Initialize Message Sequence Engine

        Args:
            db_session: SQLAlchemy database session
            config: Configuration dictionary
        """
        self.db = db_session
        self.config = config

    # ========================================
    # A/B TESTING FOR MESSAGE VARIATIONS
    # ========================================

    def create_ab_test_sequence(self, name: str, variant_a: List[Dict],
                                variant_b: List[Dict], split_ratio: float = 0.5,
                                **kwargs) -> Dict:
        """
        Create A/B test with two message sequence variants

        Args:
            name: Base name for the test
            variant_a: List of message steps for variant A
            variant_b: List of message steps for variant B
            split_ratio: Percentage to assign to variant A (default 0.5 = 50/50)
            **kwargs: Additional arguments for sequence creation

        Returns:
            Dictionary with both sequence IDs and test configuration
        """
        # Create variant A sequence
        seq_a = MessageSequence(
            name=f"{name} (Variant A)",
            description=kwargs.get('description'),
            trigger_type=kwargs.get('trigger_type', 'new_connection'),
            trigger_criteria=kwargs.get('trigger_criteria'),
            steps=json.dumps(variant_a),
            target_industries=kwargs.get('target_industries'),
            target_titles=kwargs.get('target_titles'),
            target_companies=kwargs.get('target_companies'),
            is_active=True
        )

        # Create variant B sequence
        seq_b = MessageSequence(
            name=f"{name} (Variant B)",
            description=kwargs.get('description'),
            trigger_type=kwargs.get('trigger_type', 'new_connection'),
            trigger_criteria=kwargs.get('trigger_criteria'),
            steps=json.dumps(variant_b),
            target_industries=kwargs.get('target_industries'),
            target_titles=kwargs.get('target_titles'),
            target_companies=kwargs.get('target_companies'),
            is_active=True
        )

        self.db.add(seq_a)
        self.db.add(seq_b)
        self.db.commit()

        return {
            'test_name': name,
            'variant_a_id': seq_a.id,
            'variant_b_id': seq_b.id,
            'split_ratio': split_ratio,
            'created_at': datetime.utcnow()
        }

    def assign_to_ab_variant(self, test_config: Dict, connection_id: int) -> int:
        """
        Assign connection to A or B variant based on split ratio

        Args:
            test_config: A/B test configuration from create_ab_test_sequence
            connection_id: Connection ID to assign

        Returns:
            Sequence ID (either variant A or B)
        """
        import random

        split_ratio = test_config.get('split_ratio', 0.5)

        # Random assignment based on split ratio
        if random.random() < split_ratio:
            return test_config['variant_a_id']
        else:
            return test_config['variant_b_id']

    def get_ab_test_results(self, test_config: Dict) -> Dict:
        """
        Get A/B test results comparing performance of variants

        Args:
            test_config: A/B test configuration

        Returns:
            Dictionary with comparative results
        """
        seq_a_id = test_config['variant_a_id']
        seq_b_id = test_config['variant_b_id']

        # Get metrics for variant A
        seq_a = self.db.query(MessageSequence).get(seq_a_id)
        enrollments_a = self.db.query(SequenceEnrollment).filter(
            SequenceEnrollment.sequence_id == seq_a_id
        ).all()

        # Get metrics for variant B
        seq_b = self.db.query(MessageSequence).get(seq_b_id)
        enrollments_b = self.db.query(SequenceEnrollment).filter(
            SequenceEnrollment.sequence_id == seq_b_id
        ).all()

        # Calculate response rates
        responses_a = len([e for e in enrollments_a if e.responded])
        responses_b = len([e for e in enrollments_b if e.responded])

        total_a = len(enrollments_a)
        total_b = len(enrollments_b)

        response_rate_a = (responses_a / total_a * 100) if total_a > 0 else 0
        response_rate_b = (responses_b / total_b * 100) if total_b > 0 else 0

        # Calculate completion rates
        completed_a = len([e for e in enrollments_a if e.status == 'completed'])
        completed_b = len([e for e in enrollments_b if e.status == 'completed'])

        completion_rate_a = (completed_a / total_a * 100) if total_a > 0 else 0
        completion_rate_b = (completed_b / total_b * 100) if total_b > 0 else 0

        # Determine winner
        winner = None
        if total_a >= 30 and total_b >= 30:  # Minimum sample size
            if response_rate_a > response_rate_b * 1.1:  # 10% lift threshold
                winner = 'A'
            elif response_rate_b > response_rate_a * 1.1:
                winner = 'B'

        return {
            'test_name': test_config['test_name'],
            'variant_a': {
                'sequence_id': seq_a_id,
                'name': seq_a.name,
                'total_enrolled': total_a,
                'responses': responses_a,
                'response_rate': round(response_rate_a, 1),
                'completed': completed_a,
                'completion_rate': round(completion_rate_a, 1)
            },
            'variant_b': {
                'sequence_id': seq_b_id,
                'name': seq_b.name,
                'total_enrolled': total_b,
                'responses': responses_b,
                'response_rate': round(response_rate_b, 1),
                'completed': completed_b,
                'completion_rate': round(completion_rate_b, 1)
            },
            'winner': winner,
            'sample_size_sufficient': total_a >= 30 and total_b >= 30,
            'recommendation': self._get_ab_recommendation(response_rate_a, response_rate_b, total_a, total_b, winner)
        }

    def _get_ab_recommendation(self, rate_a: float, rate_b: float,
                               total_a: int, total_b: int, winner: Optional[str]) -> str:
        """Generate recommendation based on A/B test results"""
        if total_a < 30 or total_b < 30:
            return "Continue test - need minimum 30 enrollments per variant"

        if winner == 'A':
            lift = ((rate_a - rate_b) / rate_b * 100) if rate_b > 0 else 0
            return f"✅ Variant A wins with {lift:.1f}% lift! Use this sequence going forward"
        elif winner == 'B':
            lift = ((rate_b - rate_a) / rate_a * 100) if rate_a > 0 else 0
            return f"✅ Variant B wins with {lift:.1f}% lift! Use this sequence going forward"
        else:
            return "⏸️  No clear winner - results too close. Consider testing different variations"

    # ========================================
    # BEHAVIORAL TRIGGERS
    # ========================================

    def check_behavioral_triggers(self) -> List[Dict]:
        """
        Check for behavioral triggers and create actions

        Triggers:
        - Profile view detected
        - Engaged with your post
        - Commented on your content

        Returns:
            List of triggered actions
        """
        triggered_actions = []
        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)

        # Check for recent profile views (if tracked)
        profile_views = self.db.query(Activity).filter(
            and_(
                Activity.action_type == 'profile_view',
                Activity.performed_at >= last_24h
            )
        ).all()

        for view in profile_views:
            # Check if this person is a connection
            connection = self.db.query(Connection).filter(
                Connection.profile_url == view.target_id
            ).first()

            if connection:
                # Trigger: send personalized message mentioning the profile view
                triggered_actions.append({
                    'trigger_type': 'profile_view',
                    'connection_id': connection.id,
                    'connection_name': connection.name,
                    'action': 'send_message',
                    'message_template': 'profile_view_followup',
                    'priority': 'high',
                    'detected_at': view.performed_at
                })

        # Check for recent engagement on your posts
        recent_engagement = self.db.query(Activity).filter(
            and_(
                Activity.action_type.in_(['received_like', 'received_comment']),
                Activity.performed_at >= last_24h
            )
        ).all()

        for engagement in recent_engagement:
            connection = self.db.query(Connection).filter(
                Connection.profile_url == engagement.target_id
            ).first()

            if connection:
                # Check if already in a sequence
                active_enrollment = self.db.query(SequenceEnrollment).filter(
                    and_(
                        SequenceEnrollment.connection_id == connection.id,
                        SequenceEnrollment.status == 'active'
                    )
                ).first()

                if not active_enrollment:
                    triggered_actions.append({
                        'trigger_type': 'post_engagement',
                        'connection_id': connection.id,
                        'connection_name': connection.name,
                        'action': 'enroll_in_sequence',
                        'sequence_type': 'engagement_followup',
                        'priority': 'medium',
                        'detected_at': engagement.performed_at
                    })

        return triggered_actions

    # ========================================
    # SEQUENCE BRANCHING
    # ========================================

    def create_branching_sequence(self, name: str,
                                  initial_steps: List[Dict],
                                  response_path: List[Dict],
                                  no_response_path: List[Dict],
                                  **kwargs) -> MessageSequence:
        """
        Create a sequence with branching logic

        Args:
            name: Sequence name
            initial_steps: Initial messages sent to everyone
            response_path: Steps to follow if they respond
            no_response_path: Steps to follow if no response
            **kwargs: Additional sequence parameters

        Returns:
            MessageSequence object with branching configuration
        """
        # Build branching configuration
        branching_config = {
            'type': 'response_based',
            'initial_steps': initial_steps,
            'branches': {
                'responded': {
                    'condition': 'responded == True',
                    'steps': response_path
                },
                'no_response': {
                    'condition': 'responded == False',
                    'steps': no_response_path
                }
            },
            'branch_point': len(initial_steps)  # After initial steps, check for response
        }

        sequence = MessageSequence(
            name=name,
            description=kwargs.get('description'),
            trigger_type=kwargs.get('trigger_type', 'new_connection'),
            trigger_criteria=json.dumps(branching_config),
            steps=json.dumps(initial_steps),  # Store initial steps
            target_industries=kwargs.get('target_industries'),
            target_titles=kwargs.get('target_titles'),
            target_companies=kwargs.get('target_companies'),
            is_active=True
        )

        self.db.add(sequence)
        self.db.commit()

        return sequence

    def process_branching_logic(self, enrollment: SequenceEnrollment) -> Optional[List[Dict]]:
        """
        Check if sequence has branching and determine next path

        Args:
            enrollment: SequenceEnrollment to check

        Returns:
            New steps to follow based on branching logic, or None if no branching
        """
        sequence = enrollment.sequence

        # Check if sequence has branching configuration
        if not sequence.trigger_criteria:
            return None

        try:
            branching_config = json.loads(sequence.trigger_criteria)
        except:
            return None

        if branching_config.get('type') != 'response_based':
            return None

        # Check if we're at the branch point
        branch_point = branching_config.get('branch_point', 0)
        if enrollment.current_step != branch_point:
            return None

        # Determine which branch to follow
        if enrollment.responded:
            # Follow response path
            return branching_config['branches']['responded']['steps']
        else:
            # Follow no-response path
            return branching_config['branches']['no_response']['steps']

    # ========================================
    # TIMEZONE-BASED SCHEDULING
    # ========================================

    def schedule_with_timezone(self, connection: Connection,
                               send_time_local: str = "09:00") -> datetime:
        """
        Schedule message based on connection's timezone

        Args:
            connection: Connection object
            send_time_local: Desired send time in their local time (HH:MM format)

        Returns:
            UTC datetime for sending
        """
        # Try to detect timezone from location
        timezone = self._detect_timezone(connection.location)

        # Parse desired local time
        hour, minute = map(int, send_time_local.split(':'))

        # Get current date in their timezone
        local_tz = pytz.timezone(timezone)
        now_local = datetime.now(local_tz)

        # Create send time for today
        send_datetime_local = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # If time has passed today, schedule for tomorrow
        if send_datetime_local <= now_local:
            send_datetime_local += timedelta(days=1)

        # Convert to UTC
        send_datetime_utc = send_datetime_local.astimezone(pytz.UTC).replace(tzinfo=None)

        return send_datetime_utc

    def _detect_timezone(self, location: Optional[str]) -> str:
        """
        Detect timezone from location string

        Args:
            location: Location string (e.g., "San Francisco, CA" or "London, UK")

        Returns:
            Timezone string (defaults to UTC if unknown)
        """
        if not location:
            return 'UTC'

        location_lower = location.lower()

        # Simple timezone mapping (expand as needed)
        timezone_map = {
            'san francisco': 'America/Los_Angeles',
            'los angeles': 'America/Los_Angeles',
            'seattle': 'America/Los_Angeles',
            'portland': 'America/Los_Angeles',
            'california': 'America/Los_Angeles',
            'new york': 'America/New_York',
            'boston': 'America/New_York',
            'washington': 'America/New_York',
            'chicago': 'America/Chicago',
            'austin': 'America/Chicago',
            'denver': 'America/Denver',
            'london': 'Europe/London',
            'paris': 'Europe/Paris',
            'berlin': 'Europe/Berlin',
            'amsterdam': 'Europe/Amsterdam',
            'madrid': 'Europe/Madrid',
            'tokyo': 'Asia/Tokyo',
            'singapore': 'Asia/Singapore',
            'sydney': 'Australia/Sydney',
            'india': 'Asia/Kolkata',
            'mumbai': 'Asia/Kolkata',
            'bangalore': 'Asia/Kolkata',
        }

        # Check if any key matches the location
        for key, tz in timezone_map.items():
            if key in location_lower:
                return tz

        # Default to UTC if unknown
        return 'UTC'

    # ========================================
    # RESPONSE RATE TRACKING
    # ========================================

    def get_sequence_performance(self, sequence_id: int) -> Dict:
        """
        Get detailed performance metrics for a sequence

        Args:
            sequence_id: MessageSequence ID

        Returns:
            Dictionary with performance metrics
        """
        sequence = self.db.query(MessageSequence).get(sequence_id)
        if not sequence:
            return {'error': 'Sequence not found'}

        enrollments = self.db.query(SequenceEnrollment).filter(
            SequenceEnrollment.sequence_id == sequence_id
        ).all()

        total_enrolled = len(enrollments)
        if total_enrolled == 0:
            return {
                'sequence_id': sequence_id,
                'sequence_name': sequence.name,
                'total_enrolled': 0,
                'message': 'No enrollments yet'
            }

        # Calculate metrics
        total_responses = len([e for e in enrollments if e.responded])
        total_completed = len([e for e in enrollments if e.status == 'completed'])
        total_active = len([e for e in enrollments if e.status == 'active'])
        total_stopped = len([e for e in enrollments if e.status == 'stopped'])

        response_rate = (total_responses / total_enrolled * 100)
        completion_rate = (total_completed / total_enrolled * 100)

        # Get average time to response
        responded_enrollments = [e for e in enrollments if e.responded and e.response_date and e.enrollment_date]
        if responded_enrollments:
            avg_days_to_response = sum(
                (e.response_date - e.enrollment_date).days
                for e in responded_enrollments
            ) / len(responded_enrollments)
        else:
            avg_days_to_response = None

        # Get message-level stats
        all_messages = self.db.query(SequenceMessage).join(SequenceEnrollment).filter(
            SequenceEnrollment.sequence_id == sequence_id
        ).all()

        messages_sent = len([m for m in all_messages if m.status == 'sent'])
        messages_failed = len([m for m in all_messages if m.status == 'failed'])

        return {
            'sequence_id': sequence_id,
            'sequence_name': sequence.name,
            'total_enrolled': total_enrolled,
            'responses': total_responses,
            'response_rate': round(response_rate, 1),
            'completion_rate': round(completion_rate, 1),
            'active_enrollments': total_active,
            'completed_enrollments': total_completed,
            'stopped_enrollments': total_stopped,
            'avg_days_to_response': round(avg_days_to_response, 1) if avg_days_to_response else None,
            'messages_sent': messages_sent,
            'messages_failed': messages_failed,
            'success_rate': round((messages_sent / (messages_sent + messages_failed) * 100), 1) if (messages_sent + messages_failed) > 0 else 100
        }

    def optimize_sequence_timing(self, sequence_id: int) -> Dict:
        """
        Analyze response patterns and recommend optimal send times

        Args:
            sequence_id: MessageSequence ID

        Returns:
            Dictionary with optimization recommendations
        """
        # Get all messages for this sequence
        messages = self.db.query(SequenceMessage).join(SequenceEnrollment).filter(
            SequenceEnrollment.sequence_id == sequence_id,
            SequenceMessage.status == 'sent'
        ).all()

        if len(messages) < 10:
            return {'message': 'Need at least 10 sent messages for analysis'}

        # Analyze send time vs response rate
        # Group by hour of day
        hour_performance = {}
        for msg in messages:
            if msg.sent_at:
                hour = msg.sent_at.hour
                if hour not in hour_performance:
                    hour_performance[hour] = {'sent': 0, 'responses': 0}

                hour_performance[hour]['sent'] += 1

                # Check if this enrollment responded
                if msg.enrollment.responded:
                    hour_performance[hour]['responses'] += 1

        # Calculate response rate per hour
        hour_response_rates = {}
        for hour, stats in hour_performance.items():
            if stats['sent'] >= 3:  # Minimum sample size
                hour_response_rates[hour] = (stats['responses'] / stats['sent'] * 100)

        # Find best hours
        if hour_response_rates:
            best_hours = sorted(hour_response_rates.items(), key=lambda x: x[1], reverse=True)[:3]
            worst_hours = sorted(hour_response_rates.items(), key=lambda x: x[1])[:3]
        else:
            best_hours = []
            worst_hours = []

        return {
            'sequence_id': sequence_id,
            'total_messages_analyzed': len(messages),
            'best_hours': [f"{h}:00 ({r:.1f}% response rate)" for h, r in best_hours],
            'worst_hours': [f"{h}:00 ({r:.1f}% response rate)" for h, r in worst_hours],
            'recommendation': f"Send messages between {best_hours[0][0]}:00-{best_hours[-1][0]}:00 for best results" if best_hours else "Need more data"
        }
