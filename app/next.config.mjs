import withPWAInit from '@ducanh2912/next-pwa'

const withPWA = withPWAInit({
  dest: 'public',
  disable: process.env.NODE_ENV === 'development',
  runtimeCaching: [
    {
      urlPattern: /\/data\/.*\.json$/,
      handler: 'NetworkFirst',
      options: { cacheName: 'data-cache', expiration: { maxAgeSeconds: 60 * 60 } },
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
