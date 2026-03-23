"""Background tasks — portfolio snapshots."""

from __future__ import annotations

import asyncio
import logging

from fastapi import FastAPI

from app.market.cache import PriceCache
from app.routers.portfolio import snapshot_portfolio_now

logger = logging.getLogger(__name__)


async def _snapshot_loop(cache: PriceCache, interval: float = 5.0) -> None:
    """Periodically snapshot portfolio value."""
    while True:
        await asyncio.sleep(interval)
        try:
            snapshot_portfolio_now(cache)
        except Exception:
            logger.exception("Error taking portfolio snapshot")


def start_snapshot_task(app: FastAPI, cache: PriceCache) -> None:
    """Start the periodic portfolio snapshot background task."""
    task = asyncio.create_task(_snapshot_loop(cache))
    # Store reference on app to prevent garbage collection
    if not hasattr(app, "_background_tasks"):
        app._background_tasks = []
    app._background_tasks.append(task)
    logger.info("Portfolio snapshot task started (every 5s)")
