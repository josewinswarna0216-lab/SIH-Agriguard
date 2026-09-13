// Minimal service worker -- satisfies Android's install criteria.
// No offline caching: this dashboard is inherently live-data, so serving
// stale cached data instead of fresh network data would be misleading.
self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  event.respondWith(fetch(event.request));
});
