/* Service worker-ul aplicației pe telefon.
 * - interfața (index + fișierele din /assets) se păstrează local: aplicația pornește și fără internet;
 * - datele de lucru pe teren (rutele șoferului, comenzile echipei) se văd și fără internet — ultima variantă primită;
 * - restul API-ului merge doar prin rețea. La ieșirea din cont datele păstrate se șterg.
 */
const SHELL = 'crm-shell-v3'
const DATA = 'crm-data-v1'
const SHELL_URLS = ['/', '/m', '/manifest.webmanifest', '/favicon.svg', '/icons/icon-192.png']
const OFFLINE_DATA = ['/api/m/home/', '/api/m/driver/routes/', '/api/m/team/orders/']

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(SHELL).then((cache) => cache.addAll(SHELL_URLS)).then(() => self.skipWaiting()))
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== SHELL && k !== DATA).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  )
})

self.addEventListener('message', (event) => {
  if (event.data === 'logout') event.waitUntil(caches.delete(DATA))
})

async function networkFirst(request, cacheName, fallbackUrl) {
  const cache = await caches.open(cacheName)
  try {
    const response = await fetch(request)
    if (response.ok) cache.put(fallbackUrl || request, response.clone())
    return response
  } catch (err) {
    const cached = await cache.match(fallbackUrl || request, { ignoreVary: true })
    if (cached) return cached
    throw err
  }
}

async function cacheFirst(request) {
  const cache = await caches.open(SHELL)
  const cached = await cache.match(request)
  if (cached) return cached
  const response = await fetch(request)
  if (response.ok) cache.put(request, response.clone())
  return response
}

self.addEventListener('fetch', (event) => {
  const request = event.request
  if (request.method !== 'GET') return
  const url = new URL(request.url)
  if (url.origin !== self.location.origin) return
  if (url.pathname.startsWith('/__platform')) return // alegerea bazei (platforma) merge doar prin rețea
  if (request.mode === 'navigate') {
    // orice pagină a aplicației este același index.html
    event.respondWith(networkFirst(request, SHELL, '/'))
    return
  }
  if (url.pathname.startsWith('/assets/') || url.pathname.startsWith('/icons/')) {
    event.respondWith(cacheFirst(request))
    return
  }
  if (OFFLINE_DATA.some((p) => url.pathname === p) || /^\/api\/m\/team\/orders\/\d+\/$/.test(url.pathname)) {
    event.respondWith(networkFirst(request, DATA))
  }
})
