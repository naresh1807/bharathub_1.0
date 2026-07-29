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
from .utils import display_name_for

# ============================================================================
# meetings/views.py
# ============================================================================


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
    """Employer dashboard లోని "🎥 Meetings" పేజీ నుండి -- కంపెనీ
    మీటింగ్ (instant లేదా షెడ్యూల్డ్) క్రియేట్ చేయడానికి. Employer
    ఖాతాలకి మాత్రమే (host అవ్వాలంటే)."""

    login_url = "accounts:employer_login"

    def post(self, request, *args, **kwargs):
        if not hasattr(request.user, "employer_profile"):
            raise PermissionDenied("కంపెనీ మీటింగ్ క్రియేట్ చేయడం Employer ఖాతాలకి మాత్రమే.")
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
            return redirect("meetings:meeting_list")
        return redirect("meetings:room", room_code=meeting.room_code)


class MeetingListView(LoginRequiredMixin, TemplateView):
    """Employer తను host చేసిన మీటింగ్‌ల జాబితా + కొత్తది
    క్రియేట్ చేసే ఫారమ్."""

    template_name = "meetings/meeting_list.html"
    login_url = "accounts:employer_login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not hasattr(self.request.user, "employer_profile"):
            raise PermissionDenied("ఈ పేజీ Employer ఖాతాలకి మాత్రమే.")
        context["meetings"] = Meeting.objects.filter(
            host=self.request.user, meeting_type=Meeting.MeetingType.COMPANY,
        )
        context["room_base_url"] = self.request.build_absolute_uri("/meetings/room/")
        return context


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
        return redirect("meetings:room", room_code=meeting.room_code)
