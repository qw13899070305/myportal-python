/**
 * Service Worker：只缓存静态资源。
 *
 * 关键点：
 * - 绝不缓存 /api 请求（否则登录态错乱、数据不更新）
 * - 页面导航使用 network-first，保证部署新版本后刷新即可生效
 * - 静态资源使用 stale-while-revalidate
 *
 * 注册在 src/main.js 中完成，且只在生产构建里注册。
 */
const CACHE_NAME = 'myportal-static-v1'
const PRECACHE = ['/', '/index.html', '/manifest.json', '/icon.svg']

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE))
      .then(() => self.skipWaiting()),
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((names) =>
        Promise.all(
          names.filter((name) => name !== CACHE_NAME).map((name) => caches.delete(name)),
        ),
      )
      .then(() => self.clients.claim()),
  )
})

self.addEventListener('fetch', (event) => {
  const { request } = event

  // 只处理同源 GET
  if (request.method !== 'GET') return
  const url = new URL(request.url)
  if (url.origin !== self.location.origin) return

  // 接口与实时通信一律走网络，不缓存
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/ws/')) return

  // 页面导航：network-first
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() =>
        caches.match('/index.html').then((cached) => cached || Response.error()),
      ),
    )
    return
  }

  // 其他静态资源：stale-while-revalidate
  event.respondWith(
    caches.match(request).then((cached) => {
      const network = fetch(request)
        .then((response) => {
          if (response && response.status === 200 && response.type === 'basic') {
            const clone = response.clone()
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone))
          }
          return response
        })
        .catch(() => cached || Response.error())
      return cached || network
    }),
  )
})
