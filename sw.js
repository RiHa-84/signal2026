// Signal 2026 – service worker: aplikace funguje i bez signálu
const CACHE = 'signal2026-v1';
const TILES = 'signal2026-tiles-v1';
const CORE = [
  './', './index.html', './manifest.webmanifest',
  './icon-180.png', './icon-192.png', './icon-512.png',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => Promise.all(
    CORE.map(u => c.add(new Request(u, u.startsWith('http') ? { mode: 'no-cors' } : {})).catch(() => {}))
  )).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(
    keys.filter(k => k !== CACHE && k !== TILES).map(k => caches.delete(k))
  )).then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);

  // Stránka: nejdřív internet (aktuální verze), bez signálu uložená kopie
  if (req.mode === 'navigate') {
    e.respondWith(fetch(req).then(r => {
      const copy = r.clone(); caches.open(CACHE).then(c => c.put('./index.html', copy)); return r;
    }).catch(() => caches.match('./index.html')));
    return;
  }

  // Mapové dlaždice: co už jste jednou viděli, zobrazí se i bez signálu
  if (url.hostname.endsWith('basemaps.cartocdn.com')) {
    e.respondWith(caches.open(TILES).then(c => c.match(req).then(hit => hit || fetch(req).then(r => {
      c.put(req, r.clone()); return r;
    }).catch(() => hit))));
    return;
  }

  // Ostatní (Leaflet, ikony): z cache, jinak internet
  e.respondWith(caches.match(req).then(hit => hit || fetch(req)));
});
