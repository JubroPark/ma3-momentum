import { render, screen, fireEvent } from '@testing-library/react';
import AppShell from '@/components/AppShell';

jest.mock('@/hooks/useSignals', () => ({
  useSignals: () => ({ data: null, error: null, isLoading: false }),
}));

jest.mock('@/hooks/useMasam', () => ({
  useMasam: () => ({ data: null, error: null, isLoading: false }),
}));

test('전략 토글 버튼이 두 개 렌더된다', () => {
  render(<AppShell />);
  expect(screen.getByText('마삼 대응')).toBeInTheDocument();
  expect(screen.getByText('MA50 스크리너')).toBeInTheDocument();
});

test('기본값은 MA50 스크리너다', () => {
  render(<AppShell />);
  const ma50Btn = screen.getByText('MA50 스크리너');
  expect(ma50Btn).toHaveClass('on');
});

test('마삼 대응 클릭 시 마삼 탭이 표시된다', () => {
  render(<AppShell />);
  fireEvent.click(screen.getByText('마삼 대응'));
  expect(screen.getByText('현재 국면')).toBeInTheDocument();
  expect(screen.getByText('행동 가이드')).toBeInTheDocument();
});

test('면책 문구가 항상 표시된다', () => {
  render(<AppShell />);
  expect(screen.getByText(/투자 권유 아님/)).toBeInTheDocument();
});
