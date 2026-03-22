# Market Data Interface Design

Unified Python interface for market data in FinAlly. Two implementations — simulator and Massive API — behind one abstract interface. All downstream code (SSE streaming, portfolio valuation, trade execution) is source-agnostic.

**Status**: Implemented in `backend/app/market/`. See `planning/MARKET_DATA_SUMMARY.md` for the full summary.

## Core Data Model

```python
# backend/app/market/models.py
from dataclasses import dataclass

@dataclass(frozen=True)
class PriceUpdate:
    """Immutable snapshot of a single price update for one ticker."""
    ticker: str
    price: float           # Current price (rounded to 2 decimal places)
    previous_price: float  # Price from the prior update
    timestamp: float       # Unix seconds

    @property
    def change(self) -> float:
        return round(self.price - self.previous_price, 4)

    @property
    def change_percent(self) -> float:
        if self.previous_price == 0:
            return 0.0
        return round((self.price - self.previous_price) / self.previous_price * 100, 4)

    @property
    def direction(self) -> str:
        """'up', 'down', or 'flat'."""
        if self.price > self.previous_price:
            return "up"
        elif self.price < self.previous_price:
            return "down"
        return "flat"

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "price": self.price,
            "previous_price": self.previous_price,
            "timestamp": self.timestamp,
            "change": self.change,
            "change_percent": self.change_percent,
            "direction": self.direction,
        }
```

`PriceUpdate` is the only data structure that leaves the market data layer. It is immutable (frozen dataclass). Everything downstream works with `PriceUpdate` objects or their dict representation.

## Abstract Interface

```python
# backend/app/market/interface.py
from abc import ABC, abstractmethod

class MarketDataSource(ABC):
    """Contract for market data providers.

    Implementations push price updates into a shared PriceCache on their own
    schedule. Downstream code never calls the data source directly for prices —
    it reads from the cache.

    Lifecycle:
        source = create_market_data_source(cache)
        await source.start(["AAPL", "GOOGL", ...])
        # ... app runs ...
        await source.add_ticker("TSLA")
        await source.remove_ticker("GOOGL")
        # ... app shutting down ...
        await source.stop()
    """

    @abstractmethod
    async def start(self, tickers: list[str]) -> None:
        """Begin producing price updates for the given tickers.

        Starts a background task that periodically writes to the PriceCache.
        Must be called exactly once.
        """

    @abstractmethod
    async def stop(self) -> None:
        """Stop the background task and release resources.

        Safe to call multiple times.
        """

    @abstractmethod
    async def add_ticker(self, ticker: str) -> None:
        """Add a ticker to the active set. No-op if already present."""

    @abstractmethod
    async def remove_ticker(self, ticker: str) -> None:
        """Remove a ticker from the active set. Also removes from PriceCache."""

    @abstractmethod
    def get_tickers(self) -> list[str]:
        """Return the current list of actively tracked tickers."""
```

Both implementations write to a shared `PriceCache`. The interface does **not** return prices directly — it pushes updates into the cache on its own schedule.

## Price Cache

Shared in-memory store. The market data source writes; the SSE streamer, portfolio valuation, and trade execution all read.

```python
# backend/app/market/cache.py
import time
from threading import Lock
from .models import PriceUpdate

class PriceCache:
    """Thread-safe in-memory cache of the latest price for each ticker.

    Writers: SimulatorDataSource or MassiveDataSource (one at a time).
    Readers: SSE streaming endpoint, portfolio valuation, trade execution.
    """

    def __init__(self) -> None:
        self._prices: dict[str, PriceUpdate] = {}
        self._lock = Lock()
        self._version: int = 0  # Monotonically increasing; bumped on every update

    def update(self, ticker: str, price: float, timestamp: float | None = None) -> PriceUpdate:
        """Record a new price. Returns the created PriceUpdate.

        Automatically computes direction and change from the previous value.
        First update for a ticker: previous_price == price, direction='flat'.
        """
        with self._lock:
            ts = timestamp or time.time()
            prev = self._prices.get(ticker)
            previous_price = prev.price if prev else price

            update = PriceUpdate(
                ticker=ticker,
                price=round(price, 2),
                previous_price=round(previous_price, 2),
                timestamp=ts,
            )
            self._prices[ticker] = update
            self._version += 1
            return update

    def get(self, ticker: str) -> PriceUpdate | None:
        """Latest PriceUpdate for a ticker, or None if unknown."""
        with self._lock:
            return self._prices.get(ticker)

    def get_price(self, ticker: str) -> float | None:
        """Convenience: just the price float, or None."""
        update = self.get(ticker)
        return update.price if update else None

    def get_all(self) -> dict[str, PriceUpdate]:
        """Snapshot of all current prices (shallow copy)."""
        with self._lock:
            return dict(self._prices)

    def remove(self, ticker: str) -> None:
        """Remove a ticker from the cache (e.g., removed from watchlist)."""
        with self._lock:
            self._prices.pop(ticker, None)

    @property
    def version(self) -> int:
        """Monotonic counter; increments on every update. Used by SSE for change detection."""
        return self._version
```

