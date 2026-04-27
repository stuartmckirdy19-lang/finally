# Review of planning/PLAN.md

Reviewed by: claude-sonnet-4-6
Date: 2026-03-24

---

## Overall Assessment

PLAN.md remains a well-structured specification with clear vision and sound architectural rationale. Since the last review (2026-03-21) the backend API layer has been implemented, which allows this review to assess both the plan's remaining gaps and divergences between the plan and the actual code. The most urgent issues are concrete implementation bugs introduced by the new code that will break the system at runtime: the market data source is started with no tickers, newly-added watchlist tickers never receive price data, and the mock LLM response contains no trade action — making a key E2E scenario impossible. Several high-severity issues from the prior review remain unresolved in the plan.

---

## What Has Changed Since the Last Review

The following components have been built and committed since 2026-03-21:

- `backend/app/main.py` — FastAPI app entry point with lifespan, snapshot loop, static file serving
- `backend/app/database.py` — SQLite schema initialisation and `db_conn()` context manager
- `backend/app/routes/portfolio.py` — `GET /api/portfolio`, `POST /api/portfolio/trade`, `GET /api/portfolio/history`
- `backend/app/routes/watchlist.py` — `GET /api/watchlist`, `POST /api/watchlist`, `DELETE /api/watchlist/{ticker}`
- `backend/app/routes/chat.py` — `GET /api/chat/history`, `POST /api/chat`
- `backend/app/routes/health.py` — `GET /api/health`
- `backend/app/market/stream.py` — updated SSE router (now uses a module-level router rather than the factory pattern documented in `MARKET_INTERFACE.md`)

The frontend has not yet been built.

---

## Section-by-Section Findings

### New findings arising from the implemented code

**Issue N.1 — `market_data_source.start()` called with no arguments (runtime bug)**

`main.py` line 77 calls `await market_data_source.start()` with no arguments. The `MarketDataSource` abstract interface requires `start(tickers: list[str])` as a mandatory positional parameter (`interface.py` line 26). Both `SimulatorDataSource` and `MassiveDataSource` will raise `TypeError` at startup. The call must be `await market_data_source.start(initial_tickers)` where `initial_tickers` is loaded from the watchlist table. This is a startup-blocking bug: the application will not run at all in its current state.

**Issue N.2 — Watchlist add/remove routes do not update the market data source (data gap)**

`watchlist.py` inserts or deletes from the `watchlist` database table but never calls `source.add_ticker()` or `source.remove_ticker()` on the market data source. A ticker added via `POST /api/watchlist` will appear in the database but will never have prices generated for it — `cache.get(ticker)` will return `None` indefinitely, causing every watchlist response to show `"price": null` for the new ticker. Similarly, a deleted ticker remains in the price cache, consuming simulator cycles. The watchlist routes must import the global `market_data_source` from `app.main` and call the appropriate lifecycle method on every add and remove.

**Issue N.3 — SSE streams all cached tickers, not the watchlist-union-positions set**

`stream.py` calls `price_cache.get_all()` and emits every ticker in the cache with no filtering. The plan (Section 6) specifies that the SSE endpoint must push "the union of the user's watchlist and any tickers with open positions." In practice this means the SSE payload should not include tickers the user has removed from their watchlist once those tickers have no open position. With the current implementation, removed tickers stay in the cache (Issue N.2) and are streamed forever. This is a coherence issue for the frontend, which uses SSE as the authoritative source of live prices and would continue showing stale data for removed tickers.

**Issue N.4 — Mock LLM response includes no trades, breaking the E2E chat-with-trade scenario**

`chat.py` defines `MOCK_RESPONSE` as `{"message": "...", "trades": [], "watchlist_changes": []}`. The E2E test scenario listed in Section 12 is "AI chat (mocked): send a message, receive a response, trade execution appears inline." With an empty `trades` array, no trade is ever executed in mock mode and the inline execution display cannot be tested. The mock response must include at least one trade, for example `{"ticker": "AAPL", "side": "buy", "quantity": 1}`, to make the scenario exercisable.

**Issue N.5 — User and assistant messages stored with identical timestamps, breaking ordering**

