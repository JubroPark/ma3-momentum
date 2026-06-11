import { render, screen } from '@testing-library/react';
import MarketTab from '@/components/ma50/MarketTab';

jest.mock('@/hooks/useSignals', () => ({
  useSignals: () => ({
    data: { as_of: '2026-06-09', regime: 'RISK_ON', items: [] },
    error: null, isLoading: false,
  }),
}));

test('레짐 게이지가 렌더된다', () => {
  render(<MarketTab />);
  expect(screen.getByText('RISK_ON')).toBeInTheDocument();
});

test('RISK_ON 설명 문구가 표시된다', () => {
  render(<MarketTab />);
  expect(screen.getByText(/SPY가 200일선 위/)).toBeInTheDocument();
});
