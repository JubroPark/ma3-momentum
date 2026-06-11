import { renderHook, waitFor } from '@testing-library/react';
import { SWRConfig } from 'swr';
import React from 'react';
import { useMasam } from '@/hooks/useMasam';

const mockData = {
  as_of: '2026-06-10',
  mode: 'REBALANCING' as const,
};

const freshWrapper = ({ children }: { children: React.ReactNode }) =>
  React.createElement(SWRConfig, { value: { provider: () => new Map() } }, children);

beforeEach(() => {
  global.fetch = jest.fn(() =>
    Promise.resolve({ ok: true, json: () => Promise.resolve(mockData) } as Response)
  );
});

test('masam.json을 fetch해 데이터를 반환한다', async () => {
  const { result } = renderHook(() => useMasam(), { wrapper: freshWrapper });
  await waitFor(() => expect(result.current.isLoading).toBe(false));
  expect(result.current.data?.as_of).toBe('2026-06-10');
  expect(result.current.data?.mode).toBe('REBALANCING');
  expect(result.current.error).toBeUndefined();
});

test('fetch 실패 시 error를 반환한다', async () => {
  (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network Error'));
  const { result } = renderHook(() => useMasam(), { wrapper: freshWrapper });
  await waitFor(() => expect(result.current.error).toBeDefined());
});
