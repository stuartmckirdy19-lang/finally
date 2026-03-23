"use client";

import { useMarket } from "../context/MarketContext";
import { Portfolio } from "../types";

interface HeaderProps {
  portfolio: Portfolio | null;
}

export default function Header({ portfolio }: HeaderProps) {
  const { connectionStatus } = useMarket();

  const totalValue = portfolio?.total_value ?? 10000;
  const cash = portfolio?.cash_balance ?? 10000;
  const pnl = totalValue - 10000;
  const pnlPercent = ((pnl / 10000) * 100).toFixed(2);

  const statusColor =
    connectionStatus === "connected"
      ? "bg-profit"
      : connectionStatus === "connecting"
        ? "bg-accent-yellow"
        : "bg-loss";

  const statusLabel =
    connectionStatus === "connected"
      ? "LIVE"
      : connectionStatus === "connecting"
        ? "CONNECTING"
        : "OFFLINE";

  return (
    <header className="flex items-center justify-between px-4 py-2 bg-bg-tertiary border-b border-border h-12 shrink-0">
      <div className="flex items-center gap-3">
        <h1 className="text-accent-yellow font-bold text-lg tracking-wider">
          FinAlly
        </h1>
        <span className="text-text-muted text-xs hidden sm:inline">
          AI Trading Terminal
        </span>
      </div>

      <div className="flex items-center gap-6">
        <div className="flex items-center gap-4 text-sm">
          <div className="flex flex-col items-end">
            <span className="text-text-muted text-[10px] uppercase tracking-wider">
              Portfolio
            </span>
            <span
              className={`text-base font-bold tabular-nums ${
                pnl > 0
                  ? "text-profit"
                  : pnl < 0
                    ? "text-loss"
                    : "text-text-primary"
              }`}
            >
              ${totalValue.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
          <div className="flex flex-col items-end">
            <span className="text-text-muted text-[10px] uppercase tracking-wider">
              P&L
            </span>
            <span
              className={`text-sm tabular-nums ${
                pnl > 0
                  ? "text-profit"
                  : pnl < 0
                    ? "text-loss"
                    : "text-text-muted"
              }`}
            >
              {pnl >= 0 ? "+" : ""}
              {pnlPercent}%
            </span>
          </div>
          <div className="flex flex-col items-end">
            <span className="text-text-muted text-[10px] uppercase tracking-wider">
              Cash
            </span>
            <span className="text-sm text-text-primary tabular-nums">
              ${cash.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <div
          className={`w-2 h-2 rounded-full ${statusColor} ${connectionStatus === "connecting" ? "status-pulse" : ""}`}
        />
        <span className="text-text-muted text-xs">{statusLabel}</span>
      </div>
    </header>
  );
}
