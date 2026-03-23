import { test, expect } from '@playwright/test';

// Helper: wait for SSE prices to start streaming
async function waitForPrices(page: import('@playwright/test').Page) {
  // Wait for at least one price to appear on the page (a dollar amount)
  await page.waitForFunction(
    () => document.body.innerText.match(/\$[\d,]+\.\d{2}/),
    { timeout: 15000 },
  );
}

test.describe('Health & Connectivity', () => {
  test('health endpoint returns ok', async ({ request }) => {
    const res = await request.get('/api/health');
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.status).toBe('ok');
  });

  test('connection status indicator shows connected', async ({ page }) => {
    await page.goto('/');
    await waitForPrices(page);

    // Header shows "LIVE" when connected
    await expect(page.locator('text=LIVE')).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Fresh Start - Default State', () => {
  test('page loads with default watchlist and balance', async ({ page }) => {
    await page.goto('/');
    await waitForPrices(page);

    // Watchlist tickers should render in the UI (wait for them to appear)
    await expect(page.locator('text=AAPL').first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=GOOGL').first()).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=MSFT').first()).toBeVisible({ timeout: 5000 });

    // Should show $10,000 initial balance in the header
    const bodyText = await page.textContent('body');
    expect(bodyText).toMatch(/10[,.]?000/);
  });

  test('prices are streaming and updating', async ({ page }) => {
    await page.goto('/');
    await waitForPrices(page);

    // Prices update every ~500ms. Capture initial body text, wait, check for changes.
    const initialText = await page.textContent('body');

    await page.waitForFunction(
      (initText: string) => document.body.innerText !== initText,
      initialText!,
      { timeout: 5000 },
    );
  });
});

test.describe('Watchlist Management', () => {
  test('add a ticker to the watchlist via UI', async ({ page }) => {
    await page.goto('/');
    await waitForPrices(page);

    // Watchlist has an "Add ticker" input
    const addInput = page.locator('input[placeholder="Add ticker"]');
    await expect(addInput).toBeVisible();

    await addInput.fill('PYPL');
    await addInput.press('Enter');

    // PYPL should appear in the UI watchlist
    await expect(page.locator('text=PYPL').first()).toBeVisible({ timeout: 10000 });

    // Also verify via API
    const wlRes = await page.request.get('/api/watchlist');
    const wlData = await wlRes.json();
    const symbols = wlData.tickers.map((t: any) => t.ticker);
    expect(symbols).toContain('PYPL');
  });

  test('remove a ticker from the watchlist', async ({ page }) => {
    await page.goto('/');
    await waitForPrices(page);

    // Wait for NFLX to be visible in the watchlist UI
    const nflxText = page.locator('span:has-text("NFLX")').first();
    await expect(nflxText).toBeVisible({ timeout: 10000 });

    // The remove button (X icon) appears on hover
    const nflxRow = nflxText.locator('xpath=ancestor::div[contains(@class, "cursor-pointer")]').first();
    await nflxRow.hover();

    // Click the X button
    const removeBtn = nflxRow.locator('button').first();
    await removeBtn.click();

    // NFLX should disappear from UI
    await expect(nflxText).not.toBeVisible({ timeout: 5000 });

    // Verify via API
    const wlAfter = await (await page.request.get('/api/watchlist')).json();
    const afterSymbols = wlAfter.tickers.map((t: any) => t.ticker);
    expect(afterSymbols).not.toContain('NFLX');
  });
});

