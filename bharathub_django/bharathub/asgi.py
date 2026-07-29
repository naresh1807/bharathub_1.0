"""
ASGI config for the BharatHub project.

ఇప్పుడు ఇది రెండు రకాల ప్రోటోకాల్‌లని హ్యాండిల్ చేస్తుంది:
  - http  -> మామూలు Django views (register/login/dashboards/...)
  - websocket -> messaging/routing.py లోని Channels consumers
                 (real-time chat: send/edit/delete/react/typing/presence)

AuthMiddlewareStack: HTTP రిక్వెస్ట్ లో సెషన్ కుకీ ఆధారంగా Django
ఎలా request.user ని పాపులేట్ చేస్తుందో, సరిగ్గా అదే పని WebSocket
కనెక్షన్ కి కూడా చేస్తుంది -- కాబట్టి consumers.py లో
self.scope["user"] ఎప్పుడూ లాగిన్ అయిన నిజమైన యూజర్ నే ఉంటుంది
(లేదా AnonymousUser, లాగిన్ అవ్వకపోతే).
"""
import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bharathub.settings")

# get_asgi_application() ని ముందే కాల్ చేయాలి -- ఇది Django app
# registry ని లోడ్ చేస్తుంది; ఆ తర్వాతే messaging.routing ని
# import చేయాలి (అది models.py ని import చేస్తుంది కాబట్టి, apps
# ఇంకా లోడ్ కాకముందే import చేస్తే AppRegistryNotReady ఎర్రర్ వస్తుంది).
django_asgi_app = get_asgi_application()

import messaging.routing  # noqa: E402  (see comment above)
import meetings.routing  # noqa: E402

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(messaging.routing.websocket_urlpatterns + meetings.routing.websocket_urlpatterns)
    ),
})
