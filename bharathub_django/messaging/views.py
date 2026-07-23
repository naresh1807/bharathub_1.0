import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.html import escape
from django.views.generic import TemplateView, View

from .forms import GroupForm, MessageForm
from .models import Conversation, Message, PushSubscription
from .permissions import avatar_url_for, can_message, contacts_for, _role_of

# ============================================================================
# messaging/views.py
#
# Employee (candidate) ⇄ Employer ⇄ Vendor -- మూడు డాష్‌బోర్డుల్లోనూ
# ఇదే బ్యాకెండ్ లాజిక్ పని చేస్తుంది. ఇప్పుడు ఇక్కడ మూడు రకాల
# ఎండ్‌పాయింట్లు ఉన్నాయి:
#   1. పేజీ వ్యూలు (TemplateView) -- చాట్ షెల్ HTML ని రెండర్ చేస్తాయి,
#      అసలైన మెసేజ్ పంపడం/అందుకోవడం ఇప్పుడు WebSocket ద్వారానే
#      జరుగుతుంది (messaging/consumers.py చూడండి).
#   2. REST-తరహా JSON APIలు -- ఫైల్ అప్‌లోడ్ (HTTP), పాత మెసేజ్‌ల
#      పేజినేషన్ (infinite scroll), గ్రూప్ క్రియేట్/add/remove.
#   3. SendMessageView: WebSocket లేని బ్రౌజర్ల కోసం fallback మాత్రమే
#      (JS లేకపోయినా చాట్ కనీసం పనిచేయాలి).
#
# SECURITY: ప్రతి view LoginRequiredMixin తో మొదలవుతుంది, ప్రతి
# conversation యాక్సెస్ కి ముందు conversation.is_participant(user)
# చెక్ అవుతుంది (IDOR గార్డ్).
# ============================================================================

User = get_user_model()

ATTACHMENT_MAX_MB = 10
attachment_extension_validator = FileExtensionValidator(
    allowed_extensions=[
        "jpg", "jpeg", "png", "gif", "webp",  # images
        "pdf", "doc", "docx", "xls", "xlsx", "txt",  # documents
    ],
)


class _RoleMessagesMixin(LoginRequiredMixin):
    """dashboard_url_name: ఆ రోల్ కి సంబంధించిన 'తిరిగి డాష్‌బోర్డ్ కి'
    లింక్ కోసం. redirect_url_name: సందేశం పంపిన తర్వాత ఇదే పేజీ కి
    తిరిగి రావడానికి (ప్రతి రోల్ కి దాని సొంత messages URL name)."""
    redirect_url_name = ""  # subclasses override

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # members=user: direct మరియు group రెండు రకాల conversations
        # నీ ఒక్కటే query లో తీసుకొస్తుంది.
        conversations = list(
            Conversation.objects.filter(members=user)
            .select_related("participant_one", "participant_two")
            .prefetch_related("members")
            .distinct()
        )

        active_id = self.request.GET.get("c")
        active_conversation = None
        thread_messages = []
        if active_id:
            active_conversation = next(
                (c for c in conversations if str(c.pk) == str(active_id)), None,
            )
            if active_conversation is not None:
                thread_messages = list(
                    active_conversation.messages
                    .select_related("sender")
                    .prefetch_related("reactions", "read_by", "delivered_to")
                    .order_by("-created_at")[:30][::-1]  # చివరి 30 మెసేజ్‌లు, పాతవి ముందు
                )
                unread = active_conversation.messages.exclude(sender=user)
                for m in unread:
                    m.read_by.add(user)
                    m.delivered_to.add(user)

        conv_rows = []
        for c in conversations:
            if c.chat_type == Conversation.ChatType.GROUP:
                display_name = c.name or "Group"
                other = None
                avatar_url = c.group_photo.url if c.group_photo else None
            else:
                other = c.other_participant(user)
                display_name = _display_name(other) if other else "Unknown"
                avatar_url = avatar_url_for(other) if other else None
            last_msg = c.messages.last()
            unread_count = c.messages.exclude(sender=user).exclude(read_by=user).count()
            conv_rows.append({
                "conversation": c,
                "other_user": other,
                "other_name": display_name,
                "avatar_url": avatar_url,
                "last_message": last_msg,
                "unread_count": unread_count,
            })
        conv_rows.sort(key=lambda r: r["conversation"].updated_at, reverse=True)

        active_avatar_url = None
        if active_conversation is not None:
            if active_conversation.chat_type == Conversation.ChatType.GROUP:
                active_avatar_url = active_conversation.group_photo.url if active_conversation.group_photo else None
            else:
                active_avatar_url = avatar_url_for(active_conversation.other_participant(user))

        new_contacts = contacts_for(user)

        context.update({
            "conversation_rows": conv_rows,
            "active_conversation": active_conversation,
            "active_other_name": (
                (active_conversation.name or "Group")
                if active_conversation and active_conversation.chat_type == Conversation.ChatType.GROUP
                else (_display_name(active_conversation.other_participant(user)) if active_conversation else None)
            ),
            "active_avatar_url": active_avatar_url,
            "thread_messages": thread_messages,
            "message_form": MessageForm(),
            "group_form": GroupForm(),
            "new_contacts": new_contacts,
            "new_contacts_json": json.dumps([
                {
                    "id": c["user"].id,
                    "name": c["name"],
                    "identifier": c["identifier"],
                    "avatar_url": c["avatar_url"] or "",
                }
                for c in new_contacts
            ]).replace("</", "<\\/"),  # ఒక కంపెనీ/candidate పేరులో
            # "</script>" లాంటి స్ట్రింగ్ ఉంటే, ఇది <script type=
            # "application/json"> ట్యాగ్ ని బ్రేక్ చేయకుండా ఆపుతుంది.
            "redirect_url_name": self.redirect_url_name,
            "unread_message_count": sum(r["unread_count"] for r in conv_rows),
            "vapid_public_key": settings.VAPID_PUBLIC_KEY,
            # JS (WS క్లయింట్) కి కావాల్సిన ఐడీలు -- websocket URL
            # కట్టడానికి, "ఇది నా సందేశమా" అని చెక్ చేయడానికి.
            "current_user_id": user.id,
        })
        return context


