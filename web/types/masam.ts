export type MasamMode = 'REBALANCING' | 'CRISIS_STAKING' | 'PANIC' | 'PANIC_EMERGENCY';

export type AllInCondition = {
  id: number;
  label: string;
  met: boolean;
  grade: '약' | '중' | '강';
};

export type MasamJson = {
  as_of: string;
  mode: MasamMode;
  panic_type: string | null;
  rate_env: 'ZERO' | 'NON_ZERO';
  qe_active: boolean;
  masam: {
    month_count: number;
    cumulative_count: number;
    last_masam_date: string;
  };
  leader_status: {
    rank1_ticker: string;
    rank1_mcap: number;
    rank2_ticker: string;
    rank2_mcap: number;
    gap_pct: number;
    overtake_detected: boolean;
    gap_below_10pct: boolean;
  };
  target_allocation: {
    stock_pct: number;
    hedge_pct: number;
    cash_pct: number;
    label: string;
  };
  hedge_allocation: {
    type: 'DOLLAR' | 'TLT' | 'IAU_GLD_TIP';
    rationale: string;
    exit_trigger: string;
  };
  distance_to_triggers: {
    v_allin_pct_needed: number;
    emergency_allin_pct_away: number;
  };
  all_in_conditions: AllInCondition[];
  additional_buy_signal: {
    rsi14: number | null;
    mfi14: number | null;
    both_below_50: boolean;
    label: string;
  };
  panic_reentry: {
    stage: number;
    next_tranche_pct: number;
    tranches: number[];
  };
  recommended_action: string;
  alerts: string[];
};
