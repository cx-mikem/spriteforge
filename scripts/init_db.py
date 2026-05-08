#!/usr/bin/env python
"""Initialize database schema from models."""

import sys
import logging
from app.config import Config
from app.database import init_db, engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    try:
        logger.info("Initializing database...")
        init_db()
        logger.info("✓ Database initialized successfully")

        # Verify connection
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            logger.info(f"✓ Database connection verified")

        return 0
    except Exception as e:
        logger.error(f"✗ Failed to initialize database: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
