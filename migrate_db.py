#!/usr/bin/env python3
"""
Database Migration Script
Adds scheduling columns to existing database
"""

import sqlite3
import os

def migrate_database():
    """Add scheduling columns to posts table"""

    db_path = 'linkedin_assistant.db'

    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        print("No migration needed - database will be created with correct schema")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if columns already exist
    cursor.execute("PRAGMA table_info(posts)")
    columns = [column[1] for column in cursor.fetchall()]

    migrations_needed = []

    if 'scheduled_time' not in columns:
        migrations_needed.append('scheduled_time')

    if 'is_scheduled' not in columns:
        migrations_needed.append('is_scheduled')

    if not migrations_needed:
        print("✓ Database is already up to date!")
        conn.close()
        return

    print(f"Applying migrations: {', '.join(migrations_needed)}")

    try:
        # Add scheduled_time column
        if 'scheduled_time' in migrations_needed:
            cursor.execute("""
                ALTER TABLE posts
                ADD COLUMN scheduled_time DATETIME
            """)
            print("✓ Added scheduled_time column")

        # Add is_scheduled column
        if 'is_scheduled' in migrations_needed:
            cursor.execute("""
                ALTER TABLE posts
                ADD COLUMN is_scheduled BOOLEAN DEFAULT 0
            """)
            print("✓ Added is_scheduled column")

        conn.commit()
        print("\n✓ Migration completed successfully!")

    except Exception as e:
        print(f"✗ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    print("LinkedIn Assistant Bot - Database Migration\n")
    migrate_database()
