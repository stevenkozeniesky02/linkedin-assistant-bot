"""Database session helper for LinkedIn Assistant Bot"""

import yaml
from pathlib import Path
from database.db import Database

# Global database instance
_db_instance = None


def get_session():
    """
    Get a database session.

    Returns:
        SQLAlchemy session
    """
    global _db_instance

    if _db_instance is None:
        # Load config
        config_path = Path(__file__).parent.parent / 'config.yaml'
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        # Initialize database
        _db_instance = Database(config)

    return _db_instance.get_session()
