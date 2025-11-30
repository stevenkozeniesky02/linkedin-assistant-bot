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
from utils.lead_scoring import LeadScoringEngine
from utils.message_sequence_engine import MessageSequenceEngine
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

        # Initialize lead scoring engine
        self.lead_scorer = LeadScoringEngine(db_session, config)

        # Initialize message sequence engine
        self.sequence_engine = MessageSequenceEngine(db_session, config)

        # Get network growth config
        self.growth_config = config.get('network_growth', {})

        # Connection request settings
        self.max_requests_per_day = self.growth_config.get('max_requests_per_day', 10)
        self.personalize_requests = self.growth_config.get('personalize_requests', True)
        self.use_lead_scoring = self.growth_config.get('use_lead_scoring', True)
        self.min_lead_score = self.growth_config.get('min_lead_score', 40)  # Minimum score to send request

        # Auto-accept settings
        self.auto_accept_enabled = self.growth_config.get('auto_accept_enabled', False)
        self.auto_accept_criteria = self.growth_config.get('auto_accept_criteria', {})

        # Message sequence settings
        self.auto_enroll_new_connections = self.growth_config.get('auto_enroll_new_connections', True)
        self.use_sequence_ab_testing = self.growth_config.get('use_sequence_ab_testing', False)
        self.use_behavioral_triggers = self.growth_config.get('use_behavioral_triggers', True)
        self.use_timezone_scheduling = self.growth_config.get('use_timezone_scheduling', True)

    # ========================================
    # CONNECTION REQUEST AUTOMATION
    # ========================================

    def send_connection_request(self, profile_url: str, name: str,
                                title: str = None, company: str = None,
                                location: str = None, industry: str = None,
                                mutual_connections: int = 0,
                                mutual_connection_names: List[str] = None,
                                has_profile_photo: bool = True,
                                connection_count: int = None,
                                recent_activity: datetime = None,
                                custom_message: str = None,
                                source: str = 'manual',
                                skip_scoring: bool = False) -> Optional[ConnectionRequest]:
        """
        Send a connection request with optional personalized message

        Args:
            profile_url: LinkedIn profile URL
            name: Target's name
            title: Target's job title
            company: Target's company
            location: Target's location
            industry: Target's industry
            mutual_connections: Number of mutual connections
            mutual_connection_names: List of mutual connection names
            has_profile_photo: Whether profile has photo
            connection_count: Their total connection count
            recent_activity: Last activity date
            custom_message: Custom message (if None, will generate with AI)
            source: Source of this request (manual, campaign, auto, search)
            skip_scoring: Skip lead scoring (for manual overrides)

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

        # Score the prospect using lead scoring engine
        lead_score = None
        score_breakdown = None
        priority = None

        if self.use_lead_scoring and not skip_scoring:
            prospect = {
                'name': name,
                'title': title,
                'company': company,
                'industry': industry,
                'location': location,
                'profile_url': profile_url,
                'mutual_connections': mutual_connections,
                'mutual_connection_names': mutual_connection_names or [],
                'has_profile_photo': has_profile_photo,
                'connection_count': connection_count,
                'recent_activity': recent_activity
            }

            score_result = self.lead_scorer.score_prospect(prospect)
            lead_score = score_result['total_score']
            score_breakdown = score_result['scores_breakdown']
            priority = score_result['priority']

            # Check minimum score threshold
            if lead_score < self.min_lead_score:
                print(f"⛔ Lead score too low ({lead_score:.1f} < {self.min_lead_score}) - skipping {name}")
                print(f"   Priority: {priority} | Recommendation: {score_result['recommendation']}")
                return None

            print(f"✅ Lead score: {lead_score:.1f}/100 (Priority: {priority})")
            if score_breakdown['engagement_history'] > 50:
                print(f"   💎 Has engaged with your content!")
            if score_breakdown['mutual_connections'] > 70:
                print(f"   🤝 Strong mutual connections")
            if score_breakdown['company_targeting'] > 70:
                print(f"   🎯 Target company employee")

        # Generate personalized message if needed
        message = custom_message
        if message is None and self.personalize_requests:
            # Pass score context to message generator for better personalization
            message = self._generate_connection_message(
                name, title, company,
                lead_score=lead_score,
                score_breakdown=score_breakdown
            )

        try:
            # Send connection request via LinkedIn client
            if self.client:
                success = self.client.send_connection_request(profile_url, message)
            else:
                # Client not initialized (testing mode)
                print("⚠️  LinkedIn client not initialized - simulating request")
                success = True

            # Create connection request record with lead score
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
                success=success,
                lead_score=lead_score,
                score_breakdown=json.dumps(score_breakdown) if score_breakdown else None,
                priority_tier=priority
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
                                    company: str = None, lead_score: float = None,
                                    score_breakdown: Dict = None) -> str:
        """
        Generate personalized connection request message with AI

        Args:
            name: Target's name
            title: Target's job title
            company: Target's company
            lead_score: Lead score (0-100) if available
            score_breakdown: Score breakdown by category if available

        Returns:
            Personalized message string
        """
        user_profile = self.config.get('user_profile', {})

        # Build context from score breakdown for better personalization
        context_hints = []
        if score_breakdown:
            if score_breakdown.get('engagement_history', 0) > 50:
                context_hints.append("they've engaged with your content before")
            if score_breakdown.get('mutual_connections', 0) > 70:
                context_hints.append("you have strong mutual connections")
            if score_breakdown.get('company_targeting', 0) > 70:
                context_hints.append("they work at a target company")

        context_note = f"\nContext: {', '.join(context_hints)}" if context_hints else ""

        prompt = f"""Generate a brief, professional LinkedIn connection request message.

