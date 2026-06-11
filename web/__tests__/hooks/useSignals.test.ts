import { renderHook, waitFor } from '@testing-library/react';
import { useSignals } from '@/hooks/useSignals';

const mockData = {
  as_of: '2026-06-09',
  regime: 'RISK_ON' as const,
  items: [
    {
      ticker: 'NVDA',
      signal_type: 'STRONG_BREAKOUT' as const,
      state: 'WATCH' as const,
      score: 88,
      trigger_reason: '',
      metrics: {
        close: 150, ma50: 140, ma200: 130,
        gap50: 0.07, vol_ratio: 2.1, rs_pct: 93,
        ma50_slope_pct: 0.04, high_n: 148, atr14: 3.2, sector_etf: 'XLK',
      },
    },
  ],
};

global.fetch = jest.fn(() =>
  Promise.resolve({ json: () => Promise.resolve(mockData) } as Response)
);

test('signals.json을 fetch해 데이터를 반환한다', async () => {
  const { result } = renderHook(() => useSignals());
  await waitFor(() => expect(result.current.isLoading).toBe(false));
  expect(result.current.data?.regime).toBe('RISK_ON');
  expect(result.current.data?.items[0].ticker).toBe('NVDA');
  expect(result.current.error).toBeUndefined();
});

test('fetch 실패 시 error를 반환한다', async () => {
  (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network Error'));
  const { result } = renderHook(() => useSignals());
  await waitFor(() => expect(result.current.isLoading).toBe(false));
  expect(result.current.error).toBeDefined();
});
