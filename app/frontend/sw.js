/**
 * Service Worker para Ecko
 * Permite recibir notificaciones push incluso cuando la web está cerrada
 */

const CACHE_NAME = 'ecko-v1';
const urlsToCache = [
  '/',
  '/static/app.js',
  '/static/styles.css',
  '/static/index.html'
];

// Instalar Service Worker
self.addEventListener('install', (event) => {
  console.log('[SW] Instalando Service Worker...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[SW] Cache abierto');
        return cache.addAll(urlsToCache);
      })
  );
  self.skipWaiting(); // Activar inmediatamente
});

// Activar Service Worker
self.addEventListener('activate', (event) => {
  console.log('[SW] Activando Service Worker...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('[SW] Eliminando cache antiguo:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  return self.clients.claim();
});

// Interceptar fetch requests (para offline support)
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request)
      .then((response) => {
        // Cache hit - return response
        if (response) {
          return response;
        }
        return fetch(event.request);
      }
    )
  );
});

// Recibir notificaciones push
self.addEventListener('push', (event) => {
  console.log('[SW] Notificación push recibida');
  
  let notificationData = {
    title: 'Ecko',
    body: 'Tienes un nuevo mensaje',
    icon: '/static/logo.svg',
    badge: '/static/logo.svg',
    tag: 'ecko-notification'
  };
  
  if (event.data) {
    try {
      const data = event.data.json();
      notificationData = {
        title: data.title || 'Ecko',
        body: data.body || 'Tienes un nuevo mensaje',
        icon: data.icon || '/static/logo.svg',
        badge: data.badge || '/static/logo.svg',
        tag: data.tag || 'ecko-notification',
        requireInteraction: data.requireInteraction || false,
        data: data.data || {}
      };
    } catch (e) {
      console.error('[SW] Error parseando datos push:', e);
      notificationData.body = event.data.text();
    }
  }
  
  event.waitUntil(
    self.registration.showNotification(notificationData.title, {
      body: notificationData.body,
      icon: notificationData.icon,
      badge: notificationData.badge,
      tag: notificationData.tag,
      requireInteraction: notificationData.requireInteraction,
      data: notificationData.data,
      vibrate: [200, 100, 200],
      actions: [
        {
          action: 'open',
          title: 'Abrir Ecko'
        },
        {
          action: 'close',
          title: 'Cerrar'
        }
      ]
    })
  );
});

// Manejar clicks en notificaciones
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Click en notificación:', event.action);
  
  event.notification.close();
  
  if (event.action === 'open' || !event.action) {
    // Abrir o enfocar la aplicación
    event.waitUntil(
      clients.matchAll({ type: 'window', includeUncontrolled: true })
        .then((clientList) => {
          // Si hay una ventana abierta, enfocarla
          for (let client of clientList) {
            if (client.url === self.registration.scope && 'focus' in client) {
              return client.focus();
            }
          }
          // Si no hay ventana abierta, abrir una nueva
          if (clients.openWindow) {
            return clients.openWindow('/');
          }
        })
    );
  }
});

// Manejar sincronización en segundo plano (para futuras funcionalidades)
self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync:', event.tag);
  if (event.tag === 'sync-reminders') {
    event.waitUntil(
      // Sincronizar recordatorios
      fetch('/api/reminders/sync')
        .then(response => response.json())
        .catch(err => console.error('[SW] Error en sync:', err))
    );
  }
});