def unread_total_for(user) -> int:
    """ఈ యూజర్ కి మొత్తం (అన్ని conversations కలిపి) చదవని మెసేజ్‌ల
    సంఖ్య -- topnav "💬 Messages" ట్యాబ్ పైన badge చూపించడానికి.
    candidates/employers/vendor dashboard views ఇదే దిగుమతి చేసుకుని
    వాడతాయి (ఆ మూడు dashboardల్లోనూ, messaging పేజీ కి వెళ్ళకుండానే
    ఎన్ని unread ఉన్నాయో కనిపించాలి)."""
    if not getattr(user, "is_authenticated", False):
        return 0
    return (
        Message.objects.filter(conversation__members=user)
        .exclude(sender=user)
        .exclude(read_by=user)
        .count()
    )


def _display_name(user):
    if user is None:
        return "Unknown"
    role, profile = _role_of(user)
    if role == "candidate":
        return user.get_full_name() or user.username
    if role == "employer":
        return profile.company_name
    if role == "vendor":
        return profile.shop_name
    return user.get_full_name() or user.username


class EmployerMessagesView(_RoleMessagesMixin, TemplateView):
    template_name = "messaging/employer_messages.html"
    login_url = "accounts:employer_login"
    redirect_url_name = "messaging:employer_messages"


class VendorMessagesView(_RoleMessagesMixin, TemplateView):
    template_name = "messaging/vendor_messages.html"
    login_url = "vendor:vendor_login"
    redirect_url_name = "messaging:vendor_messages"


class CandidateMessagesView(_RoleMessagesMixin, TemplateView):
    template_name = "messaging/candidate_messages.html"
    login_url = "accounts:employee_login"
    redirect_url_name = "messaging:candidate_messages"


class SendMessageView(LoginRequiredMixin, View):
    """POST-only fallback (JS లేని బ్రౌజర్ల కోసం). JS ఉన్నప్పుడు,
    క్లయింట్ దీని బదులు WebSocket ద్వారానే మెసేజ్ పంపుతుంది
    (consumers.py లోని 'message.send')."""

    def post(self, request, pk, *args, **kwargs):
        conversation = get_object_or_404(Conversation, pk=pk)
        if not conversation.is_participant(request.user):
            messages.error(request, "⚠️ మీకు ఈ సంభాషణ యాక్సెస్ లేదు.")
            return redirect(_home_redirect(request.user))

        form = MessageForm(request.POST)
        if form.is_valid():
            Message.objects.create(
                conversation=conversation,
                sender=request.user,
                body=form.cleaned_data["body"],
            )
            conversation.save(update_fields=["updated_at"])
        else:
            messages.error(request, "⚠️ సందేశం పంపడంలో సమస్య వచ్చింది.")

        redirect_name = _redirect_name_for(request.user)
        return redirect(f"{reverse(redirect_name)}?c={conversation.pk}")


