"""Health check endpoint."""

import os

from fastapi import APIRouter

router = APIRouter(tags=["system"])


@router.get("/health")
async def health_check() -> dict:
    """Return service health status and market data source type."""
    api_key = os.environ.get("MASSIVE_API_KEY", "").strip()
    market_data = "massive" if api_key else "simulator"
    return {"status": "ok", "market_data": market_data}
