# Review of planning/PLAN.md

Reviewed by: claude-sonnet-4-6
Date: 2026-03-21

---

## Overall Assessment

PLAN.md is a well-structured, thoughtfully authored specification that successfully serves as a shared contract for multiple AI coding agents. The vision is clear, architectural decisions are explained with rationale, and the scope is appropriate for a capstone project. However, for a multi-agent project where frontend and backend are developed independently, the document has a critical gap: no API response body schemas are defined for any endpoint, which is the single most likely cause of integration failures. Several secondary issues around error handling, SQLite concurrency, and LLM reliability also need resolution before implementation begins.

---

## Section-by-Section Findings

### Section 2 — User Experience

**Issue 2.1 — Change % calculation breaks under Massive API mode**

The watchlist panel is specified to show "change % since simulator start (seed price → current price)". When the Massive API is active there is no simulator start and no seed price — the abstraction is leaky. The plan should define a source-agnostic rule such as: "the first price received for each ticker since page load is used as the baseline for change %; this calculation is performed entirely in the frontend from SSE data and requires no backend change."

**Issue 2.2 — No empty-state specification for the portfolio heatmap**

At first launch the user has no positions. The plan gives no guidance on what the heatmap renders in that state. Independent implementers will make different choices that may look broken. Add an explicit rule, for example: "display a placeholder panel with a message such as 'No positions yet — buy some shares to see your portfolio' when the positions list is empty."

**Issue 2.3 — Trade bar ticker field behaviour is unspecified**

The trade bar has a ticker field but the plan does not state whether typing in that field selects the ticker in the main chart, whether it validates against the watchlist, or what the error state looks like for an invalid or unknown ticker. This will produce divergent implementations between the frontend agent and the backend validation logic.

---

### Section 3 — Architecture Overview

**Issue 3.1 — SPA fallback for static export not mentioned**

With Next.js `output: 'export'`, the build produces only static files. FastAPI serves these files and all API routes on port 8000. If the user refreshes the browser on any URL other than `/`, FastAPI will return a 404 unless it is configured to fall back to `index.html` for all non-`/api` paths. This is a common deployment trap for SPA + static-serving backends. The plan should state explicitly: "FastAPI must serve `index.html` for all GET requests that do not match `/api/*` routes, to support browser refresh and direct URL navigation."

---

### Section 4 — Directory Structure

**Issue 4.1 — `backend/db/` and `db/` share a basename, causing confusion**

The directory tree shows `backend/db/` (schema SQL and seed logic) and a top-level `db/` (runtime SQLite volume mount). Agents working from different sections of the plan may confuse the two. The internal backend directory should be renamed to `backend/schema/` or `backend/migrations/` to make the distinction unambiguous without requiring agents to read the prose explanation.

**Issue 4.2 — `.env.example` is referenced but absent from the directory tree**

The Key Boundaries section mentions "`.env.example` committed" but it does not appear in the directory listing. An agent building the repository skeleton may omit it. Add `.env.example` explicitly to the tree at the same level as `.env`.

---

### Section 5 — Environment Variables

**Issue 5.1 — No behaviour defined when `OPENROUTER_API_KEY` is absent**

The plan marks `OPENROUTER_API_KEY` as required but does not specify what happens at runtime if it is missing. This is a realistic user error. The plan should state: "if `OPENROUTER_API_KEY` is absent or empty, all functionality except chat works normally; the `/api/chat` endpoint returns HTTP 503 with a human-readable error message."

**Issue 5.2 — `LLM_MOCK` string comparison semantics are undefined**

The `.env` block shows `LLM_MOCK=false`, but this is a string in a shell file, not a boolean. The plan does not specify whether the check is case-sensitive string equality (`== "true"`), a truthy evaluation, or something else. If a user sets `LLM_MOCK=True` or `LLM_MOCK=1`, the behaviour is undefined. Specify: "mock mode is activated if and only if the value is exactly the string `true` (case-sensitive)."

---

### Section 6 — Market Data

**Issue 6.1 — SSE endpoint ticker determination mechanism is unspecified**

The SSE endpoint `GET /api/stream/prices` takes no parameters. The plan says it "pushes price updates for the union of the user's watchlist and any tickers with open positions". The mechanism by which the SSE handler reads the current watchlist and positions is not described. The already-built `PriceCache` (per `MARKET_DATA_SUMMARY.md`) holds all tickers the data source is tracking and pushes all of them. The reconciliation between "all cached tickers" and "watchlist union positions" requires explicit logic that is absent from the plan. Specify: "on each SSE tick, the server reads the current watchlist and positions from the database (or a cached snapshot updated on each watchlist/trade change) to determine the set of tickers to include in the event payload."

