"""
meetings/consumers.py

Zoom-తరహా వీడియో మీటింగ్ రూమ్ కి "గుండె" భాగం -- messaging/consumers.py
లోని ChatConsumer లాగే ఉంటుంది, కానీ ఇక్కడ సందేశాలకి బదులు WebRTC
సిగ్నలింగ్ (offer/answer/ICE candidates) రిలే చేస్తాం. అసలు ఆడియో/
వీడియో డేటా ఎప్పుడూ ఈ సర్వర్ గుండా వెళ్ళదు -- అది బ్రౌజర్ నుండి
బ్రౌజర్ కి నేరుగా (peer-to-peer, RTCPeerConnection ద్వారా) వెళ్తుంది.
ఈ సర్వర్ కేవలం "ఎవరు ఎవరితో కనెక్ట్ కావాలి" అనే మెటాడేటా మాత్రమే
పంచుతుంది (అదే సిగ్నలింగ్).

  Client -> Server:
    join            -> నేను ఈ రూమ్ లోకి వచ్చాను (నా peer_id తెలియజేయడం)
    webrtc.offer    -> ఒక నిర్దిష్ట పీర్ కి SDP offer
    webrtc.answer   -> ఒక నిర్దిష్ట పీర్ కి SDP answer
    webrtc.ice      -> ఒక నిర్దిష్ట పీర్ కి ICE candidate
    media.state     -> నా మైక్/కెమెరా ఆన్/ఆఫ్ అని అందరికీ చెప్పడం
    room.chat       -> రూమ్ లోపలి టెక్స్ట్ చాట్ (ఎఫెమెరల్ -- DB లో
                       సేవ్ అవదు, ఇది మీటింగ్ కి మాత్రమే పరిమితం)
    leave           -> నేను వెళ్ళిపోతున్నాను

  Server -> Client (broadcast లేదా టార్గెటెడ్):
    peer.joined, peer.left, webrtc.offer, webrtc.answer, webrtc.ice,
    media.state, room.chat

SECURITY: connect() లోనే Meeting.is_participant_allowed() చెక్
చేస్తాం (IDOR గార్డ్ -- messaging/consumers.py లో వాడిన అదే సూత్రం).
"""
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.core.cache import cache
from django.utils.html import strip_tags

RATE_LIMIT_MAX_ACTIONS = 30
RATE_LIMIT_WINDOW_SECONDS = 10
MAX_CHAT_LENGTH = 500


class MeetingConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):
        self.user = self.scope["user"]
        self.room_code = self.scope["url_route"]["kwargs"]["room_code"]
        self.room_group_name = f"meeting_{self.room_code}"
        # ప్రతి బ్రౌజర్ ట్యాబ్/కనెక్షన్ కి ఒక యూనిక్ peer_id -- ఒకే
        # యూజర్ రెండు ట్యాబ్‌లలో join అయినా (ఉదా: పొరపాటున) రెండూ
        # విడి పీర్‌లుగా కనిపిస్తాయి, ఒకదాంతో ఒకటి కలవవు.
        self.peer_id = self.channel_name

        if not self.user.is_authenticated:
            await self.close(code=4001)
            return

        allowed = await self._is_allowed()
        if not allowed:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        await self._log_join()

    async def disconnect(self, close_code):
        if getattr(self, "room_group_name", None):
            await self.channel_layer.group_send(self.room_group_name, {
                "type": "broadcast.event",
                "payload": {"type": "peer.left", "peer_id": self.peer_id, "user_id": self.user.id},
            })
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        if getattr(self, "user", None) and self.user.is_authenticated:
            await self._log_leave()

    async def receive_json(self, content, **kwargs):
        msg_type = content.get("type")

        if not self._check_rate_limit():
            return

        if msg_type == "join":
            await self._handle_join()
        elif msg_type in ("webrtc.offer", "webrtc.answer", "webrtc.ice"):
            await self._relay_to_peer(msg_type, content)
        elif msg_type == "media.state":
            await self.channel_layer.group_send(self.room_group_name, {
                "type": "broadcast.event",
                "payload": {
                    "type": "media.state", "peer_id": self.peer_id, "user_id": self.user.id,
                    "audio": bool(content.get("audio")), "video": bool(content.get("video")),
                },
            })
        elif msg_type == "room.chat":
            text = strip_tags((content.get("text") or "").strip())[:MAX_CHAT_LENGTH]
            if not text:
                return
            await self.channel_layer.group_send(self.room_group_name, {
                "type": "broadcast.event",
                "payload": {
                    "type": "room.chat", "user_id": self.user.id,
                    "name": await self._display_name(), "text": text,
                },
            })

    async def _handle_join(self):
        # కొత్తగా చేరిన పీర్‌కి తనకంటే ముందున్న అందరి పీర్ ఐడీలు
        # తెలియాలి (వాళ్ళందరితో RTCPeerConnection మొదలుపెట్టడానికి) --
        # ఇక్కడ మేము channel_name లనే peer_id గా వాడుతున్నాం కాబట్టి
        # group.members API లేదు, బదులుగా ప్రతి కొత్త పీర్ join
        # అయినప్పుడు "peer.joined" broadcast ద్వారానే ఇతర పీర్‌లు
        # తమని తాము పరిచయం చేసుకుంటారు (mesh handshake, room.js చూడండి).
        await self.channel_layer.group_send(self.room_group_name, {
            "type": "broadcast.event",
            "payload": {
                "type": "peer.joined", "peer_id": self.peer_id, "user_id": self.user.id,
                "name": await self._display_name(),
            },
        })

    async def _relay_to_peer(self, msg_type, content):
        target_peer_id = content.get("target_peer_id")
        if not target_peer_id:
            return
        await self.channel_layer.send(target_peer_id, {
            "type": "direct.event",
            "payload": {
                "type": msg_type, "from_peer_id": self.peer_id, "user_id": self.user.id,
                "sdp": content.get("sdp"), "candidate": content.get("candidate"),
            },
        })

    async def broadcast_event(self, event):
        await self.send_json(event["payload"])

    async def direct_event(self, event):
        await self.send_json(event["payload"])

    def _check_rate_limit(self) -> bool:
        key = f"meeting_ratelimit:{self.user.id}"
        cache.add(key, 0, timeout=RATE_LIMIT_WINDOW_SECONDS)
        try:
            count = cache.incr(key)
        except ValueError:
            cache.set(key, 1, timeout=RATE_LIMIT_WINDOW_SECONDS)
            count = 1
        return count <= RATE_LIMIT_MAX_ACTIONS

    @database_sync_to_async
    def _is_allowed(self):
        from .models import Meeting
        try:
            meeting = Meeting.objects.select_related(
                "job_application__candidate__user", "job_application__job__employer__user",
            ).get(room_code=self.room_code)
        except Meeting.DoesNotExist:
            return False
        return meeting.is_participant_allowed(self.user)

    @database_sync_to_async
    def _display_name(self):
        from .utils import display_name_for
        return display_name_for(self.user)

    @database_sync_to_async
    def _log_join(self):
        from django.utils import timezone
        from .models import Meeting, MeetingParticipant
        meeting = Meeting.objects.get(room_code=self.room_code)
        if meeting.status == Meeting.Status.SCHEDULED:
            meeting.status = Meeting.Status.LIVE
            meeting.started_at = timezone.now()
            meeting.save(update_fields=["status", "started_at"])
        MeetingParticipant.objects.create(meeting=meeting, user=self.user)

    @database_sync_to_async
    def _log_leave(self):
        from django.utils import timezone
        from .models import MeetingParticipant
        log = MeetingParticipant.objects.filter(
            meeting__room_code=self.room_code, user=self.user, left_at__isnull=True,
        ).order_by("-joined_at").first()
        if log:
            log.left_at = timezone.now()
            log.save(update_fields=["left_at"])


