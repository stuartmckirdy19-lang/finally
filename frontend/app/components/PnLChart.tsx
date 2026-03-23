"use client";

import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";
import { PortfolioSnapshot } from "../types";

interface PnLChartProps {
  history: PortfolioSnapshot[];
}

export default function PnLChart({ history }: PnLChartProps) {
  const startValue = history.length > 0 ? history[0].total_value : 10000;
  const currentValue =
    history.length > 0 ? history[history.length - 1].total_value : 10000;
  const change = currentValue - startValue;
  const changePct = startValue > 0 ? (change / startValue) * 100 : 0;

  const data = history.map((s) => ({
    time: new Date(s.recorded_at).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    }),
    value: s.total_value,
  }));

  const isPositive = change >= 0;

  return (
    <div className="flex flex-col h-full bg-bg-primary">
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-border">
        <span className="text-text-muted text-[10px] uppercase tracking-wider">
          Portfolio Value
        </span>
        <div className="flex items-center gap-2">
          <span className="text-text-primary text-xs tabular-nums font-semibold">
            ${currentValue.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
          <span
            className={`text-[10px] tabular-nums ${
              isPositive ? "text-profit" : "text-loss"
            }`}
          >
            {isPositive ? "+" : ""}
            {changePct.toFixed(2)}%
          </span>
        </div>
      </div>
      <div className="flex-1 min-h-0">
        {data.length > 1 ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={data}
              margin={{ top: 5, right: 5, left: 5, bottom: 0 }}
            >
              <defs>
                <linearGradient id="pnlGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop
                    offset="0%"
                    stopColor={isPositive ? "#00c853" : "#ff1744"}
                    stopOpacity={0.3}
                  />
                  <stop
                    offset="100%"
                    stopColor={isPositive ? "#00c853" : "#ff1744"}
                    stopOpacity={0}
                  />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="time"
                tick={{ fontSize: 9, fill: "#8b949e" }}
                tickLine={false}
                axisLine={{ stroke: "#2d2d3d" }}
                interval="preserveStartEnd"
              />
              <YAxis
                tick={{ fontSize: 9, fill: "#8b949e" }}
                tickLine={false}
                axisLine={false}
                domain={["dataMin - 50", "dataMax + 50"]}
                tickFormatter={(v: number) => `$${v.toFixed(0)}`}
                width={55}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1a1a2e",
                  border: "1px solid #2d2d3d",
                  borderRadius: 4,
                  fontSize: 11,
                  color: "#e6edf3",
                }}
                formatter={(value) => [
                  `$${Number(value).toFixed(2)}`,
                  "Value",
                ]}
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke={isPositive ? "#00c853" : "#ff1744"}
                strokeWidth={1.5}
                fill="url(#pnlGrad)"
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex-1 flex items-center justify-center text-text-muted text-xs h-full">
            Collecting data...
          </div>
        )}
      </div>
    </div>
  );
}
