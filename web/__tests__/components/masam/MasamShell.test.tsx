import { render, screen, fireEvent } from '@testing-library/react';
import MasamShell from '@/components/masam/MasamShell';
import type { MasamJson } from '@/types/masam';

const mockData: MasamJson = {
  as_of: '2026-06-10',
  mode: 'CRISIS_STAKING',
  panic_type: null,
  rate_env: 'NON_ZERO',
  qe_active: false,
  masam: { month_count: 1, cumulative_count: 1, last_masam_date: '2026-06-05' },
  leader_status: {
    rank1_ticker: 'NVDA', rank1_mcap: 4.85e12,
    rank2_ticker: 'GOOGL', rank2_mcap: 4.35e12,
    gap_pct: 10.5, overtake_detected: false, gap_below_10pct: false,
  },
  target_allocation: { stock_pct: 10, hedge_pct: 0, cash_pct: 90, label: '말뚝박기 10%' },
  hedge_allocation: { type: 'DOLLAR', rationale: 'QE 모호', exit_trigger: 'QE 명확시 전환' },
  leader_prices: { ath: 235.47, current: 204.87, crisis_low: 199.34 },
  qqq_prices: { ath: 543.21, current: 510.00, crisis_low: 490.00 },
  distance_to_triggers: {
    v_allin_pct_needed: 10.0, v_allin_pct_away: 7.03,
    v_allin_trigger_price: 219.27, emergency_allin_pct_away: 24.29,
    emergency_trigger_price: 164.83,
  },
  all_in_conditions: [
    { id: 1, label: '한달+1일 무마삼', met: false, grade: '약' },
    { id: 2, label: '8거래일 연속 상승', met: false, grade: '중' },
    { id: 3, label: '1등주 전고 돌파', met: true, grade: '강' },
    { id: 4, label: '나스닥 전고 돌파', met: false, grade: '강' },
  ],
  additional_buy_signal: { rsi14: 33.2, mfi14: null, both_below_50: true, label: 'RSI14 ≤ 50 충족' },
  panic_reentry: { stage: 0, next_tranche_pct: 35, tranches: [35, 35, 30] },
  recommended_action: '말뚝박기 진입.',
  alerts: ['이번 달 마삼 1회'],
};

jest.mock('@/hooks/useMasam', () => ({
  useMasam: () => ({ data: mockData, error: null, isLoading: false }),
}));

jest.mock('@/hooks/useMarket', () => ({
  useMarket: () => ({
    data: {
      as_of: '2026-06-10', regime: 'RISK_ON', vix: 19.0,
      rate_env: 'NON_ZERO', dff: 5.33, qe_active: false, qe_state: 'QE_OFF',
      fear_greed: null, pmi: null,
    },
    error: null, isLoading: false,
  }),
}));

test('3개 탭 버튼이 렌더된다', () => {
  render(<MasamShell />);
  // 탭 버튼 + PhaseTab 헤딩에 모두 등장하므로 getAllByText 사용
  expect(screen.getAllByText('현재 국면').length).toBeGreaterThanOrEqual(1);
  expect(screen.getByText('행동 가이드')).toBeInTheDocument();
  expect(screen.getByText('시장환경/설정')).toBeInTheDocument();
});

test('기본 탭은 현재 국면이다 — 현재 모드가 표시된다', () => {
  render(<MasamShell />);
  expect(screen.getByText('위기대응 말뚝박기')).toBeInTheDocument();
});

test('행동 가이드 탭 클릭 시 올인 조건 체크리스트가 나타난다', () => {
  render(<MasamShell />);
  fireEvent.click(screen.getByText('행동 가이드'));
  expect(screen.getByText('올인 조건 체크리스트')).toBeInTheDocument();
});

test('시장환경/설정 탭 클릭 시 금리 환경이 나타난다', () => {
  render(<MasamShell />);
  fireEvent.click(screen.getByText('시장환경/설정'));
  expect(screen.getByText('금리 환경')).toBeInTheDocument();
});

test('CRISIS_STAKING 모드에서 PANIC_EMERGENCY 배너가 없다', () => {
  render(<MasamShell />);
  expect(screen.queryByText(/고점 -30% 몰빵 없음/)).not.toBeInTheDocument();
});

test('탭 전환 후 탭 내비게이션이 유지된다', () => {
  render(<MasamShell />);
  fireEvent.click(screen.getByText('행동 가이드'));
  // 다른 탭으로 전환해도 탭 버튼들은 유지됨
  expect(screen.getByText('시장환경/설정')).toBeInTheDocument();
});
