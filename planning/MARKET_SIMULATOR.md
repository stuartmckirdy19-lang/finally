# Market Simulator Design

Approach and code structure for simulating realistic stock prices when no `MASSIVE_API_KEY` is configured.

**Status**: Implemented in `backend/app/market/simulator.py` and `backend/app/market/seed_prices.py`.

## Overview

The simulator uses **Geometric Brownian Motion (GBM)** to generate realistic stock price paths. GBM is the standard model underlying Black-Scholes option pricing — prices evolve multiplicatively with random noise, cannot go negative, and exhibit the lognormal distribution seen in real markets.

Updates run at **500ms intervals**, producing a continuous stream of price changes that feel alive on the dashboard.

## GBM Math

At each time step, a stock price evolves as:

```
S(t+dt) = S(t) * exp((mu - sigma²/2) * dt + sigma * sqrt(dt) * Z)
```

Where:
- `S(t)` = current price
- `mu` = annualized drift (expected return), e.g. `0.05` (5% per year)
- `sigma` = annualized volatility, e.g. `0.20` (20% per year)
- `dt` = time step as a fraction of a trading year
- `Z` = standard normal random variable drawn from N(0,1)

### Time Step Calculation

For 500ms updates, with 252 trading days per year and 6.5 trading hours per day:

```
Trading seconds per year = 252 × 6.5 × 3600 = 5,896,800 seconds
dt = 0.5 / 5,896,800 ≈ 8.48 × 10⁻⁸
```

This tiny `dt` produces **sub-cent moves per tick**, which accumulate naturally over time to produce realistic intraday price action.

### Why GBM?

- Prices are multiplicative: a 1% move on a $10 stock is $0.10; on a $100 stock it's $1.00 — just as in real markets
- Prices can never go negative (the `exp()` function is always positive)
- With realistic `sigma` values, the simulated intraday range matches real stocks

## Correlated Moves

Real stocks don't move independently — tech stocks tend to move together, finance stocks move together, etc. The simulator uses **Cholesky decomposition** of a correlation matrix to produce correlated random draws.

Given a correlation matrix `C`, compute `L = cholesky(C)`. Then for independent standard normals `Z_independent`:

```
Z_correlated = L @ Z_independent
```

The correlated draws `Z_correlated` respect the pairwise correlations encoded in `C`.

### Correlation Groups

Defined in `backend/app/market/seed_prices.py`:

```python
CORRELATION_GROUPS = {
    "tech":    {"AAPL", "GOOGL", "MSFT", "AMZN", "META", "NVDA", "NFLX"},
    "finance": {"JPM", "V"},
}

INTRA_TECH_CORR    = 0.6   # Tech stocks move together strongly
INTRA_FINANCE_CORR = 0.5   # Finance stocks move together
CROSS_GROUP_CORR   = 0.3   # Between sectors or unknown tickers
TSLA_CORR          = 0.3   # TSLA does its own thing (low correlation with everything)
```

Note: TSLA is in the `tech` group definition but is handled specially — it always gets `TSLA_CORR = 0.3` against any other ticker, regardless of sector.

### Cholesky Rebuild

The correlation matrix and its Cholesky decomposition are rebuilt whenever tickers are added or removed (`_rebuild_cholesky()`). This is O(n²) but `n` is always small (< 50 tickers).

With 1 ticker: no Cholesky needed (identity matrix). With 2+ tickers: Cholesky is computed and applied.

## Random Shock Events

Every step, each ticker has a **~0.1% chance** of a sudden 2–5% move in either direction. This adds drama and makes the dashboard visually interesting.

```python
if random.random() < 0.001:   # event_probability
    shock_magnitude = random.uniform(0.02, 0.05)
    shock_sign = random.choice([-1, 1])
    price *= (1 + shock_magnitude * shock_sign)
```

With 10 tickers at 2 ticks/second:
- Each ticker: ~1 event per 500 seconds (~8 minutes)
- Any ticker: ~1 event per 50 seconds

This frequency keeps the dashboard lively without being distracting.

## Seed Prices

Realistic starting prices for the default watchlist (in `backend/app/market/seed_prices.py`):

