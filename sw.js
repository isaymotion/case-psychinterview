/* Offline support: serve the app from the iPad's cache when there is no connection. */
const CACHE = 'case-mse-v20';
const FILES = [
  './',
  './index.html',
  './slides.js',
  './pdf.js',
  './manifest.webmanifest',
  './icon-180.png',
  './icon-192.png',
  './icon-512.png',
  './icon-maskable-512.png',
  './favicon-32.png',
  './templates/colorful.pptx',
  './templates/pedia.pptx',
  './templates/purple.pptx',
  './templates/spheres.pptx',
  './templates/unicorn.pptx',
  './templates/colorful-bg/slideLayout1.jpg',
  './templates/colorful-bg/slideLayout15.jpg',
  './templates/colorful-bg/slideLayout16.jpg',
  './templates/colorful-bg/slideLayout2.jpg',
  './templates/colorful-bg/slideLayout4.jpg',
  './templates/colorful-bg/slideLayout5.jpg',
  './templates/colorful-bg/slideLayout6.jpg',
  './templates/colorful-bg/slideLayout7.jpg',
  './templates/pedia-bg/slideLayout1.jpg',
  './templates/pedia-bg/slideLayout10.jpg',
  './templates/pedia-bg/slideLayout11.jpg',
  './templates/pedia-bg/slideLayout12.jpg',
  './templates/pedia-bg/slideLayout13.jpg',
  './templates/pedia-bg/slideLayout3.jpg',
  './templates/pedia-bg/slideLayout5.jpg',
  './templates/pedia-bg/slideLayout6.jpg',
  './templates/pedia-bg/slideLayout8.jpg',
  './templates/purple-bg/slideLayout1.jpg',
  './templates/purple-bg/slideLayout14.jpg',
  './templates/purple-bg/slideLayout4.jpg',
  './templates/purple-bg/slideLayout5.jpg',
  './templates/purple-bg/slideLayout6.jpg',
  './templates/spheres-bg/slideLayout1.jpg',
  './templates/spheres-bg/slideLayout10.jpg',
  './templates/spheres-bg/slideLayout13.jpg',
  './templates/spheres-bg/slideLayout3.jpg',
  './templates/unicorn-bg/slideLayout1.jpg',
  './templates/unicorn-bg/slideLayout15.jpg',
  './templates/unicorn-bg/slideLayout16.jpg',
  './templates/unicorn-bg/slideLayout4.jpg',
  './templates/unicorn-bg/slideLayout7.jpg',
  './fonts/body-bold.woff',
  './fonts/body-bolditalic.woff',
  './fonts/body-italic.woff',
  './fonts/body-regular.woff',
  './fonts/head-bold.woff',
  './fonts/title-black.woff',
  './fonts/title-blackitalic.woff'
];
self.addEventListener('install', e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES)).then(() => self.skipWaiting())); });
self.addEventListener('activate', e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  if (new URL(e.request.url).origin !== self.location.origin) return;   // Google sign-in and Drive go straight to the network, never into the cache
  // Try the network first so updates arrive; fall back to the saved copy when offline.
  e.respondWith(fetch(e.request).then(r => { const copy = r.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); return r; })
    .catch(() => caches.match(e.request, {ignoreSearch:true}).then(r => r || caches.match('./index.html'))));
});
