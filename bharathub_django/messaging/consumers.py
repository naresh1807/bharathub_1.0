"""
messaging/consumers.py

WhatsApp-తరహా చాట్ కి "గుండె" భాగం -- ప్రతి ఓపెన్ చాట్ విండో ఒక
WebSocket కనెక్షన్ (ws/messaging/conversation/<id>/) తెరుస్తుంది.
ఈ ఒక్క consumer ఈ కింది అన్నింటినీ హ్యాండిల్ చేస్తుంది:

  Client -> Server (receive_json లో "type" ఆధారంగా):
    message.send    -> కొత్త టెక్స్ట్ మెసేజ్
    message.edit    -> ఇంతకుముందు పంపిన మెసేజ్ ని ఎడిట్ చేయడం
    message.delete  -> "Delete for everyone"
    message.react   -> ఎమోజీ రియాక్షన్ (add/replace)
    message.read    -> ఈ మెసేజ్ వరకూ చదివానని చెప్పడం (blue tick)
    typing           -> "Typing..." ఇండికేటర్ ఆన్/ఆఫ్

  Server -> Client (group broadcast, chat_<conversation_id> గ్రూప్ కి):
    message.new, message.edited, message.deleted, message.reaction,
    message.read_receipt, typing, presence

SECURITY (WebSocket లెవెల్ లో authentication + authorization):
  - self.scope["user"]: AuthMiddlewareStack (asgi.py) ఇప్పటికే సెషన్
    కుకీ నుండి పాపులేట్ చేస్తుంది -- లాగిన్ కాని యూజర్ ని connect()
    లోనే తిరస్కరిస్తాం.
  - conversation.is_participant(user): ఈ conversation లో నిజంగా
    సభ్యుడేనా అని ప్రతి connect() లోనూ DB లో చెక్ చేస్తాం (URL లో
    conversation_id ఊహించి/మార్చి వేరే వాళ్ళ చాట్ లోకి ఎవరూ చొరబడలేరు
    -- ఇదే IDOR గార్డ్, HTTP views లో వాడినదే సూత్రం ఇక్కడా).
  - ప్రతి action (edit/delete/react) కి ఆ మెసేజ్ నిజంగా ఈ యూజర్
    దేనా (edit/delete కి) అని కూడా వేరే గా చెక్ చేస్తాం.
  - మెసేజ్ కంటెంట్ ఎప్పుడూ save చేసేముందు strip_tags() తో sanitize
    అవుతుంది, పంపేటప్పుడు escape() అవుతుంది (views.py లోని
    _serialize_message చూడండి) -- XSS నుండి రెండు పొరల రక్షణ.
"""
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.core.cache import cache
from django.utils.html import strip_tags

MAX_BODY_LENGTH = 4000

# ── Rate limiting (flood/DoS protection) ──────────────────────────
# ఒక యూజర్ WebSocket ద్వారా చాలా వేగంగా message.send/edit/delete/
# react పంపుతూ (స్క్రిప్ట్ ద్వారా అయినా) సర్వర్/DB మీద భారం
# పెంచకుండా ఆపడానికి. Django cache framework వాడతాం (fixed-window
# counter) -- REDIS_URL సెట్ చేసి ఉంటే బహుళ ప్రాసెస్‌ల మధ్య కూడా
# సరిగ్గా పనిచేస్తుంది, లేకపోతే dev లో LocMemCache (ఒకే ప్రాసెస్‌
# లోపలే) ఫర్వాలేదు.
RATE_LIMIT_MAX_ACTIONS = 20
RATE_LIMIT_WINDOW_SECONDS = 10


class ChatConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):
        self.user = self.scope["user"]
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.room_group_name = f"chat_{self.conversation_id}"

        if not self.user.is_authenticated:
            await self.close(code=4001)
            return

        allowed = await self._is_participant()
        if not allowed:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # ఈ యూజర్ ఆన్‌లైన్ అయ్యాడని ఇతర సభ్యులందరికీ తెలియజేయడం +
        # ఇంతకుముందు ఇతనికి చేరని మెసేజ్‌లని ఇప్పుడు "delivered" గా
        # మార్చడం (WhatsApp లో single-tick -> double-tick అవ్వడం లాగే).
        await self._set_presence(True)
        await self.channel_layer.group_send(self.room_group_name, {
            "type": "broadcast.event",
            "payload": {"type": "presence", "user_id": self.user.id, "is_online": True},
        })
        member_presence = await self._get_members_presence()
        await self.send_json({"type": "presence.snapshot", "members": member_presence})

        delivered_ids = await self._mark_undelivered_as_delivered()
        if delivered_ids:
            await self.channel_layer.group_send(self.room_group_name, {
                "type": "broadcast.event",
                "payload": {"type": "message.status", "message_ids": delivered_ids, "state": "delivered"},
            })

    async def disconnect(self, close_code):
        if getattr(self, "room_group_name", None):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        if getattr(self, "user", None) and self.user.is_authenticated:
            await self._set_presence(False)
            await self.channel_layer.group_send(self.room_group_name, {
                "type": "broadcast.event",
                "payload": {"type": "presence", "user_id": self.user.id, "is_online": False},
            })

    # ------------------------------------------------------------------
    # Client -> Server
    # ------------------------------------------------------------------
    async def receive_json(self, content, **kwargs):
        msg_type = content.get("type")

        # typing ఈవెంట్‌లు క్లయింట్ సైడ్‌లోనే debounce అవుతున్నాయి
        # (chat.js) కాబట్టి వాటిని rate-limit చేయం -- మిగతా అన్ని
        # (సర్వర్‌లో DB రైట్ చేసే) action లనే చెక్ చేస్తాం.
        if msg_type != "typing" and not self._check_rate_limit():
            await self.send_json({
                "type": "error", "code": "rate_limited",
                "message": "మీరు చాలా వేగంగా పంపుతున్నారు, కొంచెం ఆగి మళ్ళీ ప్రయత్నించండి.",
            })
            return

        if msg_type == "message.send":
            await self._handle_send(content)
        elif msg_type == "message.edit":
            await self._handle_edit(content)
        elif msg_type == "message.delete":
            await self._handle_delete(content)
        elif msg_type == "message.react":
            await self._handle_react(content)
        elif msg_type == "message.read":
            await self._handle_read(content)
        elif msg_type == "typing":
            await self._handle_typing(content)
        elif msg_type == "message.attachment_sent":
            await self._handle_attachment_sent(content)
        # తెలియని "type" ఏదైనా వస్తే నిశ్శబ్దంగా విస్మరిస్తాం (crash
        # అవ్వకుండా) -- ప్రొటోకాల్ కొత్త వెర్షన్‌లతో backward-compatible
        # గా ఉండటానికి ఇది మంచి పద్ధతి.

    async def _handle_send(self, content):
        body = strip_tags((content.get("body") or "").strip())[:MAX_BODY_LENGTH]
        temp_id = content.get("temp_id")
        if not body:
            return
        message = await self._create_message(body)
        payload = await self._serialize(message)
        payload["temp_id"] = temp_id
        await self.channel_layer.group_send(self.room_group_name, {
            "type": "broadcast.event",
            "payload": {"type": "message.new", "message": payload},
        })
        await self._notify_offline_recipients(message.id)

    async def _handle_edit(self, content):
        message_id = content.get("message_id")
        new_body = strip_tags((content.get("body") or "").strip())[:MAX_BODY_LENGTH]
        if not new_body:
            return
        message = await self._edit_message(message_id, new_body)
        if message is None:
            return  # not sender, or not found -- silently ignore
        payload = await self._serialize(message)
        await self.channel_layer.group_send(self.room_group_name, {
            "type": "broadcast.event",
            "payload": {"type": "message.edited", "message": payload},
        })

    async def _handle_delete(self, content):
        message_id = content.get("message_id")
        ok = await self._delete_message(message_id)
        if not ok:
            return
        await self.channel_layer.group_send(self.room_group_name, {
            "type": "broadcast.event",
            "payload": {"type": "message.deleted", "message_id": message_id},
        })

    async def _handle_react(self, content):
        message_id = content.get("message_id")
        emoji = (content.get("emoji") or "").strip()[:8]
        if not emoji:
            return
        reactions = await self._set_reaction(message_id, emoji)
        if reactions is None:
            return
        await self.channel_layer.group_send(self.room_group_name, {
            "type": "broadcast.event",
            "payload": {"type": "message.reaction", "message_id": message_id, "reactions": reactions},
        })

    async def _handle_read(self, content):
        message_id = content.get("message_id")
        ok = await self._mark_read(message_id)
        if not ok:
            return
        await self.channel_layer.group_send(self.room_group_name, {
            "type": "broadcast.event",
            "payload": {
                "type": "message.read_receipt", "message_id": message_id, "user_id": self.user.id,
            },
        })

    async def _handle_typing(self, content):
        await self.channel_layer.group_send(self.room_group_name, {
            "type": "broadcast.event",
            "payload": {
                "type": "typing",
                "user_id": self.user.id,
                "user_name": self.user.get_full_name() or self.user.username,
                "is_typing": bool(content.get("is_typing")),
            },
        }, )

    async def _handle_attachment_sent(self, content):
        """MessageAttachmentUploadView (plain HTTP POST) ఇప్పటికే
        ఫైల్ ని అప్‌లోడ్ చేసి Message రికార్డ్ క్రియేట్ చేసింది --
        ఇక్కడ కేవలం దాన్ని ఈ conversation లోని అందరికీ WebSocket
        ద్వారా బ్రాడ్‌కాస్ట్ చేయడమే మిగిలింది."""
        message_id = content.get("message_id")
        message = await self._get_own_message(message_id)
        if message is None:
            return
        payload = await self._serialize(message)
        await self.channel_layer.group_send(self.room_group_name, {
            "type": "broadcast.event",
            "payload": {"type": "message.new", "message": payload},
        })
        await self._notify_offline_recipients(message.id)

    # ------------------------------------------------------------------
    # Group broadcast handler -- channel_layer.group_send() ద్వారా
    # వచ్చిన ప్రతి event ఇక్కడికే వస్తుంది, దాన్నే JSON గా క్లయింట్
    # కి ఫార్వర్డ్ చేస్తాం.
    # ------------------------------------------------------------------
    async def broadcast_event(self, event):
        await self.send_json(event["payload"])

    def _check_rate_limit(self) -> bool:
        """fixed-window counter: ఒక్కో యూజర్ కి RATE_LIMIT_WINDOW_SECONDS
        లో RATE_LIMIT_MAX_ACTIONS దాటితే False. cache.add() మొదటిసారి
        మాత్రమే key ని TTL తో సెట్ చేస్తుంది (ఇప్పటికే ఉంటే no-op),
        తర్వాత cache.incr() atomic గా పెంచుతుంది -- prod లో (Redis
        cache backend) రేస్-కండిషన్-ఫ్రీ."""
        key = f"chat_ratelimit:{self.user.id}"
        cache.add(key, 0, timeout=RATE_LIMIT_WINDOW_SECONDS)
        try:
            count = cache.incr(key)
        except ValueError:
            cache.set(key, 1, timeout=RATE_LIMIT_WINDOW_SECONDS)
            count = 1
        return count <= RATE_LIMIT_MAX_ACTIONS

    # ------------------------------------------------------------------
    # DB helpers (sync ORM కోడ్ ని async consumer లోపల సురక్షితంగా
    # రన్ చేయడానికి database_sync_to_async వాడాలి -- Channels docs లో
    # ఇదే సిఫారసు చేసిన పద్ధతి).
    # ------------------------------------------------------------------
    @database_sync_to_async
    def _is_participant(self):
        from .models import Conversation
        try:
            conversation = Conversation.objects.get(pk=self.conversation_id)
        except Conversation.DoesNotExist:
            return False
        return conversation.is_participant(self.user)

    @database_sync_to_async
    def _create_message(self, body):
        from .models import Conversation, Message
        conversation = Conversation.objects.get(pk=self.conversation_id)
        message = Message.objects.create(
            conversation=conversation, sender=self.user, body=body,
        )
        conversation.save(update_fields=["updated_at"])
        return message

    @database_sync_to_async
    def _edit_message(self, message_id, new_body):
        from django.utils import timezone
        from .models import Message
        try:
            message = Message.objects.get(
                pk=message_id, conversation_id=self.conversation_id, sender=self.user,
            )
        except Message.DoesNotExist:
            return None
        if message.is_deleted:
            return None
        message.body = new_body
        message.is_edited = True
        message.edited_at = timezone.now()
        message.save(update_fields=["body", "is_edited", "edited_at"])
        return message

    @database_sync_to_async
    def _delete_message(self, message_id):
        from .models import Message
        try:
            message = Message.objects.get(
                pk=message_id, conversation_id=self.conversation_id, sender=self.user,
            )
        except Message.DoesNotExist:
            return False
        message.soft_delete()
        return True

    @database_sync_to_async
    def _set_reaction(self, message_id, emoji):
        from .models import Message, MessageReaction
        try:
            message = Message.objects.get(pk=message_id, conversation_id=self.conversation_id)
        except Message.DoesNotExist:
            return None
        if not message.conversation.is_participant(self.user):
            return None
        MessageReaction.objects.update_or_create(
            message=message, user=self.user, defaults={"emoji": emoji},
        )
        return [
            {"user_id": r.user_id, "emoji": r.emoji}
            for r in message.reactions.select_related("user")
        ]

    @database_sync_to_async
    def _mark_read(self, message_id):
        from .models import Message
        try:
            message = Message.objects.get(pk=message_id, conversation_id=self.conversation_id)
        except Message.DoesNotExist:
            return False
        if not message.conversation.is_participant(self.user):
            return False
        message.read_by.add(self.user)
        message.delivered_to.add(self.user)
        return True

    @database_sync_to_async
    def _get_members_presence(self):
        from .models import Conversation, UserPresence
        conversation = Conversation.objects.get(pk=self.conversation_id)
        result = []
        for member in conversation.members.exclude(pk=self.user.pk):
            presence = UserPresence.objects.filter(user=member).first()
            result.append({
                "user_id": member.id,
                "is_online": presence.is_online if presence else False,
                "last_seen": presence.last_seen.isoformat() if presence else None,
            })
        return result

    @database_sync_to_async
    def _mark_undelivered_as_delivered(self):
        from .models import Conversation
        conversation = Conversation.objects.get(pk=self.conversation_id)
        undelivered = conversation.messages.exclude(sender=self.user).exclude(delivered_to=self.user)
        ids = list(undelivered.values_list("id", flat=True))
        for message in undelivered:
            message.delivered_to.add(self.user)
        return ids

    @database_sync_to_async
    def _get_own_message(self, message_id):
        from .models import Message
        try:
            return Message.objects.get(
                pk=message_id, conversation_id=self.conversation_id, sender=self.user,
            )
        except Message.DoesNotExist:
            return None

    @database_sync_to_async
    def _serialize(self, message):
        from .views import _serialize_message
        return _serialize_message(message, self.user)

    @database_sync_to_async
    def _set_presence(self, is_online):
        from .models import UserPresence
        UserPresence.objects.update_or_create(
            user=self.user, defaults={"is_online": is_online},
        )

    @database_sync_to_async
    def _notify_offline_recipients(self, message_id):
        """సందేశం అందుకోవాల్సిన వాళ్ళలో ఎవరైనా ప్రస్తుతం ఆఫ్‌లైన్‌లో
        ఉంటే, వాళ్ళకి Celery ద్వారా ఈమెయిల్ + బ్రౌజర్ push నోటిఫికేషన్
        రెండూ పంపడానికి టాస్క్‌లని క్యూ లో పెడతాం (ఇక్కడే సింక్రొనస్‌గా
        పంపడం లేదు -- అది request/consumer ని బ్లాక్ చేస్తుంది)."""
        from .models import Message, UserPresence
        from .tasks import send_new_message_email, send_push_notification

        try:
            message = Message.objects.select_related("conversation").get(pk=message_id)
        except Message.DoesNotExist:
            return
        recipients = message.conversation.members.exclude(pk=self.user.pk)
        for recipient in recipients:
            presence = UserPresence.objects.filter(user=recipient).first()
            is_online = presence.is_online if presence else False
            if not is_online:
                send_new_message_email.delay(recipient.id, message.conversation_id, message.id)
                send_push_notification.delay(recipient.id, message.conversation_id, message.id)