In `chat.py`, `now` is set once at the start of the handler (line 180) and then used for both the user message insert (line 281) and the assistant message insert (line 285). Both rows share the exact same `created_at` value. The `GET /api/chat/history` endpoint sorts by `created_at` ascending. When both messages have the same timestamp, their ordering is non-deterministic at the SQLite level and may render as assistant-before-user in the chat panel. The assistant message timestamp must be set after trade execution completes.

**Issue N.6 — `create_stream_router()` factory now silently ignores its `price_cache` argument**

`stream.py` line 50-56 retains `create_stream_router(price_cache)` for "backwards compatibility" but the `price_cache` argument is silently discarded; the router uses a module-level global reference instead. This is documented nowhere. `MARKET_INTERFACE.md` and `MARKET_DATA_SUMMARY.md` both show usage patterns that pass a `PriceCache` instance to the factory and expect it to be used. Any downstream agent or test that constructs an isolated `PriceCache` and passes it to `create_stream_router` expecting isolation will receive the global cache instead. Either remove the parameter, raise a deprecation warning, or restore the parameterised behaviour. The plan and interface documentation must be updated to match whichever approach is chosen.

**Issue N.7 — `GET /api/portfolio/history` silently caps at 1000 rows with undocumented ordering reversal**

`portfolio.py` line 213 queries with `LIMIT 1000` and then reverses the result in Python. Neither the cap nor the reversal is documented in the plan or the endpoint description. The frontend engineer will see an endpoint called "portfolio value snapshots over time" and have no idea there is a 1000-row ceiling or that the backend fetches DESC then re-reverses. This should be documented as the API contract, or a `?limit=` / `?since=` query parameter should be added so the frontend can request a specific window. (This partially addresses the prior Issue 7.2 from the 2026-03-21 review, but the fix is in code without a plan update.)

**Issue N.8 — `POST /api/portfolio/trade` auto-adds tickers to the watchlist but does not call `source.add_ticker()`**

`portfolio.py` line 154-158 runs `INSERT OR IGNORE INTO watchlist` when a trade is executed for a ticker not already on the watchlist. This correctly fulfils the plan's requirement to auto-add the ticker. However, like Issue N.2, it does not call `source.add_ticker()` on the market data source, so the newly-watchlisted ticker still has no live price generated until the next time tickers are loaded from the database (which never happens after startup). The auto-add logic must also trigger `source.add_ticker()`.

**Issue N.9 — `_call_llm` is a synchronous blocking call inside an async FastAPI route**

`chat.py` line 108 defines `_call_llm` as a plain `def` function (not `async def`) and calls `litellm.completion()` synchronously. It is called directly from the `chat()` route handler (also a plain `def` route), so FastAPI runs it in a thread pool automatically. However, this means a single blocked LLM call ties up one thread-pool worker for the full request duration (potentially 5-30 seconds). With the default thread pool this is not a problem for a single-user demo, but it is worth noting. More critically, there is no timeout on the `completion()` call (prior Issue 9.3 from the 2026-03-21 review remains unresolved in both the plan and the code).

**Issue N.10 — `GET /api/watchlist` returns `change_pct` relative to previous tick, not since page load**

`watchlist.py` line 42 returns `price_data.change_percent` from the `PriceUpdate` object. `PriceUpdate.change_percent` is the percentage change from `previous_price` to `price` — i.e., the change over the last simulator tick (~500ms), not "since simulator start (seed price → current price)" as the plan specifies in Section 10. The frontend would need to compute the since-load change itself from the seed price embedded in the SSE stream or from the first price observed since page load. The plan (Section 2, Issue 2.1 from prior review) says this calculation should be done in the frontend. The backend returning `change_pct` as a tick-level delta without labelling it as such will confuse the frontend engineer. The field should either be renamed `tick_change_pct` to clarify its meaning, or removed from the REST response and computed purely on the frontend from SSE data.

---

### Carry-Forward Findings from Prior Review (Still Unresolved in Plan)

The following high-severity issues identified in the 2026-03-21 review remain open. They are summarised here to maintain priority visibility; full descriptions remain in the prior review document.

**Issue 8.1 (carry-forward) — No response body schemas defined for any API endpoint**

