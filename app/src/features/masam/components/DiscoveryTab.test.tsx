import { render, screen } from '@testing-library/react'
import { DiscoveryTab } from './DiscoveryTab'

jest.mock('@/shared/hooks/useData', () => ({
  useMasamData: () => ({
    data: {
      as_of: '2026-06-18', mode: 'NORMAL', rate_env: 'NON_ZERO',
      masam: { month_count: 0, last_masam_date: null, crisis_end_dday: null, panic_end_dday: null },
      leader_status: { rank1_ticker: 'NVDA', rank2_ticker: 'MSFT', gap_pct: 18.4, gap_within_10pct: false, overtake_detected: false },
      target_allocation: { stock_pct: 100, hedge_pct: 0, cash_pct: 0, label: '1등주 집중' },
      recommended_action: '리밸런싱 유지',
      all_in_conditions: [],
      panic_hold: { active: false, until_new_high: true },
    }
  }),
  useLiveData: () => ({
    data: { nasdaq: { price: 19842, change_pct: 0.84, dist_to_masam_pct: 2.18 }, rank1: { ticker: 'NVDA', price: 136.80, change_pct: 1.24 } }
  }),
  useMcapDaily: () => ({ data: null }),
}))

test('NORMAL 모드 배지가 렌더링된다', () => {
  render(<DiscoveryTab />)
  expect(screen.getByText('리밸런싱')).toBeInTheDocument()
})

test('추천 액션이 표시된다', () => {
  render(<DiscoveryTab />)
  expect(screen.getByText('리밸런싱 유지')).toBeInTheDocument()
})