class StartConversationView(LoginRequiredMixin, View):
    """'కొత్త చాట్' -- target యూజర్ తో ఇప్పటికే వ్యాపార సంబంధం
    (job application / order) ఉంటేనే conversation క్రియేట్ అవుతుంది."""

    def post(self, request, *args, **kwargs):
        target = get_object_or_404(User, pk=request.POST.get("user_id"))

        if not can_message(request.user, target):
            messages.error(
                request,
                "⚠️ మీకు మరియు వీరికి మధ్య ఇంకా ఏ వ్యాపార సంబంధం (job "
                "application / order) లేదు కాబట్టి చాట్ మొదలుపెట్టలేరు.",
            )
            return redirect(_home_redirect(request.user))

        conversation = Conversation.get_or_create_between(request.user, target)
        redirect_name = _redirect_name_for(request.user)
        return redirect(f"{reverse(redirect_name)}?c={conversation.pk}")


# ============================================================================
# Group chat: create / add member / remove member
# ============================================================================

class CreateGroupView(LoginRequiredMixin, View):
    """కొత్త గ్రూప్ క్రియేట్ చేస్తుంది. సభ్యులు ఎవరిని ఎంచుకోవచ్చు --
    ప్రస్తుతం ఆ యూజర్ కి contacts_for() లో కనిపించే వాళ్ళనే (అంటే,
    ఇప్పటికే ఏదో వ్యాపార సంబంధం ఉన్నవాళ్ళనే) group లోకి యాడ్ చేయగలరు,
    దీనివల్ల గ్రూప్‌ల ద్వారా కూడా అపరిచితులకి స్పామ్ చేయలేరు."""

    def post(self, request, *args, **kwargs):
        form = GroupForm(request.POST, request.FILES)
        member_ids = request.POST.getlist("member_ids")

        if not form.is_valid():
            for error in form.errors.get("name", []):
                messages.error(request, f"⚠️ {error}")
            return redirect(_home_redirect(request.user))

        allowed_ids = {c["user"].id for c in contacts_for(request.user)}
        chosen_ids = {int(i) for i in member_ids if i.isdigit()} & allowed_ids
        if not chosen_ids:
            messages.error(request, "⚠️ కనీసం ఒక్క సభ్యుడినైనా ఎంచుకోండి.")
            return redirect(_home_redirect(request.user))

        member_users = User.objects.filter(id__in=chosen_ids)
        conversation = Conversation.create_group(form.cleaned_data["name"], request.user, member_users)
        if form.cleaned_data.get("photo"):
            conversation.group_photo = form.cleaned_data["photo"]
            conversation.save(update_fields=["group_photo"])
        Message.objects.create(
            conversation=conversation, sender=request.user,
            message_type=Message.MessageType.SYSTEM,
            body=f"{_display_name(request.user)} created the group “{form.cleaned_data['name']}”",
        )
        redirect_name = _redirect_name_for(request.user)
        return redirect(f"{reverse(redirect_name)}?c={conversation.pk}")


