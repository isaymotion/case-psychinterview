/* Offline support: serve the app from the iPad's cache when there is no connection. */
const CACHE = 'case-mse-v13';
const FILES = ['./', './index.html', './slides.js', './pdf.js', './templates/colorful.pptx',
  './templates/colorful-bg/slideLayout1.png', './templates/colorful-bg/slideLayout2.png', './templates/colorful-bg/slideLayout4.png', './templates/colorful-bg/slideLayout5.png',
  './templates/colorful-bg/slideLayout6.png', './templates/colorful-bg/slideLayout7.png', './templates/colorful-bg/slideLayout15.png', './templates/colorful-bg/slideLayout16.png',
  './fonts/body-regular.woff', './fonts/body-bold.woff', './fonts/body-italic.woff', './fonts/body-bolditalic.woff', './fonts/head-bold.woff', './fonts/title-black.woff', './fonts/title-blackitalic.woff', './manifest.webmanifest', './icon-180.png', './icon-192.png', './icon-512.png', './icon-maskable-512.png', './favicon-32.png'];
self.addEventListener('install', e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES)).then(() => self.skipWaiting())); });
self.addEventListener('activate', e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  // Try the network first so updates arrive; fall back to the saved copy when offline.
  e.respondWith(fetch(e.request).then(r => { const copy = r.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); return r; })
    .catch(() => caches.match(e.request, {ignoreSearch:true}).then(r => r || caches.match('./index.html'))));
});
