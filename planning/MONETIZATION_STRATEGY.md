# FinAlly — Monetization Strategy

## Executive Summary

FinAlly has three monetizable assets: the **course** it was built for, the **platform** itself, and the **AI copilot framework** underneath. This document outlines a phased approach from immediate revenue (the course) to scalable SaaS and B2B licensing.

---

## 1. Revenue Stream: The Course (Immediate)

FinAlly is the capstone project for an agentic AI coding course. The platform is proof that the curriculum works — students see a production-quality app built entirely by AI agents and learn to do it themselves.

### Pricing Tiers

| Tier | Price | Includes |
|------|-------|----------|
| **Self-Paced** | $199 | Video content, project files, community Discord |
| **Cohort-Based** | $499 | Everything above + 4-week live cohort, weekly office hours, peer review |
| **Mentored** | $1,499 | Everything above + 1-on-1 mentorship, code review, career guidance |

### Corporate Training

- **Team License**: $3,000–$10,000 per team (5–20 seats), includes private Slack channel and dedicated office hours
- **Enterprise Custom**: $15,000+ for tailored curriculum, on-site or virtual delivery, custom capstone projects
- Target buyers: engineering managers at companies adopting AI coding tools (Copilot, Cursor, Claude Code)

### Revenue Projections (Year 1)

| Channel | Units | Avg Price | Revenue |
|---------|-------|-----------|---------|
| Self-Paced | 500 | $199 | $99,500 |
| Cohort (4 cohorts × 30) | 120 | $499 | $59,880 |
| Mentored | 20 | $1,499 | $29,980 |
| Corporate | 5 teams | $5,000 | $25,000 |
| **Total** | | | **$214,360** |

### Growth Levers

- YouTube/Twitter content marketing using FinAlly as the visual hook (trading terminals are inherently eye-catching)
- Free tier: open-source the codebase, sell the learning experience
- Affiliate partnerships with AI tool companies

---

## 2. Revenue Stream: SaaS Platform (3–6 Months)

Transform FinAlly from a single-user Docker demo into a hosted multi-user platform.

### Required Technical Changes

1. **Authentication**: Add OAuth (Google/GitHub) — replace the hardcoded `"default"` user_id
2. **Database**: Migrate from SQLite to PostgreSQL for concurrent multi-user access
3. **Hosting**: Deploy to a container platform (Render, Railway, or AWS App Runner)
4. **Billing**: Stripe integration for subscription management
5. **Rate limiting**: Per-user API and LLM call limits by tier

### Pricing Model

| Tier | Price | Includes |
|------|-------|----------|
| **Free** | $0 | Simulated market data, basic AI (3 chats/day), $10k virtual portfolio |
| **Pro** | $19/mo | Real-time market data (Massive API), unlimited AI chat, multiple portfolios, export trade history |
| **Premium** | $49/mo | Everything above + premium AI models (Claude/GPT-4), advanced analytics, API access, priority support |

### Key Metrics to Track

- **Conversion rate**: Free → Pro (target: 5–8%)
- **Monthly churn**: Pro/Premium (target: <5%)
- **LTV:CAC ratio**: Target 3:1 minimum
- **AI cost per user**: LLM inference cost vs. subscription revenue per tier

### Unit Economics (Per User/Month)

| Cost Item | Free | Pro | Premium |
|-----------|------|-----|---------|
| Hosting | $0.50 | $0.50 | $0.50 |
| Market data (Massive API) | $0 | $2.00 | $2.00 |
| LLM inference | $0.10 | $1.50 | $5.00 |
| **Total cost** | **$0.60** | **$4.00** | **$7.50** |
| Revenue | $0 | $19.00 | $49.00 |
| **Gross margin** | — | **79%** | **85%** |

### Revenue Projections (Year 1 of SaaS)

| Metric | Month 3 | Month 6 | Month 12 |
|--------|---------|---------|----------|
| Free users | 1,000 | 5,000 | 15,000 |
| Pro subscribers | 50 | 300 | 900 |
| Premium subscribers | 10 | 50 | 150 |
| **MRR** | $1,440 | $8,150 | $24,450 |
| **ARR** | $17,280 | $97,800 | **$293,400** |

