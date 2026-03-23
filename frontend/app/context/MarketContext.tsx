"use client";

import React, {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  useCallback,
} from "react";
import { PriceData, ConnectionStatus, ChartPoint } from "../types";

const MAX_SPARKLINE = 200;
const MAX_CHART_POINTS = 2000;

interface PriceEntry {
  price: number;
  prevPrice: number;
  direction: "up" | "down" | "flat";
  timestamp: string;
  flashKey: number;
}

interface MarketContextValue {
  prices: Map<string, PriceEntry>;
  sparklines: Map<string, number[]>;
  chartHistory: Map<string, ChartPoint[]>;
  connectionStatus: ConnectionStatus;
  selectedTicker: string;
  setSelectedTicker: (t: string) => void;
}

const MarketContext = createContext<MarketContextValue>({
  prices: new Map(),
  sparklines: new Map(),
  chartHistory: new Map(),
  connectionStatus: "connecting",
  selectedTicker: "AAPL",
  setSelectedTicker: () => {},
});

export function useMarket() {
  return useContext(MarketContext);
}

export function MarketProvider({ children }: { children: React.ReactNode }) {
  const [prices, setPrices] = useState<Map<string, PriceEntry>>(new Map());
  const [sparklines, setSparklines] = useState<Map<string, number[]>>(
    new Map()
  );
  const [chartHistory, setChartHistory] = useState<
    Map<string, ChartPoint[]>
  >(new Map());
  const [connectionStatus, setConnectionStatus] =
    useState<ConnectionStatus>("connecting");
  const [selectedTicker, setSelectedTicker] = useState("AAPL");
  const flashCounter = useRef(0);

  useEffect(() => {
    let es: EventSource | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    function connect() {
      setConnectionStatus("connecting");
      es = new EventSource("/api/stream/prices");

      es.onopen = () => {
        setConnectionStatus("connected");
      };

      es.onmessage = (event) => {
        try {
          const allPrices = JSON.parse(event.data) as Record<string, {
            ticker: string;
            price: number;
            previous_price: number;
            direction: "up" | "down" | "flat";
            timestamp: number;
          }>;
          const entries = Object.entries(allPrices);
          if (entries.length === 0) return;

          const now = Date.now();
          flashCounter.current += 1;
          const fk = flashCounter.current;

          setPrices((prev) => {
            const next = new Map(prev);
            for (const [ticker, data] of entries) {
              next.set(ticker, {
                price: data.price,
                prevPrice: data.previous_price ?? data.price,
                direction: data.direction ?? "flat",
                timestamp: String(data.timestamp),
                flashKey: fk,
              });
            }
            return next;
          });

          setSparklines((prev) => {
            const next = new Map(prev);
            for (const [ticker, data] of entries) {
              const arr = [...(prev.get(ticker) || []), data.price];
              if (arr.length > MAX_SPARKLINE) arr.shift();
              next.set(ticker, arr);
            }
            return next;
          });

          setChartHistory((prev) => {
            const next = new Map(prev);
            for (const [ticker, data] of entries) {
              const arr = [
                ...(prev.get(ticker) || []),
                { time: now, price: data.price },
              ];
              if (arr.length > MAX_CHART_POINTS) arr.shift();
              next.set(ticker, arr);
            }
            return next;
          });
        } catch {
          // ignore parse errors
        }
      };

      es.onerror = () => {
        setConnectionStatus("disconnected");
        es?.close();
        reconnectTimer = setTimeout(connect, 3000);
      };
    }

    connect();

    return () => {
      es?.close();
      if (reconnectTimer) clearTimeout(reconnectTimer);
    };
  }, []);

  const setSelected = useCallback((t: string) => setSelectedTicker(t), []);

  return (
    <MarketContext.Provider
      value={{
        prices,
        sparklines,
        chartHistory,
        connectionStatus,
        selectedTicker,
        setSelectedTicker: setSelected,
      }}
    >
      {children}
    </MarketContext.Provider>
  );
}
