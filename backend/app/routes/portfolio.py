"""Portfolio and trading endpoints."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import db_conn

router = APIRouter()


class TradeRequest(BaseModel):
    ticker: str
    quantity: float
    side: str  # "buy" or "sell"


def get_price_cache():
    from app.main import price_cache
    return price_cache


def _record_snapshot(conn, user_id: str = "default"):
    """Record a portfolio snapshot. Call within an existing db_conn context."""
    row = conn.execute(
        "SELECT cash_balance FROM users_profile WHERE id = ?", (user_id,)
    ).fetchone()
    cash = row["cash_balance"] if row else 0.0

    cache = get_price_cache()
    positions = conn.execute(
        "SELECT ticker, quantity, avg_cost FROM positions WHERE user_id = ?", (user_id,)
    ).fetchall()

    total_value = cash
    for pos in positions:
        price_data = cache.get(pos["ticker"])
        price = price_data.price if price_data else pos["avg_cost"]
        total_value += pos["quantity"] * price

    conn.execute(
        "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) VALUES (?, ?, ?, ?)",
        (str(uuid.uuid4()), user_id, total_value, datetime.now(timezone.utc).isoformat()),
    )


@router.get("/api/portfolio")
def get_portfolio():
    cache = get_price_cache()
    with db_conn() as conn:
        profile = conn.execute(
            "SELECT cash_balance FROM users_profile WHERE id = ?", ("default",)
        ).fetchone()
        cash = profile["cash_balance"] if profile else 10000.0

        positions_rows = conn.execute(
            "SELECT ticker, quantity, avg_cost FROM positions WHERE user_id = ?", ("default",)
        ).fetchall()

    positions = []
    total_position_value = 0.0
    for row in positions_rows:
        price_data = cache.get(row["ticker"])
        current_price = price_data.price if price_data else row["avg_cost"]
        unrealized_pnl = (current_price - row["avg_cost"]) * row["quantity"]
        pnl_pct = (
            ((current_price - row["avg_cost"]) / row["avg_cost"] * 100)
            if row["avg_cost"] > 0
            else 0.0
        )
        position_value = current_price * row["quantity"]
        total_position_value += position_value
        positions.append({
            "ticker": row["ticker"],
            "quantity": row["quantity"],
            "avg_cost": row["avg_cost"],
            "current_price": current_price,
            "unrealized_pnl": unrealized_pnl,
            "pnl_pct": pnl_pct,
            "value": position_value,
        })

    total_value = cash + total_position_value
    return {
        "cash_balance": cash,
        "total_value": total_value,
        "positions": positions,
    }


@router.post("/api/portfolio/trade")
def execute_trade(req: TradeRequest):
    ticker = req.ticker.upper().strip()
    side = req.side.lower()
    quantity = req.quantity

    if side not in ("buy", "sell"):
        raise HTTPException(400, "Side must be 'buy' or 'sell'")
    if quantity <= 0:
        raise HTTPException(400, "Quantity must be positive")

    cache = get_price_cache()
    price_data = cache.get(ticker)
    if price_data is None:
        raise HTTPException(400, f"No price data for ticker {ticker}")

    price = price_data.price
    now = datetime.now(timezone.utc).isoformat()

    with db_conn() as conn:
        profile = conn.execute(
            "SELECT cash_balance FROM users_profile WHERE id = ?", ("default",)
        ).fetchone()
        cash = profile["cash_balance"] if profile else 10000.0

        if side == "buy":
            cost = price * quantity
            if cost > cash:
                raise HTTPException(
                    400, f"Insufficient cash. Need ${cost:.2f}, have ${cash:.2f}"
                )

            # Update cash
            conn.execute(
                "UPDATE users_profile SET cash_balance = cash_balance - ? WHERE id = ?",
                (cost, "default"),
            )

            # Upsert position
            existing = conn.execute(
                "SELECT quantity, avg_cost FROM positions WHERE user_id = ? AND ticker = ?",
                ("default", ticker),
            ).fetchone()

            if existing:
                new_qty = existing["quantity"] + quantity
                new_avg = (
                    existing["quantity"] * existing["avg_cost"] + quantity * price
                ) / new_qty
                conn.execute(
                    "UPDATE positions SET quantity = ?, avg_cost = ?, updated_at = ? "
                    "WHERE user_id = ? AND ticker = ?",
                    (new_qty, new_avg, now, "default", ticker),
                )
            else:
                conn.execute(
                    "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), "default", ticker, quantity, price, now),
                )

            # Auto-add to watchlist
            conn.execute(
                "INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
                (str(uuid.uuid4()), "default", ticker, now),
            )

        else:  # sell
            existing = conn.execute(
                "SELECT quantity, avg_cost FROM positions WHERE user_id = ? AND ticker = ?",
                ("default", ticker),
            ).fetchone()

            if not existing or existing["quantity"] < quantity:
                owned = existing["quantity"] if existing else 0
                raise HTTPException(
                    400, f"Insufficient shares. Need {quantity}, have {owned}"
                )

            proceeds = price * quantity
            conn.execute(
                "UPDATE users_profile SET cash_balance = cash_balance + ? WHERE id = ?",
                (proceeds, "default"),
            )

            new_qty = existing["quantity"] - quantity
            if new_qty < 1e-9:
                conn.execute(
                    "DELETE FROM positions WHERE user_id = ? AND ticker = ?",
                    ("default", ticker),
                )
            else:
                conn.execute(
                    "UPDATE positions SET quantity = ?, updated_at = ? "
                    "WHERE user_id = ? AND ticker = ?",
                    (new_qty, now, "default", ticker),
                )

        # Record trade
        conn.execute(
            "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), "default", ticker, side, quantity, price, now),
        )

        # Record snapshot
        _record_snapshot(conn)

    return {
        "ticker": ticker,
        "side": side,
        "quantity": quantity,
        "price": price,
        "executed_at": now,
    }


@router.get("/api/portfolio/history")
def get_portfolio_history():
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT total_value, recorded_at FROM portfolio_snapshots "
            "WHERE user_id = ? ORDER BY recorded_at DESC LIMIT 1000",
            ("default",),
        ).fetchall()
    return [
        {"total_value": r["total_value"], "recorded_at": r["recorded_at"]}
        for r in reversed(rows)
    ]
