"""LLM chat integration using Cerebras via OpenRouter."""

import json
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

LLM_MOCK = os.environ.get("LLM_MOCK", "false").lower() == "true"

MOCK_RESPONSE = {
    "message": (
        "I'm FinAlly, your AI trading assistant! I can analyze your portfolio "
        "and execute trades. What would you like to know?"
    ),
    "trades": [],
    "watchlist_changes": [],
}

MODEL = "openrouter/openai/gpt-oss-120b"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}


class ChatRequest(BaseModel):
    message: str


# Pydantic model for structured LLM output
class TradeAction(BaseModel):
    ticker: str
    side: str
    quantity: float


class WatchlistChange(BaseModel):
    ticker: str
    action: str


class LLMResponse(BaseModel):
    message: str
    trades: list[TradeAction] = []
    watchlist_changes: list[WatchlistChange] = []


def get_price_cache():
    from app.main import price_cache
    return price_cache


def _get_portfolio_context(conn) -> dict:
    cache = get_price_cache()
    profile = conn.execute(
        "SELECT cash_balance FROM users_profile WHERE id = ?", ("default",)
    ).fetchone()
    cash = profile["cash_balance"] if profile else 10000.0

    positions_rows = conn.execute(
        "SELECT ticker, quantity, avg_cost FROM positions WHERE user_id = ?", ("default",)
    ).fetchall()

    positions = []
    total_value = cash
    for row in positions_rows:
        price_data = cache.get(row["ticker"])
        current_price = price_data.price if price_data else row["avg_cost"]
        unrealized_pnl = (current_price - row["avg_cost"]) * row["quantity"]
        pnl_pct = (
            ((current_price - row["avg_cost"]) / row["avg_cost"] * 100)
            if row["avg_cost"]
            else 0
        )
        pos_value = current_price * row["quantity"]
        total_value += pos_value
        positions.append({
            "ticker": row["ticker"],
            "quantity": row["quantity"],
            "avg_cost": row["avg_cost"],
            "current_price": current_price,
            "unrealized_pnl": round(unrealized_pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "value": round(pos_value, 2),
        })

    watchlist_rows = conn.execute(
        "SELECT ticker FROM watchlist WHERE user_id = ?", ("default",)
    ).fetchall()
    watchlist = []
    for row in watchlist_rows:
        price_data = cache.get(row["ticker"])
        watchlist.append({
            "ticker": row["ticker"],
            "price": price_data.price if price_data else None,
        })

    return {
        "cash_balance": round(cash, 2),
        "total_value": round(total_value, 2),
        "positions": positions,
        "watchlist": watchlist,
    }


def _call_llm(system_prompt: str, messages: list) -> dict:
    """Call LLM via LiteLLM OpenRouter Cerebras (sync)."""
    from litellm import completion

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return {
            "message": "LLM not configured (missing OPENROUTER_API_KEY)",
            "trades": [],
            "watchlist_changes": [],
        }

    full_messages = [{"role": "system", "content": system_prompt}] + messages

    response = completion(
        model=MODEL,
        messages=full_messages,
        api_key=api_key,
        api_base="https://openrouter.ai/api/v1",
        response_format=LLMResponse,
        reasoning_effort="low",
        extra_body=EXTRA_BODY,
    )

    content = response.choices[0].message.content
    try:
        parsed = LLMResponse.model_validate_json(content)
        return {
            "message": parsed.message,
            "trades": [t.model_dump() for t in parsed.trades],
            "watchlist_changes": [w.model_dump() for w in parsed.watchlist_changes],
        }
    except Exception:
        # Fall back to raw content if parsing fails
        try:
            raw = json.loads(content)
            return {
                "message": raw.get("message", content),
                "trades": raw.get("trades", []),
                "watchlist_changes": raw.get("watchlist_changes", []),
            }
        except Exception:
            return {"message": content, "trades": [], "watchlist_changes": []}


@router.get("/api/chat/history")
def get_chat_history():
    from app.database import db_conn

    with db_conn() as conn:
        rows = conn.execute(
            "SELECT id, role, content, created_at FROM chat_messages "
            "WHERE user_id = ? ORDER BY created_at",
            ("default",),
        ).fetchall()
    return [
        {
            "id": r["id"],
            "role": r["role"],
            "content": r["content"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


@router.post("/api/chat")
def chat(req: ChatRequest):
    from app.database import db_conn
    from app.routes.portfolio import TradeRequest, execute_trade
    from app.routes.watchlist import AddTickerRequest, add_ticker, remove_ticker

    now = datetime.now(timezone.utc).isoformat()

    with db_conn() as conn:
        portfolio_ctx = _get_portfolio_context(conn)
        history_rows = conn.execute(
            "SELECT role, content FROM chat_messages "
            "WHERE user_id = ? ORDER BY created_at DESC LIMIT 20",
            ("default",),
        ).fetchall()

    history = [{"role": r["role"], "content": r["content"]} for r in reversed(history_rows)]
    history.append({"role": "user", "content": req.message})

    system_prompt = f"""You are FinAlly, an AI trading assistant for a simulated trading platform.

Current portfolio context:
{json.dumps(portfolio_ctx, indent=2)}

You can:
- Analyze portfolio composition, risk concentration, and P&L
- Suggest and execute trades
- Manage the watchlist

Always respond with valid JSON matching this exact schema:
{{
  "message": "Your conversational response to the user",
  "trades": [
    {{"ticker": "AAPL", "side": "buy", "quantity": 10}}
  ],
  "watchlist_changes": [
    {{"ticker": "PYPL", "action": "add"}}
  ]
}}

Be concise and data-driven. The trades and watchlist_changes arrays can be empty if no actions are needed."""

    if LLM_MOCK:
        llm_response = MOCK_RESPONSE
    else:
        llm_response = _call_llm(system_prompt, history)

    # Auto-execute trades
    actions = []
    for trade in llm_response.get("trades", []):
        ticker = trade.get("ticker", "").upper()
        side = trade.get("side", "").lower()
        quantity = trade.get("quantity", 0)
        try:
            result = execute_trade(TradeRequest(ticker=ticker, quantity=quantity, side=side))
            actions.append({
                "type": "trade",
                "status": "success",
                "ticker": ticker,
                "side": side,
                "quantity": quantity,
                "price": result["price"],
            })
        except HTTPException as e:
            actions.append({
                "type": "trade",
                "status": "error",
                "ticker": ticker,
                "side": side,
                "quantity": quantity,
                "error": e.detail,
            })

    # Auto-execute watchlist changes
    for change in llm_response.get("watchlist_changes", []):
        ticker = change.get("ticker", "").upper()
        action = change.get("action", "").lower()
        try:
            if action == "add":
                add_ticker(AddTickerRequest(ticker=ticker))
                actions.append({
                    "type": "watchlist",
                    "status": "success",
                    "ticker": ticker,
                    "action": "add",
                })
            elif action == "remove":
                remove_ticker(ticker)
                actions.append({
                    "type": "watchlist",
                    "status": "success",
                    "ticker": ticker,
                    "action": "remove",
                })
        except Exception as e:
            actions.append({
                "type": "watchlist",
                "status": "error",
                "ticker": ticker,
                "action": action,
                "error": str(e),
            })

    # Store messages
    with db_conn() as conn:
        conn.execute(
            "INSERT INTO chat_messages (id, user_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), "default", "user", req.message, now),
        )
        assistant_content = llm_response["message"]
        conn.execute(
            "INSERT INTO chat_messages (id, user_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), "default", "assistant", assistant_content, now),
        )

    return {
        "message": llm_response["message"],
        "actions": actions,
    }
