"""Watchlist API routes."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.database import get_connection
from app.market.cache import PriceCache

router = APIRouter(tags=["watchlist"])

_price_cache: PriceCache | None = None


def set_price_cache(cache: PriceCache) -> None:
    global _price_cache
    _price_cache = cache


def get_price_cache() -> PriceCache:
    if _price_cache is None:
        raise RuntimeError("Price cache not initialized")
    return _price_cache


USER_ID = "default"


class AddTickerRequest(BaseModel):
    ticker: str


class TickerPrice(BaseModel):
    ticker: str
    price: float | None
    prev_price: float | None
    change_pct: float | None


class WatchlistResponse(BaseModel):
    tickers: list[TickerPrice]


class WatchlistActionResponse(BaseModel):
    success: bool
    ticker: str


@router.get("/watchlist", response_model=WatchlistResponse)
async def get_watchlist() -> WatchlistResponse:
    cache = get_price_cache()

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY added_at ASC",
            (USER_ID,),
        ).fetchall()

    tickers: list[TickerPrice] = []
    for row in rows:
        t = row["ticker"]
        update = cache.get(t)
        if update:
            tickers.append(
                TickerPrice(
                    ticker=t,
                    price=update.price,
                    prev_price=update.previous_price,
                    change_pct=update.change_percent,
                )
            )
        else:
            tickers.append(TickerPrice(ticker=t, price=None, prev_price=None, change_pct=None))

    return WatchlistResponse(tickers=tickers)


@router.post("/watchlist", response_model=WatchlistActionResponse)
async def add_to_watchlist(req: AddTickerRequest) -> WatchlistActionResponse:
    ticker = req.ticker.upper()
    now = datetime.now(timezone.utc).isoformat()

    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM watchlist WHERE user_id = ? AND ticker = ?",
            (USER_ID, ticker),
        ).fetchone()

        if existing:
            raise HTTPException(status_code=409, detail=f"{ticker} already in watchlist")

        conn.execute(
            "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), USER_ID, ticker, now),
        )
        conn.commit()

    return WatchlistActionResponse(success=True, ticker=ticker)


@router.delete("/watchlist/{ticker}", response_model=WatchlistActionResponse)
async def remove_from_watchlist(ticker: str) -> WatchlistActionResponse:
    ticker = ticker.upper()

    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM watchlist WHERE user_id = ? AND ticker = ?",
            (USER_ID, ticker),
        ).fetchone()

        if not existing:
            raise HTTPException(status_code=404, detail=f"{ticker} not in watchlist")

        conn.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?",
            (USER_ID, ticker),
        )
        conn.commit()

    return WatchlistActionResponse(success=True, ticker=ticker)