class RenameGroupView(LoginRequiredMixin, View):
    """గ్రూప్ పేరు/ఫోటో మార్చడం -- అడ్మిన్ మాత్రమే (WhatsApp తరహా
    admin controls లో భాగం). ఖాళీ 'photo' అంటే ఫోటో మార్చట్లేదు అని
    అర్థం (ఫారమ్ లో required=False కాబట్టి)."""

    def post(self, request, pk, *args, **kwargs):
        conversation = get_object_or_404(
            Conversation, pk=pk, chat_type=Conversation.ChatType.GROUP,
        )
        if conversation.admin_id != request.user.id:
            messages.error(request, "⚠️ గ్రూప్ అడ్మిన్ మాత్రమే గ్రూప్ వివరాలు మార్చగలరు.")
            return redirect(_home_redirect(request.user))

        form = GroupForm(request.POST, request.FILES)
        if not form.is_valid():
            for error in form.errors.get("name", []):
                messages.error(request, f"⚠️ {error}")
            return redirect(f"{reverse(_redirect_name_for(request.user))}?c={conversation.pk}")

        old_name = conversation.name
        conversation.name = form.cleaned_data["name"]
        update_fields = ["name"]
        if form.cleaned_data.get("photo"):
            conversation.group_photo = form.cleaned_data["photo"]
            update_fields.append("group_photo")
        conversation.save(update_fields=update_fields)

        if old_name != conversation.name:
            Message.objects.create(
                conversation=conversation, sender=request.user,
                message_type=Message.MessageType.SYSTEM,
                body=f"{_display_name(request.user)} changed the group name to “{conversation.name}”",
            )
        redirect_name = _redirect_name_for(request.user)
        return redirect(f"{reverse(redirect_name)}?c={conversation.pk}")


class LeaveGroupView(LoginRequiredMixin, View):
    """WhatsApp తరహాలో, ఏ సభ్యుడైనా (అడ్మిన్ తో సహా) ఎప్పుడైనా గ్రూప్
    ని తనంతట తానే వదిలేయగలరు -- దీనికి అడ్మిన్ అనుమతి అవసరం లేదు
    (ఇది GroupMemberUpdateView.remove తో వేరు -- అది అడ్మిన్ మాత్రమే
    ఇతరులని తీసేయడానికి)."""

    def post(self, request, pk, *args, **kwargs):
        conversation = get_object_or_404(
            Conversation, pk=pk, chat_type=Conversation.ChatType.GROUP,
        )
        if not conversation.is_participant(request.user):
            raise Http404

        conversation.members.remove(request.user)
        Message.objects.create(
            conversation=conversation, sender=request.user,
            message_type=Message.MessageType.SYSTEM,
            body=f"{_display_name(request.user)} left the group",
        )
        # అడ్మిన్ నే గ్రూప్ వదిలేస్తే, గ్రూప్ అనాథ (admin-less) కాకుండా
        # మిగిలిన సభ్యుల్లో మొదటివారికి అడ్మిన్ బాధ్యత అప్పగిస్తాం
        # (WhatsApp కూడా ఇలాగే ఆటోమేటిక్‌గా కొత్త అడ్మిన్ ని ఎంచుకుంటుంది).
        if conversation.admin_id == request.user.id:
            next_admin = conversation.members.exclude(pk=request.user.id).first()
            conversation.admin = next_admin
            conversation.save(update_fields=["admin"])
            if next_admin:
                Message.objects.create(
                    conversation=conversation, sender=request.user,
                    message_type=Message.MessageType.SYSTEM,
                    body=f"{_display_name(next_admin)} is now the group admin",
                )

        messages.success(request, "మీరు గ్రూప్ నుండి బయటకు వచ్చారు.")
        return redirect(_home_redirect(request.user))


