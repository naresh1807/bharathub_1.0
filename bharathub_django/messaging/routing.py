"""
messaging/routing.py

WebSocket URLs -- bharathub/asgi.py లోని ProtocolTypeRouter ఈ జాబితా
ని "websocket" ప్రోటోకాల్ కి వాడుతుంది (HTTP urls.py తో సంబంధం లేదు,
ఇది పూర్తిగా వేరే routing table).
"""
from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(
        r"^ws/messaging/conversation/(?P<conversation_id>\d+)/$",
        consumers.ChatConsumer.as_asgi(),
    ),
]