The plan still does not define JSON response schemas. Now that the backend is implemented, the actual schemas can be inferred from the code, but they have not been written back into the plan as the shared contract. The frontend agent will need to reverse-engineer them from the code. At minimum the plan should be updated to reflect the actual response shapes now that they are implemented.

**Issue 8.2 (carry-forward) — No standard error response format**

FastAPI's default 422 validation error format and the explicit `HTTPException` 400 raises in the routes use different shapes (`{"detail": ...}` vs a plain string). No custom exception handler normalises them. The frontend will receive inconsistent error formats.

**Issue 9.2 (carry-forward) — Structured output enforcement compatibility unverified**

`chat.py` passes `response_format=LLMResponse` to `litellm.completion()`. LiteLLM will attempt to use OpenAI-style structured output enforcement. Whether Cerebras via OpenRouter honours this parameter is unverified. The fallback (`json.loads(content)`) exists in the code, but the plan still does not acknowledge this risk or specify the fallback behaviour.

**Issue 9.3 (carry-forward) — No LLM call timeout specified or implemented**

The `completion()` call in `chat.py` has no `timeout` parameter. The plan does not specify one. A hung call will block a thread indefinitely.

**Issue 3.1 (carry-forward) — FastAPI SPA fallback for non-API paths**

`main.py` line 103 uses `StaticFiles(directory=STATIC_DIR, html=True)` which does serve `index.html` as the fallback for unknown paths — this is what `html=True` does in Starlette's `StaticFiles`. So the implementation handles this correctly, but the plan still does not document it. The plan should note that `html=True` on the `StaticFiles` mount is required for SPA routing to work.

**Concern A (carry-forward) — SQLite WAL mode**

WAL mode is correctly implemented in `database.py` line 20 (`PRAGMA journal_mode=WAL`). The plan still does not mention it. Update the plan to note this is required and confirm it is implemented.

---

## Cross-Cutting Concerns

**Concern E — Global mutable state via module-level imports creates hidden coupling**

`portfolio.py`, `watchlist.py`, and `chat.py` all import `price_cache` and `market_data_source` from `app.main` at call time using `from app.main import ...` inside function bodies. This deferred import pattern avoids circular-import errors at module load time but creates tight, invisible coupling between route modules and the application entry point. It also makes unit testing routes in isolation impossible without patching `app.main` globals. The plan does not address the dependency injection strategy, and independently-developed components (e.g., a future test agent adding route unit tests) will have no guidance on how to mock the price cache. A `request.state` or `app.state` pattern would be more testable and should be specified in the plan.

**Concern F — Snapshot task and trade execution compute `total_value` independently with potential price-cache divergence**

`_snapshot_loop()` in `main.py` (lines 33-65) and `_record_snapshot()` in `portfolio.py` (lines 25-46) both compute total portfolio value using the same logic. If `price_cache.get(ticker)` returns `None` for a ticker (e.g., a ticker that was traded before its price was seeded), both fall back to `avg_cost`. This is consistent, but the duplicated logic means any future change to the valuation formula must be applied in two places. The plan does not acknowledge this duplication. Extract to a shared utility function and note it in the plan.

**Concern G — `reasoning_effort="low"` is an undocumented model parameter**

`chat.py` line 129 passes `reasoning_effort="low"` to `litellm.completion()`. This is an OpenAI o-series model parameter and may not be supported by `openrouter/openai/gpt-oss-120b` via Cerebras. If the model rejects the parameter, the call may fail or produce unexpected behaviour. The plan does not mention this parameter at all. It should either be documented or removed.

---

## Summary Table