**Issue 6.2 — Massive API rate-limit error handling is unspecified**

The plan notes the free tier limit (5 calls/min) but gives no guidance on handling HTTP 429 responses. The poller should be specified to: back off with exponential retry, log a warning, and not surface the error to the frontend until prices are stale beyond a defined threshold.

**Issue 6.3 — Ticker validation for the Massive API is unspecified**

In simulator mode any string becomes a valid ticker because prices are generated synthetically. In Massive API mode an unknown ticker returns an empty or error response. The plan does not specify whether the watchlist POST endpoint should validate tickers at add-time (via an API probe) or accept them and handle the empty-response case silently. This needs a decision recorded in the plan.

---

### Section 7 — Database

**Issue 7.1 — No pruning strategy for `portfolio_snapshots`**

The plan acknowledges ~17,000 rows per day and states "this is fine for SQLite" for demo sessions. However, there is no pruning strategy. A user leaving the app running overnight accumulates rows indefinitely. Add a note specifying a simple pruning rule, for example: "the snapshot background task deletes rows older than 24 hours when recording a new snapshot."

**Issue 7.2 — `/api/portfolio/history` response size is unbounded**

The endpoint description says "portfolio value snapshots over time" with no query parameters defined. After a long session the response may contain thousands of rows. Specify whether the endpoint accepts a `?since=` ISO timestamp parameter or a `?limit=` count, and what the default behaviour is (e.g., "return the most recent 500 snapshots by default").

**Issue 7.3 — `avg_cost` update logic on partial sell is not specified**

The plan describes deleting the position row on a full sell but does not describe what happens to `avg_cost` on a partial sell. In standard FIFO/average-cost accounting, `avg_cost` does not change when shares are sold — only `quantity` decreases. This must be stated explicitly to prevent different agents implementing conflicting cost-basis calculations. Add: "`avg_cost` is recalculated only on buy orders using a weighted average; sell orders reduce `quantity` only and leave `avg_cost` unchanged."

**Issue 7.4 — Watchlist "audit trail" claim is inaccurate**

The plan states "trade and watchlist audit trail is fully covered by the `trades` and `watchlist` tables." The `watchlist` table has only `added_at`; deletions are hard-deletes that leave no record. The audit claim is only true for additions. Either correct the claim ("the watchlist table records current state and add history only; deletions are not logged") or add soft-delete support if a true audit trail is needed.

---

### Section 8 — API Endpoints

**Issue 8.1 — No response body schemas are defined for any endpoint**

The endpoint table lists method, path, and a one-line description only. For a multi-agent project where frontend and backend are developed independently, missing response schemas are the highest-risk gap in the document. At minimum, each endpoint needs a JSON skeleton showing field names and types. For example, `GET /api/portfolio` should specify: `{"cash_balance": float, "total_value": float, "positions": [{"ticker": str, "quantity": float, "avg_cost": float, "current_price": float, "unrealized_pnl": float, "pnl_pct": float}]}`.

**Issue 8.2 — No standard error response format is defined**

There is no error envelope convention. FastAPI's default validation error format (HTTP 422, `{"detail": [...]}`) differs from a custom `{"error": "message"}` format. The frontend must know which format to expect. Define a single convention used throughout the API, for example: "all error responses use HTTP 4xx/5xx with body `{"error": "<human-readable message>"}`; FastAPI validation errors (422) are reformatted to this shape by a custom exception handler."

**Issue 8.3 — `POST /api/chat` response shape is inconsistent between sections 8 and 9**

Section 8 describes the response as "complete JSON response (message + executed actions)" and references an `actions` field. Section 9's Structured Output Schema shows `trades` and `watchlist_changes` as field names — these are the LLM's output fields before server-side execution. The actual HTTP response the frontend receives (after execution) is never separately defined. This will cause the frontend and backend agents to produce incompatible implementations. Define the client-facing response shape explicitly, for example:

```json
{
  "message": "string",
  "actions": [
    {
      "type": "trade",
      "ticker": "AAPL",
      "side": "buy",
      "quantity": 10,
      "price": 191.50,
      "status": "success" | "failed",
      "reason": "string (on failure only)"
    },
    {
      "type": "watchlist",
      "ticker": "PYPL",
      "action": "add",
      "status": "success" | "failed"
    }
  ]
}
```

---

### Section 9 — LLM Integration

**Issue 9.1 — Model identifier may not be stable or current**

