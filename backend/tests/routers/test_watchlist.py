"""Tests for watchlist endpoints."""

import pytest


@pytest.mark.asyncio
async def test_get_watchlist_defaults(client):
    """Default watchlist should have 10 tickers from seed data."""
    resp = await client.get("/api/watchlist")
    assert resp.status_code == 200
    data = resp.json()
    tickers = [t["ticker"] for t in data["tickers"]]
    assert "AAPL" in tickers
    assert "GOOGL" in tickers
    assert len(tickers) == 10


@pytest.mark.asyncio
async def test_get_watchlist_includes_prices(client):
    """Tickers with cached prices should show price data."""
    resp = await client.get("/api/watchlist")
    data = resp.json()
    aapl = next(t for t in data["tickers"] if t["ticker"] == "AAPL")
    assert aapl["price"] == 190.0


@pytest.mark.asyncio
async def test_add_ticker(client):
    """Adding a new ticker should succeed."""
    resp = await client.post("/api/watchlist", json={"ticker": "PYPL"})
    assert resp.status_code == 200
    assert resp.json() == {"success": True, "ticker": "PYPL"}

    # Verify it appears in the list
    resp = await client.get("/api/watchlist")
    tickers = [t["ticker"] for t in resp.json()["tickers"]]
    assert "PYPL" in tickers


@pytest.mark.asyncio
async def test_add_duplicate_ticker(client):
    """Adding a ticker that already exists should return 409."""
    resp = await client.post("/api/watchlist", json={"ticker": "AAPL"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_remove_ticker(client):
    """Removing a ticker should succeed."""
    resp = await client.delete("/api/watchlist/AAPL")
    assert resp.status_code == 200
    assert resp.json() == {"success": True, "ticker": "AAPL"}

    # Verify it's gone
    resp = await client.get("/api/watchlist")
    tickers = [t["ticker"] for t in resp.json()["tickers"]]
    assert "AAPL" not in tickers


@pytest.mark.asyncio
async def test_remove_nonexistent_ticker(client):
    """Removing a ticker not in the watchlist should return 404."""
    resp = await client.delete("/api/watchlist/ZZZZ")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_add_ticker_normalizes_case(client):
    """Tickers should be uppercased."""
    resp = await client.post("/api/watchlist", json={"ticker": "pypl"})
    assert resp.status_code == 200
    assert resp.json()["ticker"] == "PYPL"
