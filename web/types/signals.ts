export type SignalType =
  | 'EARLY_TREND'
  | 'STRONG_BREAKOUT'
  | 'BOUNCE'
  | 'SELL'
  | 'HOLD_WATCH'
  | 'OK';

export type TickerState =
  | 'WATCH'
  | 'BUY'
  | 'HOLDING'
  | 'SELL_WATCH'
  | 'SELL';

export type Metrics = {
  close: number;
  ma50: number;
  ma200: number;
  gap50: number;
  gap200: number;
  vol_ratio: number;
  rs_pct: number;
  rs_sector_pct?: number;
  ma50_slope_pct: number;
  high_n: number;
  atr14: number;
  sector_etf: string;
  trailing_stop?: number;
  recent_high?: number;
  horizontal_support?: number;
};

export type PositionStatus = '1차' | '2차' | '3차';

export type SignalItem = {
  ticker: string;
  signal_type: SignalType;
  state: TickerState;
  score: number;
  trigger_reason: string;
  metrics: Metrics;
  position_status?: PositionStatus;
};

export type SignalsJson = {
  as_of: string;
  regime: 'RISK_ON' | 'RISK_OFF';
  items: SignalItem[];
};

export type MasamJson = {
  as_of: string;
  mode: 'REBALANCING' | 'CRISIS_STAKING' | 'PANIC';
  [key: string]: unknown;
};
