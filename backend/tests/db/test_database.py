"""Tests for the SQLite database layer."""

import sqlite3

import pytest

from app.db.database import get_connection, init_db


@pytest.fixture()
def db_path(tmp_path):
    """Return a temporary database file path."""
    return str(tmp_path / "test.db")


class TestSchemaCreation:
    def test_schema_creates_all_tables(self, db_path):
        init_db(db_path)
        with get_connection(db_path) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            table_names = sorted(r["name"] for r in rows)
            expected = sorted([
                "users_profile",
                "watchlist",
                "positions",
                "trades",
                "portfolio_snapshots",
                "chat_messages",
            ])
            assert table_names == expected

    def test_portfolio_snapshots_index_exists(self, db_path):
        init_db(db_path)
        with get_connection(db_path) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='portfolio_snapshots'"
            ).fetchall()
            index_names = [r["name"] for r in rows]
            assert "idx_portfolio_snapshots_user_recorded" in index_names


class TestSeedData:
    def test_seed_data_idempotent(self, db_path):
        init_db(db_path)
        init_db(db_path)
        with get_connection(db_path) as conn:
            user_count = conn.execute("SELECT COUNT(*) FROM users_profile").fetchone()[0]
            assert user_count == 1
            watchlist_count = conn.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0]
            assert watchlist_count == 10

    def test_default_user_exists(self, db_path):
        init_db(db_path)
        with get_connection(db_path) as conn:
            user = conn.execute(
                "SELECT * FROM users_profile WHERE id = ?", ("default",)
            ).fetchone()
            assert user is not None
            assert user["cash_balance"] == 10000.0

    def test_default_watchlist(self, db_path):
        init_db(db_path)
        with get_connection(db_path) as conn:
            rows = conn.execute(
                "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY ticker", ("default",)
            ).fetchall()
            tickers = [r["ticker"] for r in rows]
            expected = sorted(["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"])
            assert sorted(tickers) == expected


class TestConnection:
    def test_wal_mode(self, db_path):
        init_db(db_path)
        with get_connection(db_path) as conn:
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            assert mode == "wal"

    def test_row_factory(self, db_path):
        init_db(db_path)
        with get_connection(db_path) as conn:
            row = conn.execute("SELECT * FROM users_profile LIMIT 1").fetchone()
            assert isinstance(row, sqlite3.Row)
            assert row["id"] == "default"

    def test_connection_closes(self, db_path):
        init_db(db_path)
        with get_connection(db_path) as conn:
            conn.execute("SELECT 1")
        # After context manager exits, connection should be closed
        with pytest.raises(Exception):
            conn.execute("SELECT 1")
