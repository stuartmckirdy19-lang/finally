"""Tests for the health endpoint."""

import os

import pytest


@pytest.mark.asyncio
async def test_health_returns_ok(client):
    os.environ.pop("MASSIVE_API_KEY", None)
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["market_data"] == "simulator"


@pytest.mark.asyncio
async def test_health_shows_massive_when_key_set(client):
    os.environ["MASSIVE_API_KEY"] = "test-key"
    try:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["market_data"] == "massive"
    finally:
        os.environ.pop("MASSIVE_API_KEY", None)
