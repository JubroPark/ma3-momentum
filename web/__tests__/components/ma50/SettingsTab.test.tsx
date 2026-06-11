import { render, screen, fireEvent } from '@testing-library/react';
import SettingsTab from '@/components/ma50/SettingsTab';
import type { SignalsJson } from '@/types/signals';

const mockData: SignalsJson = {
  as_of: '2026-06-09',
  regime: 'RISK_ON',
  items: [],
};

jest.mock('@/hooks/useSignals', () => ({
  useSignals: () => ({
    data: mockData,
    error: null,
    isLoading: false,
  }),
}));

test('RISK_OFF 모드 토글이 렌더된다', () => {
  render(<SettingsTab />);
  expect(screen.getByText('차단')).toBeInTheDocument();
  expect(screen.getByText('완화')).toBeInTheDocument();
});

test('파라미터 기본값이 표시된다', () => {
  render(<SettingsTab />);
  expect(screen.getByText('1.5x')).toBeInTheDocument();
  expect(screen.getByText('20일')).toBeInTheDocument();
});

test('차단→완화 토글 전환이 작동한다', () => {
  render(<SettingsTab />);
  const softBtn = screen.getByText('완화');
  fireEvent.click(softBtn);
  expect(softBtn).toHaveClass('on');
});