The model is specified as `openrouter/openai/gpt-oss-120b`. This is an unusual identifier — OpenAI models on OpenRouter typically use their standard names. Model identifiers change over time. The plan should advise implementers to verify this ID against current OpenRouter documentation and make it configurable via an environment variable (e.g., `LLM_MODEL`) rather than hardcoding it.

**Issue 9.2 — Structured output enforcement compatibility is unverified**

Structured Outputs (JSON schema enforcement at the model level) is an OpenAI-specific API feature. Its availability when routing through OpenRouter to Cerebras is not guaranteed. If enforcement is not supported, the LLM may return malformed JSON. The plan should specify a fallback: "if structured output enforcement is unavailable or the response fails JSON parsing, return `{"error": "LLM response could not be parsed"}` to the frontend without executing any trades."

**Issue 9.3 — No LLM call timeout is specified**

The plan relies on fast Cerebras inference and uses a non-streaming call, but specifies no timeout. A hung network call will leave the frontend showing a loading indicator indefinitely. Specify a timeout (e.g., 30 seconds) and the response returned when it is exceeded.

**Issue 9.4 — `watchlist_changes` action values are not fully enumerated**

The schema shows `{"ticker": "PYPL", "action": "add"}` but does not enumerate all valid values for `action`. The only other sensible value is `"remove"`. Specify both values and the edge-case behaviour: "if `action` is `"remove"` for a ticker not on the watchlist, the operation is a no-op and recorded as `status: "success"` in the actions response."

**Issue 9.5 — User message is not persisted before the LLM call**

Step 7 in the How It Works sequence stores both user and assistant messages after the LLM responds. If the LLM call fails or times out, the user's message is silently lost from history. The user message should be persisted to `chat_messages` before the LLM call is made, so history remains consistent on failure.

---

### Section 10 — Frontend Design

**Issue 10.1 — Recharts is SVG-based, not canvas-based**

The plan says "Canvas-based charting library preferred (Lightweight Charts or Recharts)." Recharts renders SVG, not canvas. Lightweight Charts (TradingView) is canvas-based. An implementer choosing Recharts for the high-frequency sparkline and main chart on the basis of this recommendation will encounter performance problems at ~2 price updates per second. Clarify: use Lightweight Charts (canvas) for the sparklines and main price chart; Recharts (SVG) is acceptable for the lower-frequency P&L line chart.

**Issue 10.2 — Sparkline data retention is unbounded**

Sparklines accumulate price points from the SSE stream since page load with no upper limit. At 2 updates/second per ticker, a page open for one hour accumulates ~7,200 data points per sparkline. This will degrade rendering performance. Specify a maximum retention window, for example: "retain at most the last 200 price points per ticker for sparkline display."

**Issue 10.3 — Watchlist input validation feedback is unspecified**

The add-ticker flow does not describe user-facing feedback for invalid or duplicate tickers. The plan should state whether ticker validation is the frontend's responsibility (pre-validate before calling the API) or the backend's (return an error the frontend displays), and what the user sees in each failure case.

**Issue 10.4 — Chat panel default open/closed state is unspecified**

The chat panel is described as "docked/collapsible sidebar" with no default state specified. On a 1440px design target with a "data-dense" layout this is a significant layout decision. Specify the default (e.g., "open by default on first load; state persists in localStorage across refreshes").

---

### Section 11 — Docker and Deployment

**Issue 11.1 — Static file copy path in Dockerfile is unspecified**

The Dockerfile spec says "Copy frontend build output into a static/ directory" but does not specify the source path (Next.js export to `frontend/out/` by default) or the exact destination inside the container, nor how FastAPI's `StaticFiles` mount is configured to point at it. Implementers need: the `COPY` source and destination paths and the FastAPI `app.mount("/", StaticFiles(...))` configuration.

**Issue 11.2 — No container name convention for start/stop scripts**

The example `docker run` command does not include `--name finally`. The stop script needs to identify the container by name or by filtering on the image name. Without a specified container name, the start and stop scripts cannot be written consistently by different agents. Add `--name finally` to the canonical `docker run` command.

**Issue 11.3 — Relationship between `docker-compose.yml` and start scripts is ambiguous**

The file is listed as "optional convenience wrapper" and the rationale table says "no docker-compose for production". It is not clear whether the start scripts wrap `docker-compose up` or call `docker run` directly, or whether the two approaches can coexist without conflict. Clarify: "the start/stop scripts call `docker run`/`docker stop` directly; `docker-compose.yml` is a standalone alternative for users who prefer Compose and is not used by the scripts."

---

### Section 12 — Testing Strategy

