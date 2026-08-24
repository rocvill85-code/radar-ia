// Radar IA · service worker — estrategia "network-first":
// siempre intenta la versión más reciente cuando hay internet, y si no hay
// conexión, muestra la última guardada. Así la revista se refresca sola.
const CACHE = "radar-ia-cache";

self.addEventListener("install", (e) => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  e.respondWith(
    fetch(req)
      .then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
        return res;
      })
      .catch(() => caches.match(req))
  );
});
