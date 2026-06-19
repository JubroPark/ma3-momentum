import type { Metadata } from 'next'
import './globals.css'
import { AppProvider } from '@/shared/context/AppContext'

export const metadata: Metadata = {
  title: 'Ma3 Momentum',
  description: '마삼룰·모멘텀 투자 모니터링',
  manifest: '/manifest.json',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <head>
        <link
          rel="stylesheet"
          as="style"
          crossOrigin="anonymous"
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.min.css"
        />
        <script src="https://code.iconify.design/3/3.1.1/iconify.min.js" async />
      </head>
      <body>
        <AppProvider>
          <div className="w-full h-full max-w-app mx-auto bg-bg flex flex-col shadow-2xl">
            {children}
          </div>
        </AppProvider>
      </body>
    </html>
  )
}
