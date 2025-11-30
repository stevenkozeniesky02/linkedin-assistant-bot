"""Database Migration: Add Lead Scoring Fields to ConnectionRequest

This migration adds the following columns to the connection_requests table:
- lead_score: Float - Overall lead score (0-100)
- score_breakdown: Text - JSON-encoded score breakdown
- priority_tier: String(20) - Priority tier (critical, high, medium, low, ignore)

Run this script ONCE to upgrade your database.
"""

import sqlite3
from pathlib import Path

def migrate_database():
    """Add lead scoring columns to connection_requests table"""

    # Try multiple possible database locations
    possible_paths = [
        Path(__file__).parent / 'linkedin_assistant.db',
        Path(__file__).parent / 'data' / 'linkedin_bot.db',
        Path(__file__).parent / 'data' / 'linkedin_assistant.db',
    ]

    db_path = None
    for path in possible_paths:
        if path.exists():
            db_path = path
            break

    if not db_path:
        print(f"❌ Database not found in any of these locations:")
        for path in possible_paths:
            print(f"   - {path}")
        print("\n   Run the bot at least once to create the database first.")
        return False

    print(f"📦 Migrating database at {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if columns already exist
        cursor.execute("PRAGMA table_info(connection_requests)")
        columns = [row[1] for row in cursor.fetchall()]

        migrations_applied = 0

        # Add lead_score column if it doesn't exist
        if 'lead_score' not in columns:
            print("   Adding 'lead_score' column...")
            cursor.execute("""
                ALTER TABLE connection_requests
                ADD COLUMN lead_score REAL
            """)
            migrations_applied += 1
        else:
            print("   ✓ 'lead_score' column already exists")

        # Add score_breakdown column if it doesn't exist
        if 'score_breakdown' not in columns:
            print("   Adding 'score_breakdown' column...")
            cursor.execute("""
                ALTER TABLE connection_requests
                ADD COLUMN score_breakdown TEXT
            """)
            migrations_applied += 1
        else:
            print("   ✓ 'score_breakdown' column already exists")

        # Add priority_tier column if it doesn't exist
        if 'priority_tier' not in columns:
            print("   Adding 'priority_tier' column...")
            cursor.execute("""
                ALTER TABLE connection_requests
                ADD COLUMN priority_tier VARCHAR(20)
            """)
            migrations_applied += 1
        else:
            print("   ✓ 'priority_tier' column already exists")

        # Commit changes
        conn.commit()

        if migrations_applied > 0:
            print(f"\n✅ Migration completed successfully!")
            print(f"   Applied {migrations_applied} schema change(s)")
        else:
            print(f"\n✅ Database already up to date - no changes needed")

        # Verify columns exist
        cursor.execute("PRAGMA table_info(connection_requests)")
        updated_columns = [row[1] for row in cursor.fetchall()]

        required_columns = ['lead_score', 'score_breakdown', 'priority_tier']
        all_present = all(col in updated_columns for col in required_columns)

        if all_present:
            print("\n✅ Verification successful - all lead scoring columns present")
        else:
            print("\n⚠️  Warning: Some columns may be missing")

        conn.close()
        return True

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("LinkedIn Assistant Bot - Database Migration")
    print("Add Lead Scoring Fields to Connection Requests")
    print("=" * 60)
    print()

    success = migrate_database()

    print()
    if success:
        print("🎉 You can now use lead scoring features!")
        print()
        print("Next steps:")
        print("1. Update config.yaml with your target companies/titles")
        print("2. Enable lead scoring: use_lead_scoring: true")
        print("3. Set minimum score threshold: min_lead_score: 40")
        print("4. Run connection requests - they'll be automatically scored!")
    else:
        print("❌ Migration failed - please check the error message above")

    print()
    print("=" * 60)
