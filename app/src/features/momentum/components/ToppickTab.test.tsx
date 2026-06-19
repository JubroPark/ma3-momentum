import { render, screen } from '@testing-library/react'
import { ToppickTab } from './ToppickTab'

jest.mock('@/shared/hooks/useData', () => ({
  useMomentumPositions: () => ({
    data: {
      as_of: '2026-06-18', regime: 'GREEN',
      items: [
        { symbol: 'NVDA', name: 'NVIDIA', status: 'ENTRY_2', toppick_score: 91,
          avg_price: 118.40, weight: 0.70, deployed_tranches: [1, 2],
          recent_high: 153.13, trailing_stop_line: 122.50, horizontal_support: 110.00,
          cooldown_until: null, next_action: 'HOLD', reason: '보유 중' }
      ]
    }
  }),
  useMomentumIndicators: () => ({
    data: {
      items: [
        { symbol: 'NVDA', price: 136.80, ma50: 128.40, ma200: 112.30,
          vol_ratio: 1.12, gap50_pct: 6.5, dist_to_stop_pct: 10.5 }
      ]
    }
  }),
}))

test('종목 카드가 렌더링된다', () => {
  render(<ToppickTab />)
  expect(screen.getByText('NVDA')).toBeInTheDocument()
})

test('탑픽 점수가 표시된다', () => {
  render(<ToppickTab />)
  expect(screen.getByText('91')).toBeInTheDocument()
})