TARGET PERSON:
- Name: {name}
- Title: {title or 'Professional'}
- Company: {company or 'their company'}{context_note}

YOUR PROFILE:
- Name: {user_profile.get('name', 'Your Name')}
- Title: {user_profile.get('title', 'Professional')}
- Industry: {user_profile.get('industry', 'Technology')}

Requirements:
- Keep it SHORT (under 200 characters to fit LinkedIn's limit)
- Be genuine and professional
- Mention a shared interest or connection point
- If they engaged with your content, acknowledge it naturally
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

    def process_incoming_requests(self, max_requests: int = None) -> Dict:
        """
        Process incoming connection requests with auto-accept filters

        Args:
            max_requests: Maximum number of requests to process (None = all)

        Returns:
            Dictionary with processing results
        """
        if not self.auto_accept_enabled:
            return {
                'enabled': False,
                'message': 'Auto-accept is disabled',
                'total_processed': 0,
                'accepted': 0,
                'declined': 0,
                'pending': 0,
                'accepted_profiles': []
            }

        # Get incoming requests via LinkedIn client
        if self.client:
            incoming_requests = self.client.get_incoming_connection_requests()
        else:
            # Client not initialized (testing mode)
            print("⚠️  LinkedIn client not initialized - no incoming requests")
            incoming_requests = []

        accepted = 0
        declined = 0
        pending = 0
        accepted_profiles = []

        # Limit requests to process if specified
        requests_to_process = incoming_requests[:max_requests] if max_requests else incoming_requests

        for request in requests_to_process:
            decision = self._evaluate_connection_request(request)

            if decision == 'accept':
                # Accept the request
                if self.client:
                    self.client.accept_connection_request(request.get('request_id', ''))
                accepted += 1

                # Track accepted profile
                profile_info = f"{request['name']}"
                if request.get('title'):
                    profile_info += f" - {request['title']}"
                if request.get('company'):
                    profile_info += f" at {request['company']}"
                accepted_profiles.append(profile_info)

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
                if self.client:
                    self.client.decline_connection_request(request.get('request_id', ''))
                declined += 1

            else:
                pending += 1

        return {
            'enabled': True,
            'total_processed': len(requests_to_process),
            'accepted': accepted,
            'declined': declined,
            'pending': pending,
            'accepted_profiles': accepted_profiles
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

    def enroll_in_sequence(self, connection_id: int, sequence_id: int,
                          use_timezone_scheduling: bool = None) -> Optional[SequenceEnrollment]:
        """
        Enroll a connection in a message sequence

        Args:
            connection_id: Connection ID
            sequence_id: MessageSequence ID
            use_timezone_scheduling: Override timezone scheduling setting (None = use config default)

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

        # Get sequence and connection
        sequence = self.db.query(MessageSequence).filter(
            MessageSequence.id == sequence_id
        ).first()

        if not sequence or not sequence.is_active:
            print(f"Sequence {sequence_id} not found or inactive")
            return None

        connection = self.db.query(Connection).filter(
            Connection.id == connection_id
        ).first()

        if not connection:
            print(f"Connection {connection_id} not found")
            return None

        # Use timezone scheduling if enabled
        use_tz = use_timezone_scheduling if use_timezone_scheduling is not None else self.use_timezone_scheduling

        # Calculate first message time
        steps = json.loads(sequence.steps)
        first_step_delay = steps[0].get('delay_days', 0)

        if use_tz and connection.location:
            # Use timezone-based scheduling from message sequence engine
            try:
                next_message_at = self.sequence_engine.schedule_with_timezone(
                    connection=connection,
                    send_time_local="09:00"  # Default to 9am their local time
                )
                # Add delay days
                next_message_at = next_message_at + timedelta(days=first_step_delay)
                print(f"   🌍 Using timezone scheduling for {connection.location}")
            except Exception as e:
                print(f"   ⚠️ Timezone scheduling failed, using UTC: {e}")
                next_message_at = datetime.utcnow() + timedelta(days=first_step_delay)
        else:
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

        Also checks for behavioral triggers if enabled

        Returns:
            Dictionary with processing results
        """
        now = datetime.utcnow()

        # Check behavioral triggers first (if enabled)
        new_enrollments = 0
        if self.use_behavioral_triggers:
            try:
                new_enrollments = self._check_behavioral_triggers()
            except Exception as e:
                print(f"⚠️ Error checking behavioral triggers: {e}")

        # Get enrollments with messages due
        due_enrollments = self.db.query(SequenceEnrollment).filter(
            and_(
                SequenceEnrollment.status == 'active',
                SequenceEnrollment.next_message_at <= now
            )
        ).all()

        if not due_enrollments:
            return {
                'messages_sent': 0,
                'message': 'No messages due',
                'new_enrollments': new_enrollments
            }

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
            'total_processed': len(due_enrollments),
            'new_enrollments': new_enrollments
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
            if self.client:
                success = self.client.send_message(connection.profile_url, message_content)
                # Close any messaging overlay
                self.client.close_messaging_overlay()
            else:
                # Client not initialized (testing mode)
                print("⚠️  LinkedIn client not initialized - simulating message send")
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

    def _check_behavioral_triggers(self) -> int:
        """
        Check for behavioral triggers and auto-enroll connections in sequences

        Returns:
            Number of new enrollments created
        """
        # Get active sequences with behavioral triggers
        sequences = self.db.query(MessageSequence).filter(
            and_(
                MessageSequence.is_active == True,
                MessageSequence.trigger_type.in_(['profile_view', 'post_engagement'])
            )
        ).all()

        if not sequences:
            return 0

        new_enrollments = 0

        for sequence in sequences:
            # Check for trigger events from message sequence engine
            trigger_type = sequence.trigger_type

            if trigger_type == 'profile_view':
                # Find connections who viewed profile recently (last 24 hours)
                trigger_connections = self.sequence_engine.check_profile_view_trigger(
                    hours_ago=24
                )
            elif trigger_type == 'post_engagement':
                # Find connections who engaged with posts recently
                trigger_connections = self.sequence_engine.check_engagement_trigger(
                    hours_ago=24
                )
            else:
                continue

            # Enroll each triggered connection
            for conn_id in trigger_connections:
                try:
                    enrollment = self.enroll_in_sequence(conn_id, sequence.id)
                    if enrollment:
                        new_enrollments += 1
                        print(f"   🎯 Behavioral trigger: Enrolled connection {conn_id} in '{sequence.name}'")
                except Exception as e:
                    print(f"   ⚠️ Failed to enroll connection {conn_id}: {e}")

        return new_enrollments

    # ========================================
    # LEAD SCORING UTILITIES
    # ========================================

    def batch_score_prospects(self, prospects: List[Dict]) -> List[Dict]:
        """
        Score multiple prospects and return sorted by score

        Args:
            prospects: List of prospect dictionaries

        Returns:
            List of prospects with scores, sorted by total_score descending
        """
        return self.lead_scorer.batch_score_prospects(prospects)

    def get_prospect_score_stats(self, prospects: List[Dict]) -> Dict:
        """
        Get statistics on a batch of scored prospects

        Args:
            prospects: List of prospects with scores

        Returns:
            Dictionary with statistics
        """
        return self.lead_scorer.get_score_stats(prospects)

    # ========================================
    # A/B TESTING FOR MESSAGE SEQUENCES
    # ========================================

    def create_ab_test_sequence(self, name: str, variant_a_steps: List[Dict],
                                variant_b_steps: List[Dict],
                                split_ratio: float = 0.5,
                                trigger_type: str = 'new_connection',
                                description: str = None) -> Dict:
        """
        Create an A/B test for message sequences

        Args:
            name: Base name for the test
            variant_a_steps: Steps for variant A
            variant_b_steps: Steps for variant B
            split_ratio: Ratio for A/B split (0.5 = 50/50)
            trigger_type: When to trigger the sequence
            description: Description of the test

        Returns:
            Dictionary with variant A and B sequence IDs
        """
        if not self.use_sequence_ab_testing:
            print("⚠️ A/B testing is disabled in config")
            return None

        # Create both sequences
        seq_a = self.create_message_sequence(
            name=f"{name} (Variant A)",
            steps=variant_a_steps,
            trigger_type=trigger_type,
            description=f"A/B Test: {description or name}"
        )

        seq_b = self.create_message_sequence(
            name=f"{name} (Variant B)",
            steps=variant_b_steps,
            trigger_type=trigger_type,
            description=f"A/B Test: {description or name}"
        )

        # Store A/B test config
        test_config = {
            'variant_a_id': seq_a.id,
            'variant_b_id': seq_b.id,
            'split_ratio': split_ratio,
            'name': name
        }

        print(f"✅ Created A/B test: {name}")
        print(f"   Variant A: Sequence {seq_a.id}")
        print(f"   Variant B: Sequence {seq_b.id}")
        print(f"   Split: {int(split_ratio*100)}% A / {int((1-split_ratio)*100)}% B")

        return test_config

    def get_ab_test_results(self, variant_a_id: int, variant_b_id: int) -> Dict:
        """
        Get A/B test results for two sequence variants

        Args:
            variant_a_id: Variant A sequence ID
            variant_b_id: Variant B sequence ID

        Returns:
            Dictionary with test results and winner
        """
        # Use message sequence engine for analysis
        test_config = {
            'variant_a_id': variant_a_id,
            'variant_b_id': variant_b_id
        }

        return self.sequence_engine.get_ab_test_results(test_config)
