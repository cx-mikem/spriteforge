#!/usr/bin/env python
"""Health check script for deployment monitoring."""

import sys
import logging
from app.config import Config
from app.database import engine

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def check_database():
    """Check database connectivity."""
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True, "Database OK"
    except Exception as e:
        return False, f"Database: {e}"


def check_openai_key():
    """Check OpenAI API key is configured."""
    if Config.OPENAI_API_KEY:
        return True, "OpenAI key configured"
    return False, "OpenAI key not set"


def check_storage():
    """Check storage backend is accessible."""
    try:
        from storage import get_storage_backend
        backend = get_storage_backend()
        # Just try to instantiate; full test would be more involved
        return True, f"Storage backend: {Config.STORAGE_BACKEND}"
    except Exception as e:
        return False, f"Storage: {e}"


def main():
    checks = [
        ("Database", check_database),
        ("OpenAI", check_openai_key),
        ("Storage", check_storage),
    ]

    results = []
    all_ok = True

    for name, check_fn in checks:
        ok, msg = check_fn()
        results.append((name, ok, msg))
        if not ok:
            all_ok = False

    # Output
    for name, ok, msg in results:
        status = "✓" if ok else "✗"
        print(f"{status} {name}: {msg}")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
