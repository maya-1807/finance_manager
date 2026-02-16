import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = os.environ.get("CASHBOARD_DB_PATH", str(BASE_DIR / "cashboard.db"))