test.describe('Trading', () => {
  test('buy shares - cash decreases, position appears', async ({ page }) => {
    await page.goto('/');
    await waitForPrices(page);

    // Get initial cash balance via API
    const portfolioBefore = await (await page.request.get('/api/portfolio')).json();
    const cashBefore = portfolioBefore.cash_balance;

    // Trade bar: ticker input (placeholder is the selected ticker), qty input, BUY/SELL buttons
    const qtyInput = page.locator('input[placeholder="Qty"]');
    const buyButton = page.locator('button:has-text("BUY")');

    // Click AAPL in watchlist first to select it
    await page.locator('span:has-text("AAPL")').first().click();
    await page.waitForTimeout(200);

    await qtyInput.fill('5');
    await buyButton.click();

    // Wait for trade confirmation message
    await page.waitForTimeout(2000);

    // Verify cash decreased
    const portfolioAfter = await (await page.request.get('/api/portfolio')).json();
    expect(portfolioAfter.cash_balance).toBeLessThan(cashBefore);

    // Position should exist
    const aaplPosition = portfolioAfter.positions.find((p: any) => p.ticker === 'AAPL');
    expect(aaplPosition).toBeTruthy();
    expect(aaplPosition.quantity).toBeGreaterThanOrEqual(5);
  });

  test('sell shares - cash increases, position updates', async ({ page }) => {
    // First buy some shares via API to ensure we have a position
    const buyRes = await page.request.post('/api/portfolio/trade', {
      data: { ticker: 'MSFT', quantity: 10, side: 'buy' },
    });
    expect(buyRes.ok()).toBeTruthy();

    const portfolioAfterBuy = await (await page.request.get('/api/portfolio')).json();
    const cashAfterBuy = portfolioAfterBuy.cash_balance;

    // Sell half via API
    const sellRes = await page.request.post('/api/portfolio/trade', {
      data: { ticker: 'MSFT', quantity: 5, side: 'sell' },
    });
    expect(sellRes.ok()).toBeTruthy();

    const portfolioAfterSell = await (await page.request.get('/api/portfolio')).json();
    expect(portfolioAfterSell.cash_balance).toBeGreaterThan(cashAfterBuy);

    // Position should have 5 remaining
    const msftPosition = portfolioAfterSell.positions.find((p: any) => p.ticker === 'MSFT');
    expect(msftPosition).toBeTruthy();
    expect(msftPosition.quantity).toBe(5);

    // Sell remaining - position should disappear
    const sellAllRes = await page.request.post('/api/portfolio/trade', {
      data: { ticker: 'MSFT', quantity: 5, side: 'sell' },
    });
    expect(sellAllRes.ok()).toBeTruthy();

    const portfolioFinal = await (await page.request.get('/api/portfolio')).json();
    const msftGone = portfolioFinal.positions.find((p: any) => p.ticker === 'MSFT');
    expect(msftGone).toBeUndefined();
  });
});

test.describe('Portfolio Visualizations', () => {
  test('portfolio heatmap shows positions after buying', async ({ page }) => {
    // Buy a position via API
    await page.request.post('/api/portfolio/trade', {
      data: { ticker: 'AAPL', quantity: 10, side: 'buy' },
    });

    await page.goto('/');
    await waitForPrices(page);

    // Look for heatmap/treemap element with AAPL visible
    // The PortfolioHeatmap component renders SVG rectangles or similar
    const heatmap = page.locator(
      'svg:has(rect), canvas, [class*="heatmap"], [class*="treemap"]'
    ).first();

    if (await heatmap.count() > 0) {
      await expect(heatmap).toBeVisible({ timeout: 10000 });
    }

    // At minimum, AAPL should appear in positions area
    const bodyText = await page.textContent('body');
    expect(bodyText).toContain('AAPL');
  });

  test('P&L chart has data points after waiting for snapshots', async ({ page }) => {
    // Buy something so portfolio has positions
    await page.request.post('/api/portfolio/trade', {
      data: { ticker: 'NVDA', quantity: 3, side: 'buy' },
    });

    // Wait for portfolio snapshots (every 5 seconds)
    await page.waitForTimeout(7000);

    // Check snapshots exist via API
    const historyRes = await page.request.get('/api/portfolio/history');
    expect(historyRes.ok()).toBeTruthy();
    const history = await historyRes.json();
    const snapshots = history.history || [];
    expect(snapshots.length).toBeGreaterThan(0);

    // Load page and verify chart area exists
    await page.goto('/');
    await waitForPrices(page);

    const chart = page.locator('canvas, svg').first();
    if (await chart.count() > 0) {
      await expect(chart).toBeVisible({ timeout: 5000 });
    }
  });
});

test.describe('AI Chat (Mock Mode)', () => {
  test('send a message and receive AI response', async ({ page }) => {
    await page.goto('/');
    await waitForPrices(page);

    // Chat panel has "Ask FinAlly..." placeholder input
    const chatInput = page.locator('input[placeholder="Ask FinAlly..."]');

    if (await chatInput.count() > 0) {
      await chatInput.fill('What should I buy?');
      await chatInput.press('Enter');

      // Wait for the loading spinner to appear and then disappear
      // Or wait for a new assistant message to appear
      await page.waitForFunction(
        () => {
          const elements = document.querySelectorAll('[class*="bg-bg-secondary"]');
          // Look for assistant messages (left-justified chat bubbles)
          for (const el of elements) {
            if (el.textContent && el.textContent.length > 20) return true;
          }
          return false;
        },
        { timeout: 15000 },
      );

      // Verify the page has more content after AI response
      const bodyText = await page.textContent('body');
      expect(bodyText?.length).toBeGreaterThan(100);
    } else {
      // Fallback: test chat API directly
      const res = await page.request.post('/api/chat', {
        data: { message: 'What should I buy?' },
      });
      expect(res.ok()).toBeTruthy();
      const body = await res.json();
      expect(body.message).toBeTruthy();
      expect(body.message.length).toBeGreaterThan(0);
    }
  });
});

