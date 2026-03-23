"use client";

import { useState, useRef, useEffect } from "react";
import { useMarket } from "../context/MarketContext";
import { WatchlistItem } from "../types";
import Sparkline from "./Sparkline";
import { Plus, X } from "lucide-react";

interface WatchlistProps {
  watchlist: WatchlistItem[];
  onAdd: (ticker: string) => Promise<boolean>;
  onRemove: (ticker: string) => Promise<boolean>;
}

export default function Watchlist({
  watchlist,
  onAdd,
  onRemove,
}: WatchlistProps) {
  const { prices, sparklines, selectedTicker, setSelectedTicker } =
    useMarket();
  const [newTicker, setNewTicker] = useState("");
  const [adding, setAdding] = useState(false);
  const flashRefs = useRef<Map<string, number>>(new Map());
  const [flashStates, setFlashStates] = useState<
    Map<string, "up" | "down" | null>
  >(new Map());

  // Track price flash animations
  useEffect(() => {
    const newFlashes = new Map<string, "up" | "down" | null>();
    let changed = false;
    for (const [ticker, entry] of prices) {
      const prevKey = flashRefs.current.get(ticker);
      if (prevKey !== undefined && prevKey !== entry.flashKey) {
        newFlashes.set(
          ticker,
          entry.direction === "up"
            ? "up"
            : entry.direction === "down"
              ? "down"
              : null
        );
        changed = true;
      }
      flashRefs.current.set(ticker, entry.flashKey);
    }
    if (changed) {
      setFlashStates((prev) => {
        const next = new Map(prev);
        for (const [t, d] of newFlashes) next.set(t, d);
        return next;
      });
      setTimeout(() => {
        setFlashStates(new Map());
      }, 500);
    }
  }, [prices]);

  const handleAdd = async () => {
    const t = newTicker.trim().toUpperCase();
    if (!t) return;
    setAdding(true);
    await onAdd(t);
    setNewTicker("");
    setAdding(false);
  };

  return (
    <div className="flex flex-col h-full bg-bg-primary">
      <div className="px-3 py-2 border-b border-border">
        <h2 className="text-xs font-semibold text-text-muted uppercase tracking-wider">
          Watchlist
        </h2>
      </div>

      <div className="flex-1 overflow-y-auto">
        {watchlist.map((item) => {
          const ticker = item.ticker;
          const priceEntry = prices.get(ticker);
          const currentPrice = priceEntry?.price;
          const sparkData = sparklines.get(ticker) || [];
          const flash = flashStates.get(ticker);
          const isSelected = selectedTicker === ticker;

          const seedPrice = sparkData.length > 0 ? sparkData[0] : undefined;
          const changePercent =
            seedPrice && currentPrice
              ? ((currentPrice - seedPrice) / seedPrice) * 100
              : 0;

          return (
            <div
              key={ticker}
              onClick={() => setSelectedTicker(ticker)}
              className={`group flex items-center px-3 py-1.5 cursor-pointer border-b border-border/50 transition-colors hover:bg-bg-secondary/50 ${
                isSelected ? "bg-bg-secondary border-l-2 border-l-accent-yellow" : ""
              } ${
                flash === "up"
                  ? "price-flash-up"
                  : flash === "down"
                    ? "price-flash-down"
                    : ""
              }`}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <span className="text-accent-yellow font-bold text-xs">
                    {ticker}
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onRemove(ticker);
                    }}
                    className="opacity-0 group-hover:opacity-100 text-text-muted hover:text-loss transition-opacity ml-1"
                  >
                    <X size={12} />
                  </button>
                </div>
                <div className="flex items-center justify-between mt-0.5">
                  <span className="text-text-primary text-xs tabular-nums">
                    {currentPrice
                      ? `$${currentPrice.toFixed(2)}`
                      : "--"}
                  </span>
                  <span
                    className={`text-[10px] tabular-nums ${
                      changePercent > 0
                        ? "text-profit"
                        : changePercent < 0
                          ? "text-loss"
                          : "text-text-muted"
                    }`}
                  >
                    {changePercent > 0 ? "+" : ""}
                    {changePercent.toFixed(2)}%
                  </span>
                </div>
              </div>
              <div className="ml-2 shrink-0">
                <Sparkline data={sparkData} width={60} height={20} />
              </div>
            </div>
          );
        })}
      </div>

      <div className="px-2 py-2 border-t border-border">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleAdd();
          }}
          className="flex gap-1"
        >
          <input
            type="text"
            value={newTicker}
            onChange={(e) => setNewTicker(e.target.value)}
            placeholder="Add ticker"
            className="flex-1 bg-bg-secondary text-text-primary text-xs px-2 py-1 rounded border border-border focus:border-blue-primary focus:outline-none placeholder:text-text-muted/50"
          />
          <button
            type="submit"
            disabled={adding || !newTicker.trim()}
            className="bg-blue-primary text-white p-1 rounded hover:opacity-80 disabled:opacity-30 transition-opacity"
          >
            <Plus size={14} />
          </button>
        </form>
      </div>
    </div>
  );
}