### Version Counter

The `version` property is a simple monotonic counter. The SSE endpoint uses it to detect whether any prices have changed since the last push, avoiding redundant events when no prices have updated.

## Factory Function

Selects the appropriate implementation at startup based on the environment:

```python
# backend/app/market/factory.py
import os

def create_market_data_source(price_cache: PriceCache) -> MarketDataSource:
    """Return the appropriate data source based on MASSIVE_API_KEY env var."""
    api_key = os.environ.get("MASSIVE_API_KEY", "").strip()

    if api_key:
        from .massive_client import MassiveDataSource
        return MassiveDataSource(api_key=api_key, price_cache=price_cache)
    else:
        from .simulator import SimulatorDataSource
        return SimulatorDataSource(price_cache=price_cache)
```

## Massive Implementation

The `MassiveDataSource` polls Polygon.io (now Massive) REST API every 15 seconds (free tier) or 2–5 seconds (paid). See `planning/MASSIVE_API.md` for full API details.

```python
# backend/app/market/massive_client.py (simplified)
import asyncio
from massive import RESTClient
from massive.rest.models import SnapshotMarketType

class MassiveDataSource(MarketDataSource):
    def __init__(self, api_key: str, price_cache: PriceCache, poll_interval: float = 15.0):
        self._client: RESTClient | None = None
        self._api_key = api_key
        self._cache = price_cache
        self._interval = poll_interval
        self._tickers: list[str] = []
        self._task: asyncio.Task | None = None

    async def start(self, tickers: list[str]) -> None:
        self._client = RESTClient(api_key=self._api_key)
        self._tickers = list(tickers)
        await self._poll_once()  # Immediate first poll — cache has data before SSE connects
        self._task = asyncio.create_task(self._poll_loop(), name="massive-poller")

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        self._client = None

    async def add_ticker(self, ticker: str) -> None:
        ticker = ticker.upper().strip()
        if ticker not in self._tickers:
            self._tickers.append(ticker)

    async def remove_ticker(self, ticker: str) -> None:
        ticker = ticker.upper().strip()
        self._tickers = [t for t in self._tickers if t != ticker]
        self._cache.remove(ticker)

    def get_tickers(self) -> list[str]:
        return list(self._tickers)

    async def _poll_loop(self) -> None:
        while True:
            await asyncio.sleep(self._interval)
            await self._poll_once()

    async def _poll_once(self) -> None:
        if not self._tickers or not self._client:
            return
        try:
            # RESTClient is synchronous — offload to thread pool
            snapshots = await asyncio.to_thread(
                self._client.get_snapshot_all,
                market_type=SnapshotMarketType.STOCKS,
                tickers=self._tickers,
            )
            for snap in snapshots:
                try:
                    self._cache.update(
                        ticker=snap.ticker,
                        price=snap.last_trade.price,
                        timestamp=snap.last_trade.timestamp / 1000.0,  # ms → seconds
                    )
                except (AttributeError, TypeError) as e:
                    logger.warning("Skipping snapshot for %s: %s", getattr(snap, "ticker", "???"), e)
        except Exception as e:
            logger.error("Massive poll failed: %s", e)
            # Don't re-raise — loop will retry next interval
```

## Simulator Implementation

The `SimulatorDataSource` wraps `GBMSimulator` (see `planning/MARKET_SIMULATOR.md`) in an async loop.