| # | Section | Severity | Issue |
|---|---------|----------|-------|
| N.1 | main.py | **Critical** | `start()` called with no tickers — application fails at startup |
| N.2 | watchlist.py | **High** | Add/remove watchlist routes never update the market data source |
| N.3 | stream.py | **High** | SSE streams all cached tickers, ignoring watchlist-union-positions filter |
| N.4 | chat.py | **High** | Mock LLM response has no trades; E2E "trade inline" scenario untestable |
| N.5 | chat.py | **High** | User and assistant messages share identical timestamp; order is non-deterministic |
| N.6 | stream.py | Medium | `create_stream_router()` silently ignores its `price_cache` argument |
| N.7 | portfolio.py | Medium | 1000-row LIMIT and DESC-then-reverse are undocumented; plan not updated |
| N.8 | portfolio.py | **High** | Trade auto-adds ticker to DB but not to market data source |
| N.9 | chat.py | Medium | Synchronous `_call_llm` has no timeout; hangs thread indefinitely on slow LLM |
| N.10 | watchlist.py | Medium | `change_pct` is tick-delta, not since-load delta as plan specifies |
| 8.1 | Plan §8 | **High** | No API response schemas in plan (carry-forward, now code-inferable) |
| 8.2 | Plan §8 | **High** | No standard error response format; FastAPI 422 vs custom 400 shapes differ |
| 9.2 | Plan §9 | **High** | Structured output via OpenRouter/Cerebras unverified; fallback undocumented |
| 9.3 | Plan §9 | Medium | No LLM call timeout in plan or code |
| 3.1 | Plan §3 | Medium | SPA fallback implemented (`html=True`) but not documented in plan |
| A | Cross-cutting | Medium | WAL mode implemented but not documented in plan |
| E | Cross-cutting | Medium | Global mutable state pattern makes route unit tests impossible in isolation |
| F | Cross-cutting | Low | Snapshot valuation logic duplicated in two files |
| G | Cross-cutting | Medium | `reasoning_effort="low"` undocumented and likely unsupported by model |

---

## Priority Recommendations

The following items are ordered by their likelihood of causing immediate runtime failures or integration failures when the frontend is built.

1. **Fix the startup crash (Issue N.1).** `main.py` must load the default watchlist from the database before calling `source.start()` and pass those tickers. Without this fix the application does not start.

2. **Wire watchlist and trade routes to the market data source (Issues N.2, N.8).** Every call to `POST /api/watchlist`, `DELETE /api/watchlist/{ticker}`, and `POST /api/portfolio/trade` (when auto-adding to watchlist) must also call `source.add_ticker()` or `source.remove_ticker()`. Without this, newly watched tickers have no prices and the live-price feature is broken for any ticker added after startup.

3. **Fix the mock LLM response to include a trade (Issue N.4).** The E2E test scenario "trade execution appears inline" cannot pass until `MOCK_RESPONSE` contains at least one trade entry. This is a one-line fix but blocks the entire E2E test suite for chat.

4. **Fix the chat message timestamp collision (Issue N.5).** Record `now` for the user message before the LLM call, and record a fresh `datetime.now(timezone.utc).isoformat()` for the assistant message after trade execution. This ensures deterministic ordering in `GET /api/chat/history`.

5. **Define a standard error response format and add it to the plan (Issue 8.2).** The frontend engineer is about to implement error handling. Without a documented format, the frontend and backend will produce incompatible error flows. Add a custom FastAPI exception handler that normalises all 4xx/5xx responses to `{"error": "<message>"}` and document it in Section 8.

6. **Document actual API response schemas in the plan (Issue 8.1).** Now that the backend is implemented, transcribe the actual response shapes into Section 8 so the frontend engineer has a reliable contract. The schemas are now definitive from the code rather than aspirational.

7. **Document the SSE event payload format explicitly (Issue N.3 / Plan §6).** The current SSE implementation sends a single JSON object keyed by ticker containing `PriceUpdate.to_dict()` fields. The plan describes the event as containing "ticker, price, previous price, timestamp, and change direction" implying a per-ticker event format. The actual implementation sends a batch of all tickers per event. This difference matters for the frontend `EventSource` handler. Update the plan to reflect the actual batch format.

8. **Verify `reasoning_effort="low"` and `response_format=LLMResponse` are supported (Concern G, Issue 9.2).** Test one real LLM call through OpenRouter to Cerebras before the frontend is connected. A broken chat endpoint will make the most impressive demo feature fail silently.

9. **Add a timeout to the LLM call (Issue 9.3).** Pass `timeout=30` to `litellm.completion()` and return a structured error response to the frontend when it fires. Document the timeout value in the plan.

10. **Clarify `change_pct` semantics between backend and frontend (Issue N.10).** Decide once: is the `change_pct` in `GET /api/watchlist` the tick-level delta (what the code currently returns) or the since-load delta (what the plan specifies for the watchlist panel)? Document the decision in the plan and either rename the field in the API response or compute the since-load value in the backend using the seed price.
