import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Ma3 Momentum',
  description: '마삼룰·모멘텀 투자 모니터링',
  manifest: '/manifest.json',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  )
}
