import sqlite3
from pathlib import Path

from config import DB_PATH

SCHEMA_PATH = Path(__file__).parent / "schema.sql"
SEED_PATH = Path(__file__).parent / "seed.sql"
MIGRATIONS_DIR = Path(__file__).parent / "migrations"

# When using an in-memory DB, all connections must share the same database.
# SQLite's shared-cache URI mode enables this. We keep one connection open
# for the lifetime of the process so the DB isn't destroyed when others close.
_keep_alive_conn: sqlite3.Connection | None = None


def _connect_uri(uri: str) -> sqlite3.Connection:
    conn = sqlite3.connect(uri, uri=True)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def get_connection() -> sqlite3.Connection:
    global _keep_alive_conn
    if DB_PATH == ":memory:":
        uri = "file:cashboard?mode=memory&cache=shared"
        if _keep_alive_conn is None:
            _keep_alive_conn = _connect_uri(uri)
        return _connect_uri(uri)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        conn.executescript(schema_sql)

        seed_sql = SEED_PATH.read_text(encoding="utf-8")
        conn.executescript(seed_sql)

        conn.commit()

        _run_migrations(conn)
    finally:
        conn.close()


def _run_migrations(conn: sqlite3.Connection) -> None:
    """Apply pending migrations based on schema_version."""
    current = conn.execute(
        "SELECT MAX(version) FROM schema_version"
    ).fetchone()[0] or 0

    migrations = {
        2: MIGRATIONS_DIR / "002_charged_month.sql",
    }

    for version in sorted(migrations):
        if current < version:
            sql = migrations[version].read_text(encoding="utf-8")
            conn.executescript(sql)
            conn.execute(
                "INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
                (version,),
            )
            conn.commit()
            print(f"Applied migration {version}: {migrations[version].name}")


def get_db():
    """FastAPI dependency that yields a DB connection."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def get_schema_version() -> int:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT MAX(version) FROM schema_version"
        ).fetchone()
        return row[0] if row[0] is not None else 0
    finally:
        conn.close()


def set_schema_version(version: int) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
            (version,),
        )
        conn.commit()
    finally:
        conn.close()
