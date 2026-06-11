import { render, screen } from '@testing-library/react';
import HoldTab from '@/components/ma50/HoldTab';
import type { SignalsJson } from '@/types/signals';

const mockData: SignalsJson = {
  as_of: '2026-06-09',
  regime: 'RISK_ON',
  items: [
    {
      ticker: 'TSLA',
      signal_type: 'OK',
      state: 'HOLDING',
      score: 60,
      trigger_reason: '',
      metrics: {
        close: 250,
        ma50: 240,
        ma200: 220,
        gap50: 0.04,
        gap200: 0.09,
        vol_ratio: 1.2,
        rs_pct: 60,
        ma50_slope_pct: 0.01,
        high_n: 255,
        atr14: 5,
        sector_etf: 'XLY',
      },
    },
    {
      ticker: 'META',
      signal_type: 'SELL',
      state: 'SELL',
      score: 40,
      trigger_reason: '',
      metrics: {
        close: 500,
        ma50: 520,
        ma200: 480,
        gap50: -0.04,
        gap200: 0.083,
        vol_ratio: 1.1,
        rs_pct: 45,
        ma50_slope_pct: -0.01,
        high_n: 510,
        atr14: 8,
        sector_etf: 'XLC',
      },
    },
    {
      ticker: 'NVDA',
      signal_type: 'STRONG_BREAKOUT',
      state: 'WATCH',
      score: 88,
      trigger_reason: '',
      metrics: {
        close: 150,
        ma50: 140,
        ma200: 130,
        gap50: 0.07,
        gap200: 0.077,
        vol_ratio: 2.1,
        rs_pct: 93,
        ma50_slope_pct: 0.04,
        high_n: 148,
        atr14: 3.2,
        sector_etf: 'XLK',
      },
    },
  ],
};

jest.mock('@/hooks/useSignals', () => ({
  useSignals: () => ({ data: mockData, error: null, isLoading: false }),
}));

test('HOLDING/SELL 종목만 표시되고 WATCH 종목은 제외된다', () => {
  render(<HoldTab />);
  expect(screen.getByText('TSLA')).toBeInTheDocument();
  expect(screen.getByText('META')).toBeInTheDocument();
  expect(screen.queryByText('NVDA')).not.toBeInTheDocument();
});

test('SELL 상태 종목에 매도 권장 박스가 표시된다', () => {
  render(<HoldTab />);
  expect(screen.getByText(/매도 권장/)).toBeInTheDocument();
});