---

## 3. Revenue Stream: Developer Platform (6–12 Months)

### Open-Core Model

- **Open source**: Core trading simulator, SSE streaming, portfolio engine, basic UI
- **Paid (hosted)**: Authentication, managed infrastructure, premium AI, analytics dashboard, team features
- **Marketplace**: Community-built plugins (custom indicators, data sources, trading strategies) with a 70/30 revenue split

### API-as-a-Product

Expose FinAlly's AI trading assistant as an embeddable API:

```
POST /v1/analyze
{
  "portfolio": [...positions],
  "question": "How concentrated am I in tech?"
}
→ Structured JSON response with analysis + suggested trades
```

Pricing: $0.01 per API call (metered), or $99/mo flat for up to 10,000 calls.

---

## 4. Revenue Stream: B2B / White-Label (12+ Months)

### Target Customers

1. **Online brokerages** (Robinhood, Webull, eToro) — embed AI copilot into existing platforms
2. **Financial education companies** (Investopedia, TastyTrade) — paper trading with AI tutoring
3. **Fintech startups** — licensed framework to avoid building from scratch
4. **Universities** — finance/CS departments for coursework

### Licensing Model

| Package | Price | Includes |
|---------|-------|---------|
| **Starter** | $2,000/mo | White-labeled platform, up to 1,000 users, standard AI |
| **Growth** | $5,000/mo | Custom branding, up to 10,000 users, premium AI, priority support |
| **Enterprise** | $15,000+/mo | Full customization, unlimited users, dedicated infrastructure, SLA |

### Competitive Advantage

- **AI-native**: Not bolted on — the AI copilot is a first-class feature, not an afterthought
- **Simple architecture**: Single container, easy to deploy and maintain
- **Extensible**: Plugin architecture allows customers to add custom data sources and strategies
- **Low infrastructure cost**: SQLite/PostgreSQL, no expensive real-time data infrastructure

---

## 5. Revenue Stream: EA Execution Layer (6–12 Months)

### The Opportunity

Expert Advisors (EAs) — automated trading bots running on platforms like MetaTrader 4/5, cTrader, and NinjaTrader — are a massive market. But they suffer from fragmentation: each EA runs independently, there's no unified view, and managing a fleet of strategies across brokers requires manual intervention. FinAlly's AI copilot becomes the **brain that orchestrates EAs** rather than replacing them.

### How It Works

FinAlly acts as a control plane sitting above one or more execution venues. The AI copilot doesn't place trades directly on exchanges — it manages EAs that do.

```
┌─────────────────────────────────────────────────────────┐
│  FinAlly Control Plane                                  │
│                                                         │
│  ┌───────────────┐    ┌──────────────────────────────┐  │
│  │  AI Copilot   │───▶│  EA Orchestration Engine      │  │
│  │  (NL commands,│    │  ┌─────────┐  ┌───────────┐  │  │
│  │   analysis,   │    │  │ EA Mgr  │  │ Risk Gate │  │  │
│  │   decisions)  │    │  └────┬────┘  └─────┬─────┘  │  │
│  └───────────────┘    │       │              │        │  │
│                       └───────┼──────────────┼────────┘  │
│                               │              │           │
└───────────────────────────────┼──────────────┼───────────┘
                                │              │
          ┌─────────────────────┼──────────────┼──────────┐
          │                     ▼              ▼          │
          │  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
          │  │ MT4/MT5  │  │ cTrader  │  │ IBKR API │   │
          │  │  EA Pool │  │  cBots   │  │  Algos   │   │
          │  └──────────┘  └──────────┘  └──────────┘   │
          │           Execution Venues                    │
          └───────────────────────────────────────────────┘
```

### Core Capabilities

#### 5.1 EA Lifecycle Management

The AI copilot manages EAs through natural language:

