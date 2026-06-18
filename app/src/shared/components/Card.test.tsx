import { render, screen } from '@testing-library/react'
import { Card } from './Card'

test('Card renders children', () => {
  render(<Card>테스트 내용</Card>)
  expect(screen.getByText('테스트 내용')).toBeInTheDocument()
})
