"""
meetings/routing.py

messaging/routing.py తరహాలోనే -- bharathub/asgi.py లోని
ProtocolTypeRouter ఈ జాబితా ని "websocket" ప్రోటోకాల్ కి వాడుతుంది.
"""
from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(
        r"^ws/meetings/room/(?P<room_code>[\w-]+)/$",
        consumers.MeetingConsumer.as_asgi(),
    ),
    re_path(
        r"^ws/meetings/notify/$",
        consumers.IncomingCallConsumer.as_asgi(),
    ),
]
