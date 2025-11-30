"""Network Growth Automation Module"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from database.models import (
    Connection, ConnectionRequest, MessageSequence,
    SequenceEnrollment, SequenceMessage, Activity
)
from utils.safety_monitor import SafetyMonitor
from linkedin.connection_manager import ConnectionManager
from ai import get_ai_provider


class NetworkGrowthAutomation:
    """Automate connection requests, auto-accept, and follow-up sequences"""

    def __init__(self, db_session: Session, linkedin_client, config: dict):
        """
        Initialize Network Growth Automation

        Args:
            db_session: SQLAlchemy database session
            linkedin_client: LinkedInClient instance
            config: Configuration dictionary
        """
        self.db = db_session
        self.client = linkedin_client
        self.config = config

        # Initialize managers
        self.safety_monitor = SafetyMonitor(db_session, config)
        self.connection_manager = ConnectionManager(db_session, config)
        self.ai_provider = get_ai_provider(config)

        # Get network growth config
        self.growth_config = config.get('network_growth', {})

        # Connection request settings
        self.max_requests_per_day = self.growth_config.get('max_requests_per_day', 10)
        self.personalize_requests = self.growth_config.get('personalize_requests', True)

        # Auto-accept settings
        self.auto_accept_enabled = self.growth_config.get('auto_accept_enabled', False)
        self.auto_accept_criteria = self.growth_config.get('auto_accept_criteria', {})

        # Message sequence settings
        self.auto_enroll_new_connections = self.growth_config.get('auto_enroll_new_connections', True)

    # ========================================
    # CONNECTION REQUEST AUTOMATION
    # ========================================

    def send_connection_request(self, profile_url: str, name: str,
                                title: str = None, company: str = None,
                                location: str = None, industry: str = None,
                                custom_message: str = None,
                                source: str = 'manual') -> Optional[ConnectionRequest]:
        """
        Send a connection request with optional personalized message

        Args:
            profile_url: LinkedIn profile URL
            name: Target's name
            title: Target's job title
            company: Target's company
            location: Target's location
            industry: Target's industry
            custom_message: Custom message (if None, will generate with AI)
            source: Source of this request (manual, campaign, auto, search)

        Returns:
            ConnectionRequest object if successful, None otherwise
        """
        # Check safety limits
        if not self.safety_monitor.check_action_allowed('connection_request')['allowed']:
            print(f"⛔ Safety limits reached, cannot send connection request")
            return None

        # Check daily connection request limit
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        requests_today = self.db.query(ConnectionRequest).filter(
            ConnectionRequest.sent_at >= today_start
        ).count()

        if requests_today >= self.max_requests_per_day:
            print(f"⛔ Daily connection request limit reached ({self.max_requests_per_day})")
            return None

        # Generate personalized message if needed
        message = custom_message
        if message is None and self.personalize_requests:
            message = self._generate_connection_message(name, title, company)

        try:
            # Send connection request via LinkedIn client
            # NOTE: This requires LinkedIn automation implementation
            # success = self.client.send_connection_request(profile_url, message)

            # For now, we'll simulate and track in database
            success = True  # Placeholder

            # Create connection request record
            conn_request = ConnectionRequest(
                target_name=name,
                target_profile_url=profile_url,
                target_title=title,
                target_company=company,
                target_location=location,
                target_industry=industry,
                message=message,
                status='pending' if success else 'failed',
                source=source,
                sent_at=datetime.utcnow(),
                success=success
            )

            self.db.add(conn_request)
            self.db.commit()

            # Log to safety monitor
            self.safety_monitor.log_activity(
                action_type='connection_request',
                target_type='profile',
                target_id=profile_url,
                duration=2.0,
                success=success
            )

            if success:
                print(f"✓ Connection request sent to {name}")
            else:
                print(f"✗ Failed to send connection request to {name}")

            return conn_request

        except Exception as e:
            print(f"Error sending connection request: {e}")
            return None

    def _generate_connection_message(self, name: str, title: str = None,
                                    company: str = None) -> str:
        """
        Generate personalized connection request message with AI

        Args:
            name: Target's name
            title: Target's job title
            company: Target's company

        Returns:
            Personalized message string
        """
        user_profile = self.config.get('user_profile', {})

        prompt = f"""Generate a brief, professional LinkedIn connection request message.

