import { render, screen } from '@testing-library/react';
import Home from '@/app/page';

jest.mock('@/hooks/useSignals', () => ({
  useSignals: () => ({ data: null, error: null, isLoading: true }),
}));

test('앱이 크래시 없이 렌더된다', () => {
  render(<Home />);
  expect(document.body).toBeInTheDocument();
});
