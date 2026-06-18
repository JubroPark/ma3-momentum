export type PositionStatus = 'WATCH' | 'ENTRY_1' | 'ENTRY_2' | 'ENTRY_3' | 'TRIM' | 'EXIT' | 'REMOVED'
export type ActionType = 'HOLD' | 'BUY_1' | 'BUY_2' | 'BUY_3' | 'TRIM_HALF' | 'EXIT'
export type Regime = 'GREEN' | 'YELLOW' | 'RED'
export type TrailMode = 'fixed' | 'atr' | 'hybrid'

export interface Position {
  symbol: string
  name: string
  status: PositionStatus
  toppick_score: number
  avg_price: number | null
  weight: number
  deployed_tranches: (1 | 2 | 3)[]
  recent_high: number | null
  trailing_stop_line: number | null
  horizontal_support: number | null
  cooldown_until: string | null
  next_action: ActionType
  reason: string
}

export interface Indicators {
  symbol: string
  date: string
  price: number
  ma50: number
  ma200: number
  atr14: number
  atr_pct: number
  recent_high: number
  horizontal_support: number | null
  vol20ma: number
  vol_ratio: number
  gap50_pct: number
  dist_to_stop_pct: number | null
}

export interface MomentumMarket {
  as_of: string
  regime: Regime
  spx: { close: number; ma50: number; ma200: number }
  ndx: { close: number; ma50: number; ma200: number }
  buy_gate: 'OPEN' | 'CAUTIOUS' | 'BLOCKED'
  vix?: number
  fear_greed?: number
}

export interface Params {
  masam: {
    rebalancing_max_pct: number
    appendix_z: Record<string, boolean>
  }
  momentum: {
    toppick_threshold: number
    max_symbols: number
    tranche_1: number
    tranche_2: number
    tranche_3: number
    reserve: number
    ma50_support_band: number
    trail_mode: TrailMode
    trail_fixed_pct: number
    trail_atr_mult: number
    trail_floor_pct: number
    trail_ceiling_pct: number
    vol_breakout_min: number
    vol_spike_warn: number
    cooldown_days: number
    rescore_cadence: 'monthly' | 'quarterly' | 'semiannual'
  }
}