class GroupMemberUpdateView(LoginRequiredMixin, View):
    """POST {action: 'add'|'remove', user_id}. కేవలం group admin
    మాత్రమే వాడగలరు (WhatsApp తరహా admin controls)."""

    def post(self, request, pk, *args, **kwargs):
        conversation = get_object_or_404(
            Conversation, pk=pk, chat_type=Conversation.ChatType.GROUP,
        )
        if conversation.admin_id != request.user.id:
            messages.error(request, "⚠️ గ్రూప్ అడ్మిన్ మాత్రమే సభ్యులని add/remove చేయగలరు.")
            return redirect(_home_redirect(request.user))

        action = request.POST.get("action")
        target = get_object_or_404(User, pk=request.POST.get("user_id"))

        if action == "add":
            if not can_message(request.user, target):
                messages.error(request, "⚠️ వీరిని గ్రూప్ లోకి యాడ్ చేయలేరు.")
                return redirect(_home_redirect(request.user))
            conversation.members.add(target)
            Message.objects.create(
                conversation=conversation, sender=request.user,
                message_type=Message.MessageType.SYSTEM,
                body=f"{_display_name(request.user)} added {_display_name(target)}",
            )
        elif action == "remove":
            # అడ్మిన్ తనని తానే ఇక్కడి నుండి తీసేసుకుంటే, admin_id ఒక
            # ఇక సభ్యుడు కాని యూజర్‌ని పాయింట్ చేస్తూ గ్రూప్
            # "అనాథ" (admin-less, ఎవరూ దాన్ని manage చేయలేని స్థితి)
            # అయిపోతుంది -- దాన్ని ఆపడానికి ఈ endpoint తో తనని తానే
            # తీసేసుకోనివ్వం, బదులుగా LeaveGroupView వాడాలి (అది
            # కొత్త అడ్మిన్ ని సరిగ్గా అప్పగిస్తుంది).
            if target.id == request.user.id:
                messages.error(
                    request,
                    "⚠️ మీరు అడ్మిన్ గా ఉండి మిమ్మల్ని మీరు తీసేసుకోలేరు -- "
                    "బదులుగా 'Leave Group' వాడండి.",
                )
                return redirect(f"{reverse(_redirect_name_for(request.user))}?c={conversation.pk}")
            conversation.members.remove(target)
            Message.objects.create(
                conversation=conversation, sender=request.user,
                message_type=Message.MessageType.SYSTEM,
                body=f"{_display_name(request.user)} removed {_display_name(target)}",
            )

        redirect_name = _redirect_name_for(request.user)
        return redirect(f"{reverse(redirect_name)}?c={conversation.pk}")


# ============================================================================
# JSON APIs (used by the WebSocket-powered chat UI)
# ============================================================================

class ConversationHistoryView(LoginRequiredMixin, View):
    """GET /messaging/conversation/<pk>/history/?before=<message_id>
    -- Infinite scroll: పైకి స్క్రోల్ చేసినప్పుడు, ఇంతకుముందు లోడ్
    అయిన అత్యంత పాత మెసేజ్ id ని 'before' గా పంపితే, దానికి ముందు
    ఉన్న 30 మెసేజ్‌లని తిరిగి ఇస్తుంది (ఒకేసారి మొత్తం థ్రెడ్
    లోడ్ చేయకుండా, DB మీద భారం తగ్గించడానికి)."""

    PAGE_SIZE = 30

    def get(self, request, pk, *args, **kwargs):
        conversation = get_object_or_404(Conversation, pk=pk)
        if not conversation.is_participant(request.user):
            raise Http404

        qs = conversation.messages.select_related("sender").prefetch_related("reactions")
        before_id = request.GET.get("before")
        if before_id and before_id.isdigit():
            qs = qs.filter(pk__lt=int(before_id))

        page = list(qs.order_by("-created_at")[: self.PAGE_SIZE])
        page.reverse()

        return JsonResponse({
            "messages": [_serialize_message(m, request.user) for m in page],
            "has_more": len(page) == self.PAGE_SIZE,
        })


