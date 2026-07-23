from django.conf import settings
from django.db import models

from .fields import EncryptedTextField

# ============================================================================
# messaging/models.py
#
# ఇది WhatsApp-తరహా చాట్ కి ఫౌండేషన్:
#   - Conversation ఇప్పుడు 1-on-1 మాత్రమే కాదు, group చాట్ కి కూడా
#     ఉపయోగపడేలా (chat_type + members M2M + admin) విస్తరించాం.
#   - Message ఇప్పుడు edit/delete, రియాక్షన్స్, ఫైల్/ఇమేజ్
#     అటాచ్‌మెంట్లు, delivered/read రిసీట్‌లని (WhatsApp టిక్‌ల
#     కోసం) సపోర్ట్ చేస్తుంది.
#   - UserPresence: ఆన్‌లైన్/ఆఫ్‌లైన్ + "last seen" ట్రాక్ చేయడానికి.
#
# బ్యాక్‌వర్డ్-కంపాటబిలిటీ నోట్: participant_one/participant_two
# ఫీల్డ్స్ ఇంతకుముందు నుండి ఉన్నవే (1-1 చాట్ల డూప్లికేషన్ ఆపడానికి
# DB-level UniqueConstraint కోసం) -- గ్రూప్ చాట్‌లకి ఇవి NULL గా
# ఉంటాయి. ఎవరు ఏ conversation లో సభ్యులో చెప్పడానికి ఇప్పుడు అన్ని
# చోట్లా (1-1 మరియు group రెండిటికీ) ఒకటే మూలం: `members` M2M.
# ============================================================================


class Conversation(models.Model):

    class ChatType(models.TextChoices):
        DIRECT = "direct", "Direct (1-on-1)"
        GROUP = "group", "Group"

    chat_type = models.CharField(
        max_length=10, choices=ChatType.choices, default=ChatType.DIRECT,
    )

    # గ్రూప్ చాట్ కి మాత్రమే వాడతాం (WhatsApp లో యూజర్ ఇచ్చే గ్రూప్ పేరు).
    name = models.CharField(max_length=150, blank=True)
    group_photo = models.ImageField(
        upload_to="group_photos/%Y/%m/", blank=True, null=True,
    )

    # ── Direct (1-1) చాట్ కి మాత్రమే: డూప్లికేట్ conversation రాకుండా
    #    ఆపే UniqueConstraint ఇక్కడి మీదే ఆధారపడుతుంది. Group చాట్
    #    లకి రెండూ NULL గా ఉంటాయి (SQL లో NULL ఎప్పుడూ దేనికీ సమానం
    #    కాదు కాబట్టి, ఎన్ని group రికార్డులు ఉన్నా ఈ constraint కి
    #    అడ్డు రాదు).
    participant_one = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="conversations_as_one", null=True, blank=True,
    )
    participant_two = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="conversations_as_two", null=True, blank=True,
    )

    # ── Direct మరియు Group రెండిటికీ: "ఈ conversation లో ఎవరెవరు
    #    ఉన్నారు" అనేదానికి ఇదే ఏకైక, ఖచ్చితమైన మూలం. Consumers.py /
    #    views.py / permissions అన్నీ దీన్నే చెక్ చేస్తాయి.
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="conversations", blank=True,
    )

    # గ్రూప్ ని క్రియేట్ చేసిన యూజర్ -- ఇతనికే (WhatsApp తరహాలో)
    # మిగతా వారిని add/remove చేసే అధికారం (admin controls).
    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="administered_groups",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    # కొత్త మెసేజ్ వచ్చినప్పుడల్లా update_fields=["updated_at"] తో
    # touch చేస్తాం -- conversation జాబితా "ఇటీవల చాట్ చేసినవి ముందు"
    # క్రమంలో కనిపించడానికి (Meta.ordering చూడండి).
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["participant_one", "participant_two"],
                name="unique_conversation_pair",
            ),
        ]

    def __str__(self):
        if self.chat_type == self.ChatType.GROUP:
            return f"Group: {self.name} ({self.members.count()} members)"
        return f"{self.participant_one} ⇄ {self.participant_two}"

    # ------------------------------------------------------------------
    # is_participant(): ప్రతి request/WS కనెక్షన్ మీదా ఇదే IDOR గార్డ్
    # -- ఈ conversation లో సభ్యుడు కాని ఎవరూ దీన్ని చదవలేరు/రాయలేరు.
    # ------------------------------------------------------------------
    def is_participant(self, user) -> bool:
        if not getattr(user, "is_authenticated", False):
            return False
        return self.members.filter(pk=user.pk).exists()

    def other_participant(self, user):
        """Direct (1-1) చాట్‌లకి మాత్రమే అర్థవంతం -- రెండో యూజర్ ని
        రిటర్న్ చేస్తుంది."""
        if self.chat_type != self.ChatType.DIRECT:
            return None
        return self.participant_two if self.participant_one_id == user.id else self.participant_one

    @classmethod
    def get_or_create_between(cls, user_a, user_b):
        """1-1 చాట్ -- (A,B) మరియు (B,A) రెండూ ఒకే row కి మ్యాప్
        అయ్యేలా ఎప్పుడూ pk ఆధారంగా sorted order లో సేవ్ చేస్తాం."""
        low, high = sorted([user_a, user_b], key=lambda u: u.pk)
        conversation, created = cls.objects.get_or_create(
            participant_one=low, participant_two=high,
            defaults={"chat_type": cls.ChatType.DIRECT},
        )
        if created:
            conversation.members.add(low, high)
        return conversation

    @classmethod
    def create_group(cls, name, creator, member_users):
        """కొత్త గ్రూప్ చాట్ క్రియేట్ చేస్తుంది. creator ఆటోమేటిక్‌గా
        admin + సభ్యుడు అవుతాడు."""
        conversation = cls.objects.create(
            chat_type=cls.ChatType.GROUP, name=name, admin=creator,
        )
        conversation.members.add(creator, *member_users)
        return conversation


