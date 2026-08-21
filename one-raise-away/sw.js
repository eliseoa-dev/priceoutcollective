// One Raise Away — service worker
const CACHE_NAME = 'one-raise-away-v1.0.1';
const ASSETS = ['./','./index.html','./shell.js','./app.js','./styles.css','./manifest.json',
  './data.js','./icons/icon-192.png','./icons/icon-512.png'];

self.addEventListener('install', (e) => {
  self.skipWaiting();
  e.waitUntil(caches.open(CACHE_NAME).then((c) => c.addAll(ASSETS)).catch(() => {}));
});
self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((keys) =>
    Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
  ).then(() => self.clients.claim()));
});
self.addEventListener('fetch', (e) => {
  const { request } = e;
  if (request.url.includes('supabase.co')) return; // never cache API calls
  // A 404 or 500 is a SUCCESSFUL fetch, so the old code handed it straight to the page
  // AND cached it over the good copy. When GitHub Pages went down on 2026-08-06 that
  // turned a working installed app into a cached 404. Only ok responses are kept, and
  // anything else falls back to what is already in the cache.
  e.respondWith(
    fetch(request).then((res) => {
      if (!res || !res.ok) return caches.match(request).then((hit) => hit || res);
      const copy = res.clone();
      caches.open(CACHE_NAME).then((c) => c.put(request, copy)).catch(() => {});
      return res;
    }).catch(() => caches.match(request))
  );
});
