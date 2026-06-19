import { render, screen, fireEvent } from '@testing-library/react'
import { StrategyToggle } from './StrategyToggle'
import { AppProvider } from '../context/AppContext'

test('모멘텀 버튼 클릭 시 전략 전환', () => {
  render(<AppProvider><StrategyToggle /></AppProvider>)
  fireEvent.click(screen.getByText('모멘텀'))
  // localStorage에 저장됐는지 확인
  expect(localStorage.getItem('strategy')).toBe('momentum')
})
