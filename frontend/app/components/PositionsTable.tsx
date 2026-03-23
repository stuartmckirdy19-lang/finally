"use client";

import { Portfolio } from "../types";
import { useMarket } from "../context/MarketContext";

interface PositionsTableProps {
  portfolio: Portfolio | null;
}

export default function PositionsTable({ portfolio }: PositionsTableProps) {
  const { prices } = useMarket();

  if (!portfolio || portfolio.positions.length === 0) {
    return (
      <div className="flex flex-col h-full bg-bg-primary">
        <div className="px-3 py-1.5 border-b border-border">
          <span className="text-text-muted text-[10px] uppercase tracking-wider">
            Positions
          </span>
        </div>
        <div className="flex-1 flex items-center justify-center text-text-muted text-xs">
          No positions yet
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-bg-primary">
      <div className="px-3 py-1.5 border-b border-border">
        <span className="text-text-muted text-[10px] uppercase tracking-wider">
          Positions
        </span>
      </div>
      <div className="flex-1 overflow-y-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-text-muted border-b border-border/50">
              <th className="text-left px-3 py-1 font-normal">Ticker</th>
              <th className="text-right px-2 py-1 font-normal">Qty</th>
              <th className="text-right px-2 py-1 font-normal">Avg Cost</th>
              <th className="text-right px-2 py-1 font-normal">Current</th>
              <th className="text-right px-2 py-1 font-normal">P&L</th>
              <th className="text-right px-3 py-1 font-normal">P&L%</th>
            </tr>
          </thead>
          <tbody>
            {portfolio.positions.map((pos) => {
              const livePrice =
                prices.get(pos.ticker)?.price ??
                pos.current_price ??
                pos.avg_cost;
              const pnl = (livePrice - pos.avg_cost) * pos.quantity;
              const pnlPct =
                ((livePrice - pos.avg_cost) / pos.avg_cost) * 100;
              const isPositive = pnl >= 0;

              return (
                <tr
                  key={pos.ticker}
                  className="border-b border-border/30 hover:bg-bg-secondary/30"
                >
                  <td className="px-3 py-1 text-accent-yellow font-semibold">
                    {pos.ticker}
                  </td>
                  <td className="px-2 py-1 text-right tabular-nums text-text-primary">
                    {pos.quantity}
                  </td>
                  <td className="px-2 py-1 text-right tabular-nums text-text-muted">
                    ${pos.avg_cost.toFixed(2)}
                  </td>
                  <td className="px-2 py-1 text-right tabular-nums text-text-primary">
                    ${livePrice.toFixed(2)}
                  </td>
                  <td
                    className={`px-2 py-1 text-right tabular-nums ${
                      isPositive ? "text-profit" : "text-loss"
                    }`}
                  >
                    {isPositive ? "+" : ""}${pnl.toFixed(2)}
                  </td>
                  <td
                    className={`px-3 py-1 text-right tabular-nums ${
                      isPositive ? "text-profit" : "text-loss"
                    }`}
                  >
                    {isPositive ? "+" : ""}
                    {pnlPct.toFixed(2)}%
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
