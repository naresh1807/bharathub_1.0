from django.contrib import admin

from .models import Conversation, Message, MessageReaction, PushSubscription, UserPresence

# SECURITY NOTE: Message.body ఇక్కడ కూడా (Django admin లో కూడా)
# EncryptedTextField.from_db_value() ద్వారానే వస్తుంది కాబట్టి admin
# లో decrypt అయిన plaintext కనిపిస్తుంది -- ఇది ఉద్దేశపూర్వకమే
# (సూపర్‌యూజర్ moderation/dispute-resolution కోసం చదవగలగాలి).
# admin ఖాతా ని ఎవరు access చేయగలరో అదే నియంత్రిస్తుంది ఎవరు
# సందేశాలు చదవగలరో -- కాబట్టి admin సూపర్‌యూజర్ పాస్‌వర్డ్ ఎప్పుడూ
# strong గా, పరిమిత మందికే ఉండాలి.


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "chat_type", "name", "participant_one", "participant_two", "admin", "updated_at")
    list_filter = ("chat_type",)
    readonly_fields = ("created_at", "updated_at")
    filter_horizontal = ("members",)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "sender", "message_type", "created_at", "is_edited", "is_deleted")
    readonly_fields = ("created_at",)
    list_filter = ("message_type", "is_edited", "is_deleted")


@admin.register(MessageReaction)
class MessageReactionAdmin(admin.ModelAdmin):
    list_display = ("id", "message", "user", "emoji", "created_at")


@admin.register(UserPresence)
class UserPresenceAdmin(admin.ModelAdmin):
    list_display = ("user", "is_online", "last_seen")
    list_filter = ("is_online",)


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "endpoint", "created_at")
    readonly_fields = ("created_at",)