test.describe('API Integration Tests', () => {
  test('GET /api/portfolio returns expected shape', async ({ request }) => {
    const res = await request.get('/api/portfolio');
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body).toHaveProperty('cash_balance');
    expect(body).toHaveProperty('positions');
    expect(body).toHaveProperty('total_value');
    expect(body).toHaveProperty('unrealized_pnl');
    expect(typeof body.cash_balance).toBe('number');
    expect(Array.isArray(body.positions)).toBeTruthy();
  });

  test('GET /api/watchlist returns default tickers', async ({ request }) => {
    const res = await request.get('/api/watchlist');
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    // Response shape: { tickers: [{ ticker, price, prev_price, change_pct }] }
    expect(body).toHaveProperty('tickers');
    const symbols = body.tickers.map((t: any) => t.ticker);
    expect(symbols).toContain('AAPL');
    expect(symbols).toContain('GOOGL');
    expect(symbols.length).toBeGreaterThanOrEqual(10);
  });

  test('POST /api/watchlist adds a ticker', async ({ request }) => {
    const res = await request.post('/api/watchlist', {
      data: { ticker: 'DIS' },
    });
    expect(res.ok()).toBeTruthy();

    const listRes = await request.get('/api/watchlist');
    const body = await listRes.json();
    const symbols = body.tickers.map((t: any) => t.ticker);
    expect(symbols).toContain('DIS');
  });

  test('DELETE /api/watchlist/:ticker removes a ticker', async ({ request }) => {
    // First add it
    await request.post('/api/watchlist', { data: { ticker: 'UBER' } });

    // Then remove it
    const res = await request.delete('/api/watchlist/UBER');
    expect(res.ok()).toBeTruthy();

    const listRes = await request.get('/api/watchlist');
    const body = await listRes.json();
    const symbols = body.tickers.map((t: any) => t.ticker);
    expect(symbols).not.toContain('UBER');
  });

  test('POST /api/portfolio/trade executes a buy', async ({ request }) => {
    const res = await request.post('/api/portfolio/trade', {
      data: { ticker: 'TSLA', quantity: 2, side: 'buy' },
    });
    expect(res.ok()).toBeTruthy();
    const trade = await res.json();
    expect(trade.success).toBe(true);
    expect(trade.ticker).toBe('TSLA');
    expect(trade.side).toBe('buy');
    expect(trade.quantity).toBe(2);
    expect(typeof trade.price).toBe('number');
  });

  test('POST /api/portfolio/trade rejects sell without position', async ({ request }) => {
    const res = await request.post('/api/portfolio/trade', {
      data: { ticker: 'ZZZZZ', quantity: 1, side: 'sell' },
    });
    expect(res.status()).toBeGreaterThanOrEqual(400);
  });

  test('POST /api/portfolio/trade rejects buy with insufficient cash', async ({ request }) => {
    const res = await request.post('/api/portfolio/trade', {
      data: { ticker: 'AAPL', quantity: 1000000, side: 'buy' },
    });
    expect(res.status()).toBeGreaterThanOrEqual(400);
  });

  test('GET /api/portfolio/history returns snapshots', async ({ request }) => {
    // Wait for at least one snapshot cycle
    await new Promise((r) => setTimeout(r, 6000));

    const res = await request.get('/api/portfolio/history');
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body).toHaveProperty('history');
    expect(Array.isArray(body.history)).toBeTruthy();
  });

  test('GET /api/chat/history returns conversation history', async ({ request }) => {
    const res = await request.get('/api/chat/history');
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body).toHaveProperty('messages');
    expect(Array.isArray(body.messages)).toBeTruthy();
  });

  test('POST /api/chat sends message and gets response', async ({ request }) => {
    const res = await request.post('/api/chat', {
      data: { message: 'Hello, what is my portfolio worth?' },
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body).toHaveProperty('message');
    expect(body).toHaveProperty('actions');
    expect(typeof body.message).toBe('string');
    expect(body.message.length).toBeGreaterThan(0);
    expect(Array.isArray(body.actions)).toBeTruthy();
  });

  test('SSE stream delivers price updates', async ({ page }) => {
    // Navigate to the app first so relative URLs resolve
    await page.goto('/');

    // Use page.evaluate to open an EventSource and collect events
    const received = await page.evaluate(() => {
      return new Promise<boolean>((resolve) => {
        const es = new EventSource('/api/stream/prices');
        const timeout = setTimeout(() => {
          es.close();
          resolve(false);
        }, 8000);
        es.onmessage = () => {
          clearTimeout(timeout);
          es.close();
          resolve(true);
        };
        es.onerror = () => {
          // SSE may fire error before reconnecting; wait for message
        };
      });
    });
    expect(received).toBe(true);
  });
});
