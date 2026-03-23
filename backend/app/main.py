"""FinAlly — FastAPI application entry point."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.background import start_snapshot_task
from app.db.database import get_connection, init_db
from app.market.cache import PriceCache
from app.market.factory import create_market_data_source
from app.market.stream import create_stream_router
from app.routers import chat, health, portfolio, watchlist

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Global singletons
price_cache = PriceCache()
market_source = create_market_data_source(price_cache)

USER_ID = "default"


def _get_active_tickers() -> list[str]:
    """Return the union of watchlist tickers and tickers with open positions."""
    with get_connection() as conn:
        wl_rows = conn.execute(
            "SELECT ticker FROM watchlist WHERE user_id = ?", (USER_ID,)
        ).fetchall()
        pos_rows = conn.execute(
            "SELECT ticker FROM positions WHERE user_id = ?", (USER_ID,)
        ).fetchall()

    tickers = {r["ticker"] for r in wl_rows} | {r["ticker"] for r in pos_rows}
    return sorted(tickers)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    logger.info("Database initialized")

    tickers = _get_active_tickers()
    await market_source.start(tickers)
    logger.info("Market data source started with tickers: %s", tickers)

    # Wire price cache into routers
    portfolio.set_price_cache(price_cache)
    watchlist.set_price_cache(price_cache)
    chat.set_price_cache(price_cache)

    start_snapshot_task(app, price_cache)

    yield

    # Shutdown
    await market_source.stop()
    logger.info("Market data source stopped")


app = FastAPI(title="FinAlly API", lifespan=lifespan)

# API routers
app.include_router(health.router, prefix="/api")
app.include_router(portfolio.router, prefix="/api")
app.include_router(watchlist.router, prefix="/api")
app.include_router(chat.router, prefix="/api")

# SSE streaming router — already has /api/stream prefix from stream.py
stream_router = create_stream_router(price_cache)
app.include_router(stream_router)

# Static file serving (Next.js export) — must be last (catch-all mount)
static_dir = os.environ.get("STATIC_DIR", "/app/static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