class MessageAttachmentUploadView(LoginRequiredMixin, View):
    """POST multipart/form-data {conversation_id, file} -- ఫైల్ ని
    సాధారణ HTTP ద్వారా అప్‌లోడ్ చేసి, DB లో ఒక Message రికార్డ్
    (attachment తో) క్రియేట్ చేస్తుంది. దీని JSON response ని client
    JS తీసుకొని, ఆ message_id/URL ని WebSocket ద్వారా బ్రాడ్‌కాస్ట్
    చేస్తుంది (consumers.py లోని 'message.attachment_sent' చూడండి)."""

    def post(self, request, *args, **kwargs):
        conversation = get_object_or_404(
            Conversation, pk=request.POST.get("conversation_id"),
        )
        if not conversation.is_participant(request.user):
            return JsonResponse({"error": "Forbidden"}, status=403)

        uploaded = request.FILES.get("file")
        if not uploaded:
            return JsonResponse({"error": "No file provided"}, status=400)

        if uploaded.size > ATTACHMENT_MAX_MB * 1024 * 1024:
            return JsonResponse(
                {"error": f"File too large (max {ATTACHMENT_MAX_MB}MB)"}, status=400,
            )
        try:
            attachment_extension_validator(uploaded)
        except ValidationError:
            return JsonResponse({"error": "Unsupported file type"}, status=400)

        is_image = uploaded.name.lower().rsplit(".", 1)[-1] in {"jpg", "jpeg", "png", "gif", "webp"}

        # SECURITY: ఒక్క ఎక్స్‌టెన్షన్ మాత్రమే చెక్ చేయడం సరిపోదు --
        # ఎవరైనా HTML/JS ఫైల్ ని "photo.jpg" అని పేరు పెట్టి అప్‌లోడ్
        # చేయొచ్చు (polyglot file). మీడియా సర్వర్ ఏదైనా కారణంగా
        # తప్పు Content-Type తో సర్వ్ చేస్తే, ఇది స్టోర్డ్-XSS కి
        # దారి తీయొచ్చు. కాబట్టి "image" అని క్లెయిమ్ చేసిన ప్రతి
        # ఫైల్‌ని Pillow తో నిజంగా డీకోడ్ అయ్యే image యేనా అని
        # ఇక్కడే ధృవీకరిస్తాం (ఇదే django.db.models.ImageField
        # లోపల చేసేది -- మనం FileField వాడుతున్నాం కాబట్టి ఇక్కడ
        # మ్యానువల్‌గా చేయాలి).
        if is_image:
            from PIL import Image, UnidentifiedImageError
            try:
                uploaded.seek(0)
                Image.open(uploaded).verify()
                uploaded.seek(0)
            except (UnidentifiedImageError, OSError):
                return JsonResponse({"error": "Invalid or corrupted image file"}, status=400)

        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            message_type=Message.MessageType.IMAGE if is_image else Message.MessageType.FILE,
            attachment=uploaded,
            attachment_name=uploaded.name,
        )
        conversation.save(update_fields=["updated_at"])

        return JsonResponse({"message": _serialize_message(message, request.user)})


class SavePushSubscriptionView(LoginRequiredMixin, View):
    """POST JSON {endpoint, keys: {p256dh, auth}} -- బ్రౌజర్
    pushManager.subscribe() తర్వాత వచ్చిన subscription ని DB లో
    సేవ్ చేస్తుంది (chat.js: registerPushNotifications()). ఇదే
    endpoint ఉంటే (వేరే యూజర్ గా లాగిన్ అయినా అదే బ్రౌజర్‌లో)
    update_or_create తో overwrite అవుతుంది.

    SECURITY (SSRF గార్డ్): tasks.py లోని send_push_notification ఈ
    'endpoint' విలువకే సర్వర్ సైడ్ నుండి నేరుగా HTTP POST చేస్తుంది
    (pywebpush ద్వారా). ఏ URL నైనా అంగీకరిస్తే, ఒక దురుద్దేశపూర్వక
    యూజర్ endpoint గా 'https://169.254.169.254/...' (cloud metadata)
    లాంటి internal URL పెట్టి, తనకే మెసేజ్ వచ్చేలా చేసి సర్వర్ ని
    (Celery worker ద్వారా) ఆ internal హోస్ట్ కి రిక్వెస్ట్ పంపేలా
    బలవంతం చేయగలరు (SSRF -- క్లౌడ్ క్రెడెన్షియల్స్ దొంగతనం లాంటి
    తీవ్రమైన దాడులకి దారి తీయొచ్చు). PushSubscription.is_endpoint_safe()
    తో ఖచ్చితంగా తెలిసిన బ్రౌజర్ push సర్వీస్ డొమైన్ల నుండే
    (Chrome/FCM, Firefox/Mozilla, Safari, Edge) ఉందా అని చెక్
    చేస్తాం -- లేకపోతే తిరస్కరిస్తాం.
    """

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            endpoint = data["endpoint"]
            p256dh = data["keys"]["p256dh"]
            auth = data["keys"]["auth"]
        except (json.JSONDecodeError, KeyError, TypeError):
            return JsonResponse({"error": "Invalid subscription payload"}, status=400)

        candidate = PushSubscription(endpoint=endpoint)
        if not candidate.is_endpoint_safe():
            return JsonResponse({"error": "Unrecognized push service endpoint"}, status=400)

        PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={"user": request.user, "p256dh": p256dh, "auth": auth},
        )
        return JsonResponse({"status": "subscribed"})

    def delete(self, request, *args, **kwargs):
        """యూజర్ notifications ఆఫ్ చేసుకుంటే, ఆ subscription ని DB
        నుండి తీసేయడానికి."""
        try:
            data = json.loads(request.body)
            endpoint = data["endpoint"]
        except (json.JSONDecodeError, KeyError, TypeError):
            return JsonResponse({"error": "Invalid payload"}, status=400)
        PushSubscription.objects.filter(endpoint=endpoint, user=request.user).delete()
        return JsonResponse({"status": "unsubscribed"})


