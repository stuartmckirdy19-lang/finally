"""Portfolio API routes — positions, trades, and history."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.db.database import get_connection
from app.market.cache import PriceCache

router = APIRouter(tags=["portfolio"])

# Module-level reference set by main.py at startup
_price_cache: PriceCache | None = None


def set_price_cache(cache: PriceCache) -> None:
    global _price_cache
    _price_cache = cache


def get_price_cache() -> PriceCache:
    if _price_cache is None:
        raise RuntimeError("Price cache not initialized")
    return _price_cache


# --- Request / Response models ---


class TradeRequest(BaseModel):
    ticker: str
    quantity: float = Field(gt=0)
    side: str = Field(pattern=r"^(buy|sell)$")


class TradeResponse(BaseModel):
    success: bool
    ticker: str
    side: str
    quantity: float
    price: float
    cash_balance: float


class PositionOut(BaseModel):
    ticker: str
    quantity: float
    avg_cost: float
    current_price: float | None
    unrealized_pnl: float
    pnl_pct: float


class PortfolioResponse(BaseModel):
    cash_balance: float
    total_value: float
    unrealized_pnl: float
    positions: list[PositionOut]


class HistoryPoint(BaseModel):
    recorded_at: str
    total_value: float


class HistoryResponse(BaseModel):
    history: list[HistoryPoint]


# --- Helpers ---

USER_ID = "default"


def _compute_portfolio_value(cache: PriceCache) -> float:
    """Compute total portfolio value = cash + market value of positions."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT cash_balance FROM users_profile WHERE id = ?", (USER_ID,)
        ).fetchone()
        cash = row["cash_balance"] if row else 10000.0

        positions = conn.execute(
            "SELECT ticker, quantity FROM positions WHERE user_id = ?", (USER_ID,)
        ).fetchall()

    total = cash
    for pos in positions:
        price = cache.get_price(pos["ticker"])
        if price is not None:
            total += pos["quantity"] * price
        else:
            total += pos["quantity"] * 0  # no price available
    return round(total, 2)


def snapshot_portfolio_now(cache: PriceCache) -> None:
    """Insert a portfolio snapshot into the database."""
    total_value = _compute_portfolio_value(cache)
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), USER_ID, total_value, now),
        )
        conn.commit()


# --- Routes ---


@router.get("/portfolio", response_model=PortfolioResponse)
async def get_portfolio() -> PortfolioResponse:
    cache = get_price_cache()

    with get_connection() as conn:
        user = conn.execute(
            "SELECT cash_balance FROM users_profile WHERE id = ?", (USER_ID,)
        ).fetchone()
        cash = user["cash_balance"] if user else 10000.0

        rows = conn.execute(
            "SELECT ticker, quantity, avg_cost FROM positions WHERE user_id = ?",
            (USER_ID,),
        ).fetchall()

    positions: list[PositionOut] = []
    total_position_value = 0.0
    total_cost_basis = 0.0

    for row in rows:
        current_price = cache.get_price(row["ticker"])
        qty = row["quantity"]
        avg = row["avg_cost"]

        if current_price is not None:
            unrealized = round((current_price - avg) * qty, 2)
            pnl_pct = round((current_price - avg) / avg * 100, 2) if avg else 0.0
            total_position_value += current_price * qty
        else:
            unrealized = 0.0
            pnl_pct = 0.0

        total_cost_basis += avg * qty

        positions.append(
            PositionOut(
                ticker=row["ticker"],
                quantity=qty,
                avg_cost=avg,
                current_price=current_price,
                unrealized_pnl=unrealized,
                pnl_pct=pnl_pct,
            )
        )

    total_value = round(cash + total_position_value, 2)
    unrealized_pnl = round(total_position_value - total_cost_basis, 2)

    return PortfolioResponse(
        cash_balance=round(cash, 2),
        total_value=total_value,
        unrealized_pnl=unrealized_pnl,
        positions=positions,
    )


@router.post("/portfolio/trade", response_model=TradeResponse)
async def execute_trade(req: TradeRequest) -> TradeResponse:
    cache = get_price_cache()
    ticker = req.ticker.upper()
    price = cache.get_price(ticker)

    if price is None:
        raise HTTPException(status_code=400, detail=f"No price available for {ticker}")

    now = datetime.now(timezone.utc).isoformat()
    cost = round(req.quantity * price, 2)

    with get_connection() as conn:
        user = conn.execute(
            "SELECT cash_balance FROM users_profile WHERE id = ?", (USER_ID,)
        ).fetchone()
        cash = user["cash_balance"]

        if req.side == "buy":
            if cash < cost:
                raise HTTPException(status_code=400, detail="Insufficient cash")

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
                new_qty = old_qty + req.quantity
                new_avg = round((old_avg * old_qty + price * req.quantity) / new_qty, 4)
                conn.execute(
                    "UPDATE positions SET quantity = ?, avg_cost = ?, updated_at = ? WHERE user_id = ? AND ticker = ?",
                    (new_qty, new_avg, now, USER_ID, ticker),
                )
            else:
                conn.execute(
                    "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), USER_ID, ticker, req.quantity, price, now),
                )

        else:  # sell
            existing = conn.execute(
                "SELECT quantity, avg_cost FROM positions WHERE user_id = ? AND ticker = ?",
                (USER_ID, ticker),
            ).fetchone()

            if not existing or existing["quantity"] < req.quantity:
                raise HTTPException(status_code=400, detail="Insufficient shares")

            new_cash = round(cash + cost, 2)
            conn.execute(
                "UPDATE users_profile SET cash_balance = ? WHERE id = ?",
                (new_cash, USER_ID),
            )

            remaining = existing["quantity"] - req.quantity
            if remaining <= 0:
                conn.execute(
                    "DELETE FROM positions WHERE user_id = ? AND ticker = ?",
                    (USER_ID, ticker),
                )
            else:
                conn.execute(
                    "UPDATE positions SET quantity = ?, updated_at = ? WHERE user_id = ? AND ticker = ?",
                    (remaining, now, USER_ID, ticker),
                )

        # Record trade
        conn.execute(
            "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), USER_ID, ticker, req.side, req.quantity, price, now),
        )
        conn.commit()

        final_cash = conn.execute(
            "SELECT cash_balance FROM users_profile WHERE id = ?", (USER_ID,)
        ).fetchone()["cash_balance"]

    # Snapshot immediately after trade
    snapshot_portfolio_now(cache)

    return TradeResponse(
        success=True,
        ticker=ticker,
        side=req.side,
        quantity=req.quantity,
        price=price,
        cash_balance=round(final_cash, 2),
    )


@router.get("/portfolio/history", response_model=HistoryResponse)
async def get_portfolio_history() -> HistoryResponse:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT recorded_at, total_value FROM portfolio_snapshots WHERE user_id = ? ORDER BY recorded_at ASC",
            (USER_ID,),
        ).fetchall()

    history = [HistoryPoint(recorded_at=r["recorded_at"], total_value=r["total_value"]) for r in rows]
    return HistoryResponse(history=history)
