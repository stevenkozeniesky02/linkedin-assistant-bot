"""Database Models for LinkedIn Assistant Bot"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Post(Base):
    """Model for LinkedIn posts"""
    __tablename__ = 'posts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    hashtags = Column(String(500))
    topic = Column(String(200))
    tone = Column(String(50))
    length = Column(String(20))

    # AI generation metadata
    ai_provider = Column(String(50))
    ai_model = Column(String(100))

    # Publishing info
    published = Column(Boolean, default=False)
    published_at = Column(DateTime)
    linkedin_url = Column(String(500))

    # Scheduling
    scheduled_time = Column(DateTime, nullable=True)
    is_scheduled = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    analytics = relationship("Analytics", back_populates="post", uselist=False)
    comments = relationship("Comment", back_populates="post")

    def __repr__(self):
        return f"<Post(id={self.id}, topic='{self.topic}', published={self.published})>"


class Comment(Base):
    """Model for LinkedIn comments"""
    __tablename__ = 'comments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey('posts.id'), nullable=True)
    content = Column(Text, nullable=False)
    tone = Column(String(50))

    # Target post information (the post we're commenting on)
    target_post_author = Column(String(200))
    target_post_url = Column(String(500))
    target_post_excerpt = Column(Text)

    # AI generation metadata
    ai_provider = Column(String(50))
    ai_model = Column(String(100))

    # Publishing info
    published = Column(Boolean, default=False)
    published_at = Column(DateTime)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    post = relationship("Post", back_populates="comments")

    def __repr__(self):
        return f"<Comment(id={self.id}, published={self.published})>"


class Analytics(Base):
    """Model for post analytics/metrics"""
    __tablename__ = 'analytics'

    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey('posts.id'), unique=True, nullable=False)

    # Engagement metrics
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    profile_views = Column(Integer, default=0)

    # Calculated metrics
    engagement_rate = Column(Float, default=0.0)
    engagement_score = Column(Integer, default=0)

    # Last updated
    last_synced = Column(DateTime)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    post = relationship("Post", back_populates="analytics")

    def calculate_engagement_rate(self):
        """Calculate engagement rate (engagement / views)"""
        if self.views > 0:
            total_engagement = self.likes + self.comments_count + self.shares
            self.engagement_rate = (total_engagement / self.views) * 100
        else:
            self.engagement_rate = 0.0
        return self.engagement_rate

    def __repr__(self):
        return f"<Analytics(post_id={self.post_id}, views={self.views}, likes={self.likes})>"


class Activity(Base):
    """Model for tracking LinkedIn activity (for safety monitoring)"""
    __tablename__ = 'activities'

    id = Column(Integer, primary_key=True, autoincrement=True)
    action_type = Column(String(50), nullable=False)  # post, comment, like, view, connection_request, etc.
    target_type = Column(String(50))  # post, profile, company, etc.
    target_id = Column(String(200))  # ID or URL of target

    # Risk scoring
    risk_score = Column(Float, default=0.0)  # 0-1 scale

    # Timestamps
    performed_at = Column(DateTime, default=datetime.utcnow)

    # Metadata
    duration_seconds = Column(Float)  # How long the action took
    success = Column(Boolean, default=True)
    error_message = Column(Text)

    def __repr__(self):
        return f"<Activity(id={self.id}, type='{self.action_type}', performed_at={self.performed_at})>"


class Connection(Base):
    """Model for LinkedIn connections"""
    __tablename__ = 'connections'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Profile information
    name = Column(String(200), nullable=False)
    title = Column(String(300))
    company = Column(String(200))
    location = Column(String(200))
    profile_url = Column(String(500), unique=True)

    # Connection metadata
    connection_date = Column(DateTime)
    connection_source = Column(String(100))  # how we connected (automated, manual, etc.)

    # Engagement tracking
    messages_sent = Column(Integer, default=0)
    messages_received = Column(Integer, default=0)
    posts_engaged = Column(Integer, default=0)  # Number of their posts we engaged with
    mutual_connections = Column(Integer, default=0)

    # Quality scoring
    quality_score = Column(Float, default=0.0)  # 0-10 scale
    engagement_level = Column(String(20))  # high, medium, low, none

    # Status
    is_active = Column(Boolean, default=True)
    is_target_audience = Column(Boolean, default=False)  # Marked as relevant to our niche
    notes = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_interaction = Column(DateTime)

    def __repr__(self):
        return f"<Connection(id={self.id}, name='{self.name}', quality={self.quality_score})>"


class SafetyAlert(Base):
    """Model for safety alerts and warnings"""
    __tablename__ = 'safety_alerts'

    id = Column(Integer, primary_key=True, autoincrement=True)

    alert_type = Column(String(50), nullable=False)  # rate_limit, suspicious_pattern, ban_risk, etc.
    severity = Column(String(20), nullable=False)  # low, medium, high, critical
    message = Column(Text, nullable=False)

    # Risk assessment
    risk_score = Column(Float)  # 0-1 scale
    recommended_action = Column(Text)

    # Status
    acknowledged = Column(Boolean, default=False)
    resolved = Column(Boolean, default=False)
    auto_paused = Column(Boolean, default=False)  # Did we auto-pause activity?

    # Metadata
    triggered_by = Column(String(200))  # What triggered the alert
    details = Column(Text)  # JSON with additional details

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    acknowledged_at = Column(DateTime)
    resolved_at = Column(DateTime)

    def __repr__(self):
        return f"<SafetyAlert(id={self.id}, type='{self.alert_type}', severity='{self.severity}')>"


class Campaign(Base):
    """Model for engagement campaigns"""
    __tablename__ = 'campaigns'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Basic info
    name = Column(String(200), nullable=False)
    description = Column(Text)
    campaign_type = Column(String(50), nullable=False)  # hashtag, company, influencer, topic

    # Status and scheduling
    status = Column(String(20), default='draft')  # draft, active, paused, completed, archived
    start_date = Column(DateTime)
    end_date = Column(DateTime)

    # Goals and metrics
    target_engagements = Column(Integer)  # Target number of engagements
    target_connections = Column(Integer)  # Target number of new connections
    max_actions_per_day = Column(Integer, default=10)  # Daily action limit for this campaign

    # Target criteria (stored as JSON string)
    target_criteria = Column(Text)  # JSON: {"hashtags": ["ai", "ml"], "companies": ["Google"], etc.}

    # Campaign strategy
    engagement_types = Column(String(200))  # Comma-separated: comment,like,share
    priority = Column(String(20), default='medium')  # low, medium, high

    # Performance tracking
    total_engagements = Column(Integer, default=0)
    total_connections_made = Column(Integer, default=0)
    total_posts_engaged = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)  # Percentage

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_executed = Column(DateTime)

    # Relationships
    targets = relationship("CampaignTarget", back_populates="campaign", cascade="all, delete-orphan")
    activities = relationship("CampaignActivity", back_populates="campaign", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Campaign(id={self.id}, name='{self.name}', type='{self.campaign_type}', status='{self.status}')>"


class CampaignTarget(Base):
    """Model for specific targets within a campaign"""
    __tablename__ = 'campaign_targets'

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'), nullable=False)

    # Target information
    target_type = Column(String(50), nullable=False)  # hashtag, company, profile, keyword
    target_value = Column(String(500), nullable=False)  # The actual hashtag, company name, profile URL, etc.

    # Priority and status
    priority = Column(String(20), default='medium')  # low, medium, high
    is_active = Column(Boolean, default=True)

    # Performance tracking
    posts_found = Column(Integer, default=0)
    engagements_count = Column(Integer, default=0)
    last_checked = Column(DateTime)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    campaign = relationship("Campaign", back_populates="targets")

    def __repr__(self):
        return f"<CampaignTarget(id={self.id}, type='{self.target_type}', value='{self.target_value}')>"


class CampaignActivity(Base):
    """Model for tracking actions taken as part of a campaign"""
    __tablename__ = 'campaign_activities'

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'), nullable=False)
    activity_id = Column(Integer, ForeignKey('activities.id'))  # Links to Activity table

    # Target information
    target_post_url = Column(String(500))
    target_author = Column(String(200))
    target_author_title = Column(String(300))
    target_author_company = Column(String(200))

    # Action details
    action_type = Column(String(50), nullable=False)  # comment, like, view, connection_request, message
    action_result = Column(String(500))  # Link to comment, result of connection request, etc.

    # Success tracking
    success = Column(Boolean, default=True)
    error_message = Column(Text)

    # Metadata
    matched_target = Column(String(500))  # Which campaign target matched (hashtag, company, etc.)
    post_excerpt = Column(Text)  # Preview of the post engaged with

    # Timestamps
    performed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    campaign = relationship("Campaign", back_populates="activities")
    activity = relationship("Activity")

    def __repr__(self):
        return f"<CampaignActivity(id={self.id}, campaign_id={self.campaign_id}, action='{self.action_type}')>"


class ConnectionRequest(Base):
    """Model for tracking outgoing connection requests"""
    __tablename__ = 'connection_requests'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Target information
    target_name = Column(String(200), nullable=False)
    target_profile_url = Column(String(500), unique=True, nullable=False)
    target_title = Column(String(300))
    target_company = Column(String(200))
    target_location = Column(String(200))
    target_industry = Column(String(200))

    # Request details
    message = Column(Text)  # Personalized connection message
    message_template = Column(String(100))  # Template used (if any)

    # Status tracking
    status = Column(String(50), default='pending')  # pending, accepted, rejected, withdrawn, expired
    sent_at = Column(DateTime, default=datetime.utcnow)
    responded_at = Column(DateTime)

    # Source tracking
    source = Column(String(100))  # campaign, manual, auto, search
    source_id = Column(String(200))  # ID of campaign or search that generated this

    # Quality scoring
    match_score = Column(Float, default=0.0)  # How well they match criteria (0-10)
    priority = Column(String(20), default='medium')  # low, medium, high

    # Lead scoring (0-100 scale)
    lead_score = Column(Float)  # Overall lead score from LeadScoringEngine
    score_breakdown = Column(Text)  # JSON-encoded score breakdown by category
    priority_tier = Column(String(20))  # critical, high, medium, low, ignore

    # Result tracking
    connection_id = Column(Integer, ForeignKey('connections.id'))  # Link to Connection if accepted
    success = Column(Boolean)
    notes = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    connection = relationship("Connection", foreign_keys=[connection_id])

    def __repr__(self):
        return f"<ConnectionRequest(id={self.id}, target='{self.target_name}', status='{self.status}')>"


class MessageSequence(Base):
    """Model for automated message sequences (follow-ups)"""
    __tablename__ = 'message_sequences'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Sequence configuration
    name = Column(String(200), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)

    # Trigger conditions
    trigger_type = Column(String(50), nullable=False)  # new_connection, campaign_engage, manual
    trigger_criteria = Column(Text)  # JSON with conditions

    # Sequence steps (stored as JSON)
    steps = Column(Text, nullable=False)  # JSON array of message steps with delays

    # Targeting
    target_industries = Column(Text)  # JSON array
    target_titles = Column(Text)  # JSON array
    target_companies = Column(Text)  # JSON array

    # Performance tracking
    total_started = Column(Integer, default=0)
    total_completed = Column(Integer, default=0)
    total_responses = Column(Integer, default=0)
    response_rate = Column(Float, default=0.0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    enrollments = relationship("SequenceEnrollment", back_populates="sequence", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<MessageSequence(id={self.id}, name='{self.name}', active={self.is_active})>"


class SequenceEnrollment(Base):
    """Model for tracking individual enrollments in message sequences"""
    __tablename__ = 'sequence_enrollments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    sequence_id = Column(Integer, ForeignKey('message_sequences.id'), nullable=False)
    connection_id = Column(Integer, ForeignKey('connections.id'), nullable=False)

    # Status tracking
    status = Column(String(50), default='active')  # active, paused, completed, stopped
    current_step = Column(Integer, default=0)  # Which step they're on (0-indexed)

    # Scheduling
    next_message_at = Column(DateTime)  # When to send next message
    last_message_sent = Column(DateTime)

    # Performance tracking
    messages_sent = Column(Integer, default=0)
    responses_received = Column(Integer, default=0)
    responded = Column(Boolean, default=False)
    response_date = Column(DateTime)

    # Metadata
    enrollment_date = Column(DateTime, default=datetime.utcnow)
    completion_date = Column(DateTime)
    notes = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sequence = relationship("MessageSequence", back_populates="enrollments")
    connection = relationship("Connection")
    messages = relationship("SequenceMessage", back_populates="enrollment", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<SequenceEnrollment(id={self.id}, sequence_id={self.sequence_id}, step={self.current_step}, status='{self.status}')>"


class SequenceMessage(Base):
    """Model for individual messages sent as part of a sequence"""
    __tablename__ = 'sequence_messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    enrollment_id = Column(Integer, ForeignKey('sequence_enrollments.id'), nullable=False)

    # Message details
    step_number = Column(Integer, nullable=False)  # Which step in the sequence
    message_content = Column(Text, nullable=False)
    message_template = Column(String(100))  # Template used

    # Delivery tracking
    status = Column(String(50), default='pending')  # pending, sent, delivered, failed
    scheduled_for = Column(DateTime)
    sent_at = Column(DateTime)
    delivered_at = Column(DateTime)

    # Response tracking
    response_received = Column(Boolean, default=False)
    response_date = Column(DateTime)
    response_content = Column(Text)

    # Metadata
    ai_provider = Column(String(50))
    error_message = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    enrollment = relationship("SequenceEnrollment", back_populates="messages")

    def __repr__(self):
        return f"<SequenceMessage(id={self.id}, enrollment_id={self.enrollment_id}, step={self.step_number}, status='{self.status}')>"


class ABTest(Base):
    """Model for A/B tests on content"""
    __tablename__ = 'ab_tests'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Test configuration
    name = Column(String(200), nullable=False)
    description = Column(Text)
    hypothesis = Column(Text)  # What we're testing (e.g., "Short posts get more engagement")

    # Test type
    test_type = Column(String(50), nullable=False)  # headline, tone, length, emoji, time_of_day, cta, hashtag

    # Status
    status = Column(String(20), default='draft')  # draft, running, paused, completed, cancelled

    # Statistical configuration
    confidence_level = Column(Float, default=0.95)  # 95% confidence by default
    minimum_sample_size = Column(Integer, default=30)  # Minimum posts per variant

    # Duration
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    planned_duration_days = Column(Integer)  # How long to run the test

    # Results
    winner_variant_id = Column(Integer, ForeignKey('test_variants.id'))
    is_significant = Column(Boolean, default=False)  # Statistical significance reached
    p_value = Column(Float)  # Statistical p-value
    confidence_interval = Column(String(100))  # Confidence interval as string

    # Metadata
    created_by = Column(String(100))
    notes = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)

    # Relationships
    variants = relationship("TestVariant", back_populates="test", foreign_keys="TestVariant.test_id", cascade="all, delete-orphan")
    winner = relationship("TestVariant", foreign_keys=[winner_variant_id], post_update=True)

    def __repr__(self):
        return f"<ABTest(id={self.id}, name='{self.name}', type='{self.test_type}', status='{self.status}')>"


class TestVariant(Base):
    """Model for individual variants within an A/B test"""
    __tablename__ = 'test_variants'

    id = Column(Integer, primary_key=True, autoincrement=True)
    test_id = Column(Integer, ForeignKey('ab_tests.id'), nullable=False)

    # Variant configuration
    variant_name = Column(String(50), nullable=False)  # control, variant_a, variant_b, etc.
    variant_label = Column(String(200))  # Human-readable label (e.g., "Short & Professional")

    # Configuration (JSON string)
    variant_config = Column(Text)  # JSON with variant settings (tone, length, emoji, etc.)

    # Sample tracking
    posts_count = Column(Integer, default=0)  # Number of posts in this variant

    # Performance metrics (aggregated from Analytics)
    total_views = Column(Integer, default=0)
    total_likes = Column(Integer, default=0)
    total_comments = Column(Integer, default=0)
    total_shares = Column(Integer, default=0)

    # Calculated metrics
    avg_engagement_rate = Column(Float, default=0.0)  # Average engagement rate
    avg_views = Column(Float, default=0.0)
    avg_likes = Column(Float, default=0.0)
    avg_comments = Column(Float, default=0.0)
    avg_shares = Column(Float, default=0.0)

    # Statistical analysis
    std_deviation = Column(Float)  # Standard deviation of engagement rates
    confidence_interval_lower = Column(Float)
    confidence_interval_upper = Column(Float)

    # Status
    is_control = Column(Boolean, default=False)  # Is this the control variant?
    is_winner = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    test = relationship("ABTest", back_populates="variants", foreign_keys=[test_id])
    assignments = relationship("TestAssignment", back_populates="variant", cascade="all, delete-orphan")

    def calculate_metrics(self):
        """Calculate average metrics from posts"""
        if self.posts_count > 0:
            self.avg_views = self.total_views / self.posts_count
            self.avg_likes = self.total_likes / self.posts_count
            self.avg_comments = self.total_comments / self.posts_count
            self.avg_shares = self.total_shares / self.posts_count

            # Calculate engagement rate
            if self.total_views > 0:
                total_engagement = self.total_likes + self.total_comments + self.total_shares
                self.avg_engagement_rate = (total_engagement / self.total_views) * 100
            else:
                self.avg_engagement_rate = 0.0

    def __repr__(self):
        return f"<TestVariant(id={self.id}, test_id={self.test_id}, name='{self.variant_name}', posts={self.posts_count})>"


class TestAssignment(Base):
    """Model for assigning posts to test variants"""
    __tablename__ = 'test_assignments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    test_id = Column(Integer, ForeignKey('ab_tests.id'), nullable=False)
    variant_id = Column(Integer, ForeignKey('test_variants.id'), nullable=False)
    post_id = Column(Integer, ForeignKey('posts.id'), unique=True, nullable=False)

    # Assignment metadata
    assigned_at = Column(DateTime, default=datetime.utcnow)
    assignment_method = Column(String(50))  # random, manual, weighted

    # Performance snapshot (cached from Analytics)
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    engagement_rate = Column(Float, default=0.0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_synced = Column(DateTime)  # When we last synced metrics from Analytics

    # Relationships
    test = relationship("ABTest")
    variant = relationship("TestVariant", back_populates="assignments")
    post = relationship("Post")

    def sync_metrics_from_analytics(self, analytics):
        """Update cached metrics from Analytics model"""
        self.views = analytics.views
        self.likes = analytics.likes
        self.comments_count = analytics.comments_count
        self.shares = analytics.shares
        self.engagement_rate = analytics.engagement_rate
        self.last_synced = datetime.utcnow()

    def __repr__(self):
        return f"<TestAssignment(id={self.id}, test_id={self.test_id}, variant_id={self.variant_id}, post_id={self.post_id})>"


class HashtagPerformance(Base):
    """Model for tracking hashtag performance across posts"""
    __tablename__ = 'hashtag_performance'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Association
    post_id = Column(Integer, ForeignKey('posts.id'), nullable=False)
    hashtag = Column(String(100), nullable=False)  # Hashtag without # symbol

    # Tracking
    recorded_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    post = relationship("Post")

    def __repr__(self):
        return f"<HashtagPerformance(id={self.id}, post_id={self.post_id}, hashtag='#{self.hashtag}')>"


class Competitor(Base):
    """Model for tracking competitors on LinkedIn"""
    __tablename__ = 'competitors'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Profile information
    name = Column(String(200), nullable=False)
    title = Column(String(300))
    company = Column(String(200))
    industry = Column(String(200))
    profile_url = Column(String(500), unique=True, nullable=False)

    # Monitoring settings
    is_active = Column(Boolean, default=True)  # Are we actively monitoring them?
    monitoring_frequency = Column(String(20), default='daily')  # daily, weekly, monthly
    priority = Column(String(20), default='medium')  # low, medium, high

    # Current stats (latest snapshot)
    followers_count = Column(Integer, default=0)
    connections_count = Column(Integer, default=0)
    posts_count = Column(Integer, default=0)

    # Derived metrics (calculated from snapshots)
    avg_posting_frequency = Column(Float, default=0.0)  # posts per week
    avg_engagement_rate = Column(Float, default=0.0)  # percentage
    avg_likes_per_post = Column(Float, default=0.0)
    avg_comments_per_post = Column(Float, default=0.0)

    # Comparison with your performance
    relative_engagement = Column(Float)  # Their engagement vs yours (ratio)
    relative_frequency = Column(Float)  # Their posting frequency vs yours (ratio)

    # Metadata
    notes = Column(Text)
    tags = Column(String(500))  # Comma-separated tags (e.g., "direct-competitor,thought-leader")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_checked = Column(DateTime)

    # Relationships
    snapshots = relationship("CompetitorSnapshot", back_populates="competitor", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Competitor(id={self.id}, name='{self.name}', active={self.is_active})>"


class CompetitorSnapshot(Base):
    """Model for tracking competitor metrics over time"""
    __tablename__ = 'competitor_snapshots'

    id = Column(Integer, primary_key=True, autoincrement=True)
    competitor_id = Column(Integer, ForeignKey('competitors.id'), nullable=False)

    # Profile stats
    followers_count = Column(Integer, default=0)
    connections_count = Column(Integer, default=0)
    posts_count = Column(Integer, default=0)

    # Recent activity (last 7 days)
    posts_last_week = Column(Integer, default=0)
    posts_last_month = Column(Integer, default=0)

    # Engagement metrics (from recent posts)
    total_likes = Column(Integer, default=0)
    total_comments = Column(Integer, default=0)
    total_shares = Column(Integer, default=0)
    total_views = Column(Integer, default=0)

    # Calculated metrics
    avg_engagement_rate = Column(Float, default=0.0)
    avg_likes_per_post = Column(Float, default=0.0)
    avg_comments_per_post = Column(Float, default=0.0)
    posting_frequency = Column(Float, default=0.0)  # posts per week

    # Content analysis
    top_hashtags = Column(Text)  # JSON array of most used hashtags
    top_topics = Column(Text)  # JSON array of most discussed topics
    content_types = Column(Text)  # JSON: {"text": 10, "image": 5, "video": 2, "poll": 1}

    # Snapshot metadata
    snapshot_date = Column(DateTime, default=datetime.utcnow)
    sample_size = Column(Integer, default=0)  # How many posts analyzed
    scrape_success = Column(Boolean, default=True)
    error_message = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    competitor = relationship("Competitor", back_populates="snapshots")

    def __repr__(self):
        return f"<CompetitorSnapshot(id={self.id}, competitor_id={self.competitor_id}, date={self.snapshot_date})>"