**Issue 12.1 — Mock LLM response payload is not defined**

`LLM_MOCK=true` is specified to return "deterministic mock responses" but the exact payload is not defined anywhere. The E2E test for "AI chat (mocked): send a message, receive a response, trade execution appears inline" requires the mock to return a specific structure including a trade. Without a canonical mock payload, the backend implementer and the E2E test author will produce inconsistent results. Define the mock response, for example: `{"message": "I have purchased 5 shares of AAPL for you.", "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 5}], "watchlist_changes": []}`.

**Issue 12.2 — Test environment may diverge from production run environment**

The production start scripts use `docker run` directly; the test infrastructure uses `docker-compose.test.yml`. Volume mount paths, port bindings, and environment variable injection may differ between the two. Specify that `docker-compose.test.yml` must use identical volume paths (`/app/db`), port (`8000`), and environment variable names to the canonical `docker run` command, and include this as a test infrastructure requirement.

**Issue 12.3 — No E2E test scenario for LLM misconfiguration**

Unit tests cover malformed LLM response parsing, but there is no E2E scenario covering what the user sees when `OPENROUTER_API_KEY` is absent or invalid. Given that this is the most common setup error for new users, a test scenario should be added: "if chat is invoked without a valid API key, the chat panel displays a clear error message and no trade is attempted."

**Issue 12.4 — Frontend unit test omissions are not scoped**

The plan states "separate frontend unit tests are omitted to reduce build complexity." This is a reasonable tradeoff, but the plan does not list what is therefore untested at the unit level (SSE event handling, price flash animation trigger, sparkline accumulation, trade form validation). This ambiguity may lead agents to add frontend tests independently in divergent ways. Add a brief explicit scope note listing the untested areas so the omission is intentional and agreed.

---

## Cross-Cutting Concerns

**Concern A — SQLite concurrent write handling is not specified**

The background snapshot task writes to `portfolio_snapshots` every 5 seconds; trade execution also triggers an immediate write; and FastAPI uses async I/O. SQLite's default journal mode can produce "database is locked" errors under concurrent async writers. The plan should specify: "enable SQLite WAL (Write-Ahead Logging) mode on database initialization (`PRAGMA journal_mode=WAL`) and use a single shared async connection with serialised write access."

**Concern B — No standard for ISO timestamp formatting**

All timestamp columns are typed as `TEXT (ISO timestamp)` but the exact format is not specified (e.g., `2026-03-21T14:32:00Z` vs `2026-03-21 14:32:00` vs `2026-03-21T14:32:00.123456`). Frontend and backend agents will independently choose formats that may be incompatible in sort operations and display rendering. Specify the canonical format: ISO 8601 with UTC timezone, e.g., `2026-03-21T14:32:00.000Z`.

**Concern C — `GET /api/portfolio/history` time range grows indefinitely**

This endpoint feeds the P&L chart. With no time-range limit, the response grows with session length. After 30 minutes at 5-second resolution it is 360 rows; after 8 hours it is ~5,760 rows. A default window or maximum row count should be documented. This concern overlaps with Issue 7.2 but also affects the frontend chart rendering decision.

**Concern D — Plan has no version number or changelog**

The plan is the shared contract between agents. There is no version number, last-updated date, or summary of changes. The git status shows the plan has been modified since the last commit (`M planning/PLAN.md`). Agents that cached a prior version of the plan have no way to know what changed. Add a version header and a brief changelog section at the top of the document.

---

## Summary Table