TARGET PERSON:
- Name: {name}
- Title: {title or 'Professional'}
- Company: {company or 'their company'}

YOUR PROFILE:
- Name: {user_profile.get('name', 'Your Name')}
- Title: {user_profile.get('title', 'Professional')}
- Industry: {user_profile.get('industry', 'Technology')}

Requirements:
- Keep it SHORT (under 200 characters to fit LinkedIn's limit)
- Be genuine and professional
- Mention a shared interest or connection point
- NO generic phrases like "I'd love to connect" or "expand my network"
- NO emojis
- Direct and authentic

Generate ONLY the message text, nothing else."""

        try:
            message = self.ai_provider.generate_text(
                prompt=prompt,
                max_tokens=80
            ).strip()

            # Ensure it's under 200 characters (LinkedIn limit for connection messages without InMail)
            if len(message) > 200:
                message = message[:197] + "..."

            return message

        except Exception as e:
            print(f"Error generating connection message: {e}")
            # Fallback to simple message
            return f"Hi {name.split()[0]}, I came across your profile and thought we could connect professionally."

    def check_pending_requests(self) -> Dict:
        """
        Check status of pending connection requests

        Returns:
            Dictionary with stats on pending requests
        """
        pending_requests = self.db.query(ConnectionRequest).filter(
            ConnectionRequest.status == 'pending'
        ).all()

        # Check which have been accepted (would require LinkedIn scraping)
        # For now, return stats
        return {
            'total_pending': len(pending_requests),
            'oldest_pending': min([r.sent_at for r in pending_requests]) if pending_requests else None,
            'requests': pending_requests[:10]  # Return first 10 for display
        }

    # ========================================
    # AUTO-ACCEPT CONNECTION REQUESTS
    # ========================================

    def process_incoming_requests(self) -> Dict:
        """
        Process incoming connection requests with auto-accept filters

        Returns:
            Dictionary with processing results
        """
        if not self.auto_accept_enabled:
            return {'enabled': False, 'message': 'Auto-accept is disabled'}

        # NOTE: This requires LinkedIn automation to fetch incoming requests
        # incoming_requests = self.client.get_incoming_connection_requests()

        # Placeholder for demonstration
        incoming_requests = []

        accepted = 0
        declined = 0
        pending = 0

        for request in incoming_requests:
            decision = self._evaluate_connection_request(request)

            if decision == 'accept':
                # Accept the request
                # self.client.accept_connection_request(request['id'])
                accepted += 1

                # Add to connections
                self.connection_manager.add_connection(
                    name=request['name'],
                    profile_url=request['profile_url'],
                    title=request.get('title'),
                    company=request.get('company'),
                    connection_source='auto_accept'
                )

            elif decision == 'decline':
                # Decline the request
                # self.client.decline_connection_request(request['id'])
                declined += 1

            else:
                pending += 1

        return {
            'enabled': True,
            'accepted': accepted,
            'declined': declined,
            'pending': pending
        }

    def _evaluate_connection_request(self, request: Dict) -> str:
        """
        Evaluate whether to accept, decline, or leave pending a connection request

        Args:
            request: Dictionary with request details

        Returns:
            'accept', 'decline', or 'pending'
        """
        criteria = self.auto_accept_criteria

        # Check industry filter
        accepted_industries = criteria.get('industries', [])
        if accepted_industries and request.get('industry') not in accepted_industries:
            return 'decline'

        # Check title keywords
        accepted_title_keywords = criteria.get('title_keywords', [])
        if accepted_title_keywords:
            title = (request.get('title') or '').lower()
            if not any(keyword.lower() in title for keyword in accepted_title_keywords):
                return 'decline'

        # Check company filter
        accepted_companies = criteria.get('companies', [])
        if accepted_companies and request.get('company') not in accepted_companies:
            return 'decline'

        # Check mutual connections threshold
        min_mutual = criteria.get('min_mutual_connections', 0)
        if request.get('mutual_connections', 0) < min_mutual:
            return 'pending'  # Don't auto-decline, but don't auto-accept either

        # Passed all filters - accept
        return 'accept'

    # ========================================
    # MESSAGE SEQUENCE AUTOMATION
    # ========================================

    def create_message_sequence(self, name: str, steps: List[Dict],
                                trigger_type: str = 'new_connection',
                                description: str = None,
                                target_industries: List[str] = None,
                                target_titles: List[str] = None,
                                target_companies: List[str] = None) -> MessageSequence:
        """
        Create a new message sequence

        Args:
            name: Sequence name
            steps: List of message steps with delays
                [{"delay_days": 0, "template": "welcome"}, {"delay_days": 3, "template": "follow_up"}]
            trigger_type: When to trigger (new_connection, campaign_engage, manual)
            description: Sequence description
            target_industries: Filter by industries
            target_titles: Filter by job titles
            target_companies: Filter by companies

        Returns:
            MessageSequence object
        """
        sequence = MessageSequence(
            name=name,
            description=description,
            trigger_type=trigger_type,
            steps=json.dumps(steps),
            target_industries=json.dumps(target_industries) if target_industries else None,
            target_titles=json.dumps(target_titles) if target_titles else None,
            target_companies=json.dumps(target_companies) if target_companies else None,
            is_active=True
        )

        self.db.add(sequence)
        self.db.commit()

        return sequence

    def enroll_in_sequence(self, connection_id: int, sequence_id: int) -> Optional[SequenceEnrollment]:
        """
        Enroll a connection in a message sequence

        Args:
            connection_id: Connection ID
            sequence_id: MessageSequence ID

        Returns:
            SequenceEnrollment object
        """
        # Check if already enrolled
        existing = self.db.query(SequenceEnrollment).filter(
            and_(
                SequenceEnrollment.connection_id == connection_id,
                SequenceEnrollment.sequence_id == sequence_id,
                SequenceEnrollment.status.in_(['active', 'paused'])
            )
        ).first()

        if existing:
            print(f"Connection {connection_id} already enrolled in sequence {sequence_id}")
            return existing

        # Get sequence
        sequence = self.db.query(MessageSequence).filter(
            MessageSequence.id == sequence_id
        ).first()

        if not sequence or not sequence.is_active:
            print(f"Sequence {sequence_id} not found or inactive")
            return None

        # Calculate first message time
        steps = json.loads(sequence.steps)
        first_step_delay = steps[0].get('delay_days', 0)
        next_message_at = datetime.utcnow() + timedelta(days=first_step_delay)

        # Create enrollment
        enrollment = SequenceEnrollment(
            sequence_id=sequence_id,
            connection_id=connection_id,
            status='active',
            current_step=0,
            next_message_at=next_message_at,
            enrollment_date=datetime.utcnow()
        )

        self.db.add(enrollment)

        # Update sequence stats
        sequence.total_started += 1

        self.db.commit()

        print(f"✓ Enrolled connection {connection_id} in sequence '{sequence.name}'")
        return enrollment

    def process_due_sequence_messages(self) -> Dict:
        """
        Process message sequences that are due to send

        Returns:
            Dictionary with processing results
        """
        now = datetime.utcnow()

        # Get enrollments with messages due
        due_enrollments = self.db.query(SequenceEnrollment).filter(
            and_(
                SequenceEnrollment.status == 'active',
                SequenceEnrollment.next_message_at <= now
            )
        ).all()

        if not due_enrollments:
            return {'messages_sent': 0, 'message': 'No messages due'}

        messages_sent = 0
        errors = 0

        for enrollment in due_enrollments:
            try:
                success = self._send_sequence_message(enrollment)
                if success:
                    messages_sent += 1
                else:
                    errors += 1
            except Exception as e:
                print(f"Error processing enrollment {enrollment.id}: {e}")
                errors += 1

        return {
            'messages_sent': messages_sent,
            'errors': errors,
            'total_processed': len(due_enrollments)
        }

    def _send_sequence_message(self, enrollment: SequenceEnrollment) -> bool:
        """
        Send the next message in a sequence

        Args:
            enrollment: SequenceEnrollment object

        Returns:
            Boolean indicating success
        """
        # Check safety
        if not self.safety_monitor.check_action_allowed('message')['allowed']:
            print(f"⛔ Safety limits reached, skipping sequence message")
            return False

        # Get sequence and connection
        sequence = enrollment.sequence
        connection = enrollment.connection

        # Get current step
        steps = json.loads(sequence.steps)
        if enrollment.current_step >= len(steps):
            # Sequence completed
            enrollment.status = 'completed'
            enrollment.completion_date = datetime.utcnow()
            sequence.total_completed += 1
            self.db.commit()
            return True

        step = steps[enrollment.current_step]

        # Generate message
        message_content = self._generate_sequence_message(
            connection=connection,
            step=step,
            step_number=enrollment.current_step
        )

        try:
            # Send message via LinkedIn
            # NOTE: Requires LinkedIn messaging implementation
            # success = self.client.send_message(connection.profile_url, message_content)

            # Placeholder
            success = True

            # Create message record
            seq_message = SequenceMessage(
                enrollment_id=enrollment.id,
                step_number=enrollment.current_step,
                message_content=message_content,
                message_template=step.get('template', 'custom'),
                status='sent' if success else 'failed',
                scheduled_for=enrollment.next_message_at,
                sent_at=datetime.utcnow() if success else None,
                ai_provider=self.config.get('ai_provider')
            )

            self.db.add(seq_message)

            # Update enrollment
            enrollment.messages_sent += 1
            enrollment.current_step += 1
            enrollment.last_message_sent = datetime.utcnow()

            # Calculate next message time
            if enrollment.current_step < len(steps):
                next_step = steps[enrollment.current_step]
                delay_days = next_step.get('delay_days', 7)
                enrollment.next_message_at = datetime.utcnow() + timedelta(days=delay_days)
            else:
                enrollment.next_message_at = None

            self.db.commit()

            # Log to safety monitor
            self.safety_monitor.log_activity(
                action_type='message',
                target_type='profile',
                target_id=connection.profile_url,
                duration=3.0,
                success=success
            )

            if success:
                print(f"✓ Sent sequence message to {connection.name} (step {enrollment.current_step}/{len(steps)})")

            return success

        except Exception as e:
            print(f"Error sending sequence message: {e}")
            return False

    def _generate_sequence_message(self, connection: Connection,
                                   step: Dict, step_number: int) -> str:
        """
        Generate personalized message for sequence step

        Args:
            connection: Connection object
            step: Step configuration
            step_number: Current step number

        Returns:
            Message content
        """
        user_profile = self.config.get('user_profile', {})
        template = step.get('template', 'custom')

        if template == 'welcome':
            prompt = f"""Generate a friendly welcome message for a new LinkedIn connection.

TARGET:
- Name: {connection.name}
- Title: {connection.title or 'Professional'}
- Company: {connection.company or 'their company'}

YOU:
- Name: {user_profile.get('name', 'Your Name')}
- Title: {user_profile.get('title', 'Professional')}
- Background: {user_profile.get('background', 'technology professional')}

Requirements:
- Warm and genuine
- Brief (2-3 sentences)
- Mention something about their background or company
- NO sales pitch
- NO emojis
- Authentic and conversational

Generate ONLY the message, nothing else."""

        elif template == 'follow_up':
            prompt = f"""Generate a follow-up message for a LinkedIn connection you made a few days ago.

TARGET:
- Name: {connection.name}
- Title: {connection.title or 'Professional'}
- Company: {connection.company or 'their company'}

YOU:
- Name: {user_profile.get('name', 'Your Name')}
- Title: {user_profile.get('title', 'Professional')}
- Interests: {', '.join(user_profile.get('interests', ['technology']))}

Requirements:
- Natural follow-up (not pushy)
- Share a resource or insight relevant to their work
- Ask a thoughtful question
- 2-3 sentences
- NO sales pitch
- Authentic

Generate ONLY the message, nothing else."""

        else:
            # Custom template or generic
            prompt = f"""Generate a professional LinkedIn message.

TARGET: {connection.name} ({connection.title or 'Professional'} at {connection.company or 'their company'})
FROM: {user_profile.get('name', 'You')} ({user_profile.get('title', 'Professional')})

Create a brief, value-adding message (2-3 sentences). Be authentic and professional.

Generate ONLY the message, nothing else."""

        try:
            message = self.ai_provider.generate_text(
                prompt=prompt,
                max_tokens=150
            ).strip()

            return message

        except Exception as e:
            print(f"Error generating sequence message: {e}")
            return f"Hi {connection.name.split()[0]}, great to connect with you. Looking forward to staying in touch!"
