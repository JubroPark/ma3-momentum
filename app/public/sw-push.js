// Push 이벤트 핸들러 (app.html 전용 서비스워커)
self.addEventListener('install', () => self.skipWaiting())
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()))

// 데이터 JSON 캐시 (NetworkFirst)
self.addEventListener('fetch', event => {
  if (event.request.url.includes('/data/') && event.request.url.endsWith('.json')) {
    event.respondWith(
      fetch(event.request)
        .then(res => {
          const clone = res.clone()
          caches.open('ma3-data').then(c => c.put(event.request, clone))
          return res
        })
        .catch(() => caches.match(event.request))
    )
  }
})

self.addEventListener('push', event => {
  const data = event.data ? event.data.json() : {}
  const title = data.title || '마삼룰 & 모멘텀'
  const options = {
    body: data.body || '',
    icon: '/icon-192.png',
    badge: '/icon-192.png',
    tag: data.tag || 'ma3-alert',
    data: { url: data.url || '/app.html' },
    requireInteraction: data.requireInteraction || false,
  }
  event.waitUntil(self.registration.showNotification(title, options))
})

self.addEventListener('notificationclick', event => {
  event.notification.close()
  const url = event.notification.data?.url || '/app.html'
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
      const existing = list.find(c => c.url.includes('app.html'))
      if (existing) return existing.focus()
      return clients.openWindow(url)
    })
  )
})
