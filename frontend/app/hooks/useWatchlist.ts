"use client";

import { useState, useEffect, useCallback } from "react";
import { WatchlistItem } from "../types";

export function useWatchlist() {
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const res = await fetch("/api/watchlist");
      if (res.ok) {
        const data = await res.json();
        const items = Array.isArray(data) ? data : data.tickers || [];
        setWatchlist(
          items.map((d: WatchlistItem | string) =>
            typeof d === "string" ? { ticker: d } : d
          )
        );
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const addTicker = useCallback(
    async (ticker: string) => {
      try {
        const res = await fetch("/api/watchlist", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ticker: ticker.toUpperCase() }),
        });
        if (res.ok) {
          await refresh();
          return true;
        }
      } catch {
        // ignore
      }
      return false;
    },
    [refresh]
  );

  const removeTicker = useCallback(
    async (ticker: string) => {
      try {
        const res = await fetch(`/api/watchlist/${ticker.toUpperCase()}`, {
          method: "DELETE",
        });
        if (res.ok) {
          await refresh();
          return true;
        }
      } catch {
        // ignore
      }
      return false;
    },
    [refresh]
  );

  return { watchlist, loading, refresh, addTicker, removeTicker };
}