```python
SEED_PRICES: dict[str, float] = {
    "AAPL": 190.00,
    "GOOGL": 175.00,
    "MSFT": 420.00,
    "AMZN": 185.00,
    "TSLA": 250.00,
    "NVDA": 800.00,
    "META": 500.00,
    "JPM":  195.00,
    "V":    280.00,
    "NFLX": 600.00,
}
```

Tickers added dynamically (not in the seed list) start at a random price between **$50 and $300**.

## Per-Ticker Parameters

Each ticker has calibrated GBM parameters reflecting real-world volatility characteristics:

```python
TICKER_PARAMS: dict[str, dict[str, float]] = {
    "AAPL":  {"sigma": 0.22, "mu": 0.05},
    "GOOGL": {"sigma": 0.25, "mu": 0.05},
    "MSFT":  {"sigma": 0.20, "mu": 0.05},
    "AMZN":  {"sigma": 0.28, "mu": 0.05},
    "TSLA":  {"sigma": 0.50, "mu": 0.03},  # High volatility
    "NVDA":  {"sigma": 0.40, "mu": 0.08},  # High volatility, strong upward drift
    "META":  {"sigma": 0.30, "mu": 0.05},
    "JPM":   {"sigma": 0.18, "mu": 0.04},  # Low volatility (bank)
    "V":     {"sigma": 0.17, "mu": 0.04},  # Low volatility (payments)
    "NFLX":  {"sigma": 0.35, "mu": 0.05},
}

# Default for unknown tickers (dynamically added)
DEFAULT_PARAMS: dict[str, float] = {"sigma": 0.25, "mu": 0.05}
```

`sigma = 0.50` for TSLA means 50% annualized volatility — roughly matching historical TSLA behavior. `sigma = 0.17` for V reflects the stable, lower-volatility nature of payments companies.

## Implementation

