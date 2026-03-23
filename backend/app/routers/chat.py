"""Chat API routes — LLM integration with auto-execution of trades and watchlist changes."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.database import get_connection
from app.market.cache import PriceCache
from app.services.llm import LLMResponse, get_llm_response

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

_price_cache: PriceCache | None = None

USER_ID = "default"


def set_price_cache(cache: PriceCache) -> None:
    global _price_cache
    _price_cache = cache


def get_price_cache() -> PriceCache:
    if _price_cache is None:
        raise RuntimeError("Price cache not initialized")
    return _price_cache


# --- Request / Response models ---


class ChatRequest(BaseModel):
    message: str


class ActionResult(BaseModel):
    type: str  # "trade" or "watchlist"
    ticker: str
    side: str | None = None
    quantity: float | None = None
    price: float | None = None
    success: bool
    error: str | None = None


class ChatMessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: str


class ChatHistoryResponse(BaseModel):
    messages: list[ChatMessageOut]


class ChatResponse(BaseModel):
    message: str
    actions: list[ActionResult]


# --- Helpers ---


def _build_portfolio_context(cache: PriceCache) -> dict:
    """Build the portfolio context dict for the LLM system prompt."""
    with get_connection() as conn:
        user = conn.execute(
            "SELECT cash_balance FROM users_profile WHERE id = ?", (USER_ID,)
        ).fetchone()
        cash = user["cash_balance"] if user else 10000.0

        pos_rows = conn.execute(
            "SELECT ticker, quantity, avg_cost FROM positions WHERE user_id = ?",
            (USER_ID,),
        ).fetchall()

        wl_rows = conn.execute(
            "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY added_at ASC",
            (USER_ID,),
        ).fetchall()

    positions = []
    total_position_value = 0.0
    for row in pos_rows:
        ticker = row["ticker"]
        qty = row["quantity"]
        avg_cost = row["avg_cost"]
        current_price = cache.get_price(ticker)
        if current_price is not None:
            unrealized_pnl = round((current_price - avg_cost) * qty, 2)
            total_position_value += current_price * qty
        else:
            current_price = avg_cost
            unrealized_pnl = 0.0
            total_position_value += avg_cost * qty

        positions.append({
            "ticker": ticker,
            "quantity": qty,
            "avg_cost": avg_cost,
            "current_price": current_price,
            "unrealized_pnl": unrealized_pnl,
        })

    watchlist = []
    for row in wl_rows:
        ticker = row["ticker"]
        price = cache.get_price(ticker)
        watchlist.append({"ticker": ticker, "price": price})

    return {
        "cash_balance": cash,
        "total_value": round(cash + total_position_value, 2),
        "positions": positions,
        "watchlist": watchlist,
    }


def _load_chat_history(limit: int = 20) -> list[dict]:
    """Load the last N chat messages for the LLM context."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT role, content FROM chat_messages WHERE user_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (USER_ID, limit),
        ).fetchall()

    # Reverse to chronological order
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def _save_chat_message(role: str, content: str) -> str:
    """Save a chat message and return its id."""
    msg_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO chat_messages (id, user_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (msg_id, USER_ID, role, content, now),
        )
        conn.commit()
    return msg_id


def _execute_trade(ticker: str, side: str, quantity: float, cache: PriceCache) -> ActionResult:
    """Execute a single trade, returning the result."""
    ticker = ticker.upper()
    price = cache.get_price(ticker)

    if price is None:
        return ActionResult(
            type="trade", ticker=ticker, side=side, quantity=quantity,
            price=None, success=False, error=f"No price available for {ticker}",
        )

    now = datetime.now(timezone.utc).isoformat()
    cost = round(quantity * price, 2)

    try:
        with get_connection() as conn:
            user = conn.execute(
                "SELECT cash_balance FROM users_profile WHERE id = ?", (USER_ID,)
            ).fetchone()
            cash = user["cash_balance"]

            if side == "buy":
                if cash < cost:
                    return ActionResult(
                        type="trade", ticker=ticker, side=side, quantity=quantity,
                        price=price, success=False, error="Insufficient cash",
                    )

                new_cash = round(cash - cost, 2)
                conn.execute(
                    "UPDATE users_profile SET cash_balance = ? WHERE id = ?",
                    (new_cash, USER_ID),
                )

                existing = conn.execute(
                    "SELECT quantity, avg_cost FROM positions WHERE user_id = ? AND ticker = ?",
                    (USER_ID, ticker),
                ).fetchone()

                if existing:
                    old_qty = existing["quantity"]
                    old_avg = existing["avg_cost"]
                    new_qty = old_qty + quantity
                    new_avg = round((old_avg * old_qty + price * quantity) / new_qty, 4)
                    conn.execute(
                        "UPDATE positions SET quantity = ?, avg_cost = ?, updated_at = ? "
                        "WHERE user_id = ? AND ticker = ?",
                        (new_qty, new_avg, now, USER_ID, ticker),
                    )
                else:
                    conn.execute(
                        "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (str(uuid.uuid4()), USER_ID, ticker, quantity, price, now),
                    )

            elif side == "sell":
                existing = conn.execute(
                    "SELECT quantity FROM positions WHERE user_id = ? AND ticker = ?",
                    (USER_ID, ticker),
                ).fetchone()

                if not existing or existing["quantity"] < quantity:
                    return ActionResult(
                        type="trade", ticker=ticker, side=side, quantity=quantity,
                        price=price, success=False, error="Insufficient shares",
                    )

                new_cash = round(cash + cost, 2)
                conn.execute(
                    "UPDATE users_profile SET cash_balance = ? WHERE id = ?",
                    (new_cash, USER_ID),
                )

                remaining = existing["quantity"] - quantity
                if remaining <= 0:
                    conn.execute(
                        "DELETE FROM positions WHERE user_id = ? AND ticker = ?",
                        (USER_ID, ticker),
                    )
                else:
                    conn.execute(
                        "UPDATE positions SET quantity = ?, updated_at = ? "
                        "WHERE user_id = ? AND ticker = ?",
                        (remaining, now, USER_ID, ticker),
                    )
            else:
                return ActionResult(
                    type="trade", ticker=ticker, side=side, quantity=quantity,
                    price=price, success=False, error=f"Invalid side: {side}",
                )

            # Record trade
            conn.execute(
                "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), USER_ID, ticker, side, quantity, price, now),
            )
            conn.commit()

        return ActionResult(
            type="trade", ticker=ticker, side=side, quantity=quantity,
            price=price, success=True,
        )

    except Exception as e:
        logger.error("Trade execution failed: %s", e)
        return ActionResult(
            type="trade", ticker=ticker, side=side, quantity=quantity,
            price=price, success=False, error=str(e),
        )


