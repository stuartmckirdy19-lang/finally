export interface PriceData {
  ticker: string;
  price: number;
  prevPrice: number;
  direction: "up" | "down" | "flat";
  timestamp: string;
}

export interface SparklinePoint {
  price: number;
}

export interface ChartPoint {
  time: number;
  price: number;
}

export interface Position {
  ticker: string;
  quantity: number;
  avg_cost: number;
  current_price?: number;
  unrealized_pnl?: number;
  pnl_pct?: number;
}

export interface Portfolio {
  cash_balance: number;
  total_value: number;
  positions: Position[];
  unrealized_pnl: number;
}

export interface WatchlistItem {
  ticker: string;
  price?: number;
  change_percent?: number;
}

export interface TradeRequest {
  ticker: string;
  quantity: number;
  side: "buy" | "sell";
}

export interface TradeResult {
  success: boolean;
  message: string;
  ticker?: string;
  side?: string;
  quantity?: number;
  price?: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
  actions?: ChatAction[];
}

export interface ChatAction {
  type: "trade" | "watchlist";
  success: boolean;
  message: string;
}

export interface ChatResponse {
  message: string;
  trades?: { ticker: string; side: string; quantity: number }[];
  watchlist_changes?: { ticker: string; action: string }[];
  actions?: ChatAction[];
}

export interface PortfolioSnapshot {
  total_value: number;
  recorded_at: string;
}

export type ConnectionStatus = "connected" | "connecting" | "disconnected";
