"use client";

import { useState } from "react";
import { useMarket } from "../context/MarketContext";

interface TradeBarProps {
  onTradeComplete: () => void;
}

export default function TradeBar({ onTradeComplete }: TradeBarProps) {
  const { selectedTicker } = useMarket();
  const [ticker, setTicker] = useState("");
  const [quantity, setQuantity] = useState("");
  const [status, setStatus] = useState<{
    message: string;
    type: "success" | "error";
  } | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const activeTicker = ticker.trim().toUpperCase() || selectedTicker;

  const executeTrade = async (side: "buy" | "sell") => {
    const qty = parseFloat(quantity);
    if (!activeTicker || isNaN(qty) || qty <= 0) {
      setStatus({ message: "Enter a valid ticker and quantity", type: "error" });
      return;
    }

    setSubmitting(true);
    setStatus(null);

    try {
      const res = await fetch("/api/portfolio/trade", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticker: activeTicker,
          quantity: qty,
          side,
        }),
      });
      const data = await res.json();

      if (res.ok && (data.success !== false)) {
        setStatus({
          message: `${side.toUpperCase()} ${qty} ${activeTicker} @ $${data.price?.toFixed(2) ?? "N/A"}`,
          type: "success",
        });
        setQuantity("");
        onTradeComplete();
      } else {
        setStatus({
          message: data.message || data.detail || "Trade failed",
          type: "error",
        });
      }
    } catch {
      setStatus({ message: "Network error", type: "error" });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex items-center gap-2 px-3 py-2 bg-bg-tertiary border-t border-border">
      <input
        type="text"
        value={ticker}
        onChange={(e) => setTicker(e.target.value)}
        placeholder={selectedTicker}
        className="w-20 bg-bg-secondary text-text-primary text-xs px-2 py-1.5 rounded border border-border focus:border-blue-primary focus:outline-none placeholder:text-text-muted/50 uppercase"
      />
      <input
        type="number"
        value={quantity}
        onChange={(e) => setQuantity(e.target.value)}
        placeholder="Qty"
        step="0.01"
        min="0"
        className="w-20 bg-bg-secondary text-text-primary text-xs px-2 py-1.5 rounded border border-border focus:border-blue-primary focus:outline-none placeholder:text-text-muted/50 tabular-nums"
      />
      <button
        onClick={() => executeTrade("buy")}
        disabled={submitting}
        className="px-3 py-1.5 bg-blue-primary text-white text-xs font-semibold rounded hover:opacity-80 disabled:opacity-40 transition-opacity"
      >
        BUY
      </button>
      <button
        onClick={() => executeTrade("sell")}
        disabled={submitting}
        className="px-3 py-1.5 bg-purple-secondary text-white text-xs font-semibold rounded hover:opacity-80 disabled:opacity-40 transition-opacity"
      >
        SELL
      </button>
      {status && (
        <span
          className={`text-xs truncate ${
            status.type === "success" ? "text-profit" : "text-loss"
          }`}
        >
          {status.message}
        </span>
      )}
    </div>
  );
}
