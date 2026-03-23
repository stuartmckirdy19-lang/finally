"use client";

import { useEffect, useRef } from "react";
import { useMarket } from "../context/MarketContext";
import { createChart, IChartApi, ISeriesApi, LineSeries } from "lightweight-charts";

export default function MainChart() {
  const { selectedTicker, chartHistory, prices } = useMarket();
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Line"> | null>(null);

  // Create chart once
  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { color: "#0d1117" },
        textColor: "#8b949e",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "rgba(45, 45, 61, 0.3)" },
        horzLines: { color: "rgba(45, 45, 61, 0.3)" },
      },
      crosshair: {
        vertLine: { color: "rgba(32, 157, 215, 0.3)" },
        horzLine: { color: "rgba(32, 157, 215, 0.3)" },
      },
      rightPriceScale: {
        borderColor: "#2d2d3d",
      },
      timeScale: {
        borderColor: "#2d2d3d",
        timeVisible: true,
        secondsVisible: false,
      },
    });

    const series = chart.addSeries(LineSeries, {
      color: "#209dd7",
      lineWidth: 2,
      priceFormat: { type: "price", precision: 2, minMove: 0.01 },
    });

    chartRef.current = chart;
    seriesRef.current = series;

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
        });
      }
    };

    const ro = new ResizeObserver(handleResize);
    ro.observe(containerRef.current);
    handleResize();

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  // Update data when ticker or history changes
  useEffect(() => {
    if (!seriesRef.current) return;

    const history = chartHistory.get(selectedTicker) || [];
    const data = history.map((p) => ({
      time: (p.time / 1000) as import("lightweight-charts").UTCTimestamp,
      value: p.price,
    }));

    seriesRef.current.setData(data);

    if (chartRef.current && data.length > 0) {
      chartRef.current.timeScale().fitContent();
    }
  }, [selectedTicker, chartHistory]);

  const priceEntry = prices.get(selectedTicker);
  const currentPrice = priceEntry?.price;
  const direction = priceEntry?.direction;

  return (
    <div className="flex flex-col h-full bg-bg-primary">
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-border">
        <div className="flex items-center gap-2">
          <span className="text-accent-yellow font-bold text-sm">
            {selectedTicker}
          </span>
          {currentPrice !== undefined && (
            <span
              className={`text-sm font-semibold tabular-nums ${
                direction === "up"
                  ? "text-profit"
                  : direction === "down"
                    ? "text-loss"
                    : "text-text-primary"
              }`}
            >
              ${currentPrice.toFixed(2)}
            </span>
          )}
        </div>
        <span className="text-text-muted text-[10px] uppercase tracking-wider">
          Price Chart
        </span>
      </div>
      <div ref={containerRef} className="flex-1" />
    </div>
  );
}
