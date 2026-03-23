# FinAlly E2E Tests

Playwright-based end-to-end tests for the FinAlly trading platform.

## Prerequisites

- Node.js 18+
- The FinAlly app running at `http://localhost:8000`

## Running Tests

### Option 1: Against a running app

Start the app first:

```bash
cd /mnt/c/Projects/finally
./scripts/start_mac.sh
```

Then run tests:

```bash
cd test
npm install
npx playwright install chromium
npm test
```

### Option 2: Via Docker Compose

```bash
cd test
docker compose -f docker-compose.test.yml up --build -d
npm install
npx playwright install chromium
npm test
docker compose -f docker-compose.test.yml down
```

## Test Scenarios

1. **Health endpoint** - `/api/health` returns `{status: "ok"}`
2. **Fresh start** - Default watchlist (AAPL, GOOGL, etc.), $10,000 balance, streaming prices
3. **Watchlist add/remove** - Add PYPL, remove NFLX via UI or API
4. **Buy/sell shares** - Trade execution, cash balance updates, position management
5. **Portfolio heatmap** - Positions visualized after trading
6. **P&L chart** - Portfolio snapshots rendered over time
7. **AI chat (mock)** - Send message, receive response with `LLM_MOCK=true`
8. **Connection status** - Green indicator on successful SSE connection
9. **API integration** - All REST endpoints return correct shapes and status codes

## Environment

Tests expect `LLM_MOCK=true` for deterministic AI responses.
