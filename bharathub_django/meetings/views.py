from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views import View
from django.views.generic import TemplateView

from .models import Meeting
from .utils import display_name_for, find_user_by_bharathub_id, notify_incoming_call
from messaging.permissions import _role_of

# ============================================================================
# meetings/views.py
# ============================================================================


def _meeting_list_redirect_name(user) -> str:
    """'🎥 Meetings' పేజీ (Personal Link / New Group Meeting / Send to a
    person) ఇంతకుముందు Employer ఖాతాలకి మాత్రమే ఉండేది -- ఇప్పుడు
    Candidate కి కూడా ఉంది (Vendor కి ఇంకా UI బిల్డ్ చేయలేదు, కానీ
    బ్యాకెండ్ ఏ రోల్ కైనా సిద్ధంగానే ఉంది -- కొత్తగా వాడేటప్పుడు ఇక్కడ
    ఒక్క లైన్ జోడిస్తే సరిపోతుంది). ఏ రోల్ దో బట్టి సరైన పేజీ కి
    రీడైరెక్ట్ చేయడానికి ఈ హెల్పర్ (messaging/views.py::
    _redirect_name_for() లో వాడిన అదే పద్ధతి)."""
    role, _ = _role_of(user)
    return {
        "employer": "meetings:meeting_list",
        "candidate": "meetings:candidate_meeting_list",
    }.get(role, "home:bharathub_home")


class MeetingRoomView(LoginRequiredMixin, TemplateView):
    """అసలైన Zoom-తరహా మీటింగ్ రూమ్ UI -- room.js ఇక్కడి WebSocket
    కనెక్షన్ (ws/meetings/room/<room_code>/) ద్వారా WebRTC సిగ్నలింగ్
    చేస్తుంది.

    గమనిక: ఇక్కడ ఉద్దేశపూర్వకంగా login_url సెట్ చేయలేదు -- ఒక మీటింగ్
    లింక్ ని Employee/Employer/Vendor ముగ్గురిలో ఎవరైనా తెరవొచ్చు, ఏ
    రోల్ దో ఈ URL లో ముందే తెలియదు. కాబట్టి లాగిన్ కాని యూజర్
    settings.LOGIN_URL (Home పేజీ) కి redirect అవుతారు -- అక్కడ
    ముగ్గురికీ లాగిన్ లింక్‌లు కనిపిస్తాయి, సరైనది వాళ్ళే
    ఎంచుకోగలరు."""

    template_name = "meetings/room.html"

    def get(self, request, *args, **kwargs):
        meeting = get_object_or_404(Meeting, room_code=kwargs["room_code"])
        if not meeting.is_participant_allowed(request.user):
            raise PermissionDenied("మీకు ఈ మీటింగ్ లోకి ప్రవేశం లేదు.")
        context = self.get_context_data(**kwargs)
        context["meeting"] = meeting
        context["display_name"] = display_name_for(request.user)
        context["room_ws_path"] = f"/ws/meetings/room/{meeting.room_code}/"
        context["ice_servers"] = [
            {"urls": "stun:stun.l.google.com:19302"},
            {"urls": "stun:stun1.l.google.com:19302"},
        ]
        return self.render_to_response(context)


class StartInstantMeetingView(LoginRequiredMixin, View):
    """'🎥 Meetings' పేజీ నుండి -- ఇన్‌స్టంట్ లేదా షెడ్యూల్డ్ గ్రూప్
    మీటింగ్ క్రియేట్ చేయడానికి. ఇంతకుముందు ఇది Employer ఖాతాలకి
    మాత్రమే ఉండేది (company meetings) -- ఇప్పుడు లాగిన్ అయిన ఎవరైనా
    (Candidate/Employer/Vendor) సొంత గ్రూప్ మీటింగ్ లింక్ క్రియేట్
    చేసుకోగలరు (Meeting.host ఏ యూజర్ అయినా కావొచ్చు, మోడల్ లోనే
    ముందే role-agnostic గా డిజైన్ చేశాం)."""

    def post(self, request, *args, **kwargs):
        redirect_name = _meeting_list_redirect_name(request.user)
        title = (request.POST.get("title") or "Company Meeting").strip()[:150]
        # ⚠️ మొబైల్ బగ్ ఫిక్స్: ఇంతకుముందు ఇక్కడ ఒకే
        # <input type="datetime-local"> వాడేవాళ్ళం -- చాలా మొబైల్
        # బ్రౌజర్లు/WebView లలో ఇది కేవలం డేట్ పికర్ నే తెరుస్తుంది,
        # టైమ్ పికర్ తెరవదు (ఇది datetime-local input కి బాగా తెలిసిన
        # క్రాస్-బ్రౌజర్ సమస్య). ఇప్పుడు date + time ని రెండు వేరే
        # ఫీల్డ్స్ గా తీసుకుంటాం (ఈ రెండిటికీ native picker support
        # అన్ని మొబైల్ బ్రౌజర్లలోనూ చాలా నమ్మదగినది), తర్వాత వాటిని
        # ఇక్కడే కలుపుతాం.
        scheduled_date = request.POST.get("scheduled_date", "").strip()
        scheduled_time = request.POST.get("scheduled_time", "").strip()
        scheduled_at = None
        if scheduled_date and scheduled_time:
            scheduled_at = parse_datetime(f"{scheduled_date}T{scheduled_time}")
            if scheduled_at and timezone.is_naive(scheduled_at):
                scheduled_at = timezone.make_aware(scheduled_at)

        meeting = Meeting.objects.create(
            title=title, meeting_type=Meeting.MeetingType.COMPANY,
            host=request.user, scheduled_at=scheduled_at,
            status=Meeting.Status.SCHEDULED,
        )
        if scheduled_at:
            messages.success(
                request,
                f"📅 '{title}' మీటింగ్ {scheduled_at:%d %b %Y, %I:%M %p} కి షెడ్యూల్ అయ్యింది. లింక్ కింద కనిపిస్తుంది.",
            )
            return redirect(redirect_name)
        return redirect("meetings:room", room_code=meeting.room_code)


