"""Tests for the LLM service module."""

import json

import pytest

from app.services.llm import (
    LLMResponse,
    TradeAction,
    WatchlistChange,
    build_system_message,
    get_llm_response,
    get_mock_response,
)


class TestMockResponse:
    """Test mock mode returns valid LLMResponse objects."""

    def test_mock_response_structure(self):
        resp = get_mock_response("hello")
        assert isinstance(resp, LLMResponse)
        assert isinstance(resp.message, str)
        assert len(resp.message) > 0
        assert isinstance(resp.trades, list)
        assert isinstance(resp.watchlist_changes, list)

    def test_mock_response_default_has_trade(self):
        resp = get_mock_response("analyze my portfolio")
        assert len(resp.trades) == 1
        trade = resp.trades[0]
        assert trade.ticker == "AAPL"
        assert trade.side == "buy"
        assert trade.quantity == 5

    def test_mock_response_sell(self):
        resp = get_mock_response("sell some stock")
        assert len(resp.trades) == 1
        assert resp.trades[0].side == "sell"

    def test_mock_response_watchlist(self):
        resp = get_mock_response("add PYPL to my watchlist")
        assert len(resp.watchlist_changes) == 1
        assert resp.watchlist_changes[0].ticker == "PYPL"
        assert resp.watchlist_changes[0].action == "add"

    def test_get_llm_response_mock_mode(self, monkeypatch):
        monkeypatch.setenv("LLM_MOCK", "true")
        resp = get_llm_response("hello", {}, [])
        assert isinstance(resp, LLMResponse)
        assert len(resp.message) > 0


class TestSystemPrompt:
    """Test that portfolio context is included in the system prompt."""

    def test_system_prompt_includes_cash(self):
        context = {"cash_balance": 5000.0, "total_value": 7500.0, "positions": [], "watchlist": []}
        prompt = build_system_message(context)
        assert "$5,000.00" in prompt
        assert "$7,500.00" in prompt

    def test_system_prompt_includes_positions(self):
        context = {
            "cash_balance": 5000.0,
            "total_value": 7500.0,
            "positions": [
                {
                    "ticker": "AAPL",
                    "quantity": 10,
                    "avg_cost": 150.0,
                    "current_price": 175.0,
                    "unrealized_pnl": 250.0,
                }
            ],
            "watchlist": [],
        }
        prompt = build_system_message(context)
        assert "AAPL" in prompt
        assert "10 shares" in prompt
        assert "$150.00" in prompt

    def test_system_prompt_includes_watchlist(self):
        context = {
            "cash_balance": 10000.0,
            "total_value": 10000.0,
            "positions": [],
            "watchlist": [{"ticker": "GOOGL", "price": 175.50}],
        }
        prompt = build_system_message(context)
        assert "GOOGL" in prompt
        assert "$175.50" in prompt

    def test_system_prompt_no_positions(self):
        context = {"cash_balance": 10000.0, "total_value": 10000.0, "positions": [], "watchlist": []}
        prompt = build_system_message(context)
        assert "No open positions" in prompt


class TestStructuredOutputParsing:
    """Test parsing various valid JSON responses into LLMResponse."""

    def test_message_only(self):
        data = {"message": "Your portfolio looks great!"}
        resp = LLMResponse(**data)
        assert resp.message == "Your portfolio looks great!"
        assert resp.trades == []
        assert resp.watchlist_changes == []

    def test_message_with_trades(self):
        data = {
            "message": "Buying AAPL",
            "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 10}],
        }
        resp = LLMResponse(**data)
        assert len(resp.trades) == 1
        assert resp.trades[0].ticker == "AAPL"
        assert resp.trades[0].side == "buy"
        assert resp.trades[0].quantity == 10

    def test_message_with_multiple_trades(self):
        data = {
            "message": "Rebalancing",
            "trades": [
                {"ticker": "AAPL", "side": "sell", "quantity": 5},
                {"ticker": "GOOGL", "side": "buy", "quantity": 3},
            ],
        }
        resp = LLMResponse(**data)
        assert len(resp.trades) == 2

    def test_message_with_watchlist_changes(self):
        data = {
            "message": "Adding to watchlist",
            "watchlist_changes": [{"ticker": "PYPL", "action": "add"}],
        }
        resp = LLMResponse(**data)
        assert len(resp.watchlist_changes) == 1
        assert resp.watchlist_changes[0].ticker == "PYPL"

    def test_full_response(self):
        data = {
            "message": "Done!",
            "trades": [{"ticker": "TSLA", "side": "buy", "quantity": 2}],
            "watchlist_changes": [{"ticker": "TSLA", "action": "add"}],
        }
        resp = LLMResponse(**data)
        assert resp.message == "Done!"
        assert len(resp.trades) == 1
        assert len(resp.watchlist_changes) == 1

    def test_fractional_quantity(self):
        data = {
            "message": "Buying fractional shares",
            "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 0.5}],
        }
        resp = LLMResponse(**data)
        assert resp.trades[0].quantity == 0.5


class TestMalformedResponse:
    """Test graceful handling of malformed responses."""

    def test_missing_message_field(self):
        data = {"trades": []}
        with pytest.raises(Exception):
            LLMResponse(**data)

    def test_invalid_trade_missing_ticker(self):
        data = {
            "message": "test",
            "trades": [{"side": "buy", "quantity": 10}],
        }
        with pytest.raises(Exception):
            LLMResponse(**data)

    def test_invalid_trade_missing_side(self):
        data = {
            "message": "test",
            "trades": [{"ticker": "AAPL", "quantity": 10}],
        }
        with pytest.raises(Exception):
            LLMResponse(**data)

    def test_extra_fields_ignored(self):
        data = {
            "message": "test",
            "trades": [],
            "watchlist_changes": [],
            "extra_field": "ignored",
        }
        # Pydantic v2 ignores extra fields by default
        resp = LLMResponse(**data)
        assert resp.message == "test"
