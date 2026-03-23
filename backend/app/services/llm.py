"""LLM integration service for FinAlly chat assistant."""

import json
import logging
import os

from litellm import completion
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class TradeAction(BaseModel):
    ticker: str
    side: str  # "buy" or "sell"
    quantity: float


class WatchlistChange(BaseModel):
    ticker: str
    action: str  # "add" or "remove"


class LLMResponse(BaseModel):
    message: str
    trades: list[TradeAction] = []
    watchlist_changes: list[WatchlistChange] = []


SYSTEM_PROMPT = """You are FinAlly, an AI trading assistant for a simulated portfolio.
You help users analyze their portfolio, suggest trades, and execute them.
Always respond with valid JSON matching the required schema.
Be concise, data-driven, and focused on the user's portfolio performance.
You can execute trades and manage the watchlist on behalf of the user.

You MUST respond with a JSON object containing these fields:
- "message": (required) Your conversational response to the user
- "trades": (optional) Array of trades to execute, each with "ticker", "side" ("buy"/"sell"), "quantity"
- "watchlist_changes": (optional) Array of watchlist changes, each with "ticker", "action" ("add"/"remove")

Example response:
{"message": "I'll buy 10 shares of AAPL for you.", "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 10}], "watchlist_changes": []}"""


def build_system_message(portfolio: dict) -> str:
    """Build the system prompt with current portfolio context."""
    context_parts = [SYSTEM_PROMPT, "\n\n--- CURRENT PORTFOLIO STATE ---"]

    cash = portfolio.get("cash_balance", 0)
    total_value = portfolio.get("total_value", cash)
    context_parts.append(f"Cash Balance: ${cash:,.2f}")
    context_parts.append(f"Total Portfolio Value: ${total_value:,.2f}")

    positions = portfolio.get("positions", [])
    if positions:
        context_parts.append("\nPositions:")
        for pos in positions:
            ticker = pos.get("ticker", "???")
            qty = pos.get("quantity", 0)
            avg_cost = pos.get("avg_cost", 0)
            current_price = pos.get("current_price", avg_cost)
            unrealized_pnl = pos.get("unrealized_pnl", 0)
            context_parts.append(
                f"  {ticker}: {qty} shares @ avg ${avg_cost:.2f}, "
                f"current ${current_price:.2f}, P&L ${unrealized_pnl:+,.2f}"
            )
    else:
        context_parts.append("\nNo open positions.")

    watchlist = portfolio.get("watchlist", [])
    if watchlist:
        context_parts.append("\nWatchlist:")
        for item in watchlist:
            ticker = item.get("ticker", "???")
            price = item.get("price")
            if price is not None:
                context_parts.append(f"  {ticker}: ${price:.2f}")
            else:
                context_parts.append(f"  {ticker}: price unavailable")

    return "\n".join(context_parts)


def get_mock_response(user_message: str) -> LLMResponse:
    """Return a deterministic mock response for testing."""
    lower = user_message.lower()

    if "sell" in lower:
        return LLMResponse(
            message="I've sold 5 shares of AAPL for you as requested.",
            trades=[TradeAction(ticker="AAPL", side="sell", quantity=5)],
            watchlist_changes=[],
        )

    if "add" in lower and "watchlist" in lower:
        return LLMResponse(
            message="I've added PYPL to your watchlist.",
            trades=[],
            watchlist_changes=[WatchlistChange(ticker="PYPL", action="add")],
        )

    # Default: buy action for E2E test coverage
    return LLMResponse(
        message="I've analyzed your portfolio. Your current holdings look balanced. "
        "I'll buy 5 shares of AAPL for you as a demonstration.",
        trades=[TradeAction(ticker="AAPL", side="buy", quantity=5)],
        watchlist_changes=[],
    )


def get_llm_response(
    user_message: str, portfolio_context: dict, chat_history: list[dict]
) -> LLMResponse:
    """Get a response from the LLM, or mock if LLM_MOCK=true."""
    if os.getenv("LLM_MOCK", "").lower() == "true":
        return get_mock_response(user_message)

    messages = [{"role": "system", "content": build_system_message(portfolio_context)}]
    messages.extend(chat_history)
    messages.append({"role": "user", "content": user_message})

    try:
        response = completion(
            model="openrouter/openai/gpt-oss-120b",
            messages=messages,
            response_format={"type": "json_object"},
            extra_headers={
                "X-Title": "FinAlly",
                "HTTP-Referer": "https://finally.app",
            },
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )

        content = response.choices[0].message.content
        data = json.loads(content)
        return LLMResponse(**data)

    except json.JSONDecodeError as e:
        logger.error("Failed to parse LLM response as JSON: %s", e)
        return LLMResponse(
            message="I'm sorry, I had trouble processing that request. Please try again.",
        )
    except Exception as e:
        logger.error("LLM call failed: %s", e)
        return LLMResponse(
            message="I'm sorry, I encountered an error. Please try again.",
        )
