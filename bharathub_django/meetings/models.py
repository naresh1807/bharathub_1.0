import secrets

from django.conf import settings
from django.db import models

from .utils import display_name_for

# ============================================================================
# meetings/models.py
#
# ఎందుకు ఈ యాప్ కావాలి: మనం నిజంగా వీడియో కాల్ చేయడానికి ఏ డేటా
# (Zoom/Meet లాంటి third-party API కీలు) లేదు కాబట్టి, సొంతంగా ఒక
# WebRTC-ఆధారిత మీటింగ్ రూమ్ ని బిల్డ్ చేశాం (browser-to-browser వీడియో/
# ఆడియో, Django Channels ద్వారా సిగ్నలింగ్ మాత్రమే -- ఆడియో/వీడియో
# డేటా ఎప్పుడూ మన సర్వర్ గుండా వెళ్ళదు, peer-to-peer గానే వెళ్తుంది).
#
# ఈ Meeting మూడు చోట్ల నుండి ట్రిగ్గర్ అవుతుంది:
#   1. Interview: employer ఒక candidate తో "Schedule Interview" లో
#      Mode=Video ఎంచుకుంటే (jobs/views.py::ScheduleInterviewView),
#      ఆటోమేటిక్‌గా ఒక Meeting క్రియేట్ అయ్యి, దాని లింకే
#      interview_location గా సేవ్ అవుతుంది.
#   2. Messaging: ఏ చాట్ (1-1 లేదా గ్రూప్) లోనైనా "📹" బటన్ నొక్కితే
#      (messaging/_messages_body.html), ఆ conversation కి ఒక Meeting.
#   3. Company Meetings: Employer dashboard లోని "🎥 Meetings" నుండి
#      ఎప్పుడైనా ఒక ఇన్‌స్టంట్/షెడ్యూల్డ్ టీమ్ మీటింగ్ క్రియేట్
#      చేసుకోవచ్చు (host = ఆ employer), దాని లింక్ ని ఎవరికైనా షేర్
#      చేసుకోవచ్చు.
# ============================================================================


def _generate_room_code():
    # Zoom తరహా "123-4567-8901" కాకుండా, URL-friendly చిన్న కోడ్
    # (ఉదా: "bh-x7k9m2q4") -- ఊహించడం కష్టం (secrets.token_urlsafe),
    # ఎవరైనా బయటి వ్యక్తి కోడ్ ని guess చేసి మీటింగ్ లోకి రాకుండా.
    return "bh-" + secrets.token_urlsafe(8).replace("_", "").replace("-", "")[:11].lower()


