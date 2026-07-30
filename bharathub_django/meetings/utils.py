def display_name_for(user):
    """మీటింగ్ రూమ్ లో (participant tiles, in-room chat) చూపించడానికి
    ఈ యూజర్ పేరు -- Candidate/Employer/Vendor ఏ రోల్ అయినా సరైన పేరు
    వచ్చేలా (messaging/permissions.py::_role_of లో వాడిన అదే
    ప్రొఫైల్ attribute లు)."""
    if hasattr(user, "employer_profile"):
        return user.employer_profile.company_name
    if hasattr(user, "vendor_profile"):
        return user.vendor_profile.shop_name
    return user.get_full_name() or user.username


def find_user_by_bharathub_id(bh_id):
    """'📩 Send to a person' ఫారమ్ లో ఇచ్చిన BharatHub ID (Candidate/
    Employer/Vendor -- మూడు రకాల ID ఫార్మాట్‌లలో ఏదైనా) కి సంబంధించిన
    User ని వెతుకుతుంది. దేనితోనూ మ్యాచ్ కాకపోతే None.
    ఖచ్చితమైన మ్యాచ్ మాత్రమే (__iexact) -- partial search allow
    చేయం, అది enumeration ముప్పు (employers/views.py::CandidateSearchView
    లో వాడిన అదే జాగ్రత్త)."""
    bh_id = (bh_id or "").strip()
    if not bh_id:
        return None

    from accounts.models import EmployeeProfile, EmployerProfile
    from vendor.models import VendorProfile

    employee = EmployeeProfile.objects.filter(bharathub_id__iexact=bh_id).select_related("user").first()
    if employee:
        return employee.user
    employer = EmployerProfile.objects.filter(employer_id__iexact=bh_id).select_related("user").first()
    if employer:
        return employer.user
    vendor = VendorProfile.objects.filter(vendor_id__iexact=bh_id).select_related("user").first()
    if vendor:
        return vendor.user
    return None


def notify_incoming_call(recipient_user_id, *, meeting, room_url, caller_name):
    """ఏ పేజీలో ఉన్నా సరే, ఆ యూజర్ తెరిచున్న ప్రతి ట్యాబ్ లోనూ
    'incoming call' ఓవర్‌లే వెంటనే కనిపించేలా చేసే హెల్పర్ --
    meetings/consumers.py::IncomingCallConsumer లోని f"user_{id}"
    గ్రూప్ కి పంపిస్తుంది (dashboard_base.html లో ప్రతి పేజీలోనూ
    incoming_call.js ఆటోమేటిక్‌గా కనెక్ట్ అయ్యి ఉంటుంది).
    StartConversationCallView మరియు SendMeetingLinkView రెండూ ఇదే
    వాడతాయి."""
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    async_to_sync(channel_layer.group_send)(f"user_{recipient_user_id}", {
        "type": "broadcast.event",
        "payload": {
            "type": "incoming_call",
            "room_code": meeting.room_code,
            "room_url": room_url,
            "meeting_title": meeting.title,
            "caller_name": caller_name,
        },
    })
