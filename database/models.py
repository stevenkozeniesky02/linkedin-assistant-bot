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
