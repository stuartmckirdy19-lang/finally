"""Tests for portfolio endpoints."""

import pytest


@pytest.mark.asyncio
async def test_get_portfolio_initial(client):
    """Fresh portfolio should have $10k cash and no positions."""
    resp = await client.get("/api/portfolio")
    assert resp.status_code == 200
    data = resp.json()
    assert data["cash_balance"] == 10000.0
    assert data["total_value"] == 10000.0
    assert data["positions"] == []


@pytest.mark.asyncio
async def test_buy_trade(client):
    """Buying shares should deduct cash and create a position."""
    resp = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "buy"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["ticker"] == "AAPL"
    assert data["side"] == "buy"
    assert data["quantity"] == 10
    assert data["price"] == 190.0
    assert data["cash_balance"] == 8100.0

    # Verify portfolio
    resp = await client.get("/api/portfolio")
    data = resp.json()
    assert data["cash_balance"] == 8100.0
    assert len(data["positions"]) == 1
    assert data["positions"][0]["ticker"] == "AAPL"
    assert data["positions"][0]["quantity"] == 10


@pytest.mark.asyncio
async def test_sell_trade(client):
    """Selling shares should add cash and update position."""
    # First buy
    await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "buy"},
    )
    # Then sell half
    resp = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 5, "side": "sell"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["side"] == "sell"
    assert data["cash_balance"] == 9050.0  # 8100 + 5*190


@pytest.mark.asyncio
async def test_sell_all_removes_position(client):
    """Selling all shares should remove the position row."""
    await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 5, "side": "buy"},
    )
    await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 5, "side": "sell"},
    )
    resp = await client.get("/api/portfolio")
    assert resp.json()["positions"] == []


@pytest.mark.asyncio
async def test_buy_insufficient_cash(client):
    """Cannot buy more than cash allows."""
    resp = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 1000, "side": "buy"},
    )
    assert resp.status_code == 400
    assert "Insufficient cash" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_sell_insufficient_shares(client):
    """Cannot sell shares you don't own."""
    resp = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 1, "side": "sell"},
    )
    assert resp.status_code == 400
    assert "Insufficient shares" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_trade_no_price_available(client):
    """Cannot trade a ticker with no cached price."""
    resp = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "UNKNOWN", "quantity": 1, "side": "buy"},
    )
    assert resp.status_code == 400
    assert "No price available" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_trade_invalid_quantity(client):
    """Quantity must be positive."""
    resp = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": -1, "side": "buy"},
    )
    assert resp.status_code == 422  # Pydantic validation


@pytest.mark.asyncio
async def test_trade_invalid_side(client):
    """Side must be 'buy' or 'sell'."""
    resp = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 1, "side": "hold"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_fractional_shares(client):
    """Should support fractional share quantities."""
    resp = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 0.5, "side": "buy"},
    )
    assert resp.status_code == 200
    assert resp.json()["quantity"] == 0.5


@pytest.mark.asyncio
async def test_buy_adds_to_existing_position(client):
    """Buying more of an existing position should update weighted avg cost."""
    await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "buy"},
    )
    # Price is still 190, so avg_cost stays 190
    await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "buy"},
    )
    resp = await client.get("/api/portfolio")
    pos = resp.json()["positions"][0]
    assert pos["quantity"] == 20
    assert pos["avg_cost"] == 190.0


@pytest.mark.asyncio
async def test_portfolio_history(client):
    """After a trade, there should be at least one snapshot."""
    await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 1, "side": "buy"},
    )
    resp = await client.get("/api/portfolio/history")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["history"]) >= 1
