/**
 * MiganCore Service Worker — Reliability Layer (Day 71c)
 *
 * Strategy:
 *   - HTML  → network-first, fallback to cache (always try fresh, survive offline)
 *   - Static assets (JS/CSS/fonts/img) → cache-first with stale-while-revalidate
 *   - API calls → network-only (never cache /v1/*, /chat/*, /sse/*)
 *
 * Versioning:
 *   - Bump CACHE_VERSION to invalidate old caches on next visit
 *   - Old caches deleted automatically on activate
 */

const CACHE_VERSION = 'v1.0.74a';
const CACHE_HTML = `migancore-html-${CACHE_VERSION}`;
const CACHE_ASSETS = `migancore-assets-${CACHE_VERSION}`;

// Pre-cache critical assets on install (best-effort, don't block install if any fail)
const PRECACHE_URLS = [
  '/chat.html',
  '/favicon.svg',
  '/favicon.ico',
  '/manifest.json',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_HTML).then(async (cache) => {
      // Use addAll-with-tolerance: don't fail entire install if one resource fails
      await Promise.all(
        PRECACHE_URLS.map((url) =>
          cache.add(url).catch((err) => console.warn('[SW] precache miss:', url, err))
        )
      );
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(
        keys
          .filter((k) => k.startsWith('migancore-') && !k.includes(CACHE_VERSION))
          .map((k) => caches.delete(k))
      );
      await self.clients.claim();
    })()
  );
});

// Fetch strategy router
self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return; // Only intercept GET

  const url = new URL(req.url);

  // Skip API/SSE/streaming endpoints — never cache live data
  if (
    url.pathname.startsWith('/v1/') ||
    url.pathname.startsWith('/chat/') ||
    url.pathname.startsWith('/sse/') ||
    url.pathname.startsWith('/admin/') ||
    url.pathname.startsWith('/api/') ||
    url.hostname === 'api.migancore.com'
  ) {
    return; // Let browser handle directly (no SW intervention)
  }

  // Skip cross-origin (fonts, CDN) — let browser cache normally with their own headers
  if (url.origin !== self.location.origin) {
    return;
  }

  // HTML → network-first
  const accept = req.headers.get('accept') || '';
  if (req.mode === 'navigate' || accept.includes('text/html')) {
    event.respondWith(networkFirst(req, CACHE_HTML));
    return;
  }

  // Static assets → cache-first with stale-while-revalidate
  event.respondWith(cacheFirstSWR(req, CACHE_ASSETS));
});

async function networkFirst(req, cacheName) {
  try {
    const fresh = await fetch(req);
    if (fresh && fresh.ok) {
      const cache = await caches.open(cacheName);
      cache.put(req, fresh.clone()); // background save
    }
    return fresh;
  } catch (err) {
    const cached = await caches.match(req);
    if (cached) return cached;
    // No cache + offline: return basic offline HTML
    return new Response(
      '<!DOCTYPE html><html lang="id"><head><meta charset="utf-8"><title>Offline — MiganCore</title>' +
        '<meta name="viewport" content="width=device-width,initial-scale=1">' +
        '<style>body{background:#07100e;color:#e9f5ee;font-family:sans-serif;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;margin:0;padding:1rem;text-align:center}h1{color:#ff8a24}p{color:#93b3a5;max-width:32rem}button{background:#ff8a24;color:#07100e;border:0;padding:.75rem 1.5rem;border-radius:8px;font-weight:600;margin-top:1rem;cursor:pointer}</style>' +
        '</head><body><h1>Offline</h1><p>Koneksi internet sedang putus. MiganCore butuh online untuk chat realtime.</p><button onclick="location.reload()">Coba lagi</button></body></html>',
      { headers: { 'Content-Type': 'text/html; charset=utf-8' }, status: 503 }
    );
  }
}

async function cacheFirstSWR(req, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(req);

  // Background revalidation
  const fetchPromise = fetch(req)
    .then((res) => {
      if (res && res.ok) cache.put(req, res.clone());
      return res;
    })
    .catch(() => null);

  // Return cached immediately if available, else wait for network
  return cached || (await fetchPromise) || new Response('Asset unavailable offline', { status: 503 });
}

// Listen for skipWaiting message from client (allows in-tab update without F5)
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