def _ensure_on_watchlist(ticker: str) -> None:
    """Add ticker to watchlist if not already present."""
    ticker = ticker.upper()
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM watchlist WHERE user_id = ? AND ticker = ?",
            (USER_ID, ticker),
        ).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
                (str(uuid.uuid4()), USER_ID, ticker, now),
            )
            conn.commit()


def _execute_watchlist_change(ticker: str, action: str) -> ActionResult:
    """Execute a watchlist add or remove."""
    ticker = ticker.upper()
    now = datetime.now(timezone.utc).isoformat()

    try:
        with get_connection() as conn:
            if action == "add":
                existing = conn.execute(
                    "SELECT id FROM watchlist WHERE user_id = ? AND ticker = ?",
                    (USER_ID, ticker),
                ).fetchone()
                if existing:
                    return ActionResult(
                        type="watchlist", ticker=ticker, success=True,
                        error=None,
                    )
                conn.execute(
                    "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
                    (str(uuid.uuid4()), USER_ID, ticker, now),
                )
                conn.commit()
                return ActionResult(type="watchlist", ticker=ticker, success=True)

            elif action == "remove":
                existing = conn.execute(
                    "SELECT id FROM watchlist WHERE user_id = ? AND ticker = ?",
                    (USER_ID, ticker),
                ).fetchone()
                if not existing:
                    return ActionResult(
                        type="watchlist", ticker=ticker, success=False,
                        error=f"{ticker} not in watchlist",
                    )
                conn.execute(
                    "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?",
                    (USER_ID, ticker),
                )
                conn.commit()
                return ActionResult(type="watchlist", ticker=ticker, success=True)

            else:
                return ActionResult(
                    type="watchlist", ticker=ticker, success=False,
                    error=f"Invalid action: {action}",
                )

    except Exception as e:
        logger.error("Watchlist change failed: %s", e)
        return ActionResult(
            type="watchlist", ticker=ticker, success=False, error=str(e),
        )


# --- Routes ---


@router.get("/chat/history", response_model=ChatHistoryResponse)
async def get_chat_history() -> ChatHistoryResponse:
    """Load full conversation history for display."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, role, content, created_at FROM chat_messages "
            "WHERE user_id = ? ORDER BY created_at ASC",
            (USER_ID,),
        ).fetchall()

    messages = [
        ChatMessageOut(
            id=r["id"], role=r["role"], content=r["content"], created_at=r["created_at"]
        )
        for r in rows
    ]
    return ChatHistoryResponse(messages=messages)


@router.post("/chat", response_model=ChatResponse)
async def send_chat_message(req: ChatRequest) -> ChatResponse:
    """Process a user chat message through the LLM and auto-execute actions."""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    cache = get_price_cache()

    # 1. Build portfolio context
    portfolio_context = _build_portfolio_context(cache)

    # 2. Load recent chat history for LLM context
    chat_history = _load_chat_history(limit=20)

    # 3. Call LLM
    llm_response: LLMResponse = get_llm_response(
        user_message=req.message,
        portfolio_context=portfolio_context,
        chat_history=chat_history,
    )

    actions: list[ActionResult] = []

    # 4. Auto-execute trades
    for trade in llm_response.trades:
        # Ensure ticker is on watchlist before trading
        _ensure_on_watchlist(trade.ticker)
        result = _execute_trade(trade.ticker, trade.side, trade.quantity, cache)
        actions.append(result)

    # 5. Auto-execute watchlist changes
    for change in llm_response.watchlist_changes:
        result = _execute_watchlist_change(change.ticker, change.action)
        actions.append(result)

    # 6. Save messages to database
    _save_chat_message("user", req.message)
    _save_chat_message("assistant", llm_response.message)

    # 7. Snapshot portfolio after any trades
    if any(a.type == "trade" and a.success for a in actions):
        try:
            from app.routers.portfolio import snapshot_portfolio_now
            snapshot_portfolio_now(cache)
        except Exception as e:
            logger.warning("Failed to snapshot portfolio after chat trade: %s", e)

    return ChatResponse(message=llm_response.message, actions=actions)