class _MeetingListMixin(LoginRequiredMixin):
    """'🎥 Meetings' పేజీ కి కామన్ కంటెక్స్ట్ -- messaging/webmail యాప్‌లలో
    వాడిన అదే షేర్డ్-ఫీచర్ పద్ధతి (ఒక్కటే మిక్సిన్, రోల్ కి ఒక్కో
    subclass కేవలం `template_name` మాత్రమే మారుస్తుంది). ఇక్కడి
    క్వెరీలు ఏవీ రోల్ ని బట్టి మారవు (`host=user` ఏ రోల్ కైనా
    పనిచేస్తుంది) -- మార్చాల్సింది టెంప్లేట్/నావ్ మాత్రమే, అది
    role-specific wrapper (employer_meetings.html/candidate_meetings.html)
    లో ఉంటుంది."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        role, _ = _role_of(user)
        context["meetings"] = Meeting.objects.filter(
            host=user, meeting_type=Meeting.MeetingType.COMPANY, is_personal_room=False,
        )
        context["personal_room"] = Meeting.get_or_create_personal_room(host=user)
        context["room_base_url"] = self.request.build_absolute_uri("/meetings/room/")
        # Meeting share చేసేటప్పుడు "✉️ Email It" / "💬 Send via Messages"
        # లింకులు -- ఏ రోల్ అయితే ఆ రోల్ యొక్క సొంత Mail/Messages
        # పేజీకే వెళ్ళాలి (webmail/messaging రెండూ ఇప్పటికే ఒక్కో
        # రోల్‌కీ విడి URL name కలిగి ఉన్నాయి).
        context["mail_url_name"] = {
            "candidate": "webmail:candidate_mail", "employer": "webmail:employer_mail",
            "vendor": "webmail:vendor_mail",
        }.get(role, "webmail:employer_mail")
        context["messages_url_name"] = {
            "candidate": "messaging:candidate_messages", "employer": "messaging:employer_messages",
            "vendor": "messaging:vendor_messages",
        }.get(role, "messaging:employer_messages")
        return context


class MeetingListView(_MeetingListMixin, TemplateView):
    """Employer తను host చేసిన మీటింగ్‌ల జాబితా + కొత్తది క్రియేట్
    చేసే ఫారమ్."""

    template_name = "meetings/employer_meetings.html"


class CandidateMeetingListView(_MeetingListMixin, TemplateView):
    """అదే '🎥 Meetings' పేజీ, Candidate కోసం -- సొంత Personal Link,
    గ్రూప్ మీటింగ్‌లు క్రియేట్ చేసుకుని employers/friends కి BharatHub
    ID తో నేరుగా పంపుకోగలరు."""

    template_name = "meetings/candidate_meetings.html"


class StartConversationCallView(LoginRequiredMixin, View):
    """messaging చాట్ హెడర్ లోని "📹" బటన్ -- ఆ conversation కి ఒక
    Meeting క్రియేట్/రీయూజ్ చేసి, అందులో ఉన్న అందరికీ ('call.started'
    event ద్వారా, WebSocket లైవ్ గా) తెలియజేసి, నొక్కిన వ్యక్తిని
    నేరుగా రూమ్ కి పంపిస్తుంది."""

    def post(self, request, conversation_id, *args, **kwargs):
        from messaging.models import Conversation
        conversation = get_object_or_404(Conversation, pk=conversation_id)
        if not conversation.is_participant(request.user):
            raise PermissionDenied("మీరు ఈ సంభాషణలో సభ్యుడు కాదు.")

        meeting = Meeting.get_or_create_for_conversation(conversation, host=request.user)
        room_url = reverse("meetings:room", kwargs={"room_code": meeting.room_code})

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(f"chat_{conversation.pk}", {
            "type": "broadcast.event",
            "payload": {
                "type": "call.started",
                "room_code": meeting.room_code,
                "room_url": request.build_absolute_uri(room_url),
                "started_by_user_id": request.user.id,
                "started_by_name": display_name_for(request.user),
            },
        })

        # WebSocket broadcast (chat_{conversation.pk}) ఆ conversation ని
        # అప్పుడే తెరిచి ఉన్న యూజర్‌కి మాత్రమే చేరుతుంది. మిగతా వాళ్ళు
        # (వేరే పేజీలో ఉన్నా సరే -- Dashboard, Applications, ఎక్కడైనా)
        # ఇప్పుడు notify_incoming_call() ద్వారా వెంటనే ఓవర్‌లే
        # చూస్తారు (గ్లోబల్ ఛానల్, push notification permission మీద
        # ఆధారపడదు) -- push notification ని కూడా అదనపు రక్షణ గా
        # (browser tab పూర్తిగా మూసేసుంటే) అలాగే ఉంచుతున్నాం.
        absolute_room_url = request.build_absolute_uri(room_url)
        started_by_name = display_name_for(request.user)
        for other_user_id in conversation.members.exclude(pk=request.user.pk).values_list("pk", flat=True):
            notify_incoming_call(
                other_user_id, meeting=meeting,
                room_url=absolute_room_url, caller_name=started_by_name,
            )

        from messaging.tasks import send_call_push_notification
        for other_user_id in conversation.members.exclude(pk=request.user.pk).values_list("pk", flat=True):
            send_call_push_notification.delay(other_user_id, absolute_room_url, started_by_name)

        return redirect("meetings:room", room_code=meeting.room_code)


class MyPersonalRoomView(LoginRequiredMixin, View):
    """'🔗 My Personal Link' కార్డ్ -- ఈ యూజర్ యొక్క శాశ్వతమైన
    Personal Room ని (ఇంకా లేకపోతే క్రియేట్ చేసి) నేరుగా రూమ్ కి
    తీసుకెళ్తుంది. లాగిన్ అయిన ఎవరైనా (Candidate/Employer/Vendor)
    సొంత Personal Room కలిగి ఉండగలరు."""

    def get(self, request, *args, **kwargs):
        meeting = Meeting.get_or_create_personal_room(host=request.user)
        return redirect("meetings:room", room_code=meeting.room_code)


class SendMeetingLinkView(LoginRequiredMixin, View):
    """'📩 Send to a person' ఫారమ్ -- Personal Room లింక్ అయినా, ఒక
    Group Meeting లింక్ అయినా, ఒక BharatHub ID ఇచ్చి నేరుగా ఆ
    వ్యక్తికి పంపొచ్చు (Candidate/Employer/Vendor ఎవరికైనా, ఎవరి
    ID నైనా -- find_user_by_bharathub_id మూడు రకాల ID ఫార్మాట్‌లనీ
    గుర్తిస్తుంది). పంపగానే notify_incoming_call() ద్వారా వాళ్ళ
    స్క్రీన్ పైన (ఏ పేజీలో ఉన్నా) వెంటనే ఓవర్‌లే కనిపిస్తుంది --
    ఆఫ్‌లైన్ అయితే push notification fallback."""

    def post(self, request, *args, **kwargs):
        redirect_name = _meeting_list_redirect_name(request.user)
        room_code = request.POST.get("room_code", "").strip()
        bh_id = request.POST.get("bharathub_id", "").strip()
        meeting = get_object_or_404(Meeting, room_code=room_code, host=request.user)

        recipient = find_user_by_bharathub_id(bh_id)
        if recipient is None:
            messages.error(request, f"⚠️ '{bh_id}' కి సరిపోలిన BharatHub ఖాతా కనిపించలేదు.")
            return redirect(redirect_name)
        if recipient.pk == request.user.pk:
            messages.error(request, "⚠️ మీకు మీరే లింక్ పంపలేరు.")
            return redirect(redirect_name)

        room_url = request.build_absolute_uri(reverse("meetings:room", kwargs={"room_code": meeting.room_code}))
        caller_name = display_name_for(request.user)
        notify_incoming_call(recipient.pk, meeting=meeting, room_url=room_url, caller_name=caller_name)

        from messaging.tasks import send_call_push_notification
        send_call_push_notification.delay(recipient.pk, room_url, caller_name)

        messages.success(request, f"📩 Meeting link sent! (Room: {room_url})")
        return redirect(redirect_name)
