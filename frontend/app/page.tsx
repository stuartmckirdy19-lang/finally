"use client";

import { MarketProvider } from "./context/MarketContext";
import { usePortfolio } from "./hooks/usePortfolio";
import { useWatchlist } from "./hooks/useWatchlist";
import { usePnlHistory } from "./hooks/usePnlHistory";
import { useChat } from "./hooks/useChat";
import Header from "./components/Header";
import Watchlist from "./components/Watchlist";
import MainChart from "./components/MainChart";
import PortfolioHeatmap from "./components/PortfolioHeatmap";
import PnLChart from "./components/PnLChart";
import PositionsTable from "./components/PositionsTable";
import TradeBar from "./components/TradeBar";
import ChatPanel from "./components/ChatPanel";

function Dashboard() {
  const { portfolio, refresh: refreshPortfolio } = usePortfolio();
  const { watchlist, addTicker, removeTicker } = useWatchlist();
  const { history } = usePnlHistory();
  const { messages, loading: chatLoading, sendMessage } = useChat();

  return (
    <div className="flex flex-col h-screen bg-bg-primary">
      <Header portfolio={portfolio} />

      <div className="flex flex-1 min-h-0">
        {/* Left - Watchlist */}
        <div className="w-[18%] min-w-[200px] border-r border-border">
          <Watchlist
            watchlist={watchlist}
            onAdd={addTicker}
            onRemove={removeTicker}
          />
        </div>

        {/* Center */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Main Chart */}
          <div className="h-[40%] border-b border-border">
            <MainChart />
          </div>

          {/* Middle row: Heatmap + PnL Chart */}
          <div className="h-[30%] flex border-b border-border">
            <div className="w-1/2 border-r border-border">
              <PortfolioHeatmap portfolio={portfolio} />
            </div>
            <div className="w-1/2">
              <PnLChart history={history} />
            </div>
          </div>

          {/* Positions Table */}
          <div className="flex-1 min-h-0">
            <PositionsTable portfolio={portfolio} />
          </div>

          {/* Trade Bar */}
          <TradeBar onTradeComplete={refreshPortfolio} />
        </div>

        {/* Right - Chat */}
        <div className="w-[27%] min-w-[280px] border-l border-border">
          <ChatPanel
            messages={messages}
            loading={chatLoading}
            onSend={sendMessage}
            onTradeComplete={refreshPortfolio}
          />
        </div>
      </div>
    </div>
  );
}

export default function Home() {
  return (
    <MarketProvider>
      <Dashboard />
    </MarketProvider>
  );
}
