"""Main FastAPI application entry point for FinAlly."""

import asyncio
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Load .env from project root (two levels up from backend/app/)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from app.database import db_conn, init_db
from app.market.cache import PriceCache
from app.market.factory import create_market_data_source
from app.market.stream import router as stream_router
from app.routes.chat import router as chat_router
from app.routes.health import router as health_router
from app.routes.portfolio import router as portfolio_router
from app.routes.watchlist import router as watchlist_router

# Global price cache shared across the app
price_cache = PriceCache()
market_data_source = None
snapshot_task = None


async def _snapshot_loop():
    """Record portfolio snapshots every 5 seconds."""
    while True:
        await asyncio.sleep(5)
        try:
            with db_conn() as conn:
                profile = conn.execute(
                    "SELECT cash_balance FROM users_profile WHERE id = ?", ("default",)
                ).fetchone()
                cash = profile["cash_balance"] if profile else 10000.0

                positions = conn.execute(
                    "SELECT ticker, quantity, avg_cost FROM positions WHERE user_id = ?",
                    ("default",),
                ).fetchall()

                total_value = cash
                for pos in positions:
                    price_data = price_cache.get(pos["ticker"])
                    price = price_data.price if price_data else pos["avg_cost"]
                    total_value += pos["quantity"] * price

                conn.execute(
                    "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) "
                    "VALUES (?, ?, ?, ?)",
                    (
                        str(uuid.uuid4()),
                        "default",
                        total_value,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
        except Exception:
            pass  # Don't crash the snapshot loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    global market_data_source, snapshot_task

    # Initialize database
    init_db()

    # Start market data source
    market_data_source = create_market_data_source(price_cache)
    await market_data_source.start()

    # Start snapshot background task
    snapshot_task = asyncio.create_task(_snapshot_loop())

    yield

    # Cleanup
    if snapshot_task:
        snapshot_task.cancel()
    if market_data_source:
        await market_data_source.stop()


app = FastAPI(title="FinAlly API", lifespan=lifespan)

# API routes
app.include_router(health_router)
app.include_router(stream_router)
app.include_router(watchlist_router)
app.include_router(portfolio_router)
app.include_router(chat_router)

# Serve static frontend files
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
