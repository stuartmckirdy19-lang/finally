"""SQLite database module for FinAlly."""

import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = os.environ.get("DB_PATH", "/app/db/finally.db")

_SCHEMA_FILE = Path(__file__).parent / "schema.sql"

_DEFAULT_TICKERS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"]


@contextmanager
def get_connection(db_path: str | None = None):
    """Context manager returning a sqlite3.Connection with WAL mode and Row factory."""
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path: str | None = None) -> None:
    """Create all tables from schema.sql and seed default data.

    Safe to call multiple times -- uses CREATE IF NOT EXISTS and INSERT OR IGNORE.
    """
    with get_connection(db_path) as conn:
        schema_sql = _SCHEMA_FILE.read_text()
        conn.executescript(schema_sql)

        now = datetime.now(timezone.utc).isoformat()

        # Seed default user
        conn.execute(
            "INSERT OR IGNORE INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
            ("default", 10000.0, now),
        )

        # Seed default watchlist
        for ticker in _DEFAULT_TICKERS:
            conn.execute(
                "INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
                (str(uuid.uuid4()), "default", ticker, now),
            )

        conn.commit()
