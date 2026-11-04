// 페어픽 서비스 워커: 웹 푸시를 받아 알림으로 띄우고, 누르면 해당 페이지를 연다.
// 화면 캐시(오프라인)는 하지 않는다. 배포마다 새 파일이 바로 쓰이도록 Nginx 가 이 파일은 캐시하지 않는다.

self.addEventListener('install', () => self.skipWaiting())
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()))

self.addEventListener('push', (event) => {
  let data = {}
  try {
    data = event.data ? event.data.json() : {}
  } catch {
    data = { body: event.data ? event.data.text() : '' }
  }
  const title = data.title || '페어픽'
  event.waitUntil(
    self.registration.showNotification(title, {
      body: data.body || '',
      tag: data.tag, // 같은 tag 는 알림 하나로 합쳐진다
      icon: '/favicon.svg',
      data: { url: data.url || '/' },
    }),
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  // 같은 사이트 안의 경로만 연다
  const path = event.notification.data?.url || '/'
  const url = new URL(path.startsWith('/') ? path : '/', self.location.origin).href
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((wins) => {
      const open = wins.find((w) => w.url.startsWith(self.location.origin))
      if (open) {
        open.focus()
        return open.navigate(url)
      }
      return self.clients.openWindow(url)
    }),
  )
})
