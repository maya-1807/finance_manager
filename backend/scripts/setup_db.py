"""One-time database setup script.

Usage:
    cd backend && python -m scripts.setup_db
"""

import sys
from pathlib import Path

# Ensure backend/ is on the import path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DB_PATH
from db.database import init_db, get_schema_version


def main() -> None:
    print(f"Initializing database at: {DB_PATH}")
    init_db()
    version = get_schema_version()
    print(f"Database ready — schema version {version}")


if __name__ == "__main__":
    main()
