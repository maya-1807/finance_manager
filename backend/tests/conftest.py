"""Shared fixtures for backend tests.

Uses in-memory SQLite via CASHBOARD_DB_PATH=:memory: so tests
never touch the real database.
"""

import os
import sqlite3

import pytest

# Force in-memory DB before any backend module is imported
os.environ["CASHBOARD_DB_PATH"] = ":memory:"

from db.database import get_connection, init_db  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    """Reset the in-memory DB before every test."""
    import db.database as _db_mod

    # Drop the keep-alive so we get a brand-new shared-cache DB
    if _db_mod._keep_alive_conn is not None:
        _db_mod._keep_alive_conn.close()
        _db_mod._keep_alive_conn = None

    init_db()

    yield

    # Tear down
    if _db_mod._keep_alive_conn is not None:
        _db_mod._keep_alive_conn.close()
        _db_mod._keep_alive_conn = None


@pytest.fixture
def db() -> sqlite3.Connection:
    """Return a connection to the test DB."""
    conn = get_connection()
    yield conn
    conn.close()
