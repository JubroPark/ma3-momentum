import type { Metadata, Viewport } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'ma3 momentum',
  description: '나스닥 마삼룰 · 모멘텀 탑픽',
  manifest: '/manifest.json',
};

export const viewport: Viewport = {
  themeColor: '#16161a',
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