| # | Section | Severity | Issue |
|---|---------|----------|-------|
| 2.1 | UX | Medium | Change % definition breaks under Massive API |
| 2.2 | UX | Low | No empty-state spec for portfolio heatmap |
| 2.3 | UX | Low | Trade bar ticker field validation behaviour unspecified |
| 3.1 | Architecture | High | FastAPI SPA fallback for non-API paths not mentioned |
| 4.1 | Directory | Medium | `backend/db/` and `db/` naming confusion |
| 4.2 | Directory | Low | `.env.example` missing from directory tree |
| 5.1 | Env Vars | High | No behaviour defined when `OPENROUTER_API_KEY` is absent |
| 5.2 | Env Vars | Low | `LLM_MOCK` string comparison semantics unspecified |
| 6.1 | Market Data | High | SSE ticker determination mechanism not specified |
| 6.2 | Market Data | Medium | No Massive API rate-limit error handling defined |
| 6.3 | Market Data | Medium | Ticker validation undefined for Massive API mode |
| 7.1 | Database | Low | No pruning strategy for `portfolio_snapshots` |
| 7.2 | Database | Medium | `/api/portfolio/history` response size unbounded; no query params |
| 7.3 | Database | High | `avg_cost` update logic on partial sell not specified |
| 7.4 | Database | Low | Watchlist "audit trail" claim is inaccurate |
| 8.1 | API | High | No response body schemas defined for any endpoint |
| 8.2 | API | High | No standard error response format defined |
| 8.3 | API | High | `POST /api/chat` client response shape inconsistent with LLM schema |
| 9.1 | LLM | Medium | Model identifier may be unstable; should be configurable |
| 9.2 | LLM | High | Structured output enforcement unverified via OpenRouter/Cerebras; no fallback |
| 9.3 | LLM | Medium | No LLM call timeout specified |
| 9.4 | LLM | Low | `watchlist_changes` action values not fully enumerated |
| 9.5 | LLM | Medium | User message lost from history if LLM call fails |
| 10.1 | Frontend | Medium | Recharts is SVG-based, not canvas-based; contradicts plan recommendation |
| 10.2 | Frontend | Medium | No upper bound on sparkline data points retained in memory |
| 10.3 | Frontend | Low | Watchlist input validation feedback unspecified |
| 10.4 | Frontend | Low | Chat panel default open/closed state unspecified |
| 11.1 | Docker | Medium | Static file copy path and FastAPI mount configuration unspecified |
| 11.2 | Docker | Medium | No container name convention specified for start/stop scripts |
| 11.3 | Docker | Low | Relationship between `docker-compose.yml` and start scripts ambiguous |
| 12.1 | Testing | High | Mock LLM response payload not defined |
| 12.2 | Testing | Medium | Test environment may diverge from production run environment |
| 12.3 | Testing | Low | No E2E scenario for LLM misconfiguration path |
| 12.4 | Testing | Low | Frontend unit test omissions not explicitly scoped |
| A | Cross-cutting | High | SQLite WAL mode and concurrent write strategy not specified |
| B | Cross-cutting | Medium | ISO timestamp format not standardised across all tables |
| C | Cross-cutting | Medium | `GET /api/portfolio/history` default time range not defined |
| D | Cross-cutting | Low | Plan has no version number or changelog |

---

## Priority Recommendations

The following items pose the highest risk of causing integration failures between independently developed components and should be addressed before implementation begins:

1. **Define response body schemas for all API endpoints** (Issue 8.1). This is the single most critical gap. The frontend and backend agents will otherwise make independent assumptions about field names and data shapes that will fail at integration time. Add a JSON skeleton for every endpoint to Section 8.

2. **Define the standard error response format** (Issue 8.2). Decide between a custom envelope and FastAPI defaults, add a custom exception handler if needed, and document it alongside the response schemas.

3. **Clarify the `POST /api/chat` client response shape** (Issue 8.3). The LLM's internal structured output schema and the HTTP response the frontend receives are currently conflated. Define them separately; the client-facing response must include execution results (`status`, `price`) that the LLM schema does not contain.

4. **Specify `avg_cost` behaviour on partial sells** (Issue 7.3). An unspecified cost-basis calculation will produce silent portfolio accounting bugs that are difficult to diagnose after the fact.

5. **Specify the SSE ticker determination mechanism** (Issue 6.1). The already-built `PriceCache` pushes all tracked tickers. The plan requires filtering to "watchlist union positions". The missing reconciliation logic must be defined so the backend agent implementing the API routes and the market data agent are aligned.

6. **Document the FastAPI SPA fallback requirement** (Issue 3.1). Without serving `index.html` for all non-API GET routes, a browser refresh on any page will return a 404. This is a one-line fix in code but must be in the plan to ensure the implementing agent includes it.

7. **Specify the mock LLM response payload** (Issue 12.1). The E2E test for chat with `LLM_MOCK=true` cannot be written consistently without knowing the exact mock structure the backend will return.

8. **Specify SQLite WAL mode and async connection strategy** (Concern A). FastAPI's async I/O combined with multiple concurrent writers (snapshot task, trade execution) will produce intermittent "database is locked" errors without explicit guidance on connection handling.

9. **Verify and stabilise the LLM model identifier** (Issue 9.1) and specify a fallback for structured output failures (Issue 9.2). The chat feature is central to the demo experience; a misconfigured or unsupported model name will silently break the most impressive feature.

10. **Standardise the ISO timestamp format** (Concern B). Inconsistent timestamp formats between backend serialisation and frontend parsing are a subtle but common integration bug. Specify the exact format once, in Section 7, and reference it from the API schema definitions.