| User Says | System Does |
|-----------|-------------|
| "Start the mean reversion EA on EURUSD with 0.5 lots" | Sends activation signal to the EA via bridge, sets parameters |
| "Pause all EAs — FOMC is in 30 minutes" | Sends halt signal to all active EAs, holds new orders |
| "How's the scalper doing today?" | Queries EA performance metrics, returns P&L, win rate, drawdown |
| "Scale down the momentum strategy to half size" | Adjusts lot sizing parameters on the running EA |
| "Kill the grid EA, it's in drawdown" | Sends shutdown signal, optionally closes open positions |

#### 5.2 Portfolio-Level Risk Management

This is the killer feature. Individual EAs don't know about each other. FinAlly does.

- **Cross-EA position netting**: "You have 3 EAs all long EURUSD totaling 5.2 lots — that's 62% of your margin. Want me to reduce?"
- **Correlation detection**: "Your trend-follower and breakout EA are both entering GBP pairs simultaneously. Combined exposure is high."
- **Drawdown circuit breakers**: Auto-pause all EAs if portfolio drawdown exceeds a user-defined threshold (e.g., -5% daily)
- **Margin monitoring**: "You're at 78% margin utilization. If USDJPY moves 50 pips against you, you'll hit margin call. I'm reducing the grid EA's lot size."
- **Exposure heatmap**: Visual treemap (reusing FinAlly's existing portfolio heatmap) showing exposure by currency, EA, and broker

#### 5.3 Broker Bridge Architecture

FinAlly connects to execution venues through a standardized bridge layer:

| Bridge | Protocol | Status |
|--------|----------|--------|
| **MetaTrader 4/5** | ZeroMQ bridge (EA sends/receives via DLL) or REST via MT5 Web API | Primary target |
| **cTrader** | Open API (FIX-based) or cTrader Automate API | Secondary |
| **Interactive Brokers** | IBKR Client Portal API (REST) or TWS API | Advanced users |
| **Alpaca** | REST API (paper + live) | Easy onboarding |
| **Webhook-based** | Generic HTTP POST/GET for any EA that supports webhooks | Universal fallback |

The webhook bridge is the MVP — most modern EAs (TradingView alerts, custom bots) can send/receive webhooks. More sophisticated bridges (ZeroMQ for MT4/5) come later.

#### 5.4 Strategy Analytics & Reporting

The AI copilot provides insights no individual EA dashboard can:

- **Cross-strategy attribution**: Which EA contributed most to today's P&L?
- **Regime detection**: "Market volatility has doubled this week. Your mean reversion EA performs poorly in high-vol — consider pausing it."
- **Strategy correlation matrix**: Are your EAs actually diversified, or are they all doing the same thing?
- **Execution quality**: Slippage analysis per EA, per broker, per time of day
- **Natural language reports**: "This week: +$1,240 total. Scalper EA: +$890 (14 trades, 78% win rate). Grid EA: +$620. Trend follower: -$270 (choppy market). Recommendation: reduce trend follower size until volatility regime shifts."

### Pricing Model

| Tier | Price | Includes |
|------|-------|---------|
| **Paper** | $0 | Simulated execution only (FinAlly's existing simulator acts as a mock broker) |
| **Starter** | $49/mo | 1 broker connection, up to 3 active EAs, basic risk rules |
| **Trader** | $149/mo | 3 broker connections, unlimited EAs, advanced risk management, AI analysis |
| **Professional** | $399/mo | Unlimited connections, priority execution, custom risk rules, API access, dedicated support |
| **Prop Firm / Fund** | $999+/mo | Multi-user, audit logs, compliance reporting, white-label option |

### Revenue Multiplier: EA Marketplace

FinAlly becomes a distribution platform for EA developers:

- **For EA developers**: List your EA on the FinAlly marketplace. Users can one-click deploy it through the control plane. Revenue split: 70% developer / 30% FinAlly.
- **For users**: Browse rated, reviewed EAs with verified backtests and live track records. Deploy and manage them without touching MT4/5 directly.
- **Rental model**: Users rent EAs monthly ($20–$200/mo) instead of buying outright ($500–$5,000 one-time). Lower barrier to entry, recurring revenue for developers and FinAlly.

### Revenue Projections (EA Execution Layer)

| Metric | Month 6 | Month 12 | Month 18 |
|--------|---------|----------|----------|
| Paper users | 500 | 2,000 | 5,000 |
| Starter | 30 | 150 | 400 |
| Trader | 10 | 80 | 250 |
| Professional | 3 | 20 | 60 |
| Prop/Fund | 0 | 3 | 10 |
| Marketplace GMV | $2,000 | $30,000 | $150,000 |
| **MRR (subscriptions)** | $3,870 | $25,010 | $76,250 |
| **MRR (marketplace 30%)** | $600 | $9,000 | $45,000 |
| **Total MRR** | $4,470 | $34,010 | **$121,250** |
| **ARR** | $53,640 | $408,120 | **$1,455,000** |

### Technical Implementation Path

**Phase A — Webhook Bridge MVP (Month 6–8)**
- [ ] Generic webhook receiver: EAs POST trade signals to FinAlly
- [ ] Generic webhook sender: FinAlly sends commands (start/stop/modify) to EAs via HTTP
- [ ] EA registry: track active EAs, their parameters, and current state
- [ ] Position aggregation: combine positions across all connected EAs into unified portfolio view
- [ ] Integrate with existing AI copilot: "show me all active EAs" / "pause the scalper"

**Phase B — Risk Engine (Month 8–10)**
- [ ] Cross-EA exposure calculation in real-time
- [ ] Configurable risk rules (max drawdown, max exposure per instrument, max correlation)
- [ ] Circuit breaker: auto-pause EAs when rules are breached
- [ ] Risk dashboard in frontend (extend existing heatmap/portfolio views)
- [ ] AI copilot risk alerts: proactive warnings via chat

**Phase C — Native Bridges (Month 10–14)**
- [ ] MetaTrader 5 bridge via Web API (REST)
- [ ] MetaTrader 4 bridge via ZeroMQ (requires companion EA installed in MT4)
- [ ] Interactive Brokers bridge via Client Portal API
- [ ] Alpaca bridge (simplest — pure REST, good for onboarding)
- [ ] Bridge health monitoring and auto-reconnect

**Phase D — Marketplace (Month 12–16)**
- [ ] EA developer portal: upload, describe, set pricing
- [ ] Verified backtesting: run submitted EAs against historical data in sandboxed environment
- [ ] Live track record tracking: verified P&L from actual marketplace users (anonymized)
- [ ] One-click deployment: user subscribes to an EA, FinAlly configures and starts it
- [ ] Rating and review system

### Why This Wins

1. **No one does this well today.** EA users cobble together MyFXBook for monitoring, manual MT4 management, and spreadsheets for cross-strategy analysis. It's painful.
2. **Natural language control is transformative.** "Pause everything" is infinitely better than logging into 3 MT4 instances and manually disabling EAs.
3. **The AI copilot is a genuine moat.** Competitors can build dashboards. They can't easily replicate an AI that understands portfolio risk across strategies and speaks in plain English.
4. **Builds on existing FinAlly infrastructure.** The portfolio engine, heatmap, P&L charts, SSE streaming, and AI chat are already built. The EA layer extends them rather than replacing them.
5. **Paper trading → live execution funnel.** Users start with FinAlly's simulator (free), prove it works, then connect real brokers (paid). The upgrade path is natural.

---

## 6. Revenue Stream: Strategy Plugins (6–12 Months)

### The Vision

Trading strategies become first-class plugins in FinAlly — installable, configurable, composable, and controllable through the AI copilot. This turns FinAlly from a trading terminal into a **strategy runtime** where anyone can build, share, and sell automated trading logic.

### Plugin Architecture

```
┌──────────────────────────────────────────────────────┐
│  FinAlly Strategy Runtime                            │
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │  Plugin Host                                   │  │
│  │                                                │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐      │  │
│  │  │ Strategy │ │ Strategy │ │ Strategy │ ...   │  │
│  │  │ Plugin A │ │ Plugin B │ │ Plugin C │       │  │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘      │  │
│  │       │             │             │            │  │
│  │  ┌────▼─────────────▼─────────────▼─────────┐ │  │
│  │  │         Strategy Plugin API              │ │  │
│  │  │  on_tick() · on_bar() · on_signal()      │ │  │
│  │  │  get_state() · set_params() · describe() │ │  │
│  │  └──────────────────┬───────────────────────┘ │  │
│  └─────────────────────┼─────────────────────────┘  │
│                        │                             │
│  ┌─────────────────────▼─────────────────────────┐  │
│  │              Core Services                     │  │
│  │  Price Feed │ Risk Engine │ Order Router │ AI  │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

### Plugin API Contract

Every strategy plugin implements a standard interface:

```python
class StrategyPlugin:
    """Base class for all FinAlly strategy plugins."""

    # Metadata
    name: str                    # "Golden Cross MA"
    version: str                 # "1.2.0"
    author: str                  # Developer name
    description: str             # What it does, in plain English
    supported_instruments: list  # ["stocks", "forex", "crypto"] or ["*"]

    # Configuration schema — rendered as a form in the UI
    parameters: dict             # {"fast_period": {"type": "int", "default": 9, "min": 2, "max": 50}, ...}

    # Lifecycle hooks
    def on_activate(self, ctx: StrategyContext) -> None: ...
    def on_tick(self, ctx: StrategyContext, tick: Tick) -> list[Signal]: ...
    def on_bar(self, ctx: StrategyContext, bar: Bar) -> list[Signal]: ...
    def on_deactivate(self, ctx: StrategyContext) -> None: ...

    # AI integration — the copilot calls this to understand the strategy
    def describe_state(self, ctx: StrategyContext) -> str: ...
    def explain_last_signal(self, ctx: StrategyContext) -> str: ...
```

Key design decisions:
- **Plugins emit Signals, not Orders.** Signals go through the Risk Engine before becoming orders. The plugin never bypasses risk checks.
- **`describe_state()` and `explain_last_signal()`** let the AI copilot understand what the strategy is doing and explain it to the user in natural language.
- **Parameter schema** enables both UI configuration forms and AI-driven tuning ("increase the fast MA period to 12").

### Strategy Categories

#### Built-in (Free, First-Party)

Ship with FinAlly to demonstrate the plugin system and provide immediate value:

| Strategy | Type | Description |
|----------|------|-------------|
| **Moving Average Crossover** | Trend | Classic fast/slow MA cross signals |
| **RSI Mean Reversion** | Mean Reversion | Buy oversold, sell overbought with configurable thresholds |
| **Momentum Breakout** | Breakout | Enter on N-period high/low breaks with volume confirmation |
| **Dollar-Cost Averaging** | Passive | Automated recurring buys on a schedule |
| **Rebalancer** | Portfolio | Maintain target allocation weights, rebalance on drift threshold |

#### Community (Free, Third-Party)

Open-source strategies published by the community. Quality-controlled via:
- Automated backtesting on submission
- Community ratings and reviews
- Verified live track records (opt-in)

#### Premium (Paid, Marketplace)

Strategies sold by professional developers. FinAlly takes a 30% platform fee.

| Example | Creator | Price | Description |
|---------|---------|-------|-------------|
| Pairs Trading Suite | QuantDev | $29/mo | Statistical arbitrage across correlated pairs |
| Options Wheel | ThetaGang Pro | $49/mo | Automated covered call / cash-secured put wheel |
| News Sentiment Alpha | NLP Capital | $79/mo | Trades on real-time news sentiment via NLP |
| Multi-Timeframe Ichimoku | CloudTrader | $19/mo | Ichimoku system across 3 timeframes with confluence scoring |

### AI Copilot Integration

The AI copilot becomes dramatically more powerful with strategy plugins:

| User Says | System Does |
|-----------|-------------|
| "Install the momentum breakout strategy on AAPL" | Activates plugin, subscribes to AAPL price feed, applies default parameters |
| "What strategies would work well in this market?" | AI analyzes current volatility regime, trend strength, correlation structure — recommends compatible plugins |
| "Why did the RSI strategy just buy TSLA?" | Calls `explain_last_signal()` on the plugin, translates to natural language |
| "Backtest the MA crossover on NVDA for the last 6 months" | Runs strategy against historical data, returns performance report |
| "Optimize the fast period — it's whipsawing" | AI suggests parameter adjustments based on recent price action, applies with user confirmation |
| "Combine the momentum and mean reversion strategies" | Creates a composite: momentum for trending markets, mean reversion for ranging. AI manages regime detection and switching. |
| "Build me a strategy that buys dips of >3% on my watchlist" | AI generates a custom plugin from natural language spec, user reviews and activates |

### AI-Generated Strategies

The most powerful feature: **the AI copilot can write new strategy plugins from natural language descriptions.**

1. User describes the strategy: "Buy when RSI drops below 30 and MACD histogram turns positive. Sell when RSI exceeds 70. Use 2% of portfolio per trade. Stop loss at 5%."
2. AI generates a conforming `StrategyPlugin` implementation
3. System runs automated validation: does it compile, does it conform to the API, does it produce reasonable signals on sample data?
4. User reviews the code (shown in a code panel in the UI) and activates it
5. Strategy runs in paper mode by default, user opts into live execution

This closes the loop: FinAlly is not just a platform for running other people's strategies — it's a platform where the AI builds strategies tailored to each user.

### Composability: Strategy Stacks

Users can compose multiple strategies into a **Strategy Stack** — a meta-strategy that combines signals:

```
Strategy Stack: "Conservative Growth"
├── Rebalancer (60% stocks / 40% bonds target)
│   └── Runs weekly, rebalances on 5% drift
├── DCA Bot ($500/week into the stack)
│   └── Splits across allocation targets
├── RSI Mean Reversion (tactical overlay)
│   └── Buys individual stocks on RSI < 25 dips
└── Risk Limiter (meta-rule)
    └── Pauses all buying if portfolio drawdown > 8%
```

The AI copilot can suggest stacks based on the user's goals: "I want steady growth with limited downside" → recommends a stack, explains each component, lets the user tweak it.

### Plugin Developer Experience

To attract strategy developers (who bring users), the developer experience must be excellent:

- **SDK**: `pip install finally-sdk` — scaffolding, local testing, backtesting harness
- **CLI**: `finally dev new-strategy` → generates boilerplate, `finally dev backtest` → runs locally
- **Sandbox**: Plugins run in isolated processes with resource limits (CPU, memory, network). No filesystem access. Communication via the Plugin API only.
- **Hot reload**: During development, plugin code changes are picked up without restart
- **Documentation**: Full API reference, tutorials, example strategies, video walkthroughs
- **Revenue dashboard**: Track installs, active users, MRR, churn for your published strategies

### Revenue Model

| Revenue Source | Who Pays | FinAlly Take |
|----------------|----------|-------------|
| Premium strategy subscriptions | End users | 30% of subscription price |
| Strategy stack templates | End users | $9.99 one-time or included in Pro tier |
| AI-generated strategy runs | End users | Included in Pro/Premium tier (LLM cost absorbed) |
| Developer SDK (advanced features) | Developers | Free tier + $29/mo Pro (advanced backtesting, priority review) |
| Featured placement in marketplace | Developers | $99/mo for top-of-category placement |

### Projected Impact

The strategy plugin ecosystem is the **flywheel**:

```
More strategies → More users → More revenue → More developers → More strategies
```

| Metric | Month 6 | Month 12 | Month 18 |
|--------|---------|----------|----------|
| Built-in strategies | 5 | 5 | 5 |
| Community strategies | 10 | 50 | 200 |
| Premium strategies | 3 | 20 | 80 |
| Monthly strategy installs | 200 | 5,000 | 30,000 |
| Marketplace GMV | $1,500 | $25,000 | $180,000 |
| **FinAlly marketplace revenue (30%)** | $450 | $7,500 | **$54,000/mo** |

---

## 7. Phased Roadmap (Updated)

```
Phase 1 (Now)          Phase 2 (3-6mo)           Phase 3 (6-12mo)          Phase 4 (12mo+)
─────────────────      ─────────────────────      ─────────────────────     ─────────────────────
Course sales           Auth + multi-user          Strategy plugin runtime   B2B white-label
Open source repo       Hosted SaaS               EA execution layer        Enterprise contracts
Content marketing      Stripe billing             Plugin marketplace        Prop firm deals
Community building     Free/Pro/Premium tiers     Native broker bridges     AI strategy generation
                                                  Developer SDK             International expansion
```

### Phase 1 Priorities (Now)
- [ ] Complete the platform (backend, frontend, AI integration, Docker)
- [ ] Record course content using the build process as material
- [ ] Set up course hosting (Teachable, Maven, or custom)
- [ ] Launch landing page with FinAlly demo video
- [ ] Build email list via free "AI Coding" newsletter

### Phase 2 Priorities (Month 3–6)
- [ ] Add authentication (OAuth)
- [ ] Migrate to PostgreSQL
- [ ] Deploy hosted version
- [ ] Integrate Stripe
- [ ] Implement usage-based rate limiting
- [ ] Launch free tier, begin converting to paid

### Phase 3 Priorities (Month 6–12)
- [ ] Design and implement Strategy Plugin API and runtime sandbox
- [ ] Ship 5 built-in strategies as reference implementations
- [ ] Build webhook bridge for EA orchestration (MVP)
- [ ] Cross-EA/strategy risk engine
- [ ] Developer SDK (`finally-sdk`) and CLI tooling
- [ ] Launch marketplace with community + premium listings
- [ ] Ship public API with metered billing
- [ ] Backtesting engine for strategy validation

### Phase 4 Priorities (Month 12+)
- [ ] AI-generated strategies from natural language
- [ ] Strategy Stacks (composable meta-strategies)
- [ ] Native MT4/MT5 and IBKR bridges
- [ ] First white-label / prop firm customer
- [ ] Enterprise sales process
- [ ] SOC 2 / security compliance for enterprise deals

---

## 8. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM costs scale faster than revenue | High | Tier-based rate limits; cache common queries; use cheaper models for free tier |
| Market data licensing restrictions | Medium | Simulator-first approach; real data only for paid tiers; comply with redistribution terms |
| Low course conversion | Medium | Free content funnel (YouTube, blog); money-back guarantee; cohort model for accountability |
| Competition from free AI tools | High | Focus on integrated experience (not just chat); build community moat; move fast on features |
| Regulatory concerns (financial advice) | High | Clear disclaimers everywhere; simulated by default; real-money execution requires explicit user opt-in and acknowledgment |
| Malicious strategy plugins | High | Sandboxed execution; code review for marketplace; automated security scanning; resource limits |
| EA bridge reliability (real money) | Critical | Paper trading by default; graduated trust levels; kill switches; real-time health monitoring |
| Strategy marketplace quality | Medium | Mandatory backtesting; verified track records; community ratings; FinAlly editorial curation |
| Developer ecosystem bootstrapping | Medium | Ship compelling first-party strategies; offer revenue guarantees to early developers; active Discord community |

---

## 9. Success Metrics (Updated)

### Year 1 Targets

| Metric | Target |
|--------|--------|
| Course revenue | $200,000 |
| SaaS ARR (by month 12) | $290,000 |
| EA execution layer ARR (by month 12) | $408,000 |
| Strategy marketplace GMV (by month 12) | $25,000/mo |
| Free users | 15,000 |
| Paid subscribers | 1,000 |
| Active strategy plugins | 75 |
| Plugin developers | 30 |
| Connected broker accounts | 250 |
| GitHub stars | 2,000 |
| Community members (Discord) | 5,000 |

### Combined Revenue Potential (Month 18)

| Stream | ARR |
|--------|-----|
| Course sales | $250,000 |
| SaaS subscriptions | $400,000 |
| EA execution layer | $1,455,000 |
| Strategy marketplace (30% take) | $648,000 |
| B2B / white-label | $300,000 |
| **Total** | **$3,053,000** |

### North Star Metric

**Monthly active strategy sessions** — users who have at least one strategy plugin or EA actively running (paper or live) during the month. This captures the deepest engagement and correlates most strongly with paid conversion and retention across all revenue streams.