class Message(models.Model):

    class MessageType(models.TextChoices):
        TEXT = "text", "Text"
        IMAGE = "image", "Image"
        FILE = "file", "File"
        SYSTEM = "system", "System"  # "X added Y to the group" లాంటి నోటీసులు

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="sent_messages",
    )
    message_type = models.CharField(
        max_length=10, choices=MessageType.choices, default=MessageType.TEXT,
    )

    # ప్లెయిన్ TextField కాదు -- EncryptedTextField (fields.py) కాబట్టి
    # DB లో ఎప్పుడూ ciphertext మాత్రమే నిల్వ ఉంటుంది. ఇమేజ్/ఫైల్
    # మెసేజ్‌లకి ఇది ఖాళీగా ఉండొచ్చు (కేవలం caption ఉంటే తప్ప).
    body = EncryptedTextField(max_length=4000, blank=True)

    # ఫైల్/ఇమేజ్ మెసేజ్‌లకి -- HTTP ద్వారా ముందే అప్‌లోడ్ చేసిన ఫైల్,
    # ఆ తర్వాత దీని URL ని WebSocket ద్వారా బ్రాడ్‌కాస్ట్ చేస్తాం
    # (views.py లోని MessageAttachmentUploadView చూడండి).
    attachment = models.FileField(
        upload_to="chat_attachments/%Y/%m/", blank=True, null=True,
    )
    attachment_name = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    # ── Edit ──
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)

    # ── Delete for everyone ── (row అలాగే ఉంటుంది, కంటెంట్ మాత్రమే
    # ఖాళీ చేసి is_deleted=True చేస్తాం -- "This message was deleted"
    # అని చూపించడానికి soft_delete() వాడండి, .delete() కాదు.)
    is_deleted = models.BooleanField(default=False)

    # ── Delivery / Read receipts (WhatsApp టిక్‌ల కోసం) ──
    # ✓ (single)  : delivered_to ఖాళీ (సర్వర్ save చేసింది, ఇంకా ఎవరికీ
    #                చేరలేదు) -- created_at ఉంటే చాలు single-tick అనుకోవచ్చు.
    # ✓✓ (double) : delivered_to లో receiver ఉంటే.
    # ✓✓ (blue)   : read_by లో receiver ఉంటే.
    delivered_to = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="delivered_messages", blank=True,
    )
    read_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="read_messages", blank=True,
    )

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
        ]

    def __str__(self):
        return f"Message #{self.pk} in Conversation #{self.conversation_id}"

    def soft_delete(self):
        """'Delete for everyone' -- కంటెంట్ ని తీసేసి, is_deleted flag
        సెట్ చేస్తాం. టెంప్లేట్/consumer ఎప్పుడూ is_deleted చెక్ చేసి
        'This message was deleted' చూపించాలి, body నేరుగా వాడకూడదు."""
        self.body = ""
        self.attachment = None
        self.is_deleted = True
        self.save(update_fields=["body", "attachment", "is_deleted"])

    def delivery_state_for(self, viewer):
        """'sent' | 'delivered' | 'read' -- టిక్ చూపించడానికి.

        WhatsApp సెమాంటిక్స్: 1-1 చాట్‌లో ఒకే ఒక్క గ్రహీత ఉంటాడు కాబట్టి
        అతను చదివితే చాలు. కానీ GROUP చాట్‌లో బ్లూ టిక్ కావాలంటే
        సభ్యులందరూ (sender తప్ప) చదివి ఉండాలి -- ఒక్కరు చదివితే
        సరిపోదు. ఇంతకుముందు ఇక్కడ ఏ ఒక్కరు చదివినా 'read' అని
        చూపించేది -- ఇది 1-1 కి సరైనదే గానీ group కి తప్పు (5గురు
        సభ్యుల్లో 1 మంది చదివితేనే బ్లూ టిక్ చూపించేది).
        """
        other_member_ids = set(
            self.conversation.members.exclude(pk=self.sender_id).values_list("pk", flat=True)
        )
        if not other_member_ids:
            return "sent"
        read_ids = set(self.read_by.exclude(pk=self.sender_id).values_list("pk", flat=True))
        if other_member_ids.issubset(read_ids):
            return "read"
        delivered_ids = set(self.delivered_to.exclude(pk=self.sender_id).values_list("pk", flat=True))
        if other_member_ids.issubset(delivered_ids):
            return "delivered"
        return "sent"

    @property
    def is_read_by_others(self):
        """Django టెంప్లేట్‌లు మెథడ్‌కి ఆర్గ్యుమెంట్ పంపలేవు కాబట్టి,
        delivery_state_for() కి ఇది ఒక టెంప్లేట్-ఫ్రెండ్లీ షార్ట్‌కట్
        (_message_bubble.html లో టిక్‌ల కోసం వాడతాం)."""
        return self.delivery_state_for(self.sender) == "read"

    @property
    def is_delivered_to_others(self):
        return self.delivery_state_for(self.sender) in ("delivered", "read")

    @property
    def sender_avatar_url(self):
        """టెంప్లేట్‌లు (Django ఫంక్షన్‌కి ఆర్గ్యుమెంట్ పంపలేవు కాబట్టి)
        _message_bubble.html లో గ్రూప్ చాట్ బబుల్స్ పైన sender అవతార్
        చూపించడానికి ఇది వాడతాయి. WebSocket ద్వారా వచ్చే మెసేజ్‌లకి
        ఇదే విలువని views._serialize_message() JSON లో పంపుతుంది
        (permissions.avatar_url_for ఏకైక సోర్స్-ఆఫ్-ట్రూత్)."""
        from .permissions import avatar_url_for
        return avatar_url_for(self.sender)


