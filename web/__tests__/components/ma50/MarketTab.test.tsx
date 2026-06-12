import { render, screen } from '@testing-library/react';
import MarketTab from '@/components/ma50/MarketTab';

jest.mock('@/hooks/useMarket', () => ({
  useMarket: () => ({
    data: {
      as_of: '2026-06-09', regime: 'RISK_ON', vix: 18.5,
      rate_env: 'NON_ZERO', dff: 5.33, qe_active: false, qe_state: 'QE_OFF',
      fear_greed: null, pmi: null,
    },
    error: null, isLoading: false,
  }),
}));

test('핵심 지표 섹션이 렌더된다', () => {
  render(<MarketTab />);
  expect(screen.getByText('핵심 지표')).toBeInTheDocument();
});

test('VIX 값이 표시된다', () => {
  render(<MarketTab />);
  expect(screen.getByText('18.5')).toBeInTheDocument();
});

test('레짐이 RISK ON으로 표시된다', () => {
  render(<MarketTab />);
  expect(screen.getByText('RISK ON')).toBeInTheDocument();
});
