export type RateEnv = 'ZERO' | 'NON_ZERO'
export type TreasuryTrend = 'DOWN' | 'UP' | 'UNKNOWN'
export type MasamMode = 'NORMAL' | 'CRISIS' | 'PANIC'
export type HedgeType = 'TLT' | 'IAU_GLD_TIP' | 'DOLLAR' | 'NONE'

export interface AllInCondition {
  id: number
  label: string
  met: boolean
  grade: '약' | '중' | '강'
  detail?: string
}

export interface MasamData {
  as_of: string
  mode: MasamMode
  rate_env: RateEnv
  qe_active: boolean
  treasury_10y_trend: TreasuryTrend
  masam: {
    month_count: number
    last_masam_date: string | null
    crisis_end_dday: number | null
    panic_end_dday: number | null
  }
  leader_status: {
    rank1_ticker: string
    rank2_ticker: string
    gap_pct: number
    overtake_detected: boolean
    gap_within_10pct: boolean
  }
  target_allocation: {
    stock_pct: number
    hedge_pct: number
    cash_pct: number
    label: string
  }
  hedge_allocation: {
    type: HedgeType
    rationale: string
    exit_trigger: string
  }
  rebalancing: {
    cash_raised_pct: number
    max_pct: number
    qqq_pct: number
  }
  staking: {
    rate_env: RateEnv
    grid_pct: number
    target_pct: number
    deployed_pct: number
  }
  all_in_conditions: AllInCondition[]
  additional_buy: {
    target: 'rank1' | 'QQQ'
    rsi14: number
    mfi14: number
    both_below_50: boolean
  }
  panic_hold: { active: boolean; until_new_high: boolean }
  panic_reentry: { stage: number; tranches: number[] }
  recommended_action: string
  alerts: string[]
}

export interface McapItem {
  rank: number
  ticker: string
  name: string
  mcap_usd: number
  gap_pct_from_rank1: number
  is_leader: boolean
}

export interface McapDaily {
  as_of: string
  rank1_ticker: string
  items: McapItem[]
}

export interface HedgePrices {
  as_of: string
  TLT: number
  IAU: number
  GLD: number
  TIP: number
}

export interface MasamMarket {
  as_of: string
  rate_env: RateEnv
  dff: number
  qe_active: boolean
  walcl_trend: 'UP' | 'DOWN' | 'UNKNOWN'
  treasury_10y: number
  treasury_10y_trend: TreasuryTrend
  vix?: number
  fear_greed?: number
  usd_krw?: number
}

export interface LiveData {
  as_of: string
  nasdaq: { price: number; change_pct: number; dist_to_masam_pct: number }
  rank1: { ticker: string; price: number; change_pct: number }
  hedges: { TLT: number; IAU: number; GLD: number; TIP: number }
}
