# Massive API Reference (formerly Polygon.io)

Reference documentation for the Massive (formerly Polygon.io) REST API as used in FinAlly.

## Overview

Polygon.io officially rebranded to **Massive.com** on October 30, 2025. All existing API keys and integrations continue to work without changes.

- **New base URL**: `https://api.massive.com`
- **Legacy URL**: `https://api.polygon.io` (still supported)
- **Python package**: `massive` (formerly `polygon`; install via `pip install -U massive` / `uv add massive`)
- **Min Python version**: 3.9+
- **Auth**: API key passed to `RESTClient(api_key=...)` or via the `APCA_API_KEY_ID` environment variable
- **Auth header**: `Authorization: Bearer <API_KEY>` (the client handles this automatically)

## Pricing Tiers

| Tier | Monthly Cost | Rate Limit | Historical Data |
|------|-------------|------------|-----------------|
| **Free (Stocks Basic)** | $0 | 5 requests/minute | Limited |
| **Starter** | $29 | Unlimited | 5 years (15-min delay) |
| **Developer** | $79 | Unlimited | Up to 10 years |
| **Advanced** | $200 | Unlimited | Full history + market events |

For FinAlly:
- **Free tier**: Poll every 15 seconds (5 req/min ÷ some headroom = safe at 4/min)
- **Paid tiers**: Poll every 2–5 seconds (soft limit: stay under 100 req/s)

## Client Initialization

```python
from massive import RESTClient

# Pass API key explicitly (preferred — reads from env at call site)
client = RESTClient(api_key="your_api_key_here")
```

## Endpoints Used in FinAlly

### 1. Snapshot — All Tickers (Primary Endpoint)

Gets current prices for multiple tickers in a **single API call**. This is the main endpoint used for polling — critical for staying within free-tier rate limits.

**REST**: `GET /v2/snapshot/locale/us/markets/stocks/tickers?tickers=AAPL,GOOGL,MSFT`

**Python client**:
```python
from massive import RESTClient
from massive.rest.models import SnapshotMarketType

client = RESTClient(api_key=api_key)

# Fetch snapshots for all watchlist tickers in one API call
snapshots = client.get_snapshot_all(
    market_type=SnapshotMarketType.STOCKS,
    tickers=["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"],
)

for snap in snapshots:
    print(f"{snap.ticker}: ${snap.last_trade.price}")
    print(f"  Day change: {snap.day.change_percent:.2f}%")
    print(f"  OHLC: O={snap.day.open} H={snap.day.high} L={snap.day.low} C={snap.day.close}")
    print(f"  Volume: {snap.day.volume:,}")
```

**Response structure** (per ticker):
```json
{
  "ticker": "AAPL",
  "day": {
    "open": 129.61,
    "high": 130.15,
    "low": 125.07,
    "close": 125.07,
    "volume": 111237700,
    "volume_weighted_average_price": 127.35,
    "previous_close": 129.61,
    "change": -4.54,
    "change_percent": -3.50
  },
  "last_trade": {
    "price": 125.07,
    "size": 100,
    "exchange": "XNYS",
    "timestamp": 1675190399000
  },
  "last_quote": {
    "bid_price": 125.06,
    "ask_price": 125.08,
    "bid_size": 500,
    "ask_size": 1000,
    "spread": 0.02,
    "timestamp": 1675190399500
  }
}
```

**Fields extracted in FinAlly**:
- `snap.last_trade.price` — current price used for display and trade execution
- `snap.last_trade.timestamp` — Unix milliseconds; divide by 1000 for Unix seconds
- `snap.day.change_percent` — day change percentage for watchlist display

> Note: Up to 250 tickers can be requested in a single call. At 10–15 tickers, this is one API call per poll cycle.

### 2. Single Ticker Snapshot

For detailed data on one ticker (e.g., future per-ticker detail views).

```python
snapshot = client.get_snapshot_ticker(
    market_type=SnapshotMarketType.STOCKS,
    ticker="AAPL",
)

print(f"Price: ${snapshot.last_trade.price}")
print(f"Bid/Ask: ${snapshot.last_quote.bid_price} / ${snapshot.last_quote.ask_price}")
print(f"Day range: ${snapshot.day.low} – ${snapshot.day.high}")
```

### 3. Previous Close

Previous day's OHLCV. Useful for computing day change when the snapshot's `day` object hasn't reset yet (pre-market).

