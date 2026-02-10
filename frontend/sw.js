/**
 * 🧠 Cerebro Operativo — Service Worker
 * Cache offline + push notifications ready
 */

const CACHE_NAME = 'cerebro-operativo-v1';
const STATIC_ASSETS = [
    '/',
    '/static/app.js',
    '/static/styles.css',
    '/static/manifest.json',
];

// === Instalación: cachear assets estáticos ===
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log('🧠 Service Worker: cacheando assets');
            return cache.addAll(STATIC_ASSETS);
        })
    );
    self.skipWaiting();
});

// === Activación: limpiar caches antiguos ===
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((name) => name !== CACHE_NAME)
                    .map((name) => caches.delete(name))
            );
        })
    );
    self.clients.claim();
    console.log('🧠 Service Worker: activado');
});

// === Fetch: Network First con fallback a cache ===
self.addEventListener('fetch', (event) => {
    const { request } = event;

    // No cachear llamadas a la API ni WebSocket
    if (request.url.includes('/api/') || request.url.includes('/ws/')) {
        event.respondWith(
            fetch(request).catch(() => {
                // Si la API no responde, devolver error JSON
                return new Response(
                    JSON.stringify({ error: 'Sin conexión', offline: true }),
                    { headers: { 'Content-Type': 'application/json' } }
                );
            })
        );
        return;
    }

    // Para assets estáticos: Network First
    event.respondWith(
        fetch(request)
            .then((response) => {
                // Guardar copia en cache
                const responseClone = response.clone();
                caches.open(CACHE_NAME).then((cache) => {
                    cache.put(request, responseClone);
                });
                return response;
            })
            .catch(() => {
                // Si no hay red, buscar en cache
                return caches.match(request).then((cached) => {
                    return cached || new Response('Offline', { status: 503 });
                });
            })
    );
});

// === Push Notifications (listo para FCM futuro) ===
self.addEventListener('push', (event) => {
    const data = event.data?.json() || {};
    const title = data.title || '🧠 Cerebro Operativo';
    const options = {
        body: data.body || 'Nueva notificación',
        icon: '/static/icons/icon-192.png',
        badge: '/static/icons/icon-72.png',
        vibrate: [100, 50, 100],
        data: { url: data.url || '/' },
        actions: data.actions || [],
    };
    event.waitUntil(self.registration.showNotification(title, options));
});

// === Click en notificación ===
self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    const url = event.notification.data?.url || '/';
    event.waitUntil(
        self.clients.matchAll({ type: 'window' }).then((clients) => {
            // Si ya hay una ventana abierta, enfocarla
            for (const client of clients) {
                if (client.url.includes(url) && 'focus' in client) {
                    return client.focus();
                }
            }
            return self.clients.openWindow(url);
        })
    );
});
