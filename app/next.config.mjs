import withPWAInit from '@ducanh2912/next-pwa'

const withPWA = withPWAInit({
  dest: 'public',
  disable: process.env.NODE_ENV === 'development',
  // app.html도 precache 대상에서 제외 — 아래 runtimeCaching으로 항상 네트워크 우선 처리
  exclude: [/\/data\/.*\.json$/, /^app\.html$/],
  runtimeCaching: [
    {
      urlPattern: /\/data\/.*\.json$/,
      handler: 'NetworkFirst',
      options: { cacheName: 'data-cache', expiration: { maxAgeSeconds: 60 * 60 } },
    },
    {
      // 앱 셸(app.html)이 예전 빌드로 precache된 채 굳어버려 새로고침해도 안 바뀌던 문제 방지.
      // 네트워크 우선 시도(5초 타임아웃) 후 실패 시에만 캐시 폴백.
      urlPattern: ({ request, url }) => request.mode === 'navigate' || url.pathname === '/app.html' || url.pathname === '/',
      handler: 'NetworkFirst',
      options: { cacheName: 'html-cache', networkTimeoutSeconds: 5, expiration: { maxAgeSeconds: 60 * 60 } },
    },
  ],
})

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async redirects() {
    return [
      { source: '/', destination: '/app.html', permanent: false },
    ]
  },
}

export default withPWA(nextConfig)
