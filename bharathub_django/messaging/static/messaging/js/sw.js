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
  let payload = { title: "BharatHub", body: "You have a new message." };
  try {
    if (event.data) payload = event.data.json();
  } catch (e) {
    // JSON కాకపోతే డిఫాల్ట్ payload వాడతాం.
  }

  // BUG FIX: ఇంతకుముందు క్లిక్ handler ఎప్పుడూ హోమ్‌పేజీ ('/') కే
  // తెరిచేది -- ఇక్కడ నిర్దిష్ట గమ్యస్థానం (call room లింక్, లేదా
  // ఆ conversation) ని data లో పెడుతున్నాం, notificationclick లో
  // దాన్నే వాడతాం.
  const targetUrl = payload.url || (payload.conversation_id ? `/messaging/?c=${payload.conversation_id}` : "/");

  const options = {
    body: payload.body,
    data: { url: targetUrl },
    tag: payload.conversation_id ? `bh-conversation-${payload.conversation_id}` : undefined,
    renotify: true,
  };

  event.waitUntil(self.registration.showNotification(payload.title, options));
});

// నోటిఫికేషన్ మీద క్లిక్ చేస్తే -- ఇప్పటికే తెరిచి ఉన్న BharatHub ట్యాబ్
// ఉంటే దాన్ని ఆ URL కి నావిగేట్ చేసి ఫోకస్ చేస్తుంది; లేకపోతే ఆ URL
// తోనే కొత్త ట్యాబ్ తెరుస్తుంది (📹 కాల్ నోటిఫికేషన్ అయితే నేరుగా
// మీటింగ్ రూమ్ లోకి; సందేశం అయితే ఆ సంభాషణ లోకి).
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const targetUrl = (event.notification.data && event.notification.data.url) || "/";
  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((windowClients) => {
      for (const client of windowClients) {
        if ("focus" in client && "navigate" in client) {
          client.navigate(targetUrl);
          return client.focus();
        }
      }
      if (clients.openWindow) return clients.openWindow(targetUrl);
    })
  );
});
