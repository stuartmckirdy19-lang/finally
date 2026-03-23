"use client";

import { Treemap, ResponsiveContainer } from "recharts";
import { Portfolio } from "../types";
import { useMarket } from "../context/MarketContext";

interface PortfolioHeatmapProps {
  portfolio: Portfolio | null;
}

interface TreemapNode {
  name: string;
  size: number;
  pnlPercent: number;
  fill: string;
  [key: string]: string | number;
}

function getPnlColor(pnlPercent: number): string {
  if (pnlPercent > 5) return "#00c853";
  if (pnlPercent > 2) return "#00a844";
  if (pnlPercent > 0.5) return "#2d6b3f";
  if (pnlPercent > -0.5) return "#3d3d4d";
  if (pnlPercent > -2) return "#8b2232";
  if (pnlPercent > -5) return "#c41230";
  return "#ff1744";
}

interface CustomContentProps {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  name?: string;
  pnlPercent?: number;
}

function CustomContent({ x = 0, y = 0, width = 0, height = 0, name, pnlPercent = 0 }: CustomContentProps) {
  if (width < 10 || height < 10) return null;
  const fill = getPnlColor(pnlPercent);

  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        fill={fill}
        stroke="#0d1117"
        strokeWidth={2}
        rx={3}
      />
      {width > 35 && height > 20 && (
        <>
          <text
            x={x + width / 2}
            y={y + height / 2 - 5}
            textAnchor="middle"
            fill="#e6edf3"
            fontSize={Math.min(11, width / 5)}
            fontWeight="bold"
            fontFamily="monospace"
          >
            {name}
          </text>
          <text
            x={x + width / 2}
            y={y + height / 2 + 9}
            textAnchor="middle"
            fill={pnlPercent >= 0 ? "#00c853" : "#ff1744"}
            fontSize={Math.min(9, width / 6)}
            fontFamily="monospace"
          >
            {pnlPercent >= 0 ? "+" : ""}
            {pnlPercent.toFixed(1)}%
          </text>
        </>
      )}
    </g>
  );
}

export default function PortfolioHeatmap({
  portfolio,
}: PortfolioHeatmapProps) {
  const { prices } = useMarket();

  if (!portfolio || portfolio.positions.length === 0) {
    return (
      <div className="flex flex-col h-full bg-bg-primary">
        <div className="px-3 py-1.5 border-b border-border">
          <span className="text-text-muted text-[10px] uppercase tracking-wider">
            Portfolio Heatmap
          </span>
        </div>
        <div className="flex-1 flex items-center justify-center text-text-muted text-xs">
          No positions yet
        </div>
      </div>
    );
  }

  const data: TreemapNode[] = portfolio.positions.map((pos) => {
    const livePrice = prices.get(pos.ticker)?.price ?? pos.current_price ?? pos.avg_cost;
    const marketValue = livePrice * pos.quantity;
    const pnlPercent = ((livePrice - pos.avg_cost) / pos.avg_cost) * 100;
    return {
      name: pos.ticker,
      size: Math.max(marketValue, 1),
      pnlPercent,
      fill: getPnlColor(pnlPercent),
    };
  });

  return (
    <div className="flex flex-col h-full bg-bg-primary">
      <div className="px-3 py-1.5 border-b border-border">
        <span className="text-text-muted text-[10px] uppercase tracking-wider">
          Portfolio Heatmap
        </span>
      </div>
      <div className="flex-1 min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <Treemap
            data={data}
            dataKey="size"
            stroke="#0d1117"
            content={<CustomContent />}
            isAnimationActive={false}
          />
        </ResponsiveContainer>
      </div>
    </div>
  );
}