class ConversationSearchView(LoginRequiredMixin, View):
    """GET /messaging/conversation/<pk>/search/?q=... -- ఈ conversation
    లో టెక్స్ట్ సెర్చ్. NOTE: Message.body ఎన్‌క్రిప్ట్ చేసి DB లో
    నిల్వ ఉంటుంది (fields.py: EncryptedTextField) కాబట్టి,
    .filter(body__icontains=...) లాంటి DB-level సెర్చ్ పనిచేయదు
    (ప్రతి ciphertext వేరుగా ఉంటుంది). అందుకని ఈ conversation లోని
    మెసేజ్‌లని (గరిష్టం SEARCH_SCAN_LIMIT వరకు, ఇటీవలివి ముందు)
    అప్లికేషన్ లెవెల్ లో decrypt చేసి, ఆ ప్లెయిన్‌టెక్స్ట్ మీదే
    పైథాన్‌లో సరిపోల్చుతాం. పెద్ద చాట్ హిస్టరీ ఉన్నా limit వల్ల
    రెస్పాన్స్ టైమ్ అదుపులో ఉంటుంది -- ఇది E2E ఎన్‌క్రిప్షన్
    ఎంచుకున్నందుకు వచ్చే ఉద్దేశపూర్వక trade-off (fields.py లోని
    నోట్ చూడండి)."""

    SEARCH_SCAN_LIMIT = 2000

    def get(self, request, pk, *args, **kwargs):
        conversation = get_object_or_404(Conversation, pk=pk)
        if not conversation.is_participant(request.user):
            raise Http404

        query = (request.GET.get("q") or "").strip().lower()
        if not query:
            return JsonResponse({"messages": []})

        candidates_qs = (
            conversation.messages.filter(is_deleted=False, message_type=Message.MessageType.TEXT)
            .select_related("sender")
            .order_by("-created_at")[: self.SEARCH_SCAN_LIMIT]
        )
        matches = [m for m in candidates_qs if query in m.body.lower()][:50]

        return JsonResponse({
            "messages": [_serialize_message(m, request.user) for m in matches],
        })


def _serialize_message(message: Message, viewer):
    """Message ని JSON-friendly dict గా మారుస్తుంది -- HTTP APIలు
    (history/upload) మరియు WebSocket consumer రెండూ ఇదే format
    వాడతాయి, తద్వారా client-side JS ఒక్కటే రెండరింగ్ కోడ్ రాస్తే
    సరిపోతుంది."""
    return {
        "id": message.pk,
        "conversation_id": message.conversation_id,
        "sender_id": message.sender_id,
        "sender_name": _display_name(message.sender),
        "sender_avatar_url": avatar_url_for(message.sender),
        "message_type": message.message_type,
        # escape(): DB లో plaintext గా ఉన్నా (encrypt/decrypt తర్వాత),
        # క్లయింట్ కి పంపేముందు HTML-escape చేస్తాం -- ఒకవేళ client JS
        # పొరపాటున innerHTML వాడినా XSS జరగకుండా ఇది రెండో పొర రక్షణ
        # (ప్రధాన రక్షణ: client ఎప్పుడూ textContent వాడాలి).
        "body": "" if message.is_deleted else escape(message.body),
        "attachment_url": (message.attachment.url if message.attachment else None),
        "attachment_name": message.attachment_name,
        "is_edited": message.is_edited,
        "is_deleted": message.is_deleted,
        "created_at": message.created_at.isoformat(),
        "delivery_state": message.delivery_state_for(viewer),
        "reactions": [
            {"user_id": r.user_id, "emoji": r.emoji} for r in message.reactions.all()
        ],
    }


def _redirect_name_for(user) -> str:
    role, _ = _role_of(user)
    return {
        "candidate": "messaging:candidate_messages",
        "employer": "messaging:employer_messages",
        "vendor": "messaging:vendor_messages",
    }.get(role, "home:bharathub_home")


def _home_redirect(user):
    return _redirect_name_for(user)
