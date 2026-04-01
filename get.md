# Getting Started with FinAlly

This guide walks you through running FinAlly locally from scratch.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed and running
- An [OpenRouter](https://openrouter.ai/) API key (required for AI chat)
- (Optional) A [Massive/Polygon.io](https://polygon.io/) API key for real market data

## 1. Clone the Repository

```bash
git clone <repo-url> finally
cd finally
```

## 2. Configure Environment Variables

```bash
cp .env.example .env
```

Open `.env` and set your keys:

```bash
# Required
OPENROUTER_API_KEY=your-openrouter-api-key-here

# Optional — omit to use the built-in price simulator
MASSIVE_API_KEY=

# Optional — set true to use mock LLM responses (no API key needed)
LLM_MOCK=false
```

## 3. Build and Run

**macOS / Linux:**

```bash
bash scripts/start_mac.sh
```

**Windows (PowerShell):**

```powershell
.\scripts\start_windows.ps1
```

Or run Docker directly:

```bash
docker build -t finally .
docker run -v finally-data:/app/db -p 8000:8000 --env-file .env finally
```

## 4. Open the App

Navigate to [http://localhost:8000](http://localhost:8000) in your browser.

You will see:
- A watchlist of 10 default tickers (AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX) with live-streaming prices
- $10,000 in virtual cash ready to trade
- An AI chat panel in the sidebar

## 5. Try It Out

### Stream prices
Prices update approximately every 500ms with green/red flash animations indicating upticks and downticks.

### Execute a trade
Use the trade bar to enter a ticker, quantity, and click **Buy** or **Sell**. Orders fill instantly at the current simulated price.

### Chat with the AI
Open the AI chat panel and ask questions like:
- *"What does my portfolio look like?"*
- *"Buy 5 shares of AAPL"*
- *"Add PYPL to my watchlist"*
- *"Analyze my risk concentration"*

The AI can read your portfolio context and auto-execute trades on your behalf.

## 6. Stop the App

**macOS / Linux:**

```bash
bash scripts/stop_mac.sh
```

**Windows:**

```powershell
.\scripts\stop_windows.ps1
```

This stops and removes the container. Your portfolio data (SQLite database) is preserved in the `finally-data` Docker volume and will be available the next time you start the app.

To wipe all data and start fresh:

```bash
docker volume rm finally-data
```

## 7. Running Without Docker (Development)

**Backend:**

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

**Frontend** (separate terminal):

```bash
cd frontend
npm install
npm run dev   # dev server on port 3000
```

> In development the frontend runs on port 3000 and proxies `/api/*` to the backend on port 8000. In production (Docker) everything is served from a single port.

## 8. Running Tests

**Backend unit tests:**

```bash
cd backend
uv run pytest
```

**E2E tests (requires Docker):**

```bash
cd test
docker compose -f docker-compose.test.yml up --abort-on-container-exit
```

E2E tests run with `LLM_MOCK=true` by default for speed and reproducibility.

## Environment Variable Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENROUTER_API_KEY` | Yes | — | OpenRouter API key for AI chat via Cerebras |
| `MASSIVE_API_KEY` | No | (empty) | Polygon.io key; omit to use the built-in GBM simulator |
| `LLM_MOCK` | No | `false` | Return deterministic mock LLM responses (testing/CI) |

## Troubleshooting

**Port 8000 already in use:**
```bash
lsof -i :8000   # find the process
kill <PID>
```

**Docker build fails on `uv sync`:**
Ensure your `backend/uv.lock` is committed and up to date. Run `uv lock` inside `backend/` and commit the lockfile.

**Prices not updating:**
Check the connection status indicator in the header. A yellow dot means the SSE stream is reconnecting; a red dot means it has disconnected. Refresh the page to force a reconnect.

**AI chat returns no response:**
Verify `OPENROUTER_API_KEY` is set correctly in `.env` and that the file is being passed to Docker (`--env-file .env`).
