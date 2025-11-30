#!/usr/bin/env python3
"""
Database migration: Add hashtag_performance table

This migration creates the hashtag_performance table for tracking
hashtag usage and performance across posts.
"""

import sqlite3
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def migrate_database():
    """Add hashtag_performance table to the database."""

    # Find database
    possible_paths = [
        Path(__file__).parent.parent / 'linkedin_assistant.db',
        Path(__file__).parent.parent / 'data' / 'linkedin_bot.db',
        Path(__file__).parent.parent / 'data' / 'linkedin_assistant.db',
    ]

    db_path = None
    for path in possible_paths:
        if path.exists():
            db_path = path
            break

    if not db_path:
        logger.error("Could not find database file")
        logger.info(f"Searched in: {', '.join(str(p) for p in possible_paths)}")
        return False

    logger.info(f"Found database at: {db_path}")

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Check if table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='hashtag_performance'
        """)

        if cursor.fetchone():
            logger.info("Table 'hashtag_performance' already exists")
            conn.close()
            return True

        # Create hashtag_performance table
        logger.info("Creating hashtag_performance table...")

        cursor.execute("""
            CREATE TABLE hashtag_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                hashtag VARCHAR(100) NOT NULL,
                recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES posts (id)
            )
        """)

        # Create indexes for better query performance
        logger.info("Creating indexes...")

        cursor.execute("""
            CREATE INDEX idx_hashtag_performance_post_id
            ON hashtag_performance(post_id)
        """)

        cursor.execute("""
            CREATE INDEX idx_hashtag_performance_hashtag
            ON hashtag_performance(hashtag)
        """)

        cursor.execute("""
            CREATE INDEX idx_hashtag_performance_recorded_at
            ON hashtag_performance(recorded_at)
        """)

        conn.commit()
        logger.info("Migration completed successfully!")

        # Verify the table was created
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='hashtag_performance'
        """)

        if cursor.fetchone():
            logger.info("Verified: hashtag_performance table created")

            # Show table schema
            cursor.execute("PRAGMA table_info(hashtag_performance)")
            columns = cursor.fetchall()
            logger.info("Table schema:")
            for col in columns:
                logger.info(f"  {col[1]} {col[2]}")
        else:
            logger.error("Verification failed: Table not found")

        conn.close()
        return True

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


if __name__ == "__main__":
    success = migrate_database()
    exit(0 if success else 1)
