"""Watchlist CRUD endpoints."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import db_conn
from app.market.cache import PriceCache

router = APIRouter()


class AddTickerRequest(BaseModel):
    ticker: str


def get_price_cache() -> PriceCache:
    from app.main import price_cache
    return price_cache


@router.get("/api/watchlist")
def get_watchlist():
    cache = get_price_cache()
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT ticker, added_at FROM watchlist WHERE user_id = ? ORDER BY added_at",
            ("default",),
        ).fetchall()

    result = []
    for row in rows:
        ticker = row["ticker"]
        price_data = cache.get(ticker)
        result.append({
            "ticker": ticker,
            "added_at": row["added_at"],
            "price": price_data.price if price_data else None,
            "prev_price": price_data.previous_price if price_data else None,
            "change_pct": price_data.change_percent if price_data else None,
        })
    return result


@router.post("/api/watchlist", status_code=201)
def add_ticker(req: AddTickerRequest):
    ticker = req.ticker.upper().strip()
    if not ticker:
        raise HTTPException(400, "Ticker cannot be empty")
    now = datetime.now(timezone.utc).isoformat()
    try:
        with db_conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
                (str(uuid.uuid4()), "default", ticker, now),
            )
    except Exception as e:
        raise HTTPException(500, str(e))
    return {"ticker": ticker, "added_at": now}


@router.delete("/api/watchlist/{ticker}", status_code=204)
def remove_ticker(ticker: str):
    ticker = ticker.upper().strip()
    with db_conn() as conn:
        conn.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?",
            ("default", ticker),
        )
    return None