class MessageReaction(models.Model):
    """ఒక్కో మెసేజ్ కి ఒక్కో యూజర్ ఒక్క ఎమోజీ మాత్రమే ఇవ్వగలరు
    (WhatsApp లో లాగే -- మళ్ళీ వేరే ఎమోజీ నొక్కితే పాతది replace
    అవుతుంది, రెండూ కలిసి ఉండవు)."""

    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name="reactions",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="message_reactions",
    )
    emoji = models.CharField(max_length=8)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["message", "user"], name="one_reaction_per_user_per_message",
            ),
        ]

    def __str__(self):
        return f"{self.user} reacted {self.emoji} to Message #{self.message_id}"


class UserPresence(models.Model):
    """ఆన్‌లైన్/ఆఫ్‌లైన్ + 'last seen' -- ChatConsumer.connect()/
    disconnect() ఈ రికార్డ్ ని అప్‌డేట్ చేస్తుంది. Celery టాస్క్
    (tasks.py) కూడా is_online చెక్ చేసి, ఆఫ్‌లైన్‌గా ఉంటేనే ఈమెయిల్
    నోటిఫికేషన్ పంపుతుంది."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="presence",
    )
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} — {'online' if self.is_online else 'offline'}"


class PushSubscription(models.Model):
    """బ్రౌజర్ Web Push API subscription -- ఒక్కో బ్రౌజర్/పరికరం
    ఒక్కో subscription (ఒకే యూజర్ రెండు పరికరాల్లో లాగిన్ అయితే
    రెండు వేర్వేరు రికార్డులు ఉంటాయి, రెండిటికీ push పంపుతాం).

    ఎలా వాడతారు: JS లో navigator.serviceWorker.register() +
    pushManager.subscribe() చేసి వచ్చిన {endpoint, keys: {p256dh,
    auth}} ని SavePushSubscriptionView కి POST చేస్తారు (chat.js
    చూడండి). tasks.py లోని send_push_notification ఈ రికార్డుల
    ఆధారంగా pywebpush తో పంపుతుంది.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="push_subscriptions",
    )
    endpoint = models.URLField(max_length=500, unique=True)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    # SSRF గార్డ్ (views.SavePushSubscriptionView లో ఇదే allow-list
    # వాడతాం, ఇక్కడ కూడా -- send TIME లో ఒకసారి మళ్ళీ చెక్ చేయడం
    # defense-in-depth, ఎవరైనా fixture/admin ద్వారా నేరుగా బ్యాడ్
    # రో ఇన్సర్ట్ చేసినా tasks.py అమాయకంగా దాన్ని కాల్ చేయకూడదు).
    ALLOWED_PUSH_HOSTS = (
        "fcm.googleapis.com",
        "updates.push.services.mozilla.com",
        "web.push.apple.com",
        "notify.windows.com",
    )

    def is_endpoint_safe(self) -> bool:
        from urllib.parse import urlparse
        try:
            parsed = urlparse(self.endpoint)
        except ValueError:
            return False
        if parsed.scheme != "https":
            return False
        host = (parsed.hostname or "").lower()
        return any(host == h or host.endswith("." + h) for h in self.ALLOWED_PUSH_HOSTS)

    def __str__(self):
        return f"Push subscription for {self.user} ({self.endpoint[:40]}…)"