class IncomingCallConsumer(AsyncJsonWebsocketConsumer):
    """
    సైట్ మొత్తం మీద ఒకే ఒక్క గ్లోబల్ ఛానల్ -- MeetingConsumer లా కాకుండా,
    ఇది ఏదో ఒక నిర్దిష్ట మీటింగ్ రూమ్ కి పరిమితం కాదు. dashboard_base.html
    లో లాగిన్ అయిన ప్రతి యూజర్ (ఏ పేజీలో ఉన్నా సరే -- Dashboard,
    Applications, Shopping ఏదైనా) ఈ ఛానల్ కి ఆటోమేటిక్‌గా కనెక్ట్
    అవుతారు (incoming_call.js). దీని వల్లే వాట్సాప్ లో లాగే "ఏ tab లో
    ఉన్నా, కాల్ వచ్చినప్పుడు స్క్రీన్ పైన ఓవర్‌లే కనిపించి, Join/Reject
    బటన్లు రావడం" సాధ్యమవుతుంది -- ఇంతకుముందు call.started event
    కేవలం ఆ conversation పేజీ తెరిచున్న యూజర్‌కి మాత్రమే చేరేది,
    మిగతా వాళ్ళకి push notification మీదే ఆధారపడేవాళ్ళం (అది browser
    permission మీద ఆధారపడుతుంది, యూజర్‌కి అర్థం కాకపోవచ్చు).

    ప్రతి యూజర్ తన సొంత గ్రూప్ (f"user_{user.id}") లోకి చేరతారు --
    meetings/views.py లోని SendMeetingLinkView/StartConversationCallView
    ఈ గ్రూప్ కి 'incoming_call' event పంపిస్తే, ఆ యూజర్ తెరిచున్న ప్రతి
    ట్యాబ్ లోనూ ఓవర్‌లే కనిపిస్తుంది.
    """

    async def connect(self):
        self.user = self.scope["user"]
        if not self.user.is_authenticated:
            await self.close(code=4001)
            return
        self.group_name = f"user_{self.user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if getattr(self, "group_name", None):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        # ఈ ఛానల్ ద్వారా క్లయింట్ నుండి సర్వర్ కి ఏమీ పంపము (one-way,
        # సర్వర్ -> క్లయింట్ notify మాత్రమే) -- 'call.reject' లాంటివి
        # కూడా సాధారణ HTTP POST (DeclineCallView) ద్వారానే వెళ్తాయి,
        # దీనికి రిప్లై అవసరం లేదు కాబట్టి ఇక్కడ ఏమీ హ్యాండిల్ చేయం.
        pass

    async def broadcast_event(self, event):
        await self.send_json(event["payload"])