class Meeting(models.Model):

    class MeetingType(models.TextChoices):
        INTERVIEW = "interview", "📅 Job Interview"
        COMPANY = "company", "🏢 Company Meeting"
        CHAT_CALL = "chat_call", "💬 Chat Video Call"

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        LIVE = "live", "Live"
        ENDED = "ended", "Ended"

    room_code = models.SlugField(max_length=32, unique=True, default=_generate_room_code, editable=False)
    title = models.CharField(max_length=150, default="Video Meeting")
    meeting_type = models.CharField(max_length=15, choices=MeetingType.choices, default=MeetingType.COMPANY)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.SCHEDULED)
    # Personal Meeting Room -- ప్రతి యూజర్ కి ఎప్పటికీ ఒకటే permanent
    # లింక్ (Zoom యొక్క "Personal Meeting ID" తరహాలో). ఒక్కో host కి
    # is_personal_room=True ఉన్న Meeting ఒక్కటే ఉంటుంది
    # (get_or_create_personal_room చూడండి) -- ప్రతిసారీ కొత్త లింక్
    # జనరేట్ చేసుకునే అవసరం లేకుండా, ఎప్పుడైనా షేర్ చేసుకోవడానికి.
    # "Group Link" కి విరుద్ధంగా -- అది StartInstantMeetingView తో
    # ప్రతిసారీ కొత్తగా క్రియేట్ అవుతుంది (is_personal_room=False).
    is_personal_room = models.BooleanField(default=False)

    host = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="hosted_meetings",
    )

    # Interview మీటింగ్‌లకి మాత్రమే -- ఏ JobApplication కోసమో.
    job_application = models.ForeignKey(
        "jobs.JobApplication", on_delete=models.CASCADE, null=True, blank=True,
        related_name="meetings",
    )
    # Chat-call మీటింగ్‌లకి మాత్రమే -- ఏ Conversation నుండి మొదలైందో.
    conversation = models.ForeignKey(
        "messaging.Conversation", on_delete=models.CASCADE, null=True, blank=True,
        related_name="meetings",
    )

    scheduled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.room_code})"

    def is_participant_allowed(self, user):
        """ఈ యూజర్ ఈ మీటింగ్ రూమ్ లోకి రావొచ్చా అని చెక్ చేస్తుంది --
        host, లేదా (interview అయితే) candidate/employer ఇద్దరిలో ఒకరు,
        లేదా (chat call అయితే) ఆ conversation సభ్యుడు అయ్యుండాలి."""
        if not getattr(user, "is_authenticated", False):
            return False
        if self.host_id == user.id:
            return True
        if self.meeting_type == self.MeetingType.INTERVIEW and self.job_application_id:
            app = self.job_application
            if app.candidate.user_id == user.id:
                return True
            if app.job.employer.user_id == user.id:
                return True
            return False
        if self.meeting_type == self.MeetingType.CHAT_CALL and self.conversation_id:
            return self.conversation.is_participant(user)
        # COMPANY మీటింగ్‌లు: host కాకుండా ఇతరులు కూడా join
        # అవ్వాలంటే వాళ్ళకి లింక్/కోడ్ తెలిసుండాలి (secrets.token_urlsafe
        # తో guess చేయడం అసాధ్యం అనేదే ఇక్కడ యాక్సెస్ కంట్రోల్) --
        # లాగిన్ అయిన ఎవరైనా (employee/employer/vendor) join అవ్వొచ్చు.
        return True

    @classmethod
    def get_or_create_for_application(cls, application, host):
        existing = application.meetings.filter(
            meeting_type=cls.MeetingType.INTERVIEW,
        ).order_by("-created_at").first()
        if existing:
            return existing
        return cls.objects.create(
            title=f"Interview: {application.job.title}",
            meeting_type=cls.MeetingType.INTERVIEW,
            host=host,
            job_application=application,
            scheduled_at=application.interview_datetime,
            status=cls.Status.SCHEDULED,
        )

    @classmethod
    def get_or_create_for_conversation(cls, conversation, host):
        existing = conversation.meetings.filter(
            meeting_type=cls.MeetingType.CHAT_CALL, status__in=[cls.Status.SCHEDULED, cls.Status.LIVE],
        ).order_by("-created_at").first()
        if existing:
            return existing
        title = conversation.name if conversation.chat_type == conversation.ChatType.GROUP else "Video Call"
        return cls.objects.create(
            title=title, meeting_type=cls.MeetingType.CHAT_CALL,
            host=host, conversation=conversation, status=cls.Status.LIVE,
        )

    @classmethod
    def get_or_create_personal_room(cls, host):
        """ఈ యూజర్ యొక్క శాశ్వతమైన Personal Meeting Room -- ఒక్కసారి
        క్రియేట్ అయితే, ఆ లింకే ఎప్పటికీ చెల్లుబాటు అవుతుంది (Group
        Meeting లింక్‌ల లాగా ప్రతిసారీ కొత్తది కాదు)."""
        existing = cls.objects.filter(host=host, is_personal_room=True).first()
        if existing:
            return existing
        return cls.objects.create(
            title=f"{display_name_for(host)}'s Personal Room",
            meeting_type=cls.MeetingType.COMPANY,
            host=host, is_personal_room=True, status=cls.Status.SCHEDULED,
        )


class MeetingParticipant(models.Model):
    """ఎవరు ఎప్పుడు ఈ మీటింగ్ లో join అయ్యారు/వెళ్ళిపోయారు -- ఒక
    సాధారణ 'attendance log' (Zoom యొక్క participant history లాగా)."""

    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name="participant_logs")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="meeting_logs")
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["joined_at"]

    def __str__(self):
        return f"{self.user} in {self.meeting} @ {self.joined_at:%d %b %H:%M}"
