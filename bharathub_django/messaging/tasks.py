"""
messaging/tasks.py

ఆఫ్‌లైన్‌లో ఉన్న యూజర్‌కి కొత్త మెసేజ్ వచ్చినప్పుడు, ఈమెయిల్
నోటిఫికేషన్ పంపే Celery టాస్క్. consumers.py లోని
_notify_offline_recipients() దీన్ని .delay() తో క్యూ లో పెడుతుంది --
ఈమెయిల్ పంపడం (SMTP రౌండ్-ట్రిప్) నెమ్మదిగా ఉండొచ్చు కాబట్టి, అది
ఎప్పుడూ మెయిన్ WebSocket/request cycle ని బ్లాక్ చేయకూడదు.

DEV లో (settings.CELERY_TASK_ALWAYS_EAGER=True): ప్రత్యేక worker
అవసరం లేకుండా, .delay() కాల్ చేసిన వెంటనే ఇదే ప్రాసెస్ లో రన్
అవుతుంది, EMAIL_BACKEND=console కాబట్టి నిజంగా ఈమెయిల్ పంపే బదులు
టెర్మినల్ లో ప్రింట్ అవుతుంది.

PRODUCTION లో: `celery -A bharathub worker -l info` తో ప్రత్యేక
worker process రన్ చేయాలి, EMAIL_BACKEND ని నిజమైన SMTP కి మార్చాలి,
REDIS_URL ఒక నిజమైన Redis సర్వర్ ని పాయింట్ చేయాలి.
"""
import json

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_new_message_email(self, recipient_id, conversation_id, message_id):
    from django.contrib.auth import get_user_model

    from .models import Conversation, Message

    User = get_user_model()

    try:
        recipient = User.objects.get(pk=recipient_id)
        message = Message.objects.select_related("sender").get(pk=message_id)
        conversation = Conversation.objects.get(pk=conversation_id)
    except (User.DoesNotExist, Message.DoesNotExist, Conversation.DoesNotExist):
        return  # ఏదైనా ఈలోపు డిలీట్ అయిపోతే, retry చేయాల్సిన అవసరం లేదు

    if not recipient.email:
        return

    sender_name = message.sender.get_full_name() or message.sender.username
    preview = (message.body or "[Attachment]")[:120]

    try:
        send_mail(
            subject=f"BharatHub — New message from {sender_name}",
            message=(
                f"{sender_name}: {preview}\n\n"
                f"Log in to BharatHub to reply."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient.email],
            fail_silently=False,
        )
    except Exception as exc:  # SMTP సర్వర్ డౌన్ అయినా, retry తర్వాత మళ్ళీ ప్రయత్నిస్తుంది
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_push_notification(self, recipient_id, conversation_id, message_id):
    """ఆఫ్‌లైన్ (లేదా ప్రస్తుతం ఆ చాట్ ట్యాబ్ తెరవని) యూజర్‌కి బ్రౌజర్
    desktop notification పంపుతుంది. ఈమెయిల్ (పైన) కి ప్రత్యామ్నాయం
    కాదు -- రెండూ కలిసి పంపుతాం (consumers.py: _notify_offline_recipients).

    VAPID కీలు సెట్ చేయకపోతే (settings.VAPID_PRIVATE_KEY ఖాళీ),
    నిశ్శబ్దంగా స్కిప్ అవుతుంది -- ఇది dev లో అస్సలు క్రాష్ కాకూడదు
    అని, కేవలం production లో మాత్రమే ఈ ఫీచర్ ఆన్ అవ్వాలని.
    """
    if not settings.VAPID_PRIVATE_KEY:
        return

    from pywebpush import WebPushException, webpush

    from django.contrib.auth import get_user_model
    from django.urls import reverse

    from .models import Message, PushSubscription

    User = get_user_model()

    try:
        message = Message.objects.select_related("sender").get(pk=message_id)
        recipient = User.objects.get(pk=recipient_id)
    except (Message.DoesNotExist, User.DoesNotExist):
        return

    sender_name = message.sender.get_full_name() or message.sender.username
    preview = (message.body or "📎 Attachment")[:120]

    # BUG FIX: ఇంతకుముందు ఇక్కడ URL పంపేవాళ్ళం కాదు -- service worker
    # ఎప్పుడూ హోమ్‌పేజీనే తెరిచేది, ఆ సంభాషణ లోకి నేరుగా తీసుకెళ్ళేది
    # కాదు. యూజర్ role (Employee/Employer/Vendor) బట్టి సరైన messaging
    # పేజీ URL కి ?c=<conversation_id> జోడించి పంపుతున్నాం.
    if hasattr(recipient, "employer_profile"):
        base_url = reverse("messaging:employer_messages")
    elif hasattr(recipient, "vendor_profile"):
        base_url = reverse("messaging:vendor_messages")
    else:
        base_url = reverse("messaging:candidate_messages")
    conversation_url = f"{settings.SITE_BASE_URL}{base_url}?c={conversation_id}"

    subscriptions = PushSubscription.objects.filter(user_id=recipient_id)
    for subscription in subscriptions:
        if not subscription.is_endpoint_safe():
            # SSRF గార్డ్ (డిఫెన్స్-ఇన్-డెప్త్): ఏదైనా కారణంగా ఈ
            # రో దాటుకుని వచ్చినా, ఇక్కడే ఆపేస్తాం -- ఎప్పుడూ
            # తెలియని హోస్ట్‌కి outbound రిక్వెస్ట్ పంపము.
            continue
        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
                },
                data=json.dumps({
                    "title": f"BharatHub — {sender_name}",
                    "body": preview,
                    "conversation_id": conversation_id,
                    "url": conversation_url,
                }),
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": settings.VAPID_CLAIM_EMAIL},
            )
        except WebPushException as exc:
            # 404/410 అంటే ఆ subscription ఇక చెల్లదు (యూజర్
            # notifications ఆఫ్ చేసుకున్నారు, లేదా బ్రౌజర్ డేటా
            # క్లియర్ చేశారు) -- ఆ రికార్డ్ ని తీసేస్తాం, retry
            # అవసరం లేదు. మిగతా ఎర్రర్‌లకి (503 వంటివి) retry
            # చేయడం అర్థవంతం.
            status_code = getattr(exc.response, "status_code", None)
            if status_code in (404, 410):
                subscription.delete()
            else:
                raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def send_call_push_notification(self, recipient_id, room_url, started_by_name):
    """
    📹 వీడియో కాల్ మొదలైనప్పుడు రెండో యూజర్‌కి పంపే push notification.

    ఎందుకు ఇది కావాలి: "call.started" WebSocket event ఇంతకుముందు
    ఆ నిర్దిష్ట conversation ఓపెన్ చేసి, ఆ ఛానల్‌కి live గా కనెక్ట్
    అయి ఉన్న యూజర్‌కి మాత్రమే చేరేది -- మిగతా ఏ పేజీలోనైనా ఉంటే
    (లేదా టాబ్ మూసేసి ఉంటే) ఏమీ తెలిసేది కాదు, కాల్ మొదలైందని
    తెలియకుండానే మిస్ అయ్యేది (ఇదే "నా వైపు మాత్రమే కెమెరా ఆన్
    అయ్యింది, అవతలి యూజర్ కి ఏమీ కనిపించలేదు" అనే బగ్ కి అసలు కారణం).

    ఇప్పుడు StartConversationCallView, WebSocket broadcast తో పాటు
    ఇదే push notification కూడా పంపుతుంది -- browser tab మూసేసినా,
    వేరే పేజీలో ఉన్నా, OS-level నోటిఫికేషన్ (room లింక్ తో సహా)
    వస్తుంది.
    """
    if not settings.VAPID_PRIVATE_KEY:
        return

    from pywebpush import WebPushException, webpush

    from .models import PushSubscription

    subscriptions = PushSubscription.objects.filter(user_id=recipient_id)
    for subscription in subscriptions:
        if not subscription.is_endpoint_safe():
            continue
        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
                },
                data=json.dumps({
                    "title": f"📹 {started_by_name} started a video call",
                    "body": "Tap to join the call now",
                    "url": room_url,
                }),
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": settings.VAPID_CLAIM_EMAIL},
            )
        except WebPushException as exc:
            status_code = getattr(exc.response, "status_code", None)
            if status_code in (404, 410):
                subscription.delete()
            else:
                raise self.retry(exc=exc)