**REST**: `GET /v2/aggs/ticker/{ticker}/prev`

```python
for agg in client.get_previous_close_agg(ticker="AAPL"):
    print(f"Previous close: ${agg.close}")
    print(f"OHLC: O={agg.open} H={agg.high} L={agg.low} C={agg.close}")
    print(f"Volume: {agg.volume:,}")
```

### 4. Aggregates (Bars)

Historical OHLCV bars over a date range. Not used for live polling, but available if historical charts are added.

**REST**: `GET /v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from}/{to}`

```python
aggs = []
for a in client.list_aggs(
    ticker="AAPL",
    multiplier=1,
    timespan="day",       # "minute", "hour", "day", "week", "month", "quarter", "year"
    from_="2024-01-01",
    to="2024-01-31",
    limit=50000,
):
    aggs.append(a)

for a in aggs:
    print(f"Date: {a.timestamp}, O={a.open} H={a.high} L={a.low} C={a.close} V={a.volume}")
```

### 5. Last Trade / Last Quote

Individual endpoints for the most recent trade or NBBO quote. Not used in FinAlly (the snapshot endpoint covers both), but available.

```python
trade = client.get_last_trade(ticker="AAPL")
print(f"Last trade: ${trade.price} x {trade.size}")

quote = client.get_last_quote(ticker="AAPL")
print(f"NBBO: ${quote.bid} x {quote.bid_size} / ${quote.ask} x {quote.ask_size}")
```

## How FinAlly Uses the API

The `MassiveDataSource` in `backend/app/market/massive_client.py` runs as a background asyncio task:

1. On `start()`: creates the `RESTClient`, does an immediate first poll (so the cache has data before any SSE client connects), then launches the background loop
2. **Poll loop**: sleeps for `poll_interval` seconds (default 15.0), then calls `_poll_once()`
3. **`_poll_once()`**: calls `get_snapshot_all()` for all currently watched tickers in one API call, writes each price to the `PriceCache`
4. Watchlist changes (`add_ticker` / `remove_ticker`) update `self._tickers` immediately; the next poll cycle picks up the change

```python
# Simplified from backend/app/market/massive_client.py
import asyncio
from massive import RESTClient
from massive.rest.models import SnapshotMarketType

class MassiveDataSource(MarketDataSource):
    def __init__(self, api_key: str, price_cache: PriceCache, poll_interval: float = 15.0):
        self._client = RESTClient(api_key=api_key)
        self._cache = price_cache
        self._interval = poll_interval
        self._tickers: list[str] = []

    async def _poll_once(self) -> None:
        if not self._tickers:
            return
        # Massive RESTClient is synchronous; run in thread to avoid blocking event loop
        snapshots = await asyncio.to_thread(
            self._client.get_snapshot_all,
            market_type=SnapshotMarketType.STOCKS,
            tickers=self._tickers,
        )
        for snap in snapshots:
            self._cache.update(
                ticker=snap.ticker,
                price=snap.last_trade.price,
                timestamp=snap.last_trade.timestamp / 1000.0,  # ms → seconds
            )
```

## Error Handling

The `MassiveDataSource` wraps `_poll_once()` in a `try/except` — poll failures are logged but do not crash the background loop. The cache retains the last-known price until the next successful poll.

Common HTTP error codes:
- **401**: Invalid API key — check `MASSIVE_API_KEY`
- **403**: Endpoint not available on this plan
- **429**: Rate limit exceeded — reduce poll frequency or upgrade plan
- **5xx**: Server errors — the client retries automatically (3 retries by default)

Per-snapshot errors (missing fields, `None` prices) are caught individually with `AttributeError` / `TypeError` and logged as warnings, allowing valid tickers in the same response to succeed.

## Notes

- The `massive` Python client is **synchronous**. Use `asyncio.to_thread()` to call it from async code without blocking the event loop.
- Timestamps from the API are **Unix milliseconds** — divide by 1000 to get Unix seconds before storing in `PriceCache`.
- During **market-closed hours**, `last_trade.price` reflects the last traded price. After-hours trades may be included.
- The `day` object **resets at market open**; during pre-market, `day.open` and `day.volume` may still reflect the previous session.
- Up to **250 tickers** per snapshot call — well above the 10–15 typical watchlist size in FinAlly.
