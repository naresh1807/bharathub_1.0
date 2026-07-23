/**
 * messaging/static/messaging/js/sw.js
 *
 * Web Push కి అవసరమైన Service Worker -- బ్రౌజర్ ఈ ఫైల్ ని ఒక్కసారి
 * register చేసుకుంటే (chat.js లోని registerPushNotifications()),
 * ట్యాబ్ మూసేసినా / మినిమైజ్ చేసినా బ్రౌజర్ నేపథ్యంలో ఇది రన్
 * అవుతూనే ఉంటుంది, కొత్త push వచ్చినప్పుడు desktop notification
 * చూపిస్తుంది.
 *
 * ఇది కేవలం push notifications కోసమే -- ఆఫ్‌లైన్ caching / fetch
 * ఇంటర్‌సెప్షన్ (PWA-తరహా) ఇక్కడ ఉద్దేశపూర్వకంగా చేయలేదు (scope
 * పరిమితం అయినా push event పనిచేయడానికి scope అడ్డురాదు).
 */

self.addEventListener("push", (event) => {
  let payload = { title: "BharatHub", body: "మీకు కొత్త సందేశం వచ్చింది." };
  try {
    if (event.data) payload = event.data.json();
  } catch (e) {
    // JSON కాకపోతే డిఫాల్ట్ payload వాడతాం.
  }

  const options = {
    body: payload.body,
    data: { conversationId: payload.conversation_id },
    tag: payload.conversation_id ? `bh-conversation-${payload.conversation_id}` : undefined,
    renotify: true,
  };

  event.waitUntil(self.registration.showNotification(payload.title, options));
});

// నోటిఫికేషన్ మీద క్లిక్ చేస్తే, ఇప్పటికే తెరిచి ఉన్న BharatHub ట్యాబ్
// ఉంటే దాన్ని ఫోకస్ చేస్తుంది; లేకపోతే కొత్త ట్యాబ్ తెరుస్తుంది.
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((windowClients) => {
      for (const client of windowClients) {
        if ("focus" in client) return client.focus();
      }
      if (clients.openWindow) return clients.openWindow("/");
    })
  );
});
