export type MarketJson = {
  as_of: string;
  regime: 'RISK_ON' | 'RISK_OFF';
  vix: number | null;
  rate_env: 'ZERO' | 'NON_ZERO' | null;
  dff: number | null;
  qe_active: boolean | null;
  qe_state: 'QE_ON' | 'QE_OFF' | 'AMBIGUOUS' | null;
  fear_greed: number | null;
  pmi: number | null;
};
