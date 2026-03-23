"""Shared fixtures for router tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

import app.db.database as db_module
from app.db.database import init_db
from app.market.cache import PriceCache
from app.routers import portfolio, watchlist


@pytest.fixture()
def tmp_db(tmp_path):
    """Create a temporary SQLite database and patch the module-level DB_PATH."""
    db_path = str(tmp_path / "test.db")
    original = db_module.DB_PATH
    db_module.DB_PATH = db_path
    init_db(db_path)
    yield db_path
    db_module.DB_PATH = original


@pytest.fixture()
def price_cache():
    """Create a PriceCache pre-loaded with test prices."""
    cache = PriceCache()
    cache.update("AAPL", 190.0)
    cache.update("GOOGL", 175.0)
    cache.update("MSFT", 420.0)
    cache.update("TSLA", 250.0)
    return cache


@pytest.fixture()
def setup_routers(tmp_db, price_cache):
    """Wire the price cache into routers and yield the cache."""
    portfolio.set_price_cache(price_cache)
    watchlist.set_price_cache(price_cache)
    yield price_cache


@pytest.fixture()
async def client(setup_routers):
    """Async HTTP client for testing routes without lifespan."""
    from fastapi import FastAPI
    from app.routers import health, portfolio as portfolio_mod, watchlist as watchlist_mod, chat

    app = FastAPI()
    app.include_router(health.router, prefix="/api")
    app.include_router(portfolio_mod.router, prefix="/api")
    app.include_router(watchlist_mod.router, prefix="/api")
    app.include_router(chat.router, prefix="/api")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
