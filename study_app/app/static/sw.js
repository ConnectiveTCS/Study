const CACHE_NAME = "studyforce-v2";

const PRECACHE_URLS = [
  "/",
  "/static/css/base.css",
  "/static/css/components.css",
  "/static/css/sidebar.css",
  "/static/js/theme.js",
  "/static/js/sidebar.js",
  "/static/js/toast.js",
  "/static/icons/icon-192.png",
];

// Install: precache core assets
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS)),
  );
  self.skipWaiting();
});

// Activate: clean up old caches
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)),
        ),
      ),
  );
  self.clients.claim();
});

// Fetch: cache-first for static assets, network-first for everything else
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // Only handle same-origin requests
  if (url.origin !== location.origin) return;

  // Static assets — cache first
  if (url.pathname.startsWith("/static/")) {
    event.respondWith(cacheFirst(event.request));
    return;
  }

  // Navigation requests — network first, offline fallback
  if (event.request.mode === "navigate") {
    event.respondWith(networkFirstWithFallback(event.request));
    return;
  }
});

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok) {
    const cache = await caches.open(CACHE_NAME);
    cache.put(request, response.clone());
  }
  return response;
}

async function networkFirstWithFallback(request) {
  try {
    const response = await fetch(request);
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;
    return new Response("You are offline.", {
      status: 503,
      headers: { "Content-Type": "text/plain" },
    });
  }
}