```python
# backend/app/market/simulator.py
import math
import random
import logging
import numpy as np

from .cache import PriceCache
from .interface import MarketDataSource
from .seed_prices import (
    CORRELATION_GROUPS, CROSS_GROUP_CORR,
    DEFAULT_PARAMS, INTRA_FINANCE_CORR, INTRA_TECH_CORR,
    SEED_PRICES, TICKER_PARAMS, TSLA_CORR,
)

logger = logging.getLogger(__name__)


class GBMSimulator:
    """Generates correlated GBM price paths for multiple tickers.

    Math:
        S(t+dt) = S(t) * exp((mu - sigma²/2) * dt + sigma * sqrt(dt) * Z)
    """

    TRADING_SECONDS_PER_YEAR = 252 * 6.5 * 3600  # 5,896,800
    DEFAULT_DT = 0.5 / TRADING_SECONDS_PER_YEAR   # ~8.48e-8

    def __init__(
        self,
        tickers: list[str],
        dt: float = DEFAULT_DT,
        event_probability: float = 0.001,
    ) -> None:
        self._dt = dt
        self._event_prob = event_probability

        self._tickers: list[str] = []
        self._prices: dict[str, float] = {}
        self._params: dict[str, dict[str, float]] = {}
        self._cholesky: np.ndarray | None = None

        for ticker in tickers:
            self._add_ticker_internal(ticker)
        self._rebuild_cholesky()

    def step(self) -> dict[str, float]:
        """Advance all tickers by one time step. Returns {ticker: new_price}.

        Called every 500ms — the hot path. Keeps it fast with vectorized NumPy.
        """
        n = len(self._tickers)
        if n == 0:
            return {}

        # Generate n independent standard normal draws
        z_independent = np.random.standard_normal(n)

        # Apply Cholesky to introduce sector correlations
        if self._cholesky is not None:
            z_correlated = self._cholesky @ z_independent
        else:
            z_correlated = z_independent

        result: dict[str, float] = {}
        for i, ticker in enumerate(self._tickers):
            mu = self._params[ticker]["mu"]
            sigma = self._params[ticker]["sigma"]

            # GBM step: multiplicative update
            drift = (mu - 0.5 * sigma**2) * self._dt
            diffusion = sigma * math.sqrt(self._dt) * z_correlated[i]
            self._prices[ticker] *= math.exp(drift + diffusion)

            # Random shock event (~0.1% probability)
            if random.random() < self._event_prob:
                shock = random.uniform(0.02, 0.05) * random.choice([-1, 1])
                self._prices[ticker] *= (1 + shock)
                logger.debug("Random event on %s: %.1f%%", ticker, shock * 100)

            result[ticker] = round(self._prices[ticker], 2)

        return result

    def add_ticker(self, ticker: str) -> None:
        """Add a ticker to the simulation. Rebuilds the correlation matrix."""
        if ticker in self._prices:
            return
        self._add_ticker_internal(ticker)
        self._rebuild_cholesky()

    def remove_ticker(self, ticker: str) -> None:
        """Remove a ticker from the simulation. Rebuilds the correlation matrix."""
        if ticker not in self._prices:
            return
        self._tickers.remove(ticker)
        del self._prices[ticker]
        del self._params[ticker]
        self._rebuild_cholesky()

    def get_price(self, ticker: str) -> float | None:
        return self._prices.get(ticker)

    def get_tickers(self) -> list[str]:
        return list(self._tickers)

    # --- Internals ---

    def _add_ticker_internal(self, ticker: str) -> None:
        """Add without rebuilding Cholesky (for batch initialization)."""
        self._tickers.append(ticker)
        self._prices[ticker] = SEED_PRICES.get(ticker, random.uniform(50.0, 300.0))
        self._params[ticker] = TICKER_PARAMS.get(ticker, dict(DEFAULT_PARAMS))

    def _rebuild_cholesky(self) -> None:
        """Rebuild Cholesky decomposition of the ticker correlation matrix."""
        n = len(self._tickers)
        if n <= 1:
            self._cholesky = None
            return

        # Build symmetric correlation matrix
        corr = np.eye(n)
        for i in range(n):
            for j in range(i + 1, n):
                rho = self._pairwise_correlation(self._tickers[i], self._tickers[j])
                corr[i, j] = rho
                corr[j, i] = rho

        self._cholesky = np.linalg.cholesky(corr)

    @staticmethod
    def _pairwise_correlation(t1: str, t2: str) -> float:
        tech = CORRELATION_GROUPS["tech"]
        finance = CORRELATION_GROUPS["finance"]

        if t1 == "TSLA" or t2 == "TSLA":
            return TSLA_CORR                       # 0.3 — TSLA is a loner

        if t1 in tech and t2 in tech:
            return INTRA_TECH_CORR                 # 0.6 — tech stocks move together

        if t1 in finance and t2 in finance:
            return INTRA_FINANCE_CORR              # 0.5 — finance stocks move together

        return CROSS_GROUP_CORR                    # 0.3 — cross-sector or unknown
```

## File Structure

```
backend/
  app/
    market/
      simulator.py     # GBMSimulator class + SimulatorDataSource (async wrapper)
      seed_prices.py   # SEED_PRICES, TICKER_PARAMS, CORRELATION_GROUPS constants
```

`seed_prices.py` contains only constant dictionaries — no logic. `simulator.py` contains both `GBMSimulator` (the pure math class) and `SimulatorDataSource` (the `MarketDataSource` implementation that wraps it in an async loop and wires it to the `PriceCache`).

## Behavior Notes

- **Prices never go negative**: GBM is multiplicative — `exp(x)` is always positive regardless of `x`
- **Sub-cent moves per tick**: the tiny `dt` keeps individual moves small; they accumulate over time via the drift term
- **TSLA at sigma=0.50**: over a simulated trading day, expect roughly ±3–5% intraday range — matching real TSLA behavior
- **V at sigma=0.17**: tight intraday range, steady drift — matches real payment processor behavior
- **Correlation is structural, not time-varying**: it applies equally at all volatility levels and times
- **Valid positive semi-definite matrix**: all correlation values are in (0, 1) and the Cholesky decomposition is always successful for valid correlation matrices
- **Adding tickers mid-session**: `_rebuild_cholesky()` is O(n²) but n < 50, so it completes in microseconds
- **Cache seeding on start**: the simulator writes initial prices to the cache immediately on `start()`, so SSE clients connecting right away get real data instead of an empty payload
