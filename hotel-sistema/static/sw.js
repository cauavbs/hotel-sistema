// Service Worker: guarda só arquivos estáticos (públicos). Páginas e API sempre vão à rede.
const CACHE = 'hotel-app-v1';
const ESTATICOS = ['/static/style.css', '/static/manifest.json', '/static/icon-192.png', '/static/icon-512.png',
  '/static/js/comum.js', '/static/js/modal.js', '/static/js/login.js'];
self.addEventListener('install', e => e.waitUntil(caches.open(CACHE).then(c => c.addAll(ESTATICOS))));
self.addEventListener('activate', e => e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))));
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET' || !new URL(e.request.url).pathname.startsWith('/static/')) return;
  e.respondWith(fetch(e.request).then(r => { const c = r.clone(); caches.open(CACHE).then(x => x.put(e.request, c)); return r; }).catch(() => caches.match(e.request)));
});