```python
# backend/app/market/simulator.py (SimulatorDataSource only)
import asyncio

class SimulatorDataSource(MarketDataSource):
    def __init__(self, price_cache: PriceCache, update_interval: float = 0.5):
        self._cache = price_cache
        self._interval = update_interval
        self._sim: GBMSimulator | None = None
        self._task: asyncio.Task | None = None

    async def start(self, tickers: list[str]) -> None:
        self._sim = GBMSimulator(tickers=tickers)
        # Seed cache immediately so SSE has data before clients connect
        for ticker in tickers:
            price = self._sim.get_price(ticker)
            if price is not None:
                self._cache.update(ticker=ticker, price=price)
        self._task = asyncio.create_task(self._run_loop(), name="simulator-loop")

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None

    async def add_ticker(self, ticker: str) -> None:
        if self._sim:
            self._sim.add_ticker(ticker)
            price = self._sim.get_price(ticker)
            if price is not None:
                self._cache.update(ticker=ticker, price=price)

    async def remove_ticker(self, ticker: str) -> None:
        if self._sim:
            self._sim.remove_ticker(ticker)
        self._cache.remove(ticker)

    def get_tickers(self) -> list[str]:
        return self._sim.get_tickers() if self._sim else []

    async def _run_loop(self) -> None:
        while True:
            try:
                if self._sim:
                    prices = self._sim.step()       # Returns dict[str, float]
                    for ticker, price in prices.items():
                        self._cache.update(ticker=ticker, price=price)
            except Exception:
                logger.exception("Simulator step failed")
            await asyncio.sleep(self._interval)
```

## Integration with SSE

The SSE router is created by a factory function and exposes `GET /api/stream/prices`:

```python
# backend/app/market/stream.py
import json
import asyncio
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

def create_stream_router(price_cache: PriceCache) -> APIRouter:
    router = APIRouter()

    @router.get("/api/stream/prices")
    async def stream_prices():
        async def generate():
            last_version = -1
            while True:
                current_version = price_cache.version
                if current_version != last_version:
                    prices = price_cache.get_all()
                    data = {ticker: update.to_dict() for ticker, update in prices.items()}
                    yield f"data: {json.dumps(data)}\n\n"
                    last_version = current_version
                await asyncio.sleep(0.1)  # Check for updates every 100ms

        return StreamingResponse(generate(), media_type="text/event-stream")

    return router
```

The version counter means the SSE endpoint only sends an event when at least one price has actually changed — not on every 100ms poll. This keeps the event stream clean.

## File Structure

```
backend/
  app/
    market/
      __init__.py          # Re-exports: PriceCache, PriceUpdate, MarketDataSource,
                           #             create_market_data_source, create_stream_router
      models.py            # PriceUpdate frozen dataclass
      interface.py         # MarketDataSource ABC
      cache.py             # PriceCache (thread-safe, version counter)
      factory.py           # create_market_data_source() — selects by env var
      massive_client.py    # MassiveDataSource — REST polling via massive package
      simulator.py         # GBMSimulator + SimulatorDataSource
      seed_prices.py       # SEED_PRICES, TICKER_PARAMS, CORRELATION_GROUPS constants
      stream.py            # create_stream_router() — FastAPI SSE endpoint
```

## Usage for Downstream Code

```python
from app.market import PriceCache, create_market_data_source, create_stream_router

# App startup (e.g., in FastAPI lifespan handler)
cache = PriceCache()
source = create_market_data_source(cache)  # Reads MASSIVE_API_KEY env var
await source.start(["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"])

# Register SSE endpoint
app.include_router(create_stream_router(cache))

# Read prices (e.g., for trade execution or portfolio valuation)
update = cache.get("AAPL")          # PriceUpdate | None
price = cache.get_price("AAPL")     # float | None
all_prices = cache.get_all()        # dict[str, PriceUpdate]

# Dynamic watchlist changes
await source.add_ticker("PYPL")
await source.remove_ticker("NFLX")

# App shutdown
await source.stop()
```

## Lifecycle

1. **App startup**: Create `PriceCache` → `create_market_data_source(cache)` → `await source.start(initial_tickers)`
2. **SSE streaming**: Reads from `cache.version` (change detection) and `cache.get_all()` on each push
3. **Trade execution**: Reads `cache.get_price(ticker)` for current price
4. **Portfolio valuation**: Reads `cache.get_all()` to compute unrealized P&L
5. **Watchlist changes**: Calls `source.add_ticker()` or `source.remove_ticker()`
6. **App shutdown**: `await source.stop()`
