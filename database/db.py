"""Database connection and management"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from .models import Base


class Database:
    """Database connection manager"""

    def __init__(self, config: dict):
        """
        Initialize database connection

        Args:
            config: Configuration dictionary from config.yaml
        """
        self.config = config
        db_config = config.get('database', {})

        # Get database configuration
        db_type = db_config.get('type', 'sqlite')
        db_path = db_config.get('path', 'linkedin_assistant.db')

        # Create connection string
        if db_type == 'sqlite':
            # SQLite database
            self.connection_string = f'sqlite:///{db_path}'
        else:
            # PostgreSQL or other (from environment variable)
            self.connection_string = os.getenv('DATABASE_URL', f'sqlite:///{db_path}')

        # Create engine
        self.engine = create_engine(
            self.connection_string,
            echo=False,  # Set to True for SQL query logging
            pool_pre_ping=True  # Verify connections before using
        )

        # Create session factory
        session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(session_factory)

        # Create tables if they don't exist
        self.create_tables()

    def create_tables(self):
        """Create all tables in the database"""
        Base.metadata.create_all(self.engine)
        print(f"Database initialized at: {self.connection_string}")

    def get_session(self):
        """
        Get a new database session

        Returns:
            SQLAlchemy session
        """
        return self.Session()

    def close(self):
        """Close all database connections"""
        self.Session.remove()
        self.engine.dispose()
