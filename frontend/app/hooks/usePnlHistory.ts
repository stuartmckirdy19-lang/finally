"use client";

import { useState, useEffect, useCallback } from "react";
import { PortfolioSnapshot } from "../types";

const POLL_INTERVAL = 5000;

export function usePnlHistory() {
  const [history, setHistory] = useState<PortfolioSnapshot[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const res = await fetch("/api/portfolio/history");
      if (res.ok) {
        const data = await res.json();
        setHistory(Array.isArray(data) ? data : data.history || []);
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [refresh]);

  return { history, loading, refresh };
}
