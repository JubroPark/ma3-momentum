import { renderHook, waitFor } from '@testing-library/react'
import { useMasamData } from './useData'

global.fetch = jest.fn(() =>
  Promise.resolve({ json: () => Promise.resolve({ as_of: '2026-06-18', mode: 'NORMAL' }) })
) as jest.Mock

test('useMasamData returns data', async () => {
  const { result } = renderHook(() => useMasamData())
  await waitFor(() => expect(result.current.data).toBeDefined())
  expect(result.current.data?.as_of).toBe('2026-06-18')
})
